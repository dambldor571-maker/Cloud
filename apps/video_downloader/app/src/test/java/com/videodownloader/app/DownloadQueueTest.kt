package com.videodownloader.app

import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class DownloadQueueTest {

    @get:Rule val tmp = TemporaryFolder()

    @Before fun setUp() = DownloadQueue.reset()
    @After fun tearDown() = DownloadQueue.reset()

    private fun item(n: Int) = QueueItem(DownloadQueue.newId(), "https://e.com/$n.mp4", "$n.mp4", "Site")

    @Test
    fun hundredsOfItemsGoInOrder() {
        DownloadQueue.init(tmp.root)
        DownloadQueue.add((1..500).map { item(it) })
        assertEquals(500, DownloadQueue.count(QueueStatus.WAITING))
        val first = DownloadQueue.takeNext()!!
        val second = DownloadQueue.takeNext()!!
        assertEquals("1.mp4", first.name)
        assertEquals("2.mp4", second.name)
        assertEquals(2, DownloadQueue.count(QueueStatus.RUNNING))
        DownloadQueue.finish(first, QueueStatus.DONE)
        DownloadQueue.finish(second, QueueStatus.FAILED, "HTTP 403")
        assertEquals(498, DownloadQueue.count(QueueStatus.WAITING))

        DownloadQueue.retryFailed()
        assertEquals(499, DownloadQueue.count(QueueStatus.WAITING))
        assertNull(second.error)
    }

    @Test
    fun survivesRestartAndRunningWaitsAgain() {
        DownloadQueue.init(tmp.root)
        DownloadQueue.add(listOf(item(1), item(2), item(3)))
        val running = DownloadQueue.takeNext()!!
        running.done = 1234
        running.uri = "content://media/external/downloads/7"
        DownloadQueue.changed()
        DownloadQueue.finish(DownloadQueue.takeNext()!!, QueueStatus.DONE)

        DownloadQueue.reset() // the app was closed
        DownloadQueue.init(tmp.root)
        val items = DownloadQueue.snapshot()
        assertEquals(listOf(QueueStatus.WAITING, QueueStatus.DONE, QueueStatus.WAITING), items.map { it.status })
        assertEquals(1234L, items[0].done) // continues where it stopped
        assertEquals("content://media/external/downloads/7", items[0].uri)
        assertEquals("Site", items[0].folder)
        assertEquals(4L, DownloadQueue.newId()) // ids keep growing
    }

    @Test
    fun cancelAndRemove() {
        DownloadQueue.init(tmp.root)
        DownloadQueue.add((1..5).map { item(it) })
        val running = DownloadQueue.takeNext()!!
        DownloadQueue.cancelAll()
        assertEquals(5, DownloadQueue.count(QueueStatus.CANCELLED))
        // A download that ends after being cancelled stays cancelled.
        DownloadQueue.finish(running, QueueStatus.DONE)
        assertEquals(QueueStatus.CANCELLED, running.status)
        assertFalse(DownloadQueue.hasWork())

        val removed = DownloadQueue.remove { it.status == QueueStatus.CANCELLED }
        assertEquals(5, removed.size)
        assertTrue(DownloadQueue.snapshot().isEmpty())
    }

    @Test
    fun headersAndHlsKept() {
        val i = QueueItem(9, "https://e.com/a.m3u8", "a.mp4", "F", hls = true, audioUrl = "https://e.com/au.m3u8",
            headers = mapOf("Referer" to "https://e.com/page"))
        val back = QueueItem.fromJson(i.toJson())
        assertTrue(back.hls)
        assertEquals("https://e.com/au.m3u8", back.audioUrl)
        assertEquals("https://e.com/page", back.headers["Referer"])
    }

    @Test
    fun folderNames() {
        assertEquals("My_Videos_ Part 2", VideoFinder.folderName("My/Videos: Part   2"))
        assertEquals("site.com", VideoFinder.folderName(" site.com "))
        assertEquals(60, VideoFinder.folderName("x".repeat(200)).length)
        assertEquals("", VideoFinder.folderName("..."))
    }
}
