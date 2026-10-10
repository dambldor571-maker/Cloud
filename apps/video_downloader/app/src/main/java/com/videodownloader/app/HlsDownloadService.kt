package com.videodownloader.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.MediaScannerConnection
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.provider.MediaStore
import java.io.File
import java.io.IOException
import java.util.concurrent.Callable
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicInteger

/**
 * Downloads HLS (.m3u8) videos: fetches every piece of the chosen quality, glues them together,
 * repackages into MP4 and saves to Download/VideoDownloader. Runs as a foreground service with a
 * progress notification, so it keeps going when the app is in the background. Jobs run one by one.
 */
class HlsDownloadService : Service() {

    private val worker = Executors.newSingleThreadExecutor()
    private val queued = AtomicInteger()
    private val main = Handler(Looper.getMainLooper())
    @Volatile private var cancelled = false
    private lateinit var notifications: NotificationManager

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        notifications = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            notifications.createNotificationChannel(
                NotificationChannel(CHANNEL, getString(R.string.hls_channel), NotificationManager.IMPORTANCE_LOW)
            )
        }
    }

    override fun onDestroy() {
        worker.shutdownNow()
        super.onDestroy()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = progress(getString(R.string.hls_preparing), 0, 0)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(PROGRESS_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } else {
            startForeground(PROGRESS_ID, notification)
        }
        if (intent?.action == ACTION_CANCEL) {
            cancelled = true
            if (queued.get() == 0) finish()
            return START_NOT_STICKY
        }
        val url = intent?.getStringExtra(EXTRA_URL) ?: return START_NOT_STICKY.also { if (queued.get() == 0) finish() }
        val name = intent.getStringExtra(EXTRA_NAME) ?: "video"
        val audio = intent.getStringExtra(EXTRA_AUDIO)
        val bundle = intent.getBundleExtra(EXTRA_HEADERS)
        val headers = bundle?.keySet()?.associateWith { bundle.getString(it) ?: "" } ?: emptyMap()
        queued.incrementAndGet()
        worker.execute {
            try {
                if (!cancelled) run(url, audio, name, headers)
                else report(name, "HLS «$name» ${getString(R.string.hls_cancelled)}", FAILED)
            } finally {
                if (queued.decrementAndGet() == 0) main.post { finish() }
            }
        }
        return START_NOT_STICKY
    }

    private fun finish() {
        cancelled = false
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) stopForeground(STOP_FOREGROUND_REMOVE) else @Suppress("DEPRECATION") stopForeground(true)
        stopSelf()
    }

    private fun run(url: String, audioUrl: String?, name: String, headers: Map<String, String>) {
        val dir = File(cacheDir, "hls/${System.nanoTime()}").apply { mkdirs() }
        try {
            update(name, 0, 0)
            val media = loadMedia(url, headers)
            val audio = audioUrl?.let { loadMedia(it, headers) }
            val total = media.segments.size + (audio?.segments?.size ?: 0)
            val done = AtomicInteger()
            val tick = { update(name, done.incrementAndGet(), total) }

            val videoFile = File(dir, if (media.isFmp4) "video.mp4" else "video.ts")
            fetchAll(media, videoFile, File(dir, "v"), headers, tick)
            val audioFile = audio?.let { a ->
                File(dir, if (a.isFmp4) "audio.mp4" else "audio.ts").also { fetchAll(a, it, File(dir, "a"), headers, tick) }
            }
            checkCancelled()
            update(name, total, total, getString(R.string.hls_packing))

            val mp4 = File(dir, "out.mp4")
            var note = ""
            var bytes: Long
            val saved = try {
                Remuxer.toMp4(videoFile, audioFile, mp4)
                videoFile.delete()
                bytes = mp4.length()
                save(mp4, "$name.mp4", "video/mp4")
            } catch (e: Exception) {
                // The phone could not repackage it — keep what was downloaded as is.
                mp4.delete()
                note = " — не вдалося перепакувати в MP4 (${e.javaClass.simpleName}: ${e.message}), збережено як є"
                val ext = if (media.isFmp4) "mp4" else "ts"
                bytes = videoFile.length()
                val uri = save(videoFile, "$name.$ext", if (media.isFmp4) "video/mp4" else "video/mp2t")
                if (audio != null && audioFile != null) {
                    save(audioFile, "${name}_audio.${if (audio.isFmp4) "m4a" else "ts"}", if (audio.isFmp4) "audio/mp4" else "video/mp2t")
                    note += "; звук окремим файлом _audio"
                }
                uri
            }
            done(name, saved)
            report(
                name,
                "HLS «$name» скачано: ${media.segments.size} шматків, ${media.duration.toInt()} с, ${VideoFinder.humanSize(bytes)}$note",
                if (note.isEmpty()) OK else WARNING,
            )
        } catch (e: Exception) {
            val why = if (e is CancelledException) getString(R.string.hls_cancelled) else (e.message ?: e.javaClass.simpleName)
            fail(name, why)
            report(name, "HLS «$name» НЕ скачано: $why", FAILED)
        } finally {
            dir.deleteRecursively()
        }
    }

    private fun loadMedia(url: String, headers: Map<String, String>): HlsMedia {
        val playlist = Hls.parse(Hls.fetch(url, headers), url)
        val media = when (playlist) {
            is HlsPlaylist.Media -> playlist.media
            // A master playlist was passed: take the best quality.
            is HlsPlaylist.Master -> {
                val best = playlist.variants.firstOrNull() ?: throw IOException("у плейлисті немає жодної якості")
                (Hls.parse(Hls.fetch(best.url, headers), best.url) as? HlsPlaylist.Media)?.media
                    ?: throw IOException("не вдалося прочитати плейлист якості")
            }
        }
        media.problem?.let { throw IOException(it) }
        return media
    }

    /** Downloads all pieces (4 at a time, each retried) and glues them into [target] in order. */
    private fun fetchAll(media: HlsMedia, target: File, prefix: File, headers: Map<String, String>, tick: () -> Unit) {
        val pieces = listOfNotNull(media.init) + media.segments
        val pool = Executors.newFixedThreadPool(4)
        try {
            val futures = pieces.mapIndexed { i, segment ->
                pool.submit(Callable {
                    val file = File("${prefix.path}_$i")
                    fetchPiece(segment, file, headers)
                    if (i > 0 || media.init == null) tick()
                    file
                })
            }
            target.outputStream().buffered().use { out ->
                futures.forEach { future ->
                    val file = try { future.get() } catch (e: java.util.concurrent.ExecutionException) { throw e.cause ?: e }
                    file.inputStream().use { it.copyTo(out) }
                    file.delete()
                }
            }
        } finally {
            pool.shutdownNow()
        }
    }

    private fun fetchPiece(segment: HlsSegment, file: File, headers: Map<String, String>) {
        var last: Exception? = null
        repeat(3) { attempt ->
            checkCancelled()
            try {
                val conn = Hls.open(segment.url, headers, segment)
                try {
                    val code = conn.responseCode
                    if (code !in 200..299) throw IOException("шматок ${Diagnostics.shortUrl(segment.url, 80)}: HTTP $code — ${Diagnostics.httpMeaning(code)}")
                    conn.inputStream.use { input -> file.outputStream().use { input.copyTo(it) } }
                    return
                } finally {
                    conn.disconnect()
                }
            } catch (e: CancelledException) {
                throw e
            } catch (e: Exception) {
                last = e
                // 4xx will not get better on retry.
                if (e.message?.contains("HTTP 4") == true) throw e
                Thread.sleep(1000L * (attempt + 1))
            }
        }
        throw last ?: IOException("не вдалося скачати шматок")
    }

    private class CancelledException : IOException()

    private fun checkCancelled() {
        if (cancelled || Thread.currentThread().isInterrupted) throw CancelledException()
    }

    /** Copies the finished file into Download/VideoDownloader; returns a link to open it, if possible. */
    private fun save(file: File, name: String, mime: String): Uri? {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, name)
                put(MediaStore.Downloads.MIME_TYPE, mime)
                put(MediaStore.Downloads.RELATIVE_PATH, "${Environment.DIRECTORY_DOWNLOADS}/VideoDownloader")
                put(MediaStore.Downloads.IS_PENDING, 1)
            }
            val uri = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                ?: throw IOException("не вдалося створити файл у «Завантаженнях»")
            try {
                contentResolver.openOutputStream(uri)!!.use { out -> file.inputStream().use { it.copyTo(out) } }
            } catch (e: Exception) {
                contentResolver.delete(uri, null, null)
                throw e
            }
            contentResolver.update(uri, ContentValues().apply { put(MediaStore.Downloads.IS_PENDING, 0) }, null, null)
            return uri
        }
        @Suppress("DEPRECATION")
        val folder = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "VideoDownloader").apply { mkdirs() }
        var out = File(folder, name)
        var n = 1
        while (out.exists()) out = File(folder, "${name.substringBeforeLast('.')} (${n++}).${name.substringAfterLast('.')}")
        file.copyTo(out)
        MediaScannerConnection.scanFile(this, arrayOf(out.path), arrayOf(mime), null)
        return null
    }

    // --- Notifications and reporting ---

    private fun builder(): Notification.Builder =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(this, CHANNEL)
        else @Suppress("DEPRECATION") Notification.Builder(this)

    private fun progress(text: String, done: Int, total: Int): Notification {
        val cancel = PendingIntent.getService(
            this, 1, Intent(this, HlsDownloadService::class.java).setAction(ACTION_CANCEL),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        return builder()
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentTitle(getString(R.string.hls_title))
            .setContentText(text)
            .setProgress(total, done, total == 0)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .addAction(Notification.Action.Builder(null, getString(R.string.hls_cancel), cancel).build())
            .build()
    }

    private var lastUpdate = 0L

    private fun update(name: String, done: Int, total: Int, text: String? = null) {
        val now = System.currentTimeMillis()
        if (text == null && done in 1 until total && now - lastUpdate < 500) return
        lastUpdate = now
        val line = text ?: if (total == 0) name else "$name — $done / $total"
        notifications.notify(PROGRESS_ID, progress(line, done, total))
    }

    private fun done(name: String, uri: Uri?) {
        val b = builder()
            .setSmallIcon(android.R.drawable.stat_sys_download_done)
            .setContentTitle(getString(R.string.hls_done))
            .setContentText(name)
            .setAutoCancel(true)
        if (uri != null) {
            val open = Intent(Intent.ACTION_VIEW).setDataAndType(uri, "video/*").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            b.setContentIntent(PendingIntent.getActivity(this, name.hashCode(), open, PendingIntent.FLAG_IMMUTABLE))
        }
        notifications.notify(name.hashCode(), b.build())
    }

    private fun fail(name: String, why: String) {
        val openApp = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        notifications.notify(
            name.hashCode(),
            builder()
                .setSmallIcon(android.R.drawable.stat_notify_error)
                .setContentTitle(getString(R.string.hls_failed, name))
                .setContentText(why)
                .setStyle(Notification.BigTextStyle().bigText(why))
                .setContentIntent(openApp)
                .setAutoCancel(true)
                .build()
        )
    }

    private fun report(name: String, text: String, outcome: Int) {
        main.post { listener?.invoke(name, text, outcome) }
    }

    companion object {
        private const val CHANNEL = "hls"
        private const val PROGRESS_ID = 4242
        private const val ACTION_CANCEL = "cancel"
        private const val EXTRA_URL = "url"
        private const val EXTRA_AUDIO = "audio"
        private const val EXTRA_NAME = "name"
        private const val EXTRA_HEADERS = "headers"

        const val OK = 0
        /** Saved, but not as a clean MP4 (kept the raw stream). */
        const val WARNING = 1
        const val FAILED = 2

        /** The screen listens here to put results into the diagnostic report: (file name, message, outcome). */
        @Volatile var listener: ((String, String, Int) -> Unit)? = null

        fun start(context: Context, url: String, audioUrl: String?, name: String, headers: Map<String, String>) {
            val bundle = Bundle().apply { headers.forEach { (k, v) -> putString(k, v) } }
            val intent = Intent(context, HlsDownloadService::class.java)
                .putExtra(EXTRA_URL, url)
                .putExtra(EXTRA_AUDIO, audioUrl)
                .putExtra(EXTRA_NAME, name)
                .putExtra(EXTRA_HEADERS, bundle)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) context.startForegroundService(intent) else context.startService(intent)
        }
    }
}
