package com.videodownloader.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class HlsTest {

    @Test
    fun masterPlaylistBestQualityFirstWithSeparateAudio() {
        val text = """
            #EXTM3U
            #EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="aud",NAME="en",DEFAULT=YES,URI="audio/en.m3u8"
            #EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360,AUDIO="aud"
            360/index.m3u8
            #EXT-X-STREAM-INF:BANDWIDTH=5000000,AVERAGE-BANDWIDTH=4500000,RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2",AUDIO="aud"
            https://cdn.e.com/1080/index.m3u8
            #EXT-X-I-FRAME-STREAM-INF:BANDWIDTH=100000,URI="iframes.m3u8"
        """.trimIndent()
        val p = Hls.parse(text, "https://e.com/video/master.m3u8") as HlsPlaylist.Master
        assertEquals(listOf("1080p", "360p"), p.variants.map { it.label })
        assertEquals("https://cdn.e.com/1080/index.m3u8", p.variants[0].url)
        assertEquals(4_500_000L, p.variants[0].bandwidth)
        assertEquals("https://e.com/video/360/index.m3u8", p.variants[1].url)
        assertEquals("https://e.com/video/audio/en.m3u8", p.variants[0].audioUrl)
    }

    @Test
    fun mediaPlaylistTs() {
        val text = """
            #EXTM3U
            #EXT-X-VERSION:3
            #EXT-X-TARGETDURATION:10
            #EXTINF:9.009,
            seg0.ts
            #EXTINF:9.009,
            seg1.ts?token=a
            #EXTINF:3.5,
            seg2.ts
            #EXT-X-ENDLIST
        """.trimIndent()
        val m = (Hls.parse(text, "https://e.com/v/index.m3u8") as HlsPlaylist.Media).media
        assertEquals(3, m.segments.size)
        assertEquals("https://e.com/v/seg1.ts?token=a", m.segments[1].url)
        assertEquals(21.518, m.duration, 0.001)
        assertFalse(m.isFmp4)
        assertFalse(m.live)
        assertNull(m.problem)
    }

    @Test
    fun fmp4WithByteRanges() {
        val text = """
            #EXTM3U
            #EXT-X-PLAYLIST-TYPE:VOD
            #EXT-X-MAP:URI="video.mp4",BYTERANGE="720@0"
            #EXTINF:4.0,
            #EXT-X-BYTERANGE:1000@720
            video.mp4
            #EXTINF:4.0,
            #EXT-X-BYTERANGE:2000
            video.mp4
        """.trimIndent()
        val m = (Hls.parse(text, "https://e.com/v/i.m3u8") as HlsPlaylist.Media).media
        assertTrue(m.isFmp4)
        assertEquals(HlsSegment("https://e.com/v/video.mp4", 0.0, 0, 720), m.init)
        assertEquals(720L, m.segments[0].offset)
        assertEquals(1000L, m.segments[0].length)
        assertEquals(1720L, m.segments[1].offset) // continues after the previous piece
        assertEquals(2000L, m.segments[1].length)
        assertFalse(m.live) // VOD without ENDLIST is still a finished video
    }

    @Test
    fun encryptedAndLiveAreRefused() {
        val encrypted = """
            #EXTM3U
            #EXT-X-KEY:METHOD=AES-128,URI="key.bin"
            #EXTINF:6,
            a.ts
            #EXT-X-ENDLIST
        """.trimIndent()
        val e = (Hls.parse(encrypted, "https://e.com/i.m3u8") as HlsPlaylist.Media).media
        assertEquals("AES-128", e.encryption)
        assertTrue(e.problem!!.contains("зашифрований"))

        val live = "#EXTM3U\n#EXTINF:6,\na.ts\n#EXTINF:6,\nb.ts"
        val l = (Hls.parse(live, "https://e.com/i.m3u8") as HlsPlaylist.Media).media
        assertTrue(l.live)
        assertTrue(l.problem!!.contains("трансляція"))
    }

    @Test(expected = IllegalArgumentException::class)
    fun notAPlaylist() {
        Hls.parse("<html>Login</html>", "https://e.com/i.m3u8")
    }
}
