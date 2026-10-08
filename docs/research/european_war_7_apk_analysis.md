# European War 7: Medieval: статичний розбір APK

Дата аналізу: 2026-10-08. Метод: статичний аналіз (androguard, jadx, strings, readelf).
Гру не запускали, мережевий трафік не перехоплювали.

## Файл

| Параметр | Значення |
|---|---|
| Пакет | `com.offline.strategy.europeanwar.middleage` |
| Версія | 3.6.0 (versionCode 67) |
| Джерело | APKPure (XAPK), split-збірка з Google Play |
| SHA-256 XAPK | `df91f6f0df903722f539ee02da94c05872c399cf2bff1ba3a804941fada07ee3` |
| Склад | base APK 29 МБ + `assetpack.apk` 485 МБ + config.{de,ja,ko,zh,xhdpi} |
| minSdk / targetSdk | 21 (Android 5.0) / 36 |
| Підпис | v1+v2+v3, `CN=EasyTech, L=Suzhou, ST=Jiangsu`, 2021-04-21 → 2121 |
| SHA-256 сертифіката | `e2652c7c2550a37b0aae7a57080c038a1955e779191b9d3452dbdaba6f844294` |
| Штамп | `com.android.stamp.source = https://play.google.com/store` |

Усі 7 split-файлів підписані одним ключем. Ознак модифікації немає.

## Архітектура

- Власний C++ рушій EasyTech: `lib/{arm64-v8a,armeabi-v7a}/libew7.so` (14 / 10 МБ), OpenGL ES 2/3, OpenSL ES.
- Тонкий Java-шар: `EW7Activity` і `com.easytech.lib.*` (~4 тис. рядків). Він передає в нативний код
  дотики, покупки, рекламу і вхід.
- Вбудовано в `.so`: Protobuf, libpng 1.6.48, zlib/minizip, libcurl, **OpenSSL 1.1.1k (березень 2021)**.
  Збірка: NDK r19c, clang 8/9.
- Ресурси: 186 `.ktx`, 538 `.pkm` (ETC1), 1901 `.btlx` (бої: 244 preview, 16 template, 14 conquer, 8 expedition),
  262 портрети генералів, `bgm.mp3`, 12 шрифтів `.otf`.
- Ігрові дані (`assets/data/*.json`, ~65 файлів: General, Pay, LuckyDraw, Troop, Equipment...) **зашифровані**
  (ентропія 8.0, без заголовка).

## Дозволи

INTERNET, ACCESS_NETWORK_STATE, ACCESS_WIFI_STATE, `AD_ID`, `ACCESS_ADSERVICES_{AD_ID,ATTRIBUTION,TOPICS}`,
READ_PHONE_STATE, WAKE_LOCK, FOREGROUND_SERVICE, POST_NOTIFICATIONS, BILLING, c2dm RECEIVE, INSTALL_REFERRER.
Без камери, мікрофона, геолокації, контактів і доступу до файлів.

## Сторонні SDK

- **Реклама:** TradPlus (медіація, app `FC45078CB2885E29342E13E7E835437C`, rewarded `29FD5D1DB7E84B6556484D84AFC843E8`),
  TP ADX, Google AdMob (`ca-app-pub-3883584006538063~5221284979`), Meta Audience Network (`assets/audience_network.dex`),
  Mintegral (mbridge), Chartboost + Chartboost Mediation (Helium), IAB OMID.
- **Аналітика й атрибуція:** Firebase (Analytics, Messaging, Remote Config, A/B, проєкт `european-war-7`),
  AppsFlyer (dev key у коді), Facebook SDK (`AutoLogAppEventsEnabled=true`, `AdvertiserIDCollectionEnabled=true`).
- **Інше:** Google Play Games, Credential Manager, Billing Library 8.0.0, Twitter SDK, ZXing, Picasso, Retrofit/OkHttp.

Реклама тільки rewarded (за бажанням гравця). Увімкнення керується сервером
`iron.ieasytech.com/ad_video_support/google/` і Remote Config (`advideo_type`, `general_purchase_show_type`).

## Монетизація

- 78 товарів `ew7_item1…ew7_item78`, тип `inapp`, підтвердження через acknowledge і consume.
- Чек (`originalJson` + підпис) передається в нативний код. Публічного ключа Play у бінарнику немає,
  тож перевірка, ймовірно, серверна (не підтверджено).

## Сервери

- `ma.ieasytech.com`: статистика `/statistics/google/`, прив'язка email, нагороди, `/popularization/ma/{announcement,mail,recommend,service}`.
- `world.ew7.easytechgame.com/ew7`: онлайн-частина (рейтинги, хмара).
- `iron.ieasytech.com`: налаштування реклами (передаються `android_id`, ID пристрою, версія ОС, країна).
- `ew6w.ieasytech.com/upgrade/google/`: оновлення.
- `pvp.ew6w.ieasytech.cn/isbnew7/*`: китайська перевірка реального імені й обмеження гри (у Google-збірці, схоже, не викликається).

## Безпека і приватність

| # | Знахідка | Ризик |
|---|---|---|
| 1 | `network_security_config`: `base-config cleartextTrafficPermitted="true"` (HTTP дозволено всюди) | Середній |
| 2 | OpenSSL 1.1.1k, EOL з 2023-09 (CVE-2021-3711, CVE-2022-0778, CVE-2023-0286) | Середній, теоретичний |
| 3 | `ecIdentity`: логін, пароль, ім'я і номер ID передаються в query-рядку GET (`/userlogin/?account=&pass=`) | Низький (мертвий код у Google-збірці) |
| 4 | Ідентифікатори: `android_id`, AAID, спроби IMEI і серійного номера SIM (на Android 10+ не працює) | Стандартний трекінг |
| 5 | Залишки налагодження: `btn_cheat_add_gold/medal/hawk`, тестові карти `testtp`, `yyztest` | Інформаційно |
| 6 | `unzipAPK` без захисту від zip-slip | Дуже низький (не викликається) |
| 7 | `allowBackup="true"` | Низький |

Шкідливого коду не знайдено. Немає завантаження стороннього DEX (крім стандартного для Meta AN),
SMS, accessibility чи прихованих сервісів. `Runtime.exec` використовується лише для `cat /proc/version`.
