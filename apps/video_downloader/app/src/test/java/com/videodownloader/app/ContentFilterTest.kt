package com.videodownloader.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ContentFilterTest {

    private fun group(url: String, size: Long = -1, flags: Set<String> = emptySet(), duration: Double = 0.0) =
        VideoGroup(listOf(Video(url, "", size = size, flags = flags, duration = duration)))

    @Test
    fun adNetworksAndAdAddresses() {
        assertTrue(ContentFilter.shouldBlock("https://pubads.g.doubleclick.net/gampad/ads?x=1"))
        assertTrue(ContentFilter.shouldBlock("https://s.magsrv.com/v1/vast.php"))
        assertFalse(ContentFilter.shouldBlock("https://cdn.example.com/video.mp4"))
        assertFalse(ContentFilter.shouldBlock("https://notdoubleclick.net.example.com/a.mp4"))

        assertEquals(Kind.AD, ContentFilter.classify(group("https://cdn.e.com/vast/creative_123.mp4"), 0).first)
        assertEquals(Kind.AD, ContentFilter.classify(group("https://cdn.e.com/ads/preroll.mp4"), 0).first)
        assertEquals(Kind.AD, ContentFilter.classify(group("https://cdn.e.com/x.mp4", flags = setOf("adbox")), 0).first)
        // "ad" inside a word is not advertising
        assertEquals(Kind.MAIN, ContentFilter.classify(group("https://cdn.e.com/uploads/download/road-trip.mp4"), 0).first)
    }

    @Test
    fun previewsOfOtherVideos() {
        assertEquals(Kind.PREVIEW, ContentFilter.classify(group("https://e.com/previews/123.mp4"), 0).first)
        assertEquals(Kind.PREVIEW, ContentFilter.classify(group("https://e.com/v/123_thumb.mp4"), 0).first)
        assertEquals(Kind.PREVIEW, ContentFilter.classify(group("https://e.com/a.mp4", flags = setOf("link")), 0).first)
        assertEquals(Kind.PREVIEW, ContentFilter.classify(group("https://e.com/a.mp4", flags = setOf("loop")), 0).first)
        // short counts as preview only next to a long main video
        assertEquals(Kind.PREVIEW, ContentFilter.classify(group("https://e.com/a.mp4", duration = 8.0), 0, 600.0).first)
        assertEquals(Kind.MAIN, ContentFilter.classify(group("https://e.com/a.mp4", duration = 8.0), 0).first)
        assertEquals(Kind.PREVIEW, ContentFilter.classify(group("https://e.com/a.mp4", size = 300_000), 0).first)
        assertEquals(Kind.MAIN, ContentFilter.classify(group("https://e.com/a.mp4", duration = 600.0), 0).first)
    }

    @Test
    fun sizeComparedWithTheMainVideo() {
        val main = group("https://e.com/movie.mp4", size = 400_000_000)
        val small = group("https://e.com/related.mp4", size = 3_000_000)
        val groups = listOf(small, main)
        ContentFilter.apply(groups)
        assertEquals(Kind.MAIN, main.kind)
        assertEquals(Kind.PREVIEW, small.kind)
        assertEquals(listOf(main), ContentFilter.visible(groups, showHidden = false))
        assertEquals(listOf(main, small), ContentFilter.visible(groups, showHidden = true))
    }

    @Test
    fun onlyPreviewsAreStillShown() {
        val a = group("https://e.com/previews/1.mp4")
        val ad = group("https://e.com/ads/2.mp4")
        ContentFilter.apply(listOf(a, ad))
        assertEquals(listOf(a), ContentFilter.visible(listOf(a, ad), showHidden = false))
    }

    @Test
    fun collectClassifies() {
        val result = VideoFinder.collect(
            listOf(
                Tagged("https://e.com/movie.mp4", "Movie"),
                Tagged("https://e.com/teaser.mp4", flags = setOf("link", "loop")),
            ),
            emptyList(), ""
        )
        assertEquals(listOf(Kind.MAIN, Kind.PREVIEW), result.groups.map { it.kind })
    }
}
