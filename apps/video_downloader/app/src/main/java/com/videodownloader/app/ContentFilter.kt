package com.videodownloader.app

import java.net.URI

/** What a found video most likely is. Only [MAIN] is shown unless the user asks to see the rest. */
enum class Kind { MAIN, PREVIEW, AD }

/**
 * Tells real videos apart from advertising and from short preview clips of other videos
 * (hover teasers, thumbnails of "related" videos). Purely guesswork from addresses, page
 * markup and file sizes, so the app hides such items rather than dropping them.
 */
object ContentFilter {

    /** Advertising and ad-video networks; requests to them are also blocked while scanning. */
    private val adHosts = listOf(
        "doubleclick.net", "googlesyndication.com", "googleadservices.com", "imasdk.googleapis.com",
        "adservice.google.com", "adnxs.com", "adsrvr.org", "advertising.com", "adform.net", "criteo.com",
        "criteo.net", "taboola.com", "outbrain.com", "pubmatic.com", "rubiconproject.com", "openx.net",
        "smartadserver.com", "spotxchange.com", "spotx.tv", "springserve.com", "teads.tv", "yieldmo.com",
        "exoclick.com", "exosrv.com", "exdynsrv.com", "realsrv.com", "magsrv.com", "trafficjunky.net",
        "trafficjunky.com", "trafficstars.com", "tsyndicate.com", "juicyads.com", "popads.net",
        "popcash.net", "propellerads.com", "adsterra.com", "adsterratech.com", "hilltopads.net",
        "clickadu.com", "trafficfactory.biz", "ero-advertising.com", "plugrush.com", "adspyglass.com",
        "adtng.com", "a-ads.com", "adskeeper.com", "mgid.com", "yandex.ru/ads", "an.yandex.ru",
        "adfox.ru", "adriver.ru", "betweendigital.com", "vidazoo.com", "connatix.com", "primis.tech",
        "aniview.com", "vidoomy.com", "ad.plus", "jwpltx.com",
    )

    /** Address parts typical for ad creatives. */
    private val adPath = Regex(
        """(?i)(^|[/_\-.=?&])(ads?|adv|advert|advertising|adserver|banners?|vast|vpaid|preroll|pre-roll|midroll|postroll|creatives?|sponsor(ed)?)([/_\-.=?&]|$)"""
    )

    /** Address parts typical for short clips that preview another video. */
    private val previewPath = Regex(
        """(?i)(^|[/_\-.=?&])(preview|previews|teaser|teasers|thumb|thumbs|thumbnail|thumbnails|vidthumb|hover|snippet)([/_\-.=?&]|$)"""
    )

    private fun host(url: String) = try { URI(url).host?.lowercase() ?: "" } catch (_: Exception) { "" }

    /** Ad network host (domain or any of its subdomains), or null. */
    fun adNetwork(url: String): String? {
        val h = host(url)
        val full = h + (try { URI(url).rawPath ?: "" } catch (_: Exception) { "" })
        return adHosts.firstOrNull { d -> h == d || h.endsWith(".$d") || ('/' in d && full.startsWith(d)) }
    }

    /** Should the scanner refuse to load this request at all? Only known ad networks. */
    fun shouldBlock(url: String) = adNetwork(url) != null

    private fun pathOf(url: String) = url.substringAfter("://").substringAfter('/', "")

    /** Verdict for one video: kind plus a short reason in Ukrainian for the list and the report. */
    fun classify(group: VideoGroup, biggestMainSize: Long, longestMainDuration: Double = 0.0): Pair<Kind, String> {
        for (v in group.variants) {
            adNetwork(v.url)?.let { return Kind.AD to "рекламна мережа $it" }
            if ("adbox" in v.flags) return Kind.AD to "у рекламному блоці сторінки"
            if (adPath.containsMatchIn(pathOf(v.url))) return Kind.AD to "адреса схожа на рекламу"
        }
        for (v in group.variants) {
            if ("link" in v.flags) return Kind.PREVIEW to "мініатюра-посилання на іншу сторінку"
            if ("loop" in v.flags) return Kind.PREVIEW to "беззвучний зациклений ролик без керування"
            if (previewPath.containsMatchIn(pathOf(v.url))) return Kind.PREVIEW to "адреса схожа на прев'ю"
            // Short only counts next to a real, much longer video — some sites have only short clips.
            if (v.duration in 0.1..15.0 && longestMainDuration >= 60) return Kind.PREVIEW to "дуже короткий (${v.duration.toInt()} с)"
        }
        val size = group.variants.maxOf { it.size }
        if (size in 1 until 512 * 1024) return Kind.PREVIEW to "дуже малий файл (${VideoFinder.humanSize(size)})"
        if (size in 1 until 5L * 1024 * 1024 && biggestMainSize >= size * 8) {
            return Kind.PREVIEW to "набагато менший за основне відео (${VideoFinder.humanSize(size)})"
        }
        return Kind.MAIN to ""
    }

    /** Classifies all groups; sizes count once known, so call again after the size checks. */
    fun apply(groups: List<VideoGroup>) {
        // First pass without size comparison, to learn how big the real videos are.
        groups.forEach { g -> classify(g, 0).let { g.kind = it.first; g.reason = it.second } }
        val mains = groups.filter { it.kind == Kind.MAIN }
        val biggest = mains.maxOfOrNull { g -> g.variants.maxOf { it.size } } ?: 0
        val longest = mains.maxOfOrNull { g -> g.variants.maxOf { it.duration } } ?: 0.0
        groups.forEach { g -> classify(g, biggest, longest).let { g.kind = it.first; g.reason = it.second } }
        // A gallery page (all videos are tiles linking elsewhere) has no "main" video:
        // then the tiles are what the user came for, not previews.
        if (groups.none { it.kind == Kind.MAIN }) {
            groups.filter { it.kind == Kind.PREVIEW }.forEach { it.kind = Kind.MAIN; it.reason = "" }
        }
    }

    /**
     * Rows to show. Hidden kinds appear only on request; if filtering would leave nothing,
     * previews are shown anyway (better a doubtful video than an empty list). Main videos first.
     */
    fun visible(groups: List<VideoGroup>, showHidden: Boolean): List<VideoGroup> {
        if (showHidden) return groups.sortedBy { it.kind.ordinal }
        val main = groups.filter { it.kind == Kind.MAIN }
        return main.ifEmpty { groups.filter { it.kind == Kind.PREVIEW } }
    }
}
