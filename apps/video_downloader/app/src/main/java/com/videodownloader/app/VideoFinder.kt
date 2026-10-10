package com.videodownloader.app

import java.net.URI
import java.net.URLDecoder

/** One video found on the page. [size] is filled in later (-1 = not known yet). */
data class Video(val url: String, val title: String, var size: Long = -1, var mime: String = "")

/** Result of scanning a page: downloadable files and streaming playlists (HLS/DASH). */
data class ScanResult(val videos: List<Video>, val streams: List<String>)

/** Picks video links out of what the page's scripts reported plus its rendered HTML. */
object VideoFinder {

    private val fileExts = listOf("mp4", "webm", "mkv", "mov", "m4v", "3gp", "avi", "flv", "ogv", "wmv", "mpg", "mpeg", "ts")
    private val streamExts = listOf("m3u8", "mpd")

    private val urlInText = Regex(
        """https?://[^\s"'<>\\()\[\]{}]+?\.(?:${(fileExts + streamExts).joinToString("|")})(?:\?[^\s"'<>\\]*)?(?=$|[\s"'<>\\)\]},;])""",
        RegexOption.IGNORE_CASE
    )

    /** Lower-case extension of the URL's path, or "" if it has none. */
    fun extension(url: String): String {
        val path = try { URI(url).rawPath ?: "" } catch (e: Exception) { url.substringBefore('?').substringBefore('#') }
        val last = path.substringAfterLast('/')
        return if ('.' in last) last.substringAfterLast('.').lowercase() else ""
    }

    fun isStream(url: String) = extension(url) in streamExts

    /** True if the address itself looks like a video file (by extension). */
    fun looksLikeVideoFile(url: String) = extension(url) in fileExts && extension(url) != "ts"

    /**
     * [tagged] — pairs (url, title) from <video>/<source>/links/meta tags; trusted even without an extension.
     * [requests] — addresses the page actually loaded; kept only if they look like video.
     * [html] — rendered page source; searched for video addresses inside scripts and JSON.
     */
    fun collect(tagged: List<Pair<String, String>>, requests: Collection<String>, html: String): ScanResult {
        val found = LinkedHashMap<String, Video>()
        val streams = LinkedHashSet<String>()

        fun add(raw: String, title: String, trusted: Boolean) {
            val url = clean(raw) ?: return
            if (isStream(url)) { streams += url; return }
            if (!trusted && !looksLikeVideoFile(url)) return
            if (extension(url) == "ts") return // single HLS segment, not a whole video
            val old = found[url]
            if (old == null) found[url] = Video(url, title.trim())
            else if (old.title.isEmpty() && title.isNotBlank()) found[url] = old.copy(title = title.trim())
        }

        tagged.forEach { (u, t) -> add(u, t, trusted = true) }
        requests.forEach { add(it, "", trusted = false) }
        val text = html.replace("\\/", "/").replace("\\u002F", "/", ignoreCase = true).replace("&amp;", "&")
        urlInText.findAll(text).forEach { add(it.value, "", trusted = false) }

        return ScanResult(found.values.toList(), streams.toList())
    }

    private fun clean(raw: String): String? {
        val u = raw.trim()
        if (!u.startsWith("http://", true) && !u.startsWith("https://", true)) return null // skips blob:, data:
        return u.substringBefore('#')
    }

    /** A safe file name for saving: from the title or the address, always with an extension. */
    fun fileName(video: Video, index: Int): String {
        val ext = extension(video.url).takeIf { it in fileExts }
            ?: when {
                "webm" in video.mime -> "webm"
                "quicktime" in video.mime -> "mov"
                "matroska" in video.mime -> "mkv"
                "3gpp" in video.mime -> "3gp"
                else -> "mp4"
            }
        val fromUrl = try {
            URLDecoder.decode(URI(video.url).rawPath?.substringAfterLast('/') ?: "", "UTF-8")
        } catch (e: Exception) { "" }.substringBeforeLast('.')
        val base = video.title.ifBlank { fromUrl }.ifBlank { "video_${index + 1}" }
        val safe = base.replace(Regex("""[\\/:*?"<>|\x00-\x1f]"""), "_").trim().trim('.').take(100)
        return "${safe.ifBlank { "video_${index + 1}" }}.$ext"
    }

    fun humanSize(bytes: Long): String = when {
        bytes < 0 -> ""
        bytes < 1024 -> "$bytes Б"
        bytes < 1024 * 1024 -> String.format("%.0f КБ", bytes / 1024.0)
        bytes < 1024L * 1024 * 1024 -> String.format("%.1f МБ", bytes / 1024.0 / 1024)
        else -> String.format("%.2f ГБ", bytes / 1024.0 / 1024 / 1024)
    }

    /** Pulls the first web address out of shared text ("Look at this: https://…"). */
    fun firstUrl(text: String): String? = Regex("""https?://\S+""").find(text)?.value
}
