package com.videodownloader.app

import java.net.HttpURLConnection
import java.net.URL

/** One piece of an HLS video. [length] < 0 means the whole file, otherwise a byte range from [offset]. */
data class HlsSegment(val url: String, val duration: Double = 0.0, val offset: Long = 0, val length: Long = -1)

/** A media playlist: the list of pieces that make up one quality of the video. */
data class HlsMedia(
    val url: String,
    val segments: List<HlsSegment>,
    /** fMP4 header piece (EXT-X-MAP) that goes before all segments; null for MPEG-TS streams. */
    val init: HlsSegment?,
    /** Encryption method (AES-128, SAMPLE-AES…) if the stream is encrypted — those are not downloaded. */
    val encryption: String?,
    /** A live broadcast: the playlist has no end yet. */
    val live: Boolean,
) {
    val duration get() = segments.sumOf { it.duration }
    val isFmp4 get() = init != null || VideoFinder.extension(segments.firstOrNull()?.url ?: "") in listOf("m4s", "mp4", "m4v")

    /** Why this stream cannot be downloaded, or null if it can. */
    val problem: String?
        get() = when {
            encryption != null -> "потік зашифрований ($encryption) — захищене відео не скачується"
            live -> "це пряма трансляція, а не записане відео"
            segments.isEmpty() -> "плейлист порожній"
            else -> null
        }
}

/** One quality in a master playlist. [audioUrl] is a separate audio playlist, if the video has none inside. */
data class HlsVariant(val url: String, val bandwidth: Long, val width: Int, val height: Int, val audioUrl: String?) {
    val label get() = when {
        height > 0 -> "${minOf(width.takeIf { it > 0 } ?: height, height)}p"
        bandwidth > 0 -> "${bandwidth / 1000} кбіт/с"
        else -> ""
    }
}

/** What an .m3u8 file turned out to be. */
sealed class HlsPlaylist {
    data class Master(val variants: List<HlsVariant>) : HlsPlaylist()
    data class Media(val media: HlsMedia) : HlsPlaylist()
}

/** Reads HLS (.m3u8) playlists. */
object Hls {

    private val attribute = Regex("""([A-Z0-9-]+)=("[^"]*"|[^,]*)""")

    private fun attributes(line: String): Map<String, String> =
        attribute.findAll(line.substringAfter(':')).associate { it.groupValues[1] to it.groupValues[2].trim('"') }

    fun resolve(base: String, ref: String): String = try { URL(URL(base), ref.trim()).toString() } catch (_: Exception) { ref.trim() }

    /** "1000@200" → (length 1000, offset 200); without "@" the piece continues where the previous ended. */
    private fun byteRange(value: String, previousEnd: Long): Pair<Long, Long> {
        val length = value.substringBefore('@').trim().toLongOrNull() ?: -1
        val offset = if ('@' in value) value.substringAfter('@').trim().toLongOrNull() ?: 0 else previousEnd
        return length to offset
    }

    fun parse(text: String, url: String): HlsPlaylist {
        val lines = text.lines().map { it.trim() }.filter { it.isNotEmpty() }
        require(lines.firstOrNull()?.startsWith("#EXTM3U") == true) { "це не HLS-плейлист" }

        if (lines.any { it.startsWith("#EXT-X-STREAM-INF") }) {
            val audio = HashMap<String, String>()
            lines.filter { it.startsWith("#EXT-X-MEDIA:") }.forEach { line ->
                val a = attributes(line)
                val uri = a["URI"] ?: return@forEach
                val group = a["GROUP-ID"] ?: return@forEach
                if (a["TYPE"] == "AUDIO" && (group !in audio || a["DEFAULT"] == "YES")) audio[group] = resolve(url, uri)
            }
            val variants = mutableListOf<HlsVariant>()
            lines.forEachIndexed { i, line ->
                if (!line.startsWith("#EXT-X-STREAM-INF")) return@forEachIndexed
                val uri = lines.drop(i + 1).firstOrNull { !it.startsWith("#") } ?: return@forEachIndexed
                val a = attributes(line)
                val res = a["RESOLUTION"]?.split('x')
                variants += HlsVariant(
                    url = resolve(url, uri),
                    bandwidth = (a["AVERAGE-BANDWIDTH"] ?: a["BANDWIDTH"])?.toLongOrNull() ?: 0,
                    width = res?.getOrNull(0)?.toIntOrNull() ?: 0,
                    height = res?.getOrNull(1)?.toIntOrNull() ?: 0,
                    audioUrl = a["AUDIO"]?.let { audio[it] },
                )
            }
            return HlsPlaylist.Master(variants.distinctBy { it.url }.sortedWith(compareByDescending<HlsVariant> { it.height }.thenByDescending { it.bandwidth }))
        }

        val segments = mutableListOf<HlsSegment>()
        var init: HlsSegment? = null
        var encryption: String? = null
        var ended = false
        var vod = false
        var duration = 0.0
        var range: Pair<Long, Long>? = null
        var previousEnd = 0L
        for (line in lines) {
            when {
                line.startsWith("#EXTINF:") -> duration = line.substringAfter(':').substringBefore(',').trim().toDoubleOrNull() ?: 0.0
                line.startsWith("#EXT-X-BYTERANGE:") -> range = byteRange(line.substringAfter(':'), previousEnd)
                line.startsWith("#EXT-X-MAP:") -> {
                    val a = attributes(line)
                    val r = a["BYTERANGE"]?.let { byteRange(it, 0) }
                    a["URI"]?.let { init = HlsSegment(resolve(url, it), 0.0, r?.second ?: 0, r?.first ?: -1) }
                }
                line.startsWith("#EXT-X-KEY:") -> {
                    val method = attributes(line)["METHOD"] ?: "NONE"
                    if (method != "NONE") encryption = method
                }
                line.startsWith("#EXT-X-ENDLIST") -> ended = true
                line.startsWith("#EXT-X-PLAYLIST-TYPE:") -> vod = line.substringAfter(':').trim() == "VOD"
                line.startsWith("#") -> {}
                else -> {
                    val r = range
                    segments += if (r != null) HlsSegment(resolve(url, line), duration, r.second, r.first)
                    else HlsSegment(resolve(url, line), duration)
                    if (r != null) previousEnd = r.second + r.first
                    range = null
                    duration = 0.0
                }
            }
        }
        return HlsPlaylist.Media(HlsMedia(url, segments, init, encryption, live = !ended && !vod))
    }

    /** Downloads a playlist as text (playlists are small). */
    fun fetch(url: String, headers: Map<String, String>): String {
        val conn = open(url, headers)
        try {
            val code = conn.responseCode
            if (code !in 200..299) throw java.io.IOException("HTTP $code — ${Diagnostics.httpMeaning(code)}")
            return conn.inputStream.use { it.readBytes() }.decodeToString()
        } finally {
            conn.disconnect()
        }
    }

    fun open(url: String, headers: Map<String, String>, segment: HlsSegment? = null): HttpURLConnection {
        val conn = URL(url).openConnection() as HttpURLConnection
        conn.connectTimeout = 15_000
        conn.readTimeout = 30_000
        conn.instanceFollowRedirects = true
        headers.forEach { (k, v) -> conn.setRequestProperty(k, v) }
        if (segment != null && segment.length >= 0) {
            conn.setRequestProperty("Range", "bytes=${segment.offset}-${segment.offset + segment.length - 1}")
        }
        return conn
    }

    /** Fetches a playlist and, for a master playlist, the media playlist of every quality. */
    fun load(url: String, headers: Map<String, String>): Loaded {
        return when (val p = parse(fetch(url, headers), url)) {
            is HlsPlaylist.Media -> Loaded(url, listOf(Loaded.Variant(null, p.media, null)))
            is HlsPlaylist.Master -> Loaded(url, p.variants.take(8).map { v ->
                try {
                    when (val m = parse(fetch(v.url, headers), v.url)) {
                        is HlsPlaylist.Media -> Loaded.Variant(v, m.media, null)
                        is HlsPlaylist.Master -> Loaded.Variant(v, null, "вкладений головний плейлист")
                    }
                } catch (e: Exception) {
                    Loaded.Variant(v, null, e.message ?: e.javaClass.simpleName)
                }
            })
        }
    }

    /** Result of [load]: every quality with its piece list, or why it could not be read. */
    data class Loaded(val url: String, val variants: List<Variant>) {
        data class Variant(val info: HlsVariant?, val media: HlsMedia?, val error: String?)
        val isMaster get() = variants.any { it.info != null }
    }
}
