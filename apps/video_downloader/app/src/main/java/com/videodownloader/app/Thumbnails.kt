package com.videodownloader.app

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.media.MediaMetadataRetriever
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.LruCache
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

/**
 * Preview pictures for the video list. Takes the page's own preview image (poster, og:image,
 * picture next to the link); if there is none, grabs a frame from the video file itself.
 * Work runs in the background; [onChange] is called on the main thread when something arrived.
 */
class Thumbnails(private val cacheDir: File, private val onChange: () -> Unit, private val onFailed: (String) -> Unit) {

    private val main = Handler(Looper.getMainLooper())
    private val pool = Executors.newFixedThreadPool(3)
    private val cache = LruCache<String, Bitmap>(80)
    private val pending = HashSet<String>()
    private val failed = HashSet<String>()
    /** Bumped by [clear] so pictures from a previous page are dropped. */
    private var generation = 0

    /** The preview if ready; otherwise starts loading it and returns null. */
    fun get(group: VideoGroup, headers: (String) -> Map<String, String>): Bitmap? {
        val key = group.key
        cache.get(key)?.let { return it }
        if (key in pending || key in failed) return null
        pending += key
        val gen = generation
        val poster = group.poster
        val video = group.video
        pool.execute {
            var bitmap: Bitmap? = null
            var height = 0
            var error = ""
            try {
                if (poster.isNotEmpty()) bitmap = image(poster, headers(poster))
                if (bitmap == null) {
                    val hls = video.hls
                    val frame = if (hls != null) hlsFrame(hls, headers(video.url)) else frame(video.url, headers(video.url))
                    bitmap = frame.first
                    height = frame.second
                }
            } catch (e: Throwable) {
                error = "${e.javaClass.simpleName}: ${e.message}"
            }
            main.post {
                if (gen != generation) return@post
                pending -= key
                if (bitmap != null) cache.put(key, bitmap) else {
                    failed += key
                    onFailed("Прев'ю для ${Diagnostics.shortUrl(video.url)} не отримано${if (error.isNotEmpty()) ": $error" else ""}")
                }
                // The file itself tells its real height — a quality label where the page gave none.
                if (height > 0 && video.quality.isEmpty()) video.quality = "${height}p"
                onChange()
            }
        }
        return null
    }

    fun clear() {
        generation++
        pending.clear()
        failed.clear()
        cache.evictAll()
    }

    fun shutdown() = pool.shutdownNow()

    /** Downloads a picture and shrinks it to list size. */
    private fun image(url: String, headers: Map<String, String>): Bitmap? {
        val conn = URL(url).openConnection() as HttpURLConnection
        conn.connectTimeout = 10_000
        conn.readTimeout = 10_000
        headers.forEach { (k, v) -> conn.setRequestProperty(k, v) }
        try {
            if (conn.responseCode !in 200..299) return null
            val bytes = conn.inputStream.use { it.readBytes() }
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
            var sample = 1
            while (bounds.outWidth / (sample * 2) >= TARGET_WIDTH) sample *= 2
            return BitmapFactory.decodeByteArray(bytes, 0, bytes.size, BitmapFactory.Options().apply { inSampleSize = sample })
        } finally {
            conn.disconnect()
        }
    }

    /** HLS has no single file: take the piece from the middle (plus its header for fMP4) and look into it. */
    private fun hlsFrame(media: HlsMedia, headers: Map<String, String>): Pair<Bitmap?, Int> {
        val middle = media.segments.getOrNull(media.segments.size / 2) ?: return null to 0
        val file = File.createTempFile("hls", if (media.isFmp4) ".mp4" else ".ts", cacheDir)
        try {
            file.outputStream().use { out ->
                for (piece in listOfNotNull(media.init, middle)) {
                    val conn = Hls.open(piece.url, headers, piece)
                    try {
                        if (conn.responseCode !in 200..299) return null to 0
                        conn.inputStream.use { input ->
                            // A piece is a few seconds long; cap it in case it is not.
                            val buf = ByteArray(64 * 1024)
                            var total = 0
                            while (total < 12 * 1024 * 1024) {
                                val n = input.read(buf)
                                if (n < 0) break
                                out.write(buf, 0, n)
                                total += n
                            }
                        }
                    } finally {
                        conn.disconnect()
                    }
                }
            }
            return frame(file.path, null)
        } finally {
            file.delete()
        }
    }

    /**
     * A frame from the middle of the video (the start is often a black screen or a logo),
     * and the video's height in pixels (0 if unknown).
     */
    private fun frame(source: String, headers: Map<String, String>?): Pair<Bitmap?, Int> {
        val retriever = MediaMetadataRetriever()
        try {
            if (headers == null) retriever.setDataSource(source) else retriever.setDataSource(source, headers)
            val height = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT)?.toIntOrNull() ?: 0
            val width = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH)?.toIntOrNull() ?: 0
            val durationMs = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull() ?: 0
            val option = MediaMetadataRetriever.OPTION_CLOSEST_SYNC
            fun grab(timeUs: Long): Bitmap? =
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1 && width > 0 && height > 0) {
                    retriever.getScaledFrameAtTime(timeUs, option, TARGET_WIDTH, TARGET_WIDTH * height / width)
                } else {
                    retriever.getFrameAtTime(timeUs, option)?.let { scale(it) }
                }
            // Middle of the video; if that fails (unknown length, odd timestamps), any frame the file gives.
            val bitmap = (if (durationMs > 0) grab(durationMs * 1000 / 2) else null)
                ?: grab(1_000_000L)
                ?: retriever.frameAtTime?.let { scale(it) }
            // The shorter side is what people call quality (also right for portrait videos).
            val quality = if (width > 0 && height > 0) minOf(width, height) else height
            return bitmap to quality
        } finally {
            try { retriever.release() } catch (_: Exception) {}
        }
    }

    private fun scale(b: Bitmap): Bitmap =
        if (b.width <= TARGET_WIDTH) b else Bitmap.createScaledBitmap(b, TARGET_WIDTH, TARGET_WIDTH * b.height / b.width, true)

    companion object {
        private const val TARGET_WIDTH = 320
    }
}
