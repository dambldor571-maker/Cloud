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
import android.os.Environment
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.provider.MediaStore
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.io.OutputStream
import java.util.concurrent.Callable
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicInteger

/**
 * Works through [DownloadQueue]: [PARALLEL] videos at a time, the rest wait their turn, so a
 * queue of hundreds is fine. Plain files are written straight into
 * Download/VideoDownloader/<folder> and continue where they stopped after a failure; HLS videos
 * are fetched piece by piece, glued and repackaged into MP4. Runs as a foreground service with
 * one summary notification, so it keeps going when the app is in the background.
 */
class DownloadService : Service() {

    private val main = Handler(Looper.getMainLooper())
    private val workers = AtomicInteger()
    private val pool = Executors.newCachedThreadPool()
    private lateinit var notifications: NotificationManager
    private val finishedSinceStart = AtomicInteger()
    private val failedSinceStart = AtomicInteger()

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        DownloadQueue.init(filesDir)
        notifications = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            notifications.createNotificationChannel(
                NotificationChannel(CHANNEL, getString(R.string.queue_channel), NotificationManager.IMPORTANCE_LOW)
            )
        }
    }

    override fun onDestroy() {
        main.removeCallbacks(ticker)
        pool.shutdownNow()
        super.onDestroy()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = summary()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(PROGRESS_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } else {
            startForeground(PROGRESS_ID, notification)
        }
        if (intent?.action == ACTION_CANCEL_ALL) DownloadQueue.cancelAll()
        startWorkers()
        main.removeCallbacks(ticker)
        main.post(ticker)
        return START_NOT_STICKY
    }

    private fun startWorkers() {
        while (workers.get() < PARALLEL && DownloadQueue.count(QueueStatus.WAITING) > workers.get()) {
            workers.incrementAndGet()
            pool.execute {
                try {
                    while (true) {
                        val item = DownloadQueue.takeNext() ?: break
                        run(item)
                    }
                } finally {
                    if (workers.decrementAndGet() == 0) main.post { stopIfIdle() }
                }
            }
        }
        if (workers.get() == 0) main.post { stopIfIdle() }
    }

    private fun stopIfIdle() {
        if (workers.get() > 0) return
        if (DownloadQueue.count(QueueStatus.WAITING) > 0) { startWorkers(); return }
        main.removeCallbacks(ticker)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) stopForeground(STOP_FOREGROUND_REMOVE) else @Suppress("DEPRECATION") stopForeground(true)
        if (finishedSinceStart.get() + failedSinceStart.get() > 0) {
            notifications.notify(DONE_ID, finished())
            finishedSinceStart.set(0)
            failedSinceStart.set(0)
        }
        stopSelf()
    }

    private val ticker = object : Runnable {
        override fun run() {
            notifications.notify(PROGRESS_ID, summary())
            main.postDelayed(this, 1000)
        }
    }

    // --- One item ---

    private class CancelledException : IOException()
    /** A failure that retrying will not fix (403, page instead of video…). */
    private class FatalException(message: String) : IOException(message)

    private fun checkCancelled(item: QueueItem) {
        if (item.status == QueueStatus.CANCELLED || Thread.currentThread().isInterrupted) throw CancelledException()
    }

    private fun run(item: QueueItem) {
        try {
            if (item.hls) runHls(item) else runFile(item)
            DownloadQueue.finish(item, QueueStatus.DONE)
            finishedSinceStart.incrementAndGet()
            val size = if (item.hls) "" else ", ${VideoFinder.humanSize(item.done)}"
            report(item, "«${item.name}» скачано у ${item.folder}$size${item.note?.let { " — $it" } ?: ""}",
                if (item.note == null) OK else WARNING)
        } catch (e: CancelledException) {
            DownloadQueue.finish(item, QueueStatus.CANCELLED)
            discard(item)
            report(item, "«${item.name}» скасовано", FAILED)
        } catch (e: Exception) {
            val why = e.message ?: e.javaClass.simpleName
            DownloadQueue.finish(item, QueueStatus.FAILED, why)
            failedSinceStart.incrementAndGet()
            report(item, "«${item.name}» НЕ скачано: $why", FAILED)
        }
    }

    /** Plain file: up to 4 attempts, each continuing from where the previous one stopped. */
    private fun runFile(item: QueueItem) {
        var attempt = 0
        while (true) {
            checkCancelled(item)
            try {
                fileAttempt(item)
                return
            } catch (e: CancelledException) {
                throw e
            } catch (e: FatalException) {
                throw e
            } catch (e: IOException) {
                if (++attempt >= 4) throw IOException("${e.message ?: e.javaClass.simpleName} (після $attempt спроб)")
                Thread.sleep(2000L * attempt)
            }
        }
    }

    private fun fileAttempt(item: QueueItem) {
        val resume = item.done > 0 && item.uri != null
        val conn = Hls.open(item.url, item.headers)
        if (resume) conn.setRequestProperty("Range", "bytes=${item.done}-")
        try {
            val code = conn.responseCode
            if (code in 400..499) throw FatalException("HTTP $code — ${Diagnostics.httpMeaning(code)}")
            if (code !in 200..299) throw IOException("HTTP $code — ${Diagnostics.httpMeaning(code)}")
            val type = conn.contentType ?: ""
            if (type.startsWith("text/html")) throw FatalException("сервер віддав сторінку ($type) замість відео")
            // 206 = the server continues the file; 200 = it sends everything again.
            val append = resume && code == 206
            if (!append) item.done = 0
            val length = conn.contentLengthLong
            item.total = if (length > 0) item.done + length else -1

            openTarget(item, append, type.substringBefore(';').ifBlank { "video/mp4" }).use { out ->
                conn.inputStream.use { input ->
                    val buf = ByteArray(256 * 1024)
                    while (true) {
                        checkCancelled(item)
                        val n = input.read(buf)
                        if (n < 0) break
                        out.write(buf, 0, n)
                        item.done += n
                    }
                }
            }
            if (item.total > 0 && item.done < item.total) throw IOException("з'єднання обірвалося на ${VideoFinder.humanSize(item.done)}")
            publish(item)
            if (item.done < 50_000) item.note = "файл підозріло малий (${VideoFinder.humanSize(item.done)}) — можливо, це сторінка помилки"
        } finally {
            conn.disconnect()
        }
    }

    private fun relativePath(folder: String) =
        "${Environment.DIRECTORY_DOWNLOADS}/VideoDownloader" + (if (folder.isNotEmpty()) "/$folder" else "")

    @Suppress("DEPRECATION")
    private fun publicFolder(folder: String) =
        File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "VideoDownloader/$folder").apply { mkdirs() }

    /** Where the file goes; created on the first attempt and remembered for continuing. */
    private fun openTarget(item: QueueItem, append: Boolean, mime: String): OutputStream {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            var uri = item.uri?.let { Uri.parse(it) }
            if (uri == null) {
                val values = ContentValues().apply {
                    put(MediaStore.Downloads.DISPLAY_NAME, item.name)
                    put(MediaStore.Downloads.MIME_TYPE, mime)
                    put(MediaStore.Downloads.RELATIVE_PATH, relativePath(item.folder))
                    put(MediaStore.Downloads.IS_PENDING, 1)
                }
                uri = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                    ?: throw FatalException("не вдалося створити файл у «Завантаженнях»")
                item.uri = uri.toString()
                DownloadQueue.changed()
            }
            return contentResolver.openOutputStream(uri, if (append) "wa" else "wt")
                ?: throw IOException("не вдалося відкрити файл для запису")
        }
        var path = item.uri
        if (path == null) {
            val folder = publicFolder(item.folder)
            var f = File(folder, item.name)
            var n = 1
            while (f.exists()) f = File(folder, "${item.name.substringBeforeLast('.')} (${n++}).${item.name.substringAfterLast('.')}")
            path = f.path
            item.uri = path
            DownloadQueue.changed()
        }
        return FileOutputStream(path, append)
    }

    /** Makes a finished file visible to galleries and other apps. */
    private fun publish(item: QueueItem) {
        val target = item.uri ?: return
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            contentResolver.update(Uri.parse(target), ContentValues().apply { put(MediaStore.Downloads.IS_PENDING, 0) }, null, null)
        } else {
            MediaScannerConnection.scanFile(this, arrayOf(target), null, null)
        }
    }

    /** Deletes a half-written file of a cancelled or removed download. */
    private fun discard(item: QueueItem) = discardFile(this, item)

    // --- HLS ---

    private fun runHls(item: QueueItem) {
        val dir = File(cacheDir, "hls/${item.id}").apply { deleteRecursively(); mkdirs() }
        try {
            val media = loadMedia(item.url, item.headers)
            val audio = item.audioUrl?.let { loadMedia(it, item.headers) }
            item.total = (media.segments.size + (audio?.segments?.size ?: 0)).toLong()
            item.done = 0

            val videoFile = File(dir, if (media.isFmp4) "video.mp4" else "video.ts")
            fetchAll(item, media, videoFile, File(dir, "v"))
            val audioFile = audio?.let { a ->
                File(dir, if (a.isFmp4) "audio.mp4" else "audio.ts").also { fetchAll(item, a, it, File(dir, "a")) }
            }
            checkCancelled(item)

            val base = item.name.substringBeforeLast('.')
            val mp4 = File(dir, "out.mp4")
            try {
                Remuxer.toMp4(videoFile, audioFile, mp4)
                videoFile.delete()
                item.uri = save(mp4, "$base.mp4", "video/mp4", item.folder)
                item.note = null
            } catch (e: Exception) {
                // The phone could not repackage it — keep what was downloaded as is.
                mp4.delete()
                var note = "не вдалося перепакувати в MP4 (${e.javaClass.simpleName}: ${e.message}), збережено як є"
                val ext = if (media.isFmp4) "mp4" else "ts"
                item.uri = save(videoFile, "$base.$ext", if (media.isFmp4) "video/mp4" else "video/mp2t", item.folder)
                if (audio != null && audioFile != null) {
                    save(audioFile, "${base}_audio.${if (audio.isFmp4) "m4a" else "ts"}", if (audio.isFmp4) "audio/mp4" else "video/mp2t", item.folder)
                    note += "; звук окремим файлом _audio"
                }
                item.note = note
            }
        } finally {
            dir.deleteRecursively()
        }
    }

    private fun loadMedia(url: String, headers: Map<String, String>): HlsMedia {
        val media = when (val playlist = Hls.parse(Hls.fetch(url, headers), url)) {
            is HlsPlaylist.Media -> playlist.media
            // A master playlist was passed: take the best quality.
            is HlsPlaylist.Master -> {
                val best = playlist.variants.firstOrNull() ?: throw FatalException("у плейлисті немає жодної якості")
                (Hls.parse(Hls.fetch(best.url, headers), best.url) as? HlsPlaylist.Media)?.media
                    ?: throw FatalException("не вдалося прочитати плейлист якості")
            }
        }
        media.problem?.let { throw FatalException(it) }
        return media
    }

    /** Downloads all pieces (3 at a time, each retried) and glues them into [target] in order. */
    private fun fetchAll(item: QueueItem, media: HlsMedia, target: File, prefix: File) {
        val pieces = listOfNotNull(media.init) + media.segments
        val segmentPool = Executors.newFixedThreadPool(3)
        try {
            val futures = pieces.mapIndexed { i, segment ->
                segmentPool.submit(Callable {
                    val file = File("${prefix.path}_$i")
                    fetchPiece(item, segment, file)
                    if (i > 0 || media.init == null) synchronized(item) { item.done++ }
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
            segmentPool.shutdownNow()
        }
    }

    private fun fetchPiece(item: QueueItem, segment: HlsSegment, file: File) {
        var last: Exception? = null
        repeat(3) { attempt ->
            checkCancelled(item)
            try {
                val conn = Hls.open(segment.url, item.headers, segment)
                try {
                    val code = conn.responseCode
                    val what = "шматок ${Diagnostics.shortUrl(segment.url, 80)}: HTTP $code — ${Diagnostics.httpMeaning(code)}"
                    if (code in 400..499) throw FatalException(what)
                    if (code !in 200..299) throw IOException(what)
                    conn.inputStream.use { input -> file.outputStream().use { input.copyTo(it) } }
                    return
                } finally {
                    conn.disconnect()
                }
            } catch (e: CancelledException) {
                throw e
            } catch (e: FatalException) {
                throw e
            } catch (e: Exception) {
                last = e
                Thread.sleep(1000L * (attempt + 1))
            }
        }
        throw last ?: IOException("не вдалося скачати шматок")
    }

    /** Copies a finished file into Download/VideoDownloader/<folder>; returns where it went. */
    private fun save(file: File, name: String, mime: String, folder: String): String {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, name)
                put(MediaStore.Downloads.MIME_TYPE, mime)
                put(MediaStore.Downloads.RELATIVE_PATH, relativePath(folder))
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
            return uri.toString()
        }
        val dir = publicFolder(folder)
        var out = File(dir, name)
        var n = 1
        while (out.exists()) out = File(dir, "${name.substringBeforeLast('.')} (${n++}).${name.substringAfterLast('.')}")
        file.copyTo(out)
        MediaScannerConnection.scanFile(this, arrayOf(out.path), arrayOf(mime), null)
        return out.path
    }

    // --- Notifications and reporting ---

    private fun builder(): Notification.Builder =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(this, CHANNEL)
        else @Suppress("DEPRECATION") Notification.Builder(this)

    private fun openQueue() = PendingIntent.getActivity(
        this, 0, Intent(this, QueueActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK), PendingIntent.FLAG_IMMUTABLE
    )

    private fun summary(): Notification {
        val all = DownloadQueue.snapshot()
        val running = all.filter { it.status == QueueStatus.RUNNING }
        val waiting = all.count { it.status == QueueStatus.WAITING }
        val done = all.count { it.status == QueueStatus.DONE }
        val failed = all.count { it.status == QueueStatus.FAILED }
        val total = running.size + waiting + done + failed
        val cancel = PendingIntent.getService(
            this, 1, Intent(this, DownloadService::class.java).setAction(ACTION_CANCEL_ALL),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        val current = running.joinToString("\n") { "${it.name} — ${progressText(it)}" }
        return builder()
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentTitle(getString(R.string.queue_notification, running.size, waiting, done, failed))
            .setContentText(running.firstOrNull()?.name ?: getString(R.string.hls_preparing))
            .setStyle(Notification.BigTextStyle().bigText(current))
            .setProgress(total.coerceAtLeast(1), done + failed, false)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(openQueue())
            .addAction(Notification.Action.Builder(null, getString(R.string.queue_cancel_all), cancel).build())
            .build()
    }

    private fun finished(): Notification =
        builder()
            .setSmallIcon(if (failedSinceStart.get() > 0) android.R.drawable.stat_notify_error else android.R.drawable.stat_sys_download_done)
            .setContentTitle(getString(R.string.queue_finished))
            .setContentText(getString(R.string.queue_finished_text, finishedSinceStart.get(), failedSinceStart.get()))
            .setContentIntent(openQueue())
            .setAutoCancel(true)
            .build()

    private fun report(item: QueueItem, text: String, outcome: Int) {
        main.post { listener?.invoke(item.name, text, outcome) }
    }

    companion object {
        /** How many videos download at the same time; the rest wait in the queue. */
        const val PARALLEL = 3
        private const val CHANNEL = "downloads"
        private const val PROGRESS_ID = 4242
        private const val DONE_ID = 4243
        private const val ACTION_CANCEL_ALL = "cancel_all"

        const val OK = 0
        /** Saved, but something is off (raw stream kept, suspiciously small file). */
        const val WARNING = 1
        const val FAILED = 2

        /** The search screen listens here to put results into the diagnostic report: (file name, message, outcome). */
        @Volatile var listener: ((String, String, Int) -> Unit)? = null

        /** Starts working through the queue (does nothing harmful if it is already running). */
        fun start(context: Context) {
            DownloadQueue.init(context.filesDir)
            if (!DownloadQueue.hasWork()) return
            val intent = Intent(context, DownloadService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) context.startForegroundService(intent) else context.startService(intent)
        }

        /** "45 % · 12.3 МБ з 27.0 МБ" for files, "120 / 450 шматків" for HLS. */
        fun progressText(item: QueueItem): String = when {
            item.hls && item.total > 0 -> "${item.done} / ${item.total} шматків"
            item.total > 0 -> "${item.done * 100 / item.total} % · ${VideoFinder.humanSize(item.done)} з ${VideoFinder.humanSize(item.total)}"
            item.done > 0 -> VideoFinder.humanSize(item.done)
            else -> "…"
        }

        /** Deletes the unfinished file of a download that will not continue. */
        fun discardFile(context: Context, item: QueueItem) {
            val target = item.uri ?: return
            if (item.status == QueueStatus.DONE) return
            try {
                if (target.startsWith("content:")) context.contentResolver.delete(Uri.parse(target), null, null)
                else File(target).delete()
            } catch (_: Exception) {
            }
            item.uri = null
            item.done = 0
        }
    }
}
