package com.videodownloader.app

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.app.AlertDialog
import android.app.DownloadManager
import android.content.BroadcastReceiver
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.view.Menu
import android.view.MenuItem
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
import android.widget.ImageView
import android.widget.ListView
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayInputStream
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.util.Collections
import java.util.concurrent.Executors

class MainActivity : Activity() {

    private lateinit var urlInput: EditText
    private lateinit var scanButton: Button
    private lateinit var progress: ProgressBar
    private lateinit var status: TextView
    private lateinit var reportButton: Button
    private lateinit var showHiddenBox: CheckBox
    private lateinit var list: ListView
    private lateinit var selectAllButton: Button
    private lateinit var downloadButton: Button
    private lateinit var scanner: WebView

    private val main = Handler(Looper.getMainLooper())
    private val sizeLoader = Executors.newFixedThreadPool(4)

    /** Rows of the list: one per video, each with its quality variants. */
    private val groups = mutableListOf<VideoGroup>()
    private val thumbnails = Thumbnails(
        onChange = { adapter.notifyDataSetChanged() },
        onFailed = { diag?.event(it) },
    )
    /** Rows currently on screen: [groups] minus hidden ads/previews unless [showHidden]. */
    private var shown = listOf<VideoGroup>()
    private var showHidden = false
    private val selected = mutableSetOf<VideoGroup>()
    /** Ad-network requests the scanner refused to load (only for the report). */
    private val blocked: MutableSet<String> = Collections.synchronizedSet(LinkedHashSet())
    private val adapter = VideoAdapter()

    /** Every new scan bumps this, so late callbacks from an old page are ignored. */
    private var scanId = 0
    private var scanning = false
    private var pageUrl = ""
    private val requested: MutableSet<String> = Collections.synchronizedSet(LinkedHashSet())
    private var pendingDownload: List<VideoGroup> = emptyList()

    /** Report for the current scan and the downloads started from it. */
    private var diag: Diagnostics? = null
    /** Downloads still in progress: DownloadManager id → file name. Kept across restarts. */
    private val tracked = LinkedHashMap<Long, String>()
    private val reportedPauses = mutableSetOf<Long>()

    private val downloadDone = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) = checkDownloads()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        urlInput = findViewById(R.id.urlInput)
        scanButton = findViewById(R.id.scanButton)
        progress = findViewById(R.id.progress)
        status = findViewById(R.id.status)
        reportButton = findViewById(R.id.reportButton)
        showHiddenBox = findViewById(R.id.showHidden)
        list = findViewById(R.id.videoList)
        selectAllButton = findViewById(R.id.selectAllButton)
        downloadButton = findViewById(R.id.downloadButton)
        scanner = findViewById(R.id.scanner)

        list.adapter = adapter
        list.setOnItemClickListener { _, _, position, _ ->
            val group = shown[position]
            if (!selected.remove(group)) selected += group
            refreshButtons()
        }
        scanButton.setOnClickListener { startScan() }
        urlInput.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_GO) { startScan(); true } else false
        }
        selectAllButton.setOnClickListener {
            if (selected.size == shown.size) selected.clear() else selected.addAll(shown)
            refreshButtons()
        }
        downloadButton.setOnClickListener { download(shown.filter { it in selected }) }
        reportButton.setOnClickListener { showReport() }
        showHiddenBox.setOnCheckedChangeListener { _, checked ->
            showHidden = checked
            refreshList()
        }

        setUpScanner()
        loadTracked()
        val filter = IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) registerReceiver(downloadDone, filter, RECEIVER_EXPORTED)
        else registerReceiver(downloadDone, filter)

        urlInput.setText(getPreferences(MODE_PRIVATE).getString("lastUrl", ""))
        handleShare(intent)
    }

    override fun onResume() {
        super.onResume()
        checkDownloads()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleShare(intent)
    }

    override fun onDestroy() {
        unregisterReceiver(downloadDone)
        sizeLoader.shutdownNow()
        thumbnails.shutdown()
        scanner.destroy()
        super.onDestroy()
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menu.add(0, MENU_REPORT, 0, R.string.report)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        if (item.itemId != MENU_REPORT) return super.onOptionsItemSelected(item)
        showReport()
        return true
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
            // Ad networks get an empty answer: less advertising video on the page, faster scan.
            override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? {
                val url = request.url.toString()
                if (!request.isForMainFrame && ContentFilter.shouldBlock(url)) {
                    blocked += url
                    return WebResourceResponse("text/plain", "utf-8", ByteArrayInputStream(ByteArray(0)))
                }
                requested += url
                return null
            }

            override fun onPageStarted(view: WebView, url: String, favicon: Bitmap?) {
                if (url == "about:blank" || !scanning) return
                if (url != pageUrl) diag?.event("Переадресація на $url")
                pageUrl = url
                diag?.finalUrl = url
            }

            override fun onPageFinished(view: WebView, url: String) {
                if (!scanning || url == "about:blank") return
                diag?.event("Сторінка завантажилась, чекаю на скрипти 2.5 с")
                val id = scanId
                // Give the page's scripts a moment to insert players after loading.
                main.postDelayed({ if (id == scanId) collect() }, 2500)
            }

            override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
                if (!request.isForMainFrame || !scanning) return
                val text = "${error.description} (код ${error.errorCode})"
                diag?.mainError = text
                diag?.event("Помилка відкриття сторінки: $text")
                finishScan(null, error.description.toString())
            }

            override fun onReceivedHttpError(view: WebView, request: WebResourceRequest, response: WebResourceResponse) {
                if (!request.isForMainFrame || !scanning) return
                diag?.mainHttpStatus = response.statusCode
                diag?.event("Сторінка відповіла HTTP ${response.statusCode} ${response.reasonPhrase ?: ""}")
            }
        }
    }

    private fun startScan() {
        val url = VideoFinder.pageUrl(urlInput.text.toString())
        if (url == null || Uri.parse(url).host.isNullOrEmpty()) { toast(getString(R.string.bad_url)); return }
        urlInput.setText(url)
        getPreferences(MODE_PRIVATE).edit().putString("lastUrl", url).apply()
        (getSystemService(INPUT_METHOD_SERVICE) as InputMethodManager).hideSoftInputFromWindow(urlInput.windowToken, 0)

        scanId++
        scanning = true
        pageUrl = url
        requested.clear()
        blocked.clear()
        groups.clear()
        shown = emptyList()
        showHidden = false
        showHiddenBox.isChecked = false
        showHiddenBox.visibility = View.GONE
        selected.clear()
        thumbnails.clear()
        adapter.notifyDataSetChanged()
        progress.visibility = View.VISIBLE
        reportButton.visibility = View.GONE
        scanButton.isEnabled = false
        status.text = getString(R.string.status_loading)
        refreshButtons()

        diag = Diagnostics(url, environment()).also { it.event("Початок сканування $url") }
        saveReport()

        scanner.stopLoading()
        scanner.loadUrl(url)
        // Some pages never finish loading (endless ads, streams) — look at what is there after 25 s.
        val id = scanId
        main.postDelayed({
            if (id == scanId && scanning) {
                diag?.event("Сторінка не завершила завантаження за 25 с — аналізую те, що є")
                collect()
            }
        }, 25_000)
    }

    /** Asks the page for its video tags and rendered HTML, then builds the list. */
    private fun collect() {
        if (!scanning) return
        val id = scanId
        scanner.evaluateJavascript(COLLECT_JS) { raw ->
            if (id != scanId || !scanning) return@evaluateJavascript
            val d = diag
            try {
                // evaluateJavascript returns a JSON-encoded string holding our JSON.
                val json = JSONObject(JSONArray("[$raw]").getString(0))
                val items = json.getJSONArray("items")
                val tagged = (0 until items.length()).map {
                    val o = items.getJSONObject(it)
                    Tagged(
                        o.optString("u"), o.optString("t"), o.optString("g"), o.optString("q"), o.optString("p"),
                        flags = o.optString("f").split(',').filter { f -> f.isNotEmpty() }.toSet(),
                        duration = o.optDouble("d", 0.0).takeIf { d -> !d.isNaN() } ?: 0.0,
                    )
                }
                val html = json.optString("html")
                d?.page = PageInfo(
                    title = json.optString("title"),
                    videoTags = json.optInt("videoTags"),
                    blobVideos = json.optInt("blobVideos"),
                    iframes = json.optJSONArray("iframes").strings(),
                    players = json.optJSONArray("players").strings(),
                    hasPassword = json.optBoolean("password"),
                    htmlLength = html.length,
                )
                finishScan(VideoFinder.collect(tagged, requested.toList(), html, json.optString("image")), null)
            } catch (e: Exception) {
                d?.scriptFailed = true
                d?.event("Скрипт пошуку не повернув даних: ${raw?.take(100)} (${e.javaClass.simpleName})")
                finishScan(VideoFinder.collect(emptyList(), requested.toList(), ""), null)
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

        val d = diag
        val all = requested.toList()
        d?.requestCount = all.size
        d?.mediaRequests = all.filter { looksLikeMedia(it) }.distinct().take(40)
        d?.hadCookies = !CookieManager.getInstance().getCookie(pageUrl).isNullOrEmpty()
        d?.blockedRequests = blocked.toList()

        if (result == null) {
            status.text = getString(R.string.status_error, error ?: "")
            afterReportChange()
            refreshButtons()
            return
        }
        groups.addAll(result.groups)
        selected.clear()
        streamCount = result.streams.size
        d?.videos = result.videos
        d?.streams = result.streams
        d?.event("Знайдено відеофайлів: ${result.videos.size} (різних відео: ${groups.size}), " +
            "потоків: ${result.streams.size}, запитів сторінки: ${all.size}, заблоковано рекламних: ${blocked.size}")
        refreshList()
        probeVideos()
    }

    private var streamCount = 0

    /** Re-filters the list (after the scan and whenever sizes arrive) and updates the status line. */
    private fun refreshList() {
        shown = ContentFilter.visible(groups, showHidden)
        selected.retainAll(shown.toSet())
        diag?.verdicts = groups.flatMap { g ->
            g.variants.map { it.url to if (g.kind == Kind.MAIN) "" else "${kindName(g.kind)}: ${g.reason}" }
        }.toMap()

        val ads = groups.count { it.kind == Kind.AD }
        val previews = groups.count { it.kind == Kind.PREVIEW }
        val main = groups.size - ads - previews
        var text = when {
            groups.isEmpty() -> getString(R.string.status_none)
            main == 0 && !showHidden -> getString(R.string.status_only_doubtful, shown.size)
            else -> getString(R.string.status_found, if (showHidden) groups.size else main)
        }
        if (ads + previews > 0) text += "\n" + getString(R.string.status_hidden, ads, previews)
        if (streamCount > 0) text += "\n" + getString(R.string.status_streams, streamCount)
        status.text = text

        showHiddenBox.visibility = if (ads + previews > 0) View.VISIBLE else View.GONE
        showHiddenBox.text = getString(R.string.show_hidden, ads + previews)
        afterReportChange()
        refreshButtons()
    }

    private fun kindName(kind: Kind) = getString(if (kind == Kind.AD) R.string.kind_ad else R.string.kind_preview)

    private fun looksLikeMedia(url: String): Boolean {
        val ext = VideoFinder.extension(url)
        return VideoFinder.looksLikeVideoFile(url) || VideoFinder.isStream(url) || ext == "ts" || ext == "m4s" ||
            listOf("videoplayback", "/hls/", "/dash/", "manifest", "/video/").any { it in url.lowercase() }
    }

    /**
     * Asks the server for the first byte of each file: shows its size and type in the list
     * and tells early whether the server will let us download it at all.
     */
    private fun probeVideos() {
        val id = scanId
        val headers = requestHeaders()
        groups.flatMap { it.variants }.forEach { video ->
            sizeLoader.execute {
                var code = 0
                var note: String
                var size = -1L
                var mime = ""
                try {
                    val conn = URL(video.url).openConnection() as HttpURLConnection
                    conn.connectTimeout = 10_000
                    conn.readTimeout = 10_000
                    conn.instanceFollowRedirects = true
                    headers(video.url).forEach { (k, v) -> conn.setRequestProperty(k, v) }
                    conn.setRequestProperty("Range", "bytes=0-0")
                    code = conn.responseCode
                    mime = conn.contentType ?: ""
                    size = conn.getHeaderField("Content-Range")?.substringAfterLast('/')?.toLongOrNull()
                        ?: if (code == 200) conn.contentLengthLong else -1
                    note = mime
                    if (conn.url.toString() != video.url) note += ", переадресовано на ${Diagnostics.shortUrl(conn.url.toString())}"
                    if (code in 200..299 && mime.startsWith("text/html")) note += " — сервер віддає сторінку, а не відео"
                    conn.disconnect()
                } catch (e: Exception) {
                    note = "${e.javaClass.simpleName}: ${e.message}"
                }
                main.post {
                    if (id != scanId) return@post
                    if (code in 200..299) {
                        video.size = size
                        video.mime = mime
                    } else {
                        video.error = if (code == 0) getString(R.string.probe_failed) else "HTTP $code"
                    }
                    diag?.probes?.set(video.url, code to note)
                    groups.forEach { it.pickBest() }
                    // Sizes help to spot previews: a tiny clip next to a big video is not the video.
                    ContentFilter.apply(groups)
                    refreshList()
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

    private fun download(chosen: List<VideoGroup>) {
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
        chosen.forEach { group ->
            val video = group.video
            val name = VideoFinder.fileName(video, groups.indexOf(group), group.title, withQuality = group.variants.size > 1)
            try {
                val request = DownloadManager.Request(Uri.parse(video.url))
                    .setTitle(name)
                    .setDescription(Uri.parse(pageUrl).host ?: "")
                    .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                    .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, "VideoDownloader/$name")
                if (video.mime.startsWith("video/")) request.setMimeType(video.mime.substringBefore(';'))
                headers(video.url).forEach { (k, v) -> request.addRequestHeader(k, v) }
                val downloadId = manager.enqueue(request)
                tracked[downloadId] = name
                diag?.event("Скачування #$downloadId «$name» поставлено в чергу: ${Diagnostics.shortUrl(video.url)}")
                queued++
            } catch (e: Exception) {
                val why = "${e.javaClass.simpleName}: ${e.message}"
                diag?.downloadFailures?.set(name, -1 to "не вдалося поставити в чергу ($why)")
                toast(getString(R.string.download_failed, e.message ?: e.javaClass.simpleName))
            }
        }
        saveTracked()
        afterReportChange()
        if (queued > 0) {
            toast(getString(R.string.queued, queued))
            selected.clear()
            refreshButtons()
        }
    }

    /** Looks at how our downloads ended; failures and non-video results go into the report. */
    private fun checkDownloads() {
        if (tracked.isEmpty()) return
        val manager = getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
        val seen = mutableSetOf<Long>()
        val failed = mutableListOf<String>()
        manager.query(DownloadManager.Query().setFilterById(*tracked.keys.toLongArray()))?.use { c ->
            while (c.moveToNext()) {
                val id = c.getLong(c.getColumnIndexOrThrow(DownloadManager.COLUMN_ID))
                val name = tracked[id] ?: continue
                seen += id
                val state = c.getInt(c.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS))
                val reason = c.getInt(c.getColumnIndexOrThrow(DownloadManager.COLUMN_REASON))
                val total = c.getLong(c.getColumnIndexOrThrow(DownloadManager.COLUMN_TOTAL_SIZE_BYTES))
                val mime = c.getString(c.getColumnIndexOrThrow(DownloadManager.COLUMN_MEDIA_TYPE)) ?: ""
                when (state) {
                    DownloadManager.STATUS_SUCCESSFUL -> {
                        tracked.remove(id)
                        diag?.event("#$id «$name» скачано: ${VideoFinder.humanSize(total)}, тип $mime")
                        val why = when {
                            mime.startsWith("text/") -> "сервер віддав $mime (сторінку з помилкою чи захистом) замість відео"
                            total in 0 until 50_000 -> "файл підозріло малий (${VideoFinder.humanSize(total)}) — мабуть, це сторінка помилки"
                            else -> null
                        }
                        if (why != null) { diag?.suspiciousDownloads?.set(name, why); failed += name }
                    }
                    DownloadManager.STATUS_FAILED -> {
                        tracked.remove(id)
                        val text = Diagnostics.downloadFailure(reason)
                        diag?.downloadFailures?.set(name, reason to text)
                        diag?.event("#$id «$name» НЕ скачано, код $reason: $text")
                        manager.remove(id)
                        failed += name
                    }
                    DownloadManager.STATUS_PAUSED -> if (reportedPauses.add(id)) {
                        diag?.event("#$id «$name» призупинено: ${Diagnostics.downloadPause(reason)}")
                    }
                }
            }
        }
        (tracked.keys - seen).forEach { id ->
            diag?.event("#$id «${tracked[id]}» скасовано або видалено з менеджера завантажень")
            tracked.remove(id)
        }
        saveTracked()
        afterReportChange()
        if (failed.isNotEmpty()) toast(getString(R.string.download_problem, failed.joinToString()))
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        if (requestCode != REQUEST_STORAGE) return
        val chosen = pendingDownload
        pendingDownload = emptyList()
        if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) download(chosen)
        else {
            diag?.event("Користувач не дав дозволу на збереження файлів")
            toast(getString(R.string.need_permission))
        }
    }

    // --- Report ---

    private val reportFile get() = File(filesDir, "report.txt")

    /** Saves the report and shows the "send report" button when something went wrong. */
    private fun afterReportChange() {
        saveReport()
        if (diag?.hasProblem == true) reportButton.visibility = View.VISIBLE
    }

    private fun saveReport() {
        val d = diag ?: return
        try { reportFile.writeText(d.render()) } catch (_: Exception) {}
    }

    /** The latest report — from this run, or the one saved before the app was closed. */
    private fun reportText(): String? =
        diag?.render() ?: try { reportFile.takeIf { it.exists() }?.readText() } catch (_: Exception) { null }

    private fun showReport() {
        val text = reportText()
        if (text == null) { toast(getString(R.string.report_empty)); return }
        val pad = (12 * resources.displayMetrics.density).toInt()
        val view = TextView(this).apply {
            this.text = text
            setTextIsSelectable(true)
            typeface = Typeface.MONOSPACE
            textSize = 11f
            setPadding(pad, pad, pad, pad)
        }
        AlertDialog.Builder(this)
            .setTitle(R.string.report)
            .setView(ScrollView(this).apply { addView(view) })
            .setPositiveButton(R.string.report_share) { _, _ ->
                val send = Intent(Intent.ACTION_SEND).setType("text/plain")
                    .putExtra(Intent.EXTRA_SUBJECT, getString(R.string.report))
                    .putExtra(Intent.EXTRA_TEXT, text)
                startActivity(Intent.createChooser(send, getString(R.string.report_share)))
            }
            .setNeutralButton(R.string.report_copy) { _, _ ->
                (getSystemService(CLIPBOARD_SERVICE) as ClipboardManager)
                    .setPrimaryClip(ClipData.newPlainText(getString(R.string.report), text))
                toast(getString(R.string.report_copied))
            }
            .setNegativeButton(R.string.close, null)
            .show()
    }

    private fun environment(): String {
        val app = try { packageManager.getPackageInfo(packageName, 0).versionName } catch (_: Exception) { "?" }
        val webView = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            WebView.getCurrentWebViewPackage()?.versionName ?: "?" else "?"
        return "Застосунок $app · Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT}) · " +
            "${Build.MANUFACTURER} ${Build.MODEL} · WebView $webView"
    }

    private fun loadTracked() {
        val json = getPreferences(MODE_PRIVATE).getString("tracked", null) ?: return
        try {
            val obj = JSONObject(json)
            obj.keys().forEach { tracked[it.toLong()] = obj.getString(it) }
        } catch (_: Exception) {}
    }

    private fun saveTracked() {
        val obj = JSONObject()
        tracked.forEach { (id, name) -> obj.put(id.toString(), name) }
        getPreferences(MODE_PRIVATE).edit().putString("tracked", obj.toString()).apply()
    }

    private fun JSONArray?.strings(): List<String> =
        if (this == null) emptyList() else (0 until length()).map { getString(it) }

    private fun refreshButtons() {
        adapter.notifyDataSetChanged()
        selectAllButton.isEnabled = shown.isNotEmpty()
        selectAllButton.text = getString(
            if (shown.isNotEmpty() && selected.size == shown.size) R.string.deselect_all else R.string.select_all
        )
        downloadButton.isEnabled = selected.isNotEmpty()
        downloadButton.text =
            if (selected.isEmpty()) getString(R.string.download) else getString(R.string.download_n, selected.size)
    }

    private fun toast(text: String) = Toast.makeText(this, text, Toast.LENGTH_LONG).show()

    /** Short description of one quality variant: "720p · 45.2 МБ · mp4". */
    private fun variantText(video: Video, index: Int): String {
        val ext = VideoFinder.extension(video.url).ifEmpty { video.mime.substringAfter('/').substringBefore(';') }
        val parts = listOf(
            video.quality.ifEmpty { getString(R.string.variant_n, index + 1) },
            VideoFinder.humanSize(video.size),
            ext,
            video.error?.let { "⚠ $it" } ?: "",
        )
        return parts.filter { it.isNotEmpty() }.joinToString(" · ")
    }

    private fun chooseQuality(group: VideoGroup) {
        val labels = group.variants.mapIndexed { i, v -> variantText(v, i) }.toTypedArray()
        AlertDialog.Builder(this)
            .setTitle(R.string.choose_quality)
            .setSingleChoiceItems(labels, group.chosen) { dialog, which ->
                group.chosen = which
                group.userChose = true
                adapter.notifyDataSetChanged()
                dialog.dismiss()
            }
            .setNegativeButton(R.string.close, null)
            .show()
    }

    /** Big preview with the title and address, to be sure what is being downloaded. */
    private fun showPreview(group: VideoGroup, position: Int) {
        val pad = (16 * resources.displayMetrics.density).toInt()
        val box = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            setPadding(pad, pad, pad, 0)
        }
        thumbnails.get(group, requestHeaders())?.let { bmp ->
            box.addView(ImageView(this).apply {
                setImageBitmap(bmp)
                adjustViewBounds = true
                scaleType = ImageView.ScaleType.FIT_CENTER
            })
        }
        box.addView(TextView(this).apply {
            text = "${variantText(group.video, group.chosen)}\n${group.video.url}"
            setTextIsSelectable(true)
            setPadding(0, pad / 2, 0, 0)
        })
        val builder = AlertDialog.Builder(this)
            .setTitle(VideoFinder.fileName(group.video, position, group.title))
            .setView(ScrollView(this).apply { addView(box) })
            .setNegativeButton(R.string.close, null)
        if (group.kind != Kind.MAIN) {
            box.addView(TextView(this).apply { text = "🚫 ${kindName(group.kind)}: ${group.reason}" })
        }
        if (group.variants.size > 1) builder.setNeutralButton(R.string.choose_quality) { _, _ -> chooseQuality(group) }
        builder.show()
    }

    private inner class VideoAdapter : BaseAdapter() {
        override fun getCount() = shown.size
        override fun getItem(position: Int) = shown[position]
        override fun getItemId(position: Int) = position.toLong()

        override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
            val view = convertView ?: layoutInflater.inflate(R.layout.item_video, parent, false)
            val group = shown[position]
            val video = group.video
            view.findViewById<CheckBox>(R.id.check).isChecked = group in selected
            view.alpha = if (group.kind == Kind.MAIN) 1f else 0.6f

            val thumb = view.findViewById<ImageView>(R.id.thumb)
            val bitmap = thumbnails.get(group, requestHeaders())
            if (bitmap != null) {
                thumb.setImageBitmap(bitmap)
                thumb.scaleType = ImageView.ScaleType.CENTER_CROP
            } else {
                thumb.setImageResource(R.drawable.ic_video_placeholder)
                thumb.scaleType = ImageView.ScaleType.CENTER_INSIDE
            }
            thumb.setOnClickListener { showPreview(group, position) }

            view.findViewById<TextView>(R.id.name).text = VideoFinder.fileName(video, position, group.title)
            val host = Uri.parse(video.url).host ?: ""
            val single = if (group.variants.size == 1) variantText(video, 0) else ""
            val verdict = if (group.kind == Kind.MAIN) "" else "🚫 ${kindName(group.kind)}: ${group.reason}"
            view.findViewById<TextView>(R.id.details).text =
                listOf(verdict, single, host).filter { it.isNotEmpty() }.joinToString(" · ")

            val quality = view.findViewById<Button>(R.id.quality)
            if (group.variants.size > 1) {
                quality.visibility = View.VISIBLE
                quality.text = getString(R.string.quality_button, variantText(video, group.chosen), group.variants.size)
                quality.setOnClickListener { chooseQuality(group) }
            } else {
                quality.visibility = View.GONE
            }
            return view
        }
    }

    companion object {
        private const val REQUEST_STORAGE = 1
        private const val MENU_REPORT = 1

        /**
         * Gathers <video>/<source> addresses, direct video links and og:video tags, plus the page HTML
         * and a few facts for the diagnostic report (blob players, iframes, known player scripts, login form).
         */
        private val COLLECT_JS = """
            (function () {
              var items = [], groupNo = 0;
              function abs(u) { try { return u ? new URL(u, location.href).href : ''; } catch (e) { return ''; } }
              function add(u, t, g, q, p, f, d) {
                if (u) items.push({ u: String(u), t: t ? String(t).trim().slice(0, 150) : '', g: g || '',
                                    q: q ? String(q) : '', p: abs(p), f: f || '', d: d || 0 });
              }
              // Preview picture next to a link: climb a few levels while the block holds a single image.
              function imgNear(el) {
                for (var i = 0; i < 4 && el; i++, el = el.parentElement) {
                  var imgs = el.querySelectorAll('img');
                  if (imgs.length > 1) return '';
                  if (imgs.length === 1) {
                    var im = imgs[0];
                    return im.getAttribute('data-src') || im.getAttribute('data-original') || im.currentSrc || im.src;
                  }
                }
                return '';
              }
              function sourceQuality(s) {
                return s.getAttribute('label') || s.getAttribute('res') || s.getAttribute('size') ||
                    s.getAttribute('data-quality') || s.getAttribute('data-res') || s.getAttribute('title') || '';
              }
              var ogImage = (document.querySelector('meta[property="og:image"],meta[name="twitter:image"]') || {}).content || '';
              var videoExt = /\.(mp4|webm|mkv|mov|m4v|3gp|avi|flv|ogv|wmv|mpe?g|m3u8|mpd)(\?|#|$)/i;
              var videos = document.querySelectorAll('video'), blobs = 0;
              var here = location.href.split('#')[0];
              var adBox = /(^|[\s_-])(ads?|advert|advertisement|adv|banner|sponsor|sponsored|preroll|ad-container|adslot)([\s_-]|$)/i;
              // Hints for telling the real video from ads and from previews of other videos.
              function flagsOf(v) {
                var f = [], a = v.closest('a[href]');
                if (a && a.href.split('#')[0] !== here && !videoExt.test(a.href)) f.push('link');
                if (v.loop && v.muted && !v.controls) f.push('loop');
                for (var el = v, i = 0; el && i < 6; el = el.parentElement, i++) {
                  if (adBox.test((el.id || '') + ' ' + (typeof el.className === 'string' ? el.className : ''))) { f.push('adbox'); break; }
                }
                return f.join(',');
              }
              videos.forEach(function (v) {
                var t = v.getAttribute('title') || v.getAttribute('aria-label') || '';
                var g = 'v' + (groupNo++), poster = v.getAttribute('poster') || '';
                var f = flagsOf(v), d = isFinite(v.duration) ? v.duration : 0;
                if (/^blob:/.test(v.currentSrc || v.src || '')) blobs++;
                v.querySelectorAll('source').forEach(function (s) { add(s.src, t, g, sourceQuality(s), poster, f, d); });
                add(v.currentSrc, t, g, '', poster, f, d); add(v.src, t, g, '', poster, f, d);
              });
              document.querySelectorAll('source[src]').forEach(function (s) {
                if (/^video\//i.test(s.type || '') || videoExt.test(s.src)) add(s.src, '', '', sourceQuality(s), '');
              });
              document.querySelectorAll('a[href]').forEach(function (a) {
                if (videoExt.test(a.href)) add(a.href, a.getAttribute('download') || a.textContent, '', '', imgNear(a));
              });
              document.querySelectorAll('meta[property="og:video"],meta[property="og:video:url"],' +
                  'meta[property="og:video:secure_url"],meta[name="twitter:player:stream"]').forEach(function (m) {
                add(m.content, document.title, '', '', ogImage);
              });
              var iframes = [];
              document.querySelectorAll('iframe[src]').forEach(function (f) {
                if (/^https?:/.test(f.src) && iframes.length < 10) iframes.push(f.src);
              });
              var players = [], known = ['hls', 'dash', 'shaka', 'jwplayer', 'video.js', 'videojs', 'plyr',
                  'flowplayer', 'vimeo', 'youtube', 'kaltura', 'brightcove', 'clappr', 'playerjs'];
              document.querySelectorAll('script[src]').forEach(function (s) {
                var src = s.src.toLowerCase();
                known.forEach(function (k) { if (src.indexOf(k) >= 0 && players.indexOf(k) < 0) players.push(k); });
              });
              return JSON.stringify({
                items: items, html: document.documentElement.outerHTML, title: document.title, image: abs(ogImage),
                videoTags: videos.length, blobVideos: blobs, iframes: iframes, players: players,
                password: !!document.querySelector('input[type=password]')
              });
            })();
        """.trimIndent()
    }
}
