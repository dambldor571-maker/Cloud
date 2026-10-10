package com.videodownloader.app

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class DiagnosticsTest {

    private fun diag() = Diagnostics("https://site.example/page", "test")

    @Test
    fun blobPlayerExplained() {
        val d = diag()
        d.page = PageInfo(title = "Clip", videoTags = 1, blobVideos = 1, players = listOf("hls"))
        assertTrue(d.hasProblem)
        assertTrue(d.hints().first().contains("blob:"))
        assertTrue(d.render().contains("Плеєри: hls"))
    }

    @Test
    fun forbiddenFileAndFailedDownloadExplained() {
        val d = diag()
        d.page = PageInfo(title = "Clip", videoTags = 1)
        d.videos = listOf(Video("https://cdn.example/v.mp4", ""))
        d.probes["https://cdn.example/v.mp4"] = 403 to "text/html"
        d.downloadFailures["v.mp4"] = 1006 to Diagnostics.downloadFailure(1006)
        val hints = d.hints().joinToString("\n")
        assertTrue(hints.contains("HTTP 403"))
        assertTrue(hints.contains("недостатньо місця"))
    }

    @Test
    fun antiBotAndIframe() {
        val d = diag()
        d.mainHttpStatus = 403
        d.page = PageInfo(title = "Just a moment...", iframes = listOf("https://player.example/embed/1"))
        val hints = d.hints().joinToString("\n")
        assertTrue(hints.contains("захист від ботів"))
        assertTrue(hints.contains("https://player.example/embed/1"))
    }

    @Test
    fun cleanScanHasNoProblem() {
        val d = diag()
        d.page = PageInfo(title = "Clip", videoTags = 1)
        d.videos = listOf(Video("https://cdn.example/v.mp4", ""))
        d.probes["https://cdn.example/v.mp4"] = 206 to "video/mp4"
        assertFalse(d.hasProblem)
        assertTrue(d.render().contains("Проблем не виявлено"))
    }
}
