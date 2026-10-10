package com.videodownloader.app

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.CopyOnWriteArraySet

enum class QueueStatus { WAITING, RUNNING, DONE, FAILED, CANCELLED }

/**
 * One video in the download queue. [name] is the file name with extension; [folder] is the
 * sub-folder inside Download/VideoDownloader. Progress: [done]/[total] in bytes for a file,
 * in pieces for HLS ([total] < 0 = unknown). [uri] is where a file is being written, so an
 * interrupted download continues instead of starting over.
 */
class QueueItem(
    val id: Long,
    val url: String,
    val name: String,
    val folder: String,
    val hls: Boolean = false,
    val audioUrl: String? = null,
    val headers: Map<String, String> = emptyMap(),
) {
    @Volatile var status = QueueStatus.WAITING
    @Volatile var done = 0L
    @Volatile var total = -1L
    @Volatile var error: String? = null
    @Volatile var note: String? = null
    @Volatile var uri: String? = null

    fun toJson(): JSONObject = JSONObject().apply {
        put("id", id); put("url", url); put("name", name); put("folder", folder); put("hls", hls)
        audioUrl?.let { put("audio", it) }
        put("headers", JSONObject(headers))
        put("status", status.name); put("done", done); put("total", total)
        error?.let { put("error", it) }
        note?.let { put("note", it) }
        uri?.let { put("uri", it) }
    }

    companion object {
        fun fromJson(o: JSONObject): QueueItem {
            val h = o.optJSONObject("headers")
            val headers = h?.keys()?.asSequence()?.associateWith { h.getString(it) } ?: emptyMap()
            return QueueItem(
                o.getLong("id"), o.getString("url"), o.getString("name"), o.optString("folder"),
                o.optBoolean("hls"), o.optString("audio").ifEmpty { null }, headers,
            ).apply {
                status = runCatching { QueueStatus.valueOf(o.optString("status")) }.getOrDefault(QueueStatus.WAITING)
                done = o.optLong("done")
                total = o.optLong("total", -1)
                error = o.optString("error").ifEmpty { null }
                note = o.optString("note").ifEmpty { null }
                uri = o.optString("uri").ifEmpty { null }
            }
        }
    }
}

/**
 * The download queue shared by the screens and [DownloadService]. Holds any number of items
 * (hundreds are fine), keeps them in a file so the queue survives closing the app, and hands
 * items to the service one by one.
 */
object DownloadQueue {

    private val items = ArrayList<QueueItem>()
    private var file: File? = null
    private var nextId = 1L
    private val listeners = CopyOnWriteArraySet<() -> Unit>()

    /** Loads the saved queue once. Downloads that were running when the app died wait again. */
    @Synchronized
    fun init(dir: File) {
        if (file != null) return
        val f = File(dir, "queue.json")
        file = f
        if (!f.exists()) return
        try {
            val arr = JSONArray(f.readText())
            for (i in 0 until arr.length()) {
                val item = QueueItem.fromJson(arr.getJSONObject(i))
                if (item.status == QueueStatus.RUNNING) item.status = QueueStatus.WAITING
                items += item
            }
            nextId = (items.maxOfOrNull { it.id } ?: 0) + 1
        } catch (_: Exception) {
            // A damaged queue file is not worth crashing over; start with an empty queue.
        }
    }

    fun addListener(l: () -> Unit) = listeners.add(l)
    fun removeListener(l: () -> Unit) = listeners.remove(l)

    @Synchronized
    fun newId() = nextId++

    @Synchronized
    fun add(list: List<QueueItem>) {
        items += list
        changed()
    }

    @Synchronized
    fun snapshot(): List<QueueItem> = items.toList()

    @Synchronized
    fun count(status: QueueStatus) = items.count { it.status == status }

    @Synchronized
    fun hasWork() = items.any { it.status == QueueStatus.WAITING || it.status == QueueStatus.RUNNING }

    /** Next waiting item, marked as running; null when nothing is left. */
    @Synchronized
    fun takeNext(): QueueItem? {
        val item = items.firstOrNull { it.status == QueueStatus.WAITING } ?: return null
        item.status = QueueStatus.RUNNING
        item.error = null
        changed()
        return item
    }

    @Synchronized
    fun finish(item: QueueItem, status: QueueStatus, error: String? = null) {
        // A cancel that arrived while the download was finishing wins.
        if (item.status != QueueStatus.CANCELLED) item.status = status
        item.error = error
        changed()
    }

    @Synchronized
    fun retry(item: QueueItem) {
        if (item.status == QueueStatus.FAILED || item.status == QueueStatus.CANCELLED) {
            item.status = QueueStatus.WAITING
            item.error = null
            changed()
        }
    }

    @Synchronized
    fun retryFailed() = items.filter { it.status == QueueStatus.FAILED }.forEach { retry(it) }

    @Synchronized
    fun cancel(item: QueueItem) {
        if (item.status == QueueStatus.WAITING || item.status == QueueStatus.RUNNING) {
            item.status = QueueStatus.CANCELLED
            changed()
        }
    }

    @Synchronized
    fun cancelAll() = items.filter { it.status == QueueStatus.WAITING || it.status == QueueStatus.RUNNING }.forEach { cancel(it) }

    /** Removes items from the list; returns them so unfinished files can be cleaned up. */
    @Synchronized
    fun remove(predicate: (QueueItem) -> Boolean): List<QueueItem> {
        val gone = items.filter { it.status != QueueStatus.RUNNING && predicate(it) }
        items.removeAll(gone.toSet())
        changed()
        return gone
    }

    /** Saves the queue and tells the screens. Progress ticks don't call this — screens poll. */
    @Synchronized
    fun changed() {
        file?.let { f ->
            try {
                val arr = JSONArray()
                items.forEach { arr.put(it.toJson()) }
                val tmp = File(f.path + ".tmp")
                tmp.writeText(arr.toString())
                tmp.renameTo(f)
            } catch (_: Exception) {
            }
        }
        listeners.forEach { it() }
    }

    /** For tests. */
    @Synchronized
    internal fun reset() {
        items.clear()
        file = null
        nextId = 1
    }
}
