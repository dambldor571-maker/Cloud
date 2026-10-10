package com.videodownloader.app

import java.net.URI
import java.net.URLDecoder

/**
 * One video file found on the page. [size] and [mime] are filled in later (-1 / "" = not known yet);
 * [error] is set when the server refused the check request. [quality] is a label like "720p"
 * (from the page or the address; may be learned later from the file itself). [poster] is a preview image.
 * [flags] are hints from the page used by [ContentFilter] ("link", "loop", "adbox"); [duration] in seconds, 0 = unknown.
 */
data class Video(
    val url: String,
    val title: String,
    var size: Long = -1,
    var mime: String = "",
    var error: String? = null,
    var quality: String = "",
    val poster: String = "",
    val flags: Set<String> = emptySet(),
    val duration: Double = 0.0,
) {
    /** For an HLS stream: its piece list ([url] is then the .m3u8 of this quality). */
    var hls: HlsMedia? = null
    /** Separate audio playlist of an HLS quality, if the site sends sound apart from the picture. */
    var audioUrl: String? = null
    /** Why an HLS stream cannot be downloaded (encrypted, live…), or null. */
    var blocker: String? = null
}

/** What the page script reported about one video address. [group] ties together sources of one player. */
data class Tagged(
    val url: String,
    val title: String = "",
    val group: String = "",
    val quality: String = "",
    val poster: String = "",
    val flags: Set<String> = emptySet(),
    val duration: Double = 0.0,
)

/** The same video in one or more qualities; shown as one row, [chosen] is the variant to download. */
class VideoGroup(val variants: List<Video>) {
    var chosen = 0
    /** Set once the user picked a quality by hand, so automatic choice no longer overrides it. */
    var userChose = false
    var poster: String = variants.firstOrNull { it.poster.isNotBlank() }?.poster ?: ""
    /** Set by [ContentFilter]: real video, advertising or a preview of another video, and why. */
    var kind = Kind.MAIN
    var reason = ""

    val video get() = variants[chosen]
    val title get() = variants.firstOrNull { it.title.isNotBlank() }?.title ?: ""
    /** Stable identity for caches (thumbnails). */
    val key get() = variants.first().url

    /** Without quality labels the biggest file is most likely the best quality. */
    fun pickBest() {
        if (userChose || variants.size < 2 || variants.any { VideoFinder.qualityRank(it.quality) > 0 }) return
        val biggest = variants.indices.maxByOrNull { variants[it].size } ?: return
        if (variants[biggest].size > 0) chosen = biggest
    }
}

/** Result of scanning a page: downloadable files, the same files grouped by quality, and streams (HLS/DASH). */
data class ScanResult(val videos: List<Video>, val groups: List<VideoGroup>, val streams: List<String>)

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
     * [tagged] — videos from <video>/<source>/links/meta tags; trusted even without an extension.
     * [requests] — addresses the page actually loaded; kept only if they look like video.
     * [html] — rendered page source; searched for video addresses inside scripts and JSON.
     * [pageImage] — the page's og:image, used as preview when the page has a single video.
     */
    fun collect(tagged: List<Tagged>, requests: Collection<String>, html: String, pageImage: String = ""): ScanResult {
        val found = LinkedHashMap<String, Video>()
        val explicitGroup = HashMap<String, String>()
        val streams = LinkedHashSet<String>()

        fun add(raw: String, tag: Tagged?, trusted: Boolean) {
            val url = clean(raw) ?: return
            if (isStream(url)) { streams += url; return }
            if (!trusted && !looksLikeVideoFile(url)) return
            if (extension(url) == "ts") return // single HLS segment, not a whole video
            val title = tag?.title?.trim() ?: ""
            val quality = tag?.quality?.let { qualityLabel(it) }.orEmpty().ifEmpty { qualityFromUrl(url) }
            val poster = tag?.poster?.let { clean(it) } ?: ""
            val old = found[url]
            val flags = tag?.flags ?: emptySet()
            val duration = tag?.duration ?: 0.0
            if (old == null) found[url] = Video(url, title, quality = quality, poster = poster, flags = flags, duration = duration)
            else found[url] = old.copy(
                title = old.title.ifEmpty { title },
                quality = old.quality.ifEmpty { quality },
                poster = old.poster.ifEmpty { poster },
                flags = old.flags + flags,
                duration = if (old.duration > 0) old.duration else duration,
            )
            if (!tag?.group.isNullOrEmpty() && url !in explicitGroup) explicitGroup[url] = tag!!.group
        }

        tagged.forEach { add(it.url, it, trusted = true) }
        requests.forEach { add(it, null, trusted = false) }
        val text = html.replace("\\/", "/").replace("\\u002F", "/", ignoreCase = true).replace("&amp;", "&")
        urlInText.findAll(text).forEach { add(it.value, null, trusted = false) }

        // Sources of one <video> belong together; elsewhere addresses that differ only by a
        // quality mark (clip_480p.mp4 / clip_720p.mp4) are the same video.
        val byKey = LinkedHashMap<String, MutableList<Video>>()
        found.values.forEach { v ->
            val key = explicitGroup[v.url]?.let { "g:$it" } ?: "u:${groupKey(v.url)}"
            byKey.getOrPut(key) { mutableListOf() } += v
        }
        val groups = byKey.values.map { list ->
            VideoGroup(list.sortedByDescending { qualityRank(it.quality) })
        }
        if (groups.size == 1 && groups[0].poster.isEmpty()) clean(pageImage)?.let { groups[0].poster = it }
        ContentFilter.apply(groups)
        return ScanResult(found.values.toList(), groups, streams.toList())
    }

    private val qualityNumber = Regex("""(?i)(?<=^|[_\-./=,x ])(4320|2160|1440|1080|720|540|480|360|240|144)p?(?=[_\-./&,? ]|$)""")
    private val qualityWord = Regex("""(?i)(?<=[_\-./=])(4k|uhd|fhd|hd|sd|hq|lq)(?=[_\-./&?]|$)""")

    /** Quality mark inside an address ("…/clip_720p.mp4" → "720p"), or "". The host is not looked at. */
    fun qualityFromUrl(url: String): String {
        val tail = url.substringAfter("://").substringAfter('/', "")
        qualityNumber.find(tail)?.let { return "${it.groupValues[1]}p" }
        qualityWord.find(tail)?.let { return it.groupValues[1].uppercase() }
        return ""
    }

    /** Address with quality marks blanked out — equal keys mean "same video, other quality". */
    fun groupKey(url: String): String {
        val host = url.substringBefore("://") + "://" + url.substringAfter("://").substringBefore('/')
        val tail = url.removePrefix(host)
        return host + tail.replace(qualityNumber, "{q}").replace(qualityWord, "{q}")
    }

    /** Tidies a label from the page: "720" → "720p", "1280x720" → "720p", "HD 1080p" stays. */
    fun qualityLabel(raw: String): String {
        val t = raw.trim().take(30)
        if (t.isEmpty()) return ""
        Regex("""^\d{3,4}x(\d{3,4})$""").find(t)?.let { return "${it.groupValues[1]}p" }
        if (Regex("""^\d{3,4}$""").matches(t)) return "${t}p"
        return t
    }

    /** Height in pixels a quality label stands for (bigger = better), or -1 if unknown. */
    fun qualityRank(label: String): Int {
        val l = label.lowercase()
        Regex("""(\d{3,4})x(\d{3,4})""").find(l)?.let { return it.groupValues[2].toInt() }
        Regex("""(\d{3,4})""").findAll(l).map { it.value.toInt() }.filter { it in 100..4320 }.maxOrNull()?.let { return it }
        return when {
            "8k" in l -> 4320
            "4k" in l || "uhd" in l -> 2160
            "fhd" in l || "full" in l -> 1080
            "hd" in l || "hq" in l || "high" in l -> 720
            "sd" in l || "medium" in l -> 480
            "lq" in l || "low" in l -> 360
            else -> -1
        }
    }

    private fun clean(raw: String): String? {
        val u = raw.trim()
        if (!u.startsWith("http://", true) && !u.startsWith("https://", true)) return null // skips blob:, data:
        return u.substringBefore('#')
    }

    /**
     * A safe file name for saving: from [title] or the address, always with an extension.
     * [withQuality] adds the quality mark, so different qualities of one video don't clash.
     */
    fun fileName(video: Video, index: Int, title: String = video.title, withQuality: Boolean = false): String {
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
        var base = title.ifBlank { fromUrl }.ifBlank { "video_${index + 1}" }
        if (withQuality && video.quality.isNotEmpty() && !base.contains(video.quality, ignoreCase = true)) {
            base += "_${video.quality}"
        }
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

    /**
     * A safe folder name (page title or site) for Download/VideoDownloader/<folder>.
     * Slashes are not allowed, so it is always exactly one sub-folder.
     */
    fun folderName(raw: String): String =
        raw.replace(Regex("""[\\/:*?"<>|\x00-\x1f]"""), "_").replace(Regex("""\s+"""), " ")
            .trim().trim('.', ' ').take(60).trim()

    /** Pulls the first web address out of shared text ("Look at this: https://…"). */
    fun firstUrl(text: String): String? =
        Regex("""https?://\S+""", RegexOption.IGNORE_CASE).find(text)?.value?.trimEnd('.', ',', ';', ')', '»', '"', '\'')

    /**
     * Page address from what the user typed or pasted. Text shared from other apps often holds
     * a title before the link ("Funny cat https://…") — the link is taken out of it.
     * A bare "site.com/page" gets https:// added. Null if there is no usable address.
     */
    fun pageUrl(input: String): String? {
        val text = input.trim()
        firstUrl(text)?.let { return it }
        if (text.isEmpty() || text.any { it.isWhitespace() } || '.' !in text) return null
        return "https://$text"
    }
}
