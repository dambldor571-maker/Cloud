package com.videodownloader.app

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.view.ViewGroup
import android.widget.BaseAdapter
import android.widget.Button
import android.widget.ListView
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import java.io.File

/**
 * The download queue: every video with its state and progress. Handles hundreds of items —
 * the list only draws what is on screen and refreshes once a second.
 */
class QueueActivity : Activity() {

    private lateinit var summary: TextView
    private lateinit var list: ListView
    private lateinit var empty: TextView
    private val main = Handler(Looper.getMainLooper())
    private var items = listOf<QueueItem>()
    private val adapter = QueueAdapter()

    private val refresher = object : Runnable {
        override fun run() {
            refresh()
            main.postDelayed(this, 1000)
        }
    }
    private val onChange: () -> Unit = { main.post { refresh() } }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_queue)
        title = getString(R.string.queue_title)
        DownloadQueue.init(filesDir)

        summary = findViewById(R.id.summary)
        list = findViewById(R.id.queueList)
        empty = findViewById(R.id.empty)
        list.adapter = adapter
        list.setOnItemClickListener { _, _, position, _ -> actions(items[position]) }

        findViewById<Button>(R.id.retryFailed).setOnClickListener {
            DownloadQueue.retryFailed()
            DownloadService.start(this)
        }
        findViewById<Button>(R.id.clearDone).setOnClickListener {
            DownloadQueue.remove { it.status == QueueStatus.DONE || it.status == QueueStatus.CANCELLED }
                .forEach { DownloadService.discardFile(this, it) }
        }
        findViewById<Button>(R.id.cancelAll).setOnClickListener {
            if (!DownloadQueue.hasWork()) return@setOnClickListener
            AlertDialog.Builder(this)
                .setMessage(getString(R.string.queue_cancel_all_confirm, DownloadQueue.count(QueueStatus.WAITING) + DownloadQueue.count(QueueStatus.RUNNING)))
                .setPositiveButton(R.string.queue_cancel_all) { _, _ -> DownloadQueue.cancelAll() }
                .setNegativeButton(R.string.close, null)
                .show()
        }
    }

    override fun onResume() {
        super.onResume()
        DownloadQueue.addListener(onChange)
        main.post(refresher)
        // Picks up a queue left from before the app was closed.
        DownloadService.start(this)
    }

    override fun onPause() {
        DownloadQueue.removeListener(onChange)
        main.removeCallbacks(refresher)
        super.onPause()
    }

    private fun refresh() {
        // Running first, then waiting, failed, done — the newest at the top within each.
        val order = listOf(QueueStatus.RUNNING, QueueStatus.WAITING, QueueStatus.FAILED, QueueStatus.DONE, QueueStatus.CANCELLED)
        items = DownloadQueue.snapshot().sortedWith(compareBy<QueueItem> { order.indexOf(it.status) }.thenBy { it.id })
        val count = { s: QueueStatus -> items.count { it.status == s } }
        summary.text = getString(
            R.string.queue_summary,
            count(QueueStatus.RUNNING), count(QueueStatus.WAITING), count(QueueStatus.DONE), count(QueueStatus.FAILED), items.size,
        )
        empty.visibility = if (items.isEmpty()) View.VISIBLE else View.GONE
        adapter.notifyDataSetChanged()
    }

    private fun statusText(item: QueueItem): String = when (item.status) {
        QueueStatus.WAITING -> getString(R.string.queue_waiting) + if (item.done > 0) " · ${getString(R.string.queue_resume, VideoFinder.humanSize(item.done))}" else ""
        QueueStatus.RUNNING -> DownloadService.progressText(item)
        QueueStatus.DONE -> getString(R.string.queue_done) + (item.note?.let { " — ⚠ $it" } ?: "")
        QueueStatus.FAILED -> getString(R.string.queue_failed, item.error ?: "")
        QueueStatus.CANCELLED -> getString(R.string.queue_cancelled)
    }

    private fun actions(item: QueueItem) {
        val options = mutableListOf<Pair<String, () -> Unit>>()
        when (item.status) {
            QueueStatus.DONE -> options += getString(R.string.queue_open) to { open(item) }
            QueueStatus.FAILED, QueueStatus.CANCELLED -> options += getString(R.string.queue_retry) to {
                DownloadQueue.retry(item)
                DownloadService.start(this)
            }
            QueueStatus.WAITING, QueueStatus.RUNNING -> options += getString(R.string.queue_cancel) to { DownloadQueue.cancel(item) }
        }
        if (item.status != QueueStatus.RUNNING) options += getString(R.string.queue_remove) to {
            DownloadQueue.remove { it === item }.forEach { DownloadService.discardFile(this, it) }
        }
        AlertDialog.Builder(this)
            .setTitle(item.name)
            .setMessage("${statusText(item)}\n\nDownload/VideoDownloader/${item.folder}\n${item.url}")
            .setItems(options.map { it.first }.toTypedArray()) { _, which -> options[which].second() }
            .setNegativeButton(R.string.close, null)
            .show()
    }

    private fun open(item: QueueItem) {
        val target = item.uri ?: return
        val uri = if (target.startsWith("content:")) Uri.parse(target) else null
        if (uri == null) {
            Toast.makeText(this, getString(R.string.queue_saved_at, File(target).parent ?: target), Toast.LENGTH_LONG).show()
            return
        }
        try {
            startActivity(Intent(Intent.ACTION_VIEW).setDataAndType(uri, "video/*").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
        } catch (_: Exception) {
            Toast.makeText(this, R.string.queue_no_player, Toast.LENGTH_LONG).show()
        }
    }

    private inner class QueueAdapter : BaseAdapter() {
        override fun getCount() = items.size
        override fun getItem(position: Int) = items[position]
        override fun getItemId(position: Int) = items[position].id

        override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
            val view = convertView ?: layoutInflater.inflate(R.layout.item_queue, parent, false)
            val item = items[position]
            view.findViewById<TextView>(R.id.name).text = item.name
            view.findViewById<TextView>(R.id.state).text = "${item.folder} · ${statusText(item)}"
            val bar = view.findViewById<ProgressBar>(R.id.progress)
            if (item.status == QueueStatus.RUNNING) {
                bar.visibility = View.VISIBLE
                bar.isIndeterminate = item.total <= 0
                if (item.total > 0) bar.progress = (item.done * 1000 / item.total).toInt()
            } else {
                bar.visibility = View.GONE
            }
            view.alpha = if (item.status == QueueStatus.CANCELLED) 0.5f else 1f
            return view
        }
    }
}
