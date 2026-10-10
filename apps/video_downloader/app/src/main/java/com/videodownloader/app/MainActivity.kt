package com.videodownloader.app

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.app.DownloadManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.webkit.CookieManager
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.BaseAdapter
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.ListView
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Collections
import java.util.concurrent.Executors

class MainActivity : Activity() {

    private lateinit var urlInput: EditText
    private lateinit var scanButton: Button
    private lateinit var progress: ProgressBar
    private lateinit var status: TextView
    private lateinit var list: ListView
    private lateinit var selectAllButton: Button
    private lateinit var downloadButton: Button
    private lateinit var scanner: WebView

    private val main = Handler(Looper.getMainLooper())
    private val sizeLoader = Executors.newFixedThreadPool(4)

    private val videos = mutableListOf<Video>()
    private val selected = mutableSetOf<Int>()
    private val adapter = VideoAdapter()

    /** Every new scan bumps this, so late callbacks from an old page are ignored. */
    private var scanId = 0
    private var scanning = false
    private var pageUrl = ""
    private val requested: MutableSet<String> = Collections.synchronizedSet(LinkedHashSet())
    private var pendingDownload: List<Video> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        urlInput = findViewById(R.id.urlInput)
        scanButton = findViewById(R.id.scanButton)
        progress = findViewById(R.id.progress)
        status = findViewById(R.id.status)
        list = findViewById(R.id.videoList)
        selectAllButton = findViewById(R.id.selectAllButton)
        downloadButton = findViewById(R.id.downloadButton)
        scanner = findViewById(R.id.scanner)

        list.adapter = adapter
        list.setOnItemClickListener { _, _, position, _ ->
            if (!selected.remove(position)) selected += position
            refreshButtons()
        }
        scanButton.setOnClickListener { startScan() }
        urlInput.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_GO) { startScan(); true } else false
        }
        selectAllButton.setOnClickListener {
            if (selected.size == videos.size) selected.clear() else selected.addAll(videos.indices)
            refreshButtons()
        }
        downloadButton.setOnClickListener { download(selected.sorted().map { videos[it] }) }

        setUpScanner()
        urlInput.setText(getPreferences(MODE_PRIVATE).getString("lastUrl", ""))
        handleShare(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleShare(intent)
    }

    override fun onDestroy() {
        sizeLoader.shutdownNow()
        scanner.destroy()
        super.onDestroy()
    }

    /** A link shared from the browser fills the field and starts the search at once. */
    private fun handleShare(intent: Intent?) {
        if (intent?.action != Intent.ACTION_SEND) return
        val url = VideoFinder.firstUrl(intent.getStringExtra(Intent.EXTRA_TEXT) ?: return) ?: return
        urlInput.setText(url)
        startScan()
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setUpScanner() {
        scanner.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            loadsImagesAutomatically = false
            mediaPlaybackRequiresUserGesture = true
        }
        CookieManager.getInstance().setAcceptCookie(true)
        CookieManager.getInstance().setAcceptThirdPartyCookies(scanner, true)

        scanner.webViewClient = object : WebViewClient() {
            // Runs on a background thread: remember everything the page loads, videos among it.
            override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? {
                requested += request.url.toString()
                return null
            }

            override fun onPageStarted(view: WebView, url: String, favicon: Bitmap?) {
                if (url != "about:blank") pageUrl = url
            }

            override fun onPageFinished(view: WebView, url: String) {
                if (!scanning || url == "about:blank") return
                val id = scanId
                // Give the page's scripts a moment to insert players after loading.
                main.postDelayed({ if (id == scanId) collect() }, 2500)
            }

            override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
                if (!request.isForMainFrame || !scanning) return
                finishScan(null, error.description.toString())
            }
        }
    }

    private fun startScan() {
        var url = urlInput.text.toString().trim()
        if (url.isEmpty()) { toast(getString(R.string.bad_url)); return }
        if (!url.startsWith("http://", true) && !url.startsWith("https://", true)) url = "https://$url"
        if (Uri.parse(url).host.isNullOrEmpty()) { toast(getString(R.string.bad_url)); return }
        urlInput.setText(url)
        getPreferences(MODE_PRIVATE).edit().putString("lastUrl", url).apply()
        (getSystemService(INPUT_METHOD_SERVICE) as InputMethodManager).hideSoftInputFromWindow(urlInput.windowToken, 0)

        scanId++
        scanning = true
        pageUrl = url
        requested.clear()
        videos.clear()
        selected.clear()
        adapter.notifyDataSetChanged()
        progress.visibility = View.VISIBLE
        scanButton.isEnabled = false
        status.text = getString(R.string.status_loading)
        refreshButtons()

        scanner.stopLoading()
        scanner.loadUrl(url)
        // Some pages never finish loading (endless ads, streams) — look at what is there after 25 s.
        val id = scanId
        main.postDelayed({ if (id == scanId && scanning) collect() }, 25_000)
    }

    /** Asks the page for its video tags and rendered HTML, then builds the list. */
    private fun collect() {
        if (!scanning) return
        val id = scanId
        scanner.evaluateJavascript(COLLECT_JS) { raw ->
            if (id != scanId || !scanning) return@evaluateJavascript
            try {
                // evaluateJavascript returns a JSON-encoded string holding our JSON.
                val json = JSONObject(JSONArray("[$raw]").getString(0))
                val items = json.getJSONArray("items")
                val tagged = (0 until items.length()).map {
                    val pair = items.getJSONArray(it)
                    pair.getString(0) to pair.getString(1)
                }
                val result = VideoFinder.collect(tagged, requested.toList(), json.optString("html"))
                finishScan(result, null)
            } catch (e: Exception) {
                val result = VideoFinder.collect(emptyList(), requested.toList(), "")
                finishScan(result, null)
            }
        }
    }

    private fun finishScan(result: ScanResult?, error: String?) {
        scanning = false
        scanId++
        scanner.stopLoading()
        scanner.loadUrl("about:blank")
        progress.visibility = View.GONE
        scanButton.isEnabled = true

        if (result == null) {
            status.text = getString(R.string.status_error, error ?: "")
            refreshButtons()
            return
        }
        videos.addAll(result.videos)
        selected.clear()
        var text = if (videos.isEmpty()) getString(R.string.status_none)
        else getString(R.string.status_found, videos.size)
        if (result.streams.isNotEmpty()) text += "\n" + getString(R.string.status_streams, result.streams.size)
        status.text = text
        refreshButtons()
        loadSizes()
    }

    /** Asks the server for each file's size and type (HEAD request) to show next to it. */
    private fun loadSizes() {
        val id = scanId
        val headers = requestHeaders()
        videos.toList().forEach { video ->
            sizeLoader.execute {
                try {
                    val conn = URL(video.url).openConnection() as HttpURLConnection
                    conn.requestMethod = "HEAD"
                    conn.connectTimeout = 10_000
                    conn.readTimeout = 10_000
                    conn.instanceFollowRedirects = true
                    headers(video.url).forEach { (k, v) -> conn.setRequestProperty(k, v) }
                    if (conn.responseCode in 200..299) {
                        val size = conn.contentLengthLong
                        val mime = conn.contentType ?: ""
                        main.post {
                            if (id != scanId) return@post
                            video.size = size
                            video.mime = mime
                            adapter.notifyDataSetChanged()
                        }
                    }
                    conn.disconnect()
                } catch (_: Exception) {
                }
            }
        }
    }

    /** Headers that make the file server treat us like the page did (some sites check them). */
    private fun requestHeaders(): (String) -> Map<String, String> {
        val agent = scanner.settings.userAgentString
        val referer = pageUrl
        return { url ->
            val map = mutableMapOf("User-Agent" to agent, "Referer" to referer)
            CookieManager.getInstance().getCookie(url)?.let { map["Cookie"] = it }
            map
        }
    }

    private fun download(chosen: List<Video>) {
        if (chosen.isEmpty()) return
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q &&
            checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED
        ) {
            pendingDownload = chosen
            requestPermissions(arrayOf(Manifest.permission.WRITE_EXTERNAL_STORAGE), REQUEST_STORAGE)
            return
        }
        val manager = getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
        val headers = requestHeaders()
        var queued = 0
        chosen.forEach { video ->
            try {
                val name = VideoFinder.fileName(video, videos.indexOf(video))
                val request = DownloadManager.Request(Uri.parse(video.url))
                    .setTitle(name)
                    .setDescription(Uri.parse(pageUrl).host ?: "")
                    .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                    .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, "VideoDownloader/$name")
                if (video.mime.startsWith("video/")) request.setMimeType(video.mime.substringBefore(';'))
                headers(video.url).forEach { (k, v) -> request.addRequestHeader(k, v) }
                manager.enqueue(request)
                queued++
            } catch (e: Exception) {
                toast(getString(R.string.download_failed, e.message ?: e.javaClass.simpleName))
            }
        }
        if (queued > 0) {
            toast(getString(R.string.queued, queued))
            selected.clear()
            refreshButtons()
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        if (requestCode != REQUEST_STORAGE) return
        val chosen = pendingDownload
        pendingDownload = emptyList()
        if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) download(chosen)
        else toast(getString(R.string.need_permission))
    }

    private fun refreshButtons() {
        adapter.notifyDataSetChanged()
        selectAllButton.isEnabled = videos.isNotEmpty()
        selectAllButton.text = getString(
            if (videos.isNotEmpty() && selected.size == videos.size) R.string.deselect_all else R.string.select_all
        )
        downloadButton.isEnabled = selected.isNotEmpty()
        downloadButton.text =
            if (selected.isEmpty()) getString(R.string.download) else getString(R.string.download_n, selected.size)
    }

    private fun toast(text: String) = Toast.makeText(this, text, Toast.LENGTH_LONG).show()

    private inner class VideoAdapter : BaseAdapter() {
        override fun getCount() = videos.size
        override fun getItem(position: Int) = videos[position]
        override fun getItemId(position: Int) = position.toLong()

        override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
            val view = convertView ?: layoutInflater.inflate(R.layout.item_video, parent, false)
            val video = videos[position]
            view.findViewById<CheckBox>(R.id.check).isChecked = position in selected
            view.findViewById<TextView>(R.id.name).text = VideoFinder.fileName(video, position)
            val host = Uri.parse(video.url).host ?: ""
            val details = listOf(VideoFinder.humanSize(video.size), host).filter { it.isNotEmpty() }
            view.findViewById<TextView>(R.id.details).text = details.joinToString(" · ")
            return view
        }
    }

    companion object {
        private const val REQUEST_STORAGE = 1

        /** Gathers <video>/<source> addresses, direct video links and og:video tags, plus the page HTML. */
        private val COLLECT_JS = """
            (function () {
              var items = [];
              function add(u, t) { if (u) items.push([String(u), t ? String(t).trim().slice(0, 150) : '']); }
              var videoExt = /\.(mp4|webm|mkv|mov|m4v|3gp|avi|flv|ogv|wmv|mpe?g|m3u8|mpd)(\?|#|$)/i;
              document.querySelectorAll('video').forEach(function (v) {
                var t = v.getAttribute('title') || v.getAttribute('aria-label') || '';
                add(v.currentSrc, t); add(v.src, t);
                v.querySelectorAll('source').forEach(function (s) { add(s.src, t); });
              });
              document.querySelectorAll('source[src]').forEach(function (s) {
                if (/^video\//i.test(s.type || '') || videoExt.test(s.src)) add(s.src, '');
              });
              document.querySelectorAll('a[href]').forEach(function (a) {
                if (videoExt.test(a.href)) add(a.href, a.getAttribute('download') || a.textContent);
              });
              document.querySelectorAll('meta[property="og:video"],meta[property="og:video:url"],' +
                  'meta[property="og:video:secure_url"],meta[name="twitter:player:stream"]').forEach(function (m) {
                add(m.content, document.title);
              });
              return JSON.stringify({ items: items, html: document.documentElement.outerHTML });
            })();
        """.trimIndent()
    }
}
