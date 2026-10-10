package com.videodownloader.app

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.app.AlertDialog
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.os.Bundle
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
    private val thumbnails by lazy {
        Thumbnails(
            cacheDir,
        onChange = { adapter.notifyDataSetChanged() },
            onFailed = { diag?.event(it) },
        )
    }
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
    /** Row last tapped — a long press then selects everything between it and the pressed row. */
    private var anchor = -1

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
            anchor = position
            refreshButtons()
        }
        list.setOnItemLongClickListener { _, _, position, _ ->
            val from = if (anchor in shown.indices) anchor else 0
            val range = minOf(from, position)..maxOf(from, position)
            selected.addAll(shown.slice(range))
            anchor = position
            toast(getString(R.string.range_selected, range.first + 1, range.last + 1))
            refreshButtons()
            true
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
        DownloadService.listener = { name, text, outcome ->
            diag?.event(text)
            when (outcome) {
                DownloadService.FAILED -> diag?.downloadFailures?.set(name, -2 to text)
                DownloadService.WARNING -> diag?.suspiciousDownloads?.set(name, text)
            }
            afterReportChange()
        }
        // Continue a queue left from before the app was closed.
        DownloadService.start(this)

        urlInput.setText(getPreferences(MODE_PRIVATE).getString("lastUrl", ""))
        handleShare(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleShare(intent)
    }

    override fun onDestroy() {
        DownloadService.listener = null
        sizeLoader.shutdownNow()
        thumbnails.shutdown()
        scanner.destroy()
        super.onDestroy()
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menu.add(0, MENU_QUEUE, 0, R.string.queue_menu).setShowAsAction(MenuItem.SHOW_AS_ACTION_ALWAYS)
        menu.add(0, MENU_REPORT, 1, R.string.report)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        when (item.itemId) {
            MENU_REPORT -> showReport()
            MENU_QUEUE -> startActivity(Intent(this, QueueActivity::class.java))
            else -> return super.onOptionsItemSelected(item)
        }
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
                    title = json.optString("title").also { pageTitle = it },
                    videoTags = json.optInt("videoTags"),
                    blobVideos = json.optInt("blobVideos"),
                    iframes = json.optJSONArray("iframes").strings(),
                    players = json.optJSONArray("players").strings(),
                    hasPassword = json.optBoolean("password"),
                    htmlLength = html.length,
                )
                pageImage = json.optString("image")
                finishScan(VideoFinder.collect(tagged, requested.toList(), html, pageImage), null)
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
        streamCount = 0
        d?.videos = result.videos
        d?.streams = result.streams
        d?.event("Знайдено відеофайлів: ${result.videos.size} (різних відео: ${groups.size}), " +
            "потоків: ${result.streams.size}, запитів сторінки: ${all.size}, заблоковано рекламних: ${blocked.size}")
        refreshList()
        probeVideos()
        analyzeStreams(result.streams)
    }

    /** Streams that could not be turned into downloadable videos (DASH, unreadable playlists). */
    private var streamCount = 0
    private var pageTitle = ""
    private var pageImage = ""

    /** Reads the HLS playlists found on the page and adds them to the list as downloadable videos. */
    private fun analyzeStreams(streams: List<String>) {
        val playlists = streams.filter { VideoFinder.extension(it) == "m3u8" }.take(12)
        streamCount = streams.size - playlists.size
        if (playlists.isEmpty()) return
        val id = scanId
        val headers = requestHeaders()
        progress.visibility = View.VISIBLE
        diag?.event("Аналізую HLS-плейлисти: ${playlists.size}")
        sizeLoader.execute {
            val loaded = playlists.map { url -> url to runCatching { Hls.load(url, headers(url)) } }
            main.post {
                if (id != scanId) return@post
                progress.visibility = View.GONE
                addHlsGroups(loaded)
            }
        }
    }

    private fun addHlsGroups(loaded: List<Pair<String, Result<Hls.Loaded>>>) {
        // Qualities already listed inside a master playlist are not shown again on their own.
        val insideMasters = loaded.mapNotNull { it.second.getOrNull() }.filter { it.isMaster }
            .flatMap { l -> l.variants.mapNotNull { it.info?.url } }.toSet()
        val added = mutableListOf<VideoGroup>()
        loaded.forEach { (url, result) ->
            val l = result.getOrElse { e ->
                diag?.hlsNotes?.add("${Diagnostics.shortUrl(url)}: не прочитано — ${e.message ?: e.javaClass.simpleName}")
                streamCount++
                return@forEach
            }
            if (!l.isMaster && url in insideMasters) return@forEach
            val videos = l.variants.mapNotNull { v ->
                val media = v.media
                val address = media?.url ?: v.info?.url ?: return@mapNotNull null
                val bandwidth = v.info?.bandwidth ?: 0
                Video(
                    url = address,
                    title = pageTitle,
                    size = if (bandwidth > 0 && media != null) (bandwidth * media.duration / 8).toLong() else -1,
                    mime = "application/x-mpegURL",
                    quality = v.info?.label ?: "",
                    duration = media?.duration ?: 0.0,
                ).apply {
                    hls = media
                    audioUrl = v.info?.audioUrl
                    blocker = v.error?.let { "плейлист якості не прочитано: $it" } ?: media?.problem
                    if (blocker != null) error = when {
                        media?.encryption != null -> getString(R.string.hls_encrypted)
                        media?.live == true -> getString(R.string.hls_live)
                        else -> getString(R.string.probe_failed)
                    }
                }
            }
            if (videos.isEmpty()) return@forEach
            added += VideoGroup(videos)
            val first = videos.first()
            diag?.hlsNotes?.add(
                "${Diagnostics.shortUrl(url)}: ${if (l.isMaster) "головний плейлист, якостей ${videos.size}" else "плейлист"}, " +
                    "${first.duration.toInt()} с" + (first.blocker?.let { " — $it" } ?: "")
            )
        }
        if (added.isEmpty()) { refreshList(); return }
        groups.addAll(added)
        if (groups.size == 1 && groups[0].poster.isEmpty() && pageImage.isNotEmpty()) groups[0].poster = pageImage
        ContentFilter.apply(groups)
        diag?.videos = (diag?.videos ?: emptyList()) + added.flatMap { it.variants }
        diag?.event("Додано HLS-відео: ${added.size}")
        refreshList()
    }

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

    /** Asks which sub-folder to use, then puts the chosen videos into the download queue. */
    private fun download(chosen: List<VideoGroup>) {
        if (chosen.isEmpty()) return
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q &&
            checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED
        ) {
            pendingDownload = chosen
            requestPermissions(arrayOf(Manifest.permission.WRITE_EXTERNAL_STORAGE), REQUEST_STORAGE)
            return
        }
        val suggested = VideoFinder.folderName(pageTitle).ifEmpty { VideoFinder.folderName(Uri.parse(pageUrl).host ?: "") }
        val pad = (20 * resources.displayMetrics.density).toInt()
        val input = EditText(this).apply {
            setText(suggested)
            setSingleLine()
            setSelectAllOnFocus(true)
        }
        val box = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            setPadding(pad, pad / 2, pad, 0)
            addView(TextView(this@MainActivity).apply { setText(R.string.folder_message) })
            addView(input)
        }
        AlertDialog.Builder(this)
            .setTitle(getString(R.string.folder_title, chosen.size))
            .setView(box)
            .setPositiveButton(R.string.folder_add) { _, _ -> enqueue(chosen, VideoFinder.folderName(input.text.toString())) }
            .setNegativeButton(R.string.close, null)
            .show()
    }

    private fun enqueue(chosen: List<VideoGroup>, folder: String) {
        val headers = requestHeaders()
        val items = mutableListOf<QueueItem>()
        chosen.forEach { group ->
            val video = group.video
            val name = VideoFinder.fileName(video, groups.indexOf(group), group.title, withQuality = group.variants.size > 1)
            val blocker = video.blocker
            if (blocker != null) {
                toast(getString(R.string.hls_blocked, name, blocker))
                diag?.downloadFailures?.set(name, -3 to blocker)
                return@forEach
            }
            val hls = video.hls != null
            items += QueueItem(
                id = DownloadQueue.newId(),
                url = video.url,
                name = if (hls) name.substringBeforeLast('.') + ".mp4" else name,
                folder = folder,
                hls = hls,
                audioUrl = video.audioUrl,
                headers = headers(video.url),
            )
        }
        afterReportChange()
        if (items.isEmpty()) return
        DownloadQueue.add(items)
        diag?.event("Додано в чергу ${items.size} відео → Download/VideoDownloader/$folder")
        saveReport()
        DownloadService.start(this)
        askNotifications()
        toast(getString(R.string.queue_added, items.size, folder))
        selected.clear()
        refreshButtons()
    }

    /** Android 13+ hides the download progress notification unless the user allows notifications. */
    private fun askNotifications() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), REQUEST_NOTIFICATIONS)
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
        private const val REQUEST_NOTIFICATIONS = 2
        private const val MENU_REPORT = 1
        private const val MENU_QUEUE = 2

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
