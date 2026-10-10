package com.videodownloader.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class VideoFinderTest {

    @Test
    fun findsTaggedRequestedAndInlineVideos() {
        val html = """
            <script>var cfg = {"file":"https:\/\/cdn.example.com\/clips\/intro.webm?token=1"};</script>
            <a href="https://example.com/page.html">page</a>
            <img src="https://example.com/pic.jpg">
            <script>player.load('https://cdn.example.com/live/index.m3u8')</script>
        """.trimIndent()
        val result = VideoFinder.collect(
            tagged = listOf(Tagged("https://media.example.com/stream?id=7", "Lecture"), Tagged("blob:https://x/1")),
            requests = listOf("https://example.com/app.js", "https://cdn.example.com/a.mp4", "https://cdn.example.com/seg1.ts"),
            html = html
        )
        assertEquals(
            listOf(
                "https://media.example.com/stream?id=7",
                "https://cdn.example.com/a.mp4",
                "https://cdn.example.com/clips/intro.webm?token=1"
            ),
            result.videos.map { it.url }
        )
        assertEquals("Lecture", result.videos[0].title)
        assertEquals(listOf("https://cdn.example.com/live/index.m3u8"), result.streams)
    }

    @Test
    fun deduplicatesAndKeepsTitle() {
        val result = VideoFinder.collect(
            listOf(Tagged("https://e.com/v.mp4#t=10"), Tagged("https://e.com/v.mp4", "My clip")),
            emptyList(), "https://e.com/v.mp4"
        )
        assertEquals(1, result.videos.size)
        assertEquals("My clip", result.videos[0].title)
    }

    @Test
    fun fileNames() {
        assertEquals("My clip.mp4", VideoFinder.fileName(Video("https://e.com/v.mp4", "My clip"), 0))
        assertEquals("summer trip.webm", VideoFinder.fileName(Video("https://e.com/a/summer%20trip.webm?x=1", ""), 0))
        assertEquals("a_b.mp4", VideoFinder.fileName(Video("https://e.com/x", "a/b"), 0))
        assertEquals("watch.webm", VideoFinder.fileName(Video("https://e.com/watch", "", mime = "video/webm"), 0))
        assertEquals("video_3.mp4", VideoFinder.fileName(Video("https://e.com/", ""), 2))
    }

    @Test
    fun sharedText() {
        assertEquals("https://e.com/p?a=1", VideoFinder.firstUrl("Look: https://e.com/p?a=1 cool"))
        assertTrue(VideoFinder.firstUrl("no link") == null)
    }

    @Test
    fun pageUrlFromPastedText() {
        assertEquals("https://share.google/abc", VideoFinder.pageUrl("Some video title. https://share.google/abc"))
        assertEquals("https://e.com/p", VideoFinder.pageUrl("Дивись (https://e.com/p)."))
        assertEquals("https://e.com/p", VideoFinder.pageUrl("  e.com/p "))
        assertEquals("http://e.com", VideoFinder.pageUrl("http://e.com"))
        assertTrue(VideoFinder.pageUrl("just some words") == null)
        assertTrue(VideoFinder.pageUrl("") == null)
    }

    @Test
    fun sourcesOfOnePlayerAreQualityVariants() {
        val result = VideoFinder.collect(
            listOf(
                Tagged("https://cdn.e.com/a/low.mp4", "Trip", "v0", "360", "https://e.com/poster.jpg"),
                Tagged("https://cdn.e.com/a/high.mp4", "Trip", "v0", "1280x720", "https://e.com/poster.jpg"),
                Tagged("https://cdn.e.com/other.mp4", "Other", "v1"),
            ),
            emptyList(), ""
        )
        assertEquals(2, result.groups.size)
        val trip = result.groups[0]
        assertEquals(listOf("720p", "360p"), trip.variants.map { it.quality })
        assertEquals("https://cdn.e.com/a/high.mp4", trip.video.url) // best quality chosen by default
        assertEquals("https://e.com/poster.jpg", trip.poster)
        assertEquals(1, result.groups[1].variants.size)
    }

    @Test
    fun addressesDifferingOnlyByQualityAreGrouped() {
        val html = """
            {"src":"https://v.e.com/clips/sunset_480p.mp4"} {"src":"https://v.e.com/clips/sunset_1080p.mp4"}
            {"src":"https://v.e.com/clips/sunrise_480p.mp4"}
        """
        val result = VideoFinder.collect(emptyList(), emptyList(), html, pageImage = "https://e.com/og.jpg")
        assertEquals(2, result.groups.size)
        assertEquals(listOf("1080p", "480p"), result.groups[0].variants.map { it.quality })
        assertEquals("", result.groups[0].poster) // og:image only for a page with a single video
    }

    @Test
    fun singleVideoGetsPageImage() {
        val result = VideoFinder.collect(listOf(Tagged("https://e.com/v.mp4")), emptyList(), "", "https://e.com/og.jpg")
        assertEquals("https://e.com/og.jpg", result.groups[0].poster)
    }

    @Test
    fun unlabeledVariantsPickBiggest() {
        val group = VideoGroup(listOf(Video("https://e.com/a.mp4", ""), Video("https://e.com/b.mp4", "")))
        group.variants[0].size = 10
        group.variants[1].size = 900
        group.pickBest()
        assertEquals(1, group.chosen)
        group.chosen = 0
        group.userChose = true
        group.pickBest()
        assertEquals(0, group.chosen)
    }

    @Test
    fun qualityHelpers() {
        assertEquals("720p", VideoFinder.qualityFromUrl("https://e.com/v/clip-720.mp4?x=1"))
        assertEquals("HD", VideoFinder.qualityFromUrl("https://e.com/v/clip_hd.mp4"))
        assertEquals("", VideoFinder.qualityFromUrl("https://hd.e.com/v/clip.mp4"))
        assertEquals(2160, VideoFinder.qualityRank("4K"))
        assertEquals(1080, VideoFinder.qualityRank("Full HD 1080p"))
        assertEquals(-1, VideoFinder.qualityRank(""))
        assertEquals("clip_720p.mp4", VideoFinder.fileName(Video("https://e.com/x.mp4", "", quality = "720p"), 0, "clip", withQuality = true))
    }
}
