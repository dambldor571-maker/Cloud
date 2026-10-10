package com.videodownloader.app

import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.MediaMuxer
import java.io.File
import java.nio.ByteBuffer

/**
 * Repackages a downloaded HLS stream (MPEG-TS or fragmented MP4 pieces glued together) into a
 * normal MP4 that every player and gallery opens, without re-encoding. A separate audio stream,
 * if the site sends one, is merged in. Throws if the phone cannot handle the codecs — the caller
 * then keeps the raw file.
 */
object Remuxer {

    private class Source(val extractor: MediaExtractor, val tracks: Map<Int, Int>, val start: Long)

    fun toMp4(video: File, audio: File?, out: File) {
        val muxer = MediaMuxer(out.path, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        val extractors = mutableListOf<MediaExtractor>()
        var started = false
        try {
            var bufferSize = 4 * 1024 * 1024
            fun add(file: File, wantVideo: Boolean, wantAudio: Boolean): Source? {
                val ex = MediaExtractor().also { extractors += it }
                ex.setDataSource(file.path)
                val map = HashMap<Int, Int>()
                var tookVideo = false
                var tookAudio = false
                for (i in 0 until ex.trackCount) {
                    val format = ex.getTrackFormat(i)
                    val mime = format.getString(MediaFormat.KEY_MIME) ?: continue
                    val take = (wantVideo && !tookVideo && mime.startsWith("video/")) ||
                        (wantAudio && !tookAudio && mime.startsWith("audio/"))
                    if (!take) continue
                    if (mime.startsWith("video/")) tookVideo = true else tookAudio = true
                    if (format.containsKey(MediaFormat.KEY_MAX_INPUT_SIZE)) {
                        bufferSize = maxOf(bufferSize, format.getInteger(MediaFormat.KEY_MAX_INPUT_SIZE))
                    }
                    map[i] = muxer.addTrack(format)
                    ex.selectTrack(i)
                }
                if (map.isEmpty()) return null
                return Source(ex, map, ex.sampleTime.coerceAtLeast(0))
            }

            val sources = listOfNotNull(
                add(video, wantVideo = true, wantAudio = audio == null) ?: throw IllegalStateException("у потоці немає відеодоріжки"),
                audio?.let { add(it, wantVideo = false, wantAudio = true) },
            )
            muxer.start()
            started = true

            val buffer = ByteBuffer.allocateDirect(bufferSize)
            val info = MediaCodec.BufferInfo()
            while (true) {
                // Write samples in time order across both files, so audio and video stay interleaved.
                val source = sources
                    .filter { it.extractor.sampleTrackIndex >= 0 }
                    .minByOrNull { it.extractor.sampleTime - it.start } ?: break
                val ex = source.extractor
                val target = source.tracks[ex.sampleTrackIndex]
                buffer.clear()
                val size = ex.readSampleData(buffer, 0)
                if (target != null && size > 0) {
                    val flags = if (ex.sampleFlags and MediaExtractor.SAMPLE_FLAG_SYNC != 0) MediaCodec.BUFFER_FLAG_KEY_FRAME else 0
                    info.set(0, size, (ex.sampleTime - source.start).coerceAtLeast(0), flags)
                    muxer.writeSampleData(target, buffer, info)
                }
                ex.advance()
            }
            muxer.stop()
        } finally {
            if (!started) out.delete()
            try { muxer.release() } catch (_: Exception) {}
            extractors.forEach { try { it.release() } catch (_: Exception) {} }
        }
    }
}
