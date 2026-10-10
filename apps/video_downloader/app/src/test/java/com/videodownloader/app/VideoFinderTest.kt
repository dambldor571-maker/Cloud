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
            tagged = listOf("https://media.example.com/stream?id=7" to "Lecture", "blob:https://x/1" to ""),
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
            listOf("https://e.com/v.mp4#t=10" to "", "https://e.com/v.mp4" to "My clip"),
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
}
