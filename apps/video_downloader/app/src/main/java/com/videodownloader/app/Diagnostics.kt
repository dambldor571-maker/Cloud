package com.videodownloader.app

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/** What the page looked like to the scanner (filled from the collecting script). */
data class PageInfo(
    val title: String = "",
    val videoTags: Int = 0,
    val blobVideos: Int = 0,
    val iframes: List<String> = emptyList(),
    val players: List<String> = emptyList(),
    val hasPassword: Boolean = false,
    val htmlLength: Int = 0,
)

/**
 * Diagnostic report for one scan and the downloads started from it.
 * Holds raw facts plus a timeline; [render] turns them into text the user can send
 * for analysis, with the app's own guesses about the cause on top.
 * Cookie values are never written — only whether cookies were present.
 */
class Diagnostics(val pageUrl: String, private val environment: String) {

    var finalUrl = pageUrl
    var mainError: String? = null
    var mainHttpStatus = 0
    var scriptFailed = false
    var page: PageInfo? = null
    var requestCount = 0
    var mediaRequests: List<String> = emptyList()
    var videos: List<Video> = emptyList()
    var streams: List<String> = emptyList()
    var hadCookies = false
    /** Ad-network requests that were blocked while scanning. */
    var blockedRequests: List<String> = emptyList()
    /** Filter verdict per video URL ("" = a real video). */
    var verdicts: Map<String, String> = emptyMap()

    /** Probe results per video URL: HTTP status (0 = network error) and a short note. */
    val probes = LinkedHashMap<String, Pair<Int, String>>()
    /** Download problems: file name → (reason code, explanation). */
    val downloadFailures = LinkedHashMap<String, Pair<Int, String>>()
    /** Downloads that "succeeded" but brought something that is not a video. */
    val suspiciousDownloads = LinkedHashMap<String, String>()

    private val timeline = mutableListOf<String>()
    private val clock = SimpleDateFormat("HH:mm:ss", Locale.US)

    fun event(text: String) {
        timeline += "${clock.format(Date())}  $text"
    }

    /** True when there is something worth sending a report about. */
    val hasProblem: Boolean
        get() = mainError != null || mainHttpStatus >= 400 || scriptFailed ||
            (page != null && videos.isEmpty()) ||
            probes.values.any { it.first !in 200..299 } ||
            downloadFailures.isNotEmpty() || suspiciousDownloads.isNotEmpty()

    /** The app's own reading of the facts, most likely cause first. */
    fun hints(): List<String> {
        val h = mutableListOf<String>()
        val p = page
        val title = p?.title?.lowercase() ?: ""
        val antiBot = listOf("just a moment", "attention required", "captcha", "access denied", "перевірка")
            .any { it in title }

        mainError?.let { h += "Сторінка не відкрилася: $it. Перевірте адресу та інтернет." }
        if (mainHttpStatus >= 400) h += "Сервер відповів на сторінку кодом $mainHttpStatus — ${httpMeaning(mainHttpStatus)}"
        if (antiBot) h += "Сайт показав захист від ботів / капчу («${p?.title}») замість вмісту — сторінку не вдалося відкрити автоматично."
        if (scriptFailed) h += "Скрипт пошуку не виконався на сторінці (сайт блокує JavaScript або сторінка не довантажилась)."

        if (videos.isNotEmpty() && verdicts.size == videos.size && verdicts.values.all { it.isNotEmpty() }) {
            h += "Усі знайдені відео фільтр вважає рекламою або прев'ю інших відео — справжнє відео, мабуть, у потоці або підвантажується після «Play»."
        }
        if (p != null && videos.isEmpty()) {
            when {
                p.blobVideos > 0 -> h += "Плеєр отримує відео частинами через blob: (MediaSource) — окремого файлу немає, скачати так неможливо."
                streams.isNotEmpty() -> h += "Відео є лише як потік HLS/DASH (${streams.size} шт.) — цей тип скачування не підтримується."
                p.iframes.isNotEmpty() -> h += "Відео, ймовірно, у вбудованому плеєрі з іншого сайту (iframe): ${p.iframes.first()}. Спробуйте відкрити цю адресу напряму."
                p.hasPassword -> h += "На сторінці є форма входу — відео, мабуть, доступне лише після входу в акаунт."
                p.videoTags > 0 -> h += "Є теги <video>, але без адреси файлу — плеєр, імовірно, підвантажує відео лише після натискання «Play»."
                else -> h += "На сторінці немає ні відео-тегів, ні посилань на відеофайли. Можливо, відео з'являється після дії користувача або це не та сторінка."
            }
            if (p.players.isNotEmpty()) h += "Виявлені плеєри/бібліотеки: ${p.players.joinToString()}."
        }

        probes.forEach { (url, r) ->
            if (r.first !in 200..299) h += "Перевірка файлу ${shortUrl(url)}: ${if (r.first == 0) r.second else "HTTP ${r.first} — ${httpMeaning(r.first)}"}"
        }
        downloadFailures.forEach { (name, r) -> h += "Скачування «$name» не вдалося: ${r.second}" }
        suspiciousDownloads.forEach { (name, why) -> h += "«$name» скачався, але це не відео: $why" }
        return h
    }

    fun render(): String = buildString {
        appendLine("=== Звіт діагностики «Завантажувач відео» ===")
        appendLine(environment)
        appendLine()
        appendLine("--- Ймовірні причини (автоматично) ---")
        val h = hints()
        if (h.isEmpty()) appendLine("Проблем не виявлено.") else h.forEach { appendLine("• $it") }
        appendLine()
        appendLine("--- Сторінка ---")
        appendLine("Адреса: $pageUrl")
        if (finalUrl != pageUrl) appendLine("Після переадресацій: $finalUrl")
        appendLine("HTTP-статус сторінки: ${if (mainHttpStatus == 0) "200/невідомо" else mainHttpStatus}")
        mainError?.let { appendLine("Помилка завантаження: $it") }
        page?.let {
            appendLine("Заголовок: ${it.title}")
            appendLine("Розмір HTML: ${it.htmlLength} символів")
            appendLine("Тегів <video>: ${it.videoTags}, з них blob: ${it.blobVideos}")
            appendLine("Форма входу (пароль): ${if (it.hasPassword) "так" else "ні"}")
            if (it.players.isNotEmpty()) appendLine("Плеєри: ${it.players.joinToString()}")
            if (it.iframes.isNotEmpty()) {
                appendLine("Вбудовані фрейми (${it.iframes.size}):")
                it.iframes.forEach { f -> appendLine("  $f") }
            }
        } ?: appendLine("Дані сторінки не отримано${if (scriptFailed) " (скрипт не виконався)" else ""}")
        appendLine("Cookies для сайту: ${if (hadCookies) "є" else "немає"}")
        appendLine()
        if (blockedRequests.isNotEmpty()) {
            appendLine("--- Заблоковано рекламних запитів: ${blockedRequests.size} ---")
            blockedRequests.take(10).forEach { appendLine("  ${shortUrl(it, 150)}") }
            appendLine()
        }
        appendLine("--- Мережеві запити сторінки: $requestCount, схожі на медіа: ${mediaRequests.size} ---")
        mediaRequests.forEach { appendLine("  ${shortUrl(it, 200)}") }
        appendLine()
        appendLine("--- Знайдені відео: ${videos.size} ---")
        videos.forEach { v ->
            val probe = probes[v.url]
            val probeText = when {
                probe == null -> "не перевірено"
                probe.first == 0 -> "помилка: ${probe.second}"
                else -> "HTTP ${probe.first} ${probe.second}"
            }
            appendLine("  ${shortUrl(v.url, 200)}")
            verdicts[v.url]?.takeIf { it.isNotEmpty() }?.let { appendLine("     приховано фільтром — $it") }
            appendLine("     якість: ${v.quality.ifEmpty { "?" }}, тип: ${v.mime.ifEmpty { "?" }}, " +
                "розмір: ${VideoFinder.humanSize(v.size).ifEmpty { "?" }}, прев'ю: ${if (v.poster.isEmpty()) "кадр з відео" else "картинка сторінки"}, " +
                "перевірка: $probeText")
        }
        if (streams.isNotEmpty()) {
            appendLine("Потоки HLS/DASH: ${streams.size}")
            streams.take(10).forEach { appendLine("  ${shortUrl(it, 200)}") }
        }
        appendLine()
        appendLine("--- Хронологія ---")
        timeline.forEach { appendLine(it) }
    }

    companion object {
        fun shortUrl(url: String, max: Int = 120) = if (url.length <= max) url else url.take(max - 1) + "…"

        fun httpMeaning(code: Int): String = when (code) {
            400 -> "сервер не прийняв запит"
            401 -> "потрібен вхід в акаунт"
            403 -> "доступ заборонено: сайт захищає файли від скачування поза плеєром (перевірка Referer/cookies/токена) або блокує бота"
            404 -> "файл не знайдено — посилання застаріло або тимчасове"
            405 -> "сервер не підтримує такий тип запиту (для перевірки це не критично)"
            410 -> "посилання вже недійсне (тимчасовий токен закінчився)"
            416 -> "сервер не підтримує докачування частинами"
            429 -> "забагато запитів — сайт тимчасово обмежив доступ"
            451 -> "недоступно з юридичних причин у вашому регіоні"
            in 500..599 -> "помилка на боці сервера, спробуйте пізніше"
            else -> "неочікувана відповідь сервера"
        }

        /** Meaning of DownloadManager.COLUMN_REASON for a failed download. */
        fun downloadFailure(reason: Int): String = when (reason) {
            in 400..599 -> "сервер відповів HTTP $reason — ${httpMeaning(reason)}"
            1000 -> "невідома помилка менеджера завантажень"
            1001 -> "помилка запису файлу (пам'ять або дозвіл на збереження)"
            1002 -> "сервер відповів незрозумілим HTTP-кодом"
            1004 -> "з'єднання обірвалося під час передачі даних"
            1005 -> "забагато переадресацій — сервер, мабуть, вимагає вхід або перевірку"
            1006 -> "недостатньо місця на телефоні"
            1007 -> "сховище недоступне (карта пам'яті вийнята?)"
            1008 -> "не вдалося продовжити перерване завантаження — сервер не підтримує докачування"
            1009 -> "файл з такою назвою вже існує"
            else -> "код помилки $reason"
        }

        /** Meaning of DownloadManager.COLUMN_REASON for a paused download. */
        fun downloadPause(reason: Int): String = when (reason) {
            1 -> "очікує повтору після мережевої помилки"
            2 -> "очікує підключення до мережі"
            3 -> "чекає Wi-Fi (файл завеликий для мобільних даних)"
            else -> "призупинено (код $reason)"
        }
    }
}
