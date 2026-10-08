# Glory of Generals 3: WW2 SLG: статичний розбір APK

Дата аналізу: 2026-10-08. Метод: статичний аналіз (androguard, jadx, strings, readelf).
Гру не запускали, мережевий трафік не перехоплювали.

## Файл

| Параметр | Значення |
|---|---|
| Пакет | `com.easytech.iron.android` (внутрішня назва проєкту: **iron**) |
| Версія | 1.7.12 (versionCode 26), остання на APKPure |
| Джерело | APKPure (XAPK), split-збірка з Google Play |
| SHA-256 XAPK | `92358b83eb2105f9493b473aa38869cc6bcba3117e708d4cc528d23f74d86bfe` |
| Склад | base APK 108 МБ (усі ресурси всередині) + `config.mdpi` |
| minSdk / targetSdk | 21 (Android 5.0) / 36 |
| Підпис | v1+v2+v3, `CN=EasyTech, L=Suzhou, ST=Jiangsu`, 2020-08-18 → 2120 |
| SHA-256 сертифіката | `64d4e0469a7a8d0cbb4918e795cc0b540043810dfc314d68dea283e4e88e192d` |
| Штамп | `com.android.stamp.source = https://play.google.com/store` |

Ключ EasyTech інший, ніж у EW7: у кожної гри свій. Обидва split-файли підписані одним ключем,
ознак модифікації немає.

## Архітектура

- Той самий рушій EasyTech, старіша гілка: `libiron.so` (9.7 / 7.0 МБ), лише **OpenGL ES 2** (без GLES3 і OpenSL ES).
  Збірка: GCC 4.9 + clang 5/8.
- Java-шар: `IronActivity` + `com.easytech.lib.*` (той самий набір класів, що в EW7, але без `ecIdentity`/`ecRegister`).
- Вбудовано в `.so`: Protobuf, zlib/minizip, libcurl, **OpenSSL 1.1.1k**, **libpng 1.2.56 (грудень 2015)**.
- Ресурси: `assets/stage/` 459 файлів `.btl` (450 stage, 5 conquest, corps). Вони **не зашифровані**
  (бінарний формат, ентропія ~5). Також аудіо 18 МБ, зображення 12 МБ, мапи `.pkm`.
- Дані (`assets/data/*.json` 45 шт., `stringtable_*.ini`) **зашифровані** (ентропія 8.0).

## Дозволи

INTERNET, ACCESS_NETWORK_STATE, ACCESS_WIFI_STATE, `AD_ID`, `ACCESS_ADSERVICES_{AD_ID,ATTRIBUTION,TOPICS}`,
WAKE_LOCK, FOREGROUND_SERVICE, **SCHEDULE_EXACT_ALARM**, BILLING, c2dm RECEIVE, INSTALL_REFERRER.
Порівняно з EW7 **немає** READ_PHONE_STATE і POST_NOTIFICATIONS, але є SCHEDULE_EXACT_ALARM
(точні будильники, від WorkManager або локальних нагадувань).

## Сторонні SDK

Набір менший, ніж у EW7:

- **Реклама:** TradPlus (app `F74B8F85673A4DBD9DAFDBC6502DB330`, rewarded `53B51BEF7E7D34E9BA221EF69530CEE8`), TP ADX/CrossPro,
  Google AdMob (`ca-app-pub-3883584006538063~5602013600`), Meta Audience Network (`com.meta.analytics.dsp.uinode`
  + `assets/audience_network.dex`), IAB OMID.
- **Аналітика:** Firebase (Analytics, Remote Config, A/B, Installations, проєкт `glory-of-generals-3`), Facebook SDK.
- **Інше:** Google Play Games, Billing Library 8.0.0, Twitter SDK, ZXing, Picasso, Install Referrer.
- **Немає:** AppsFlyer, Mintegral, Chartboost.

Реклама тільки rewarded, керується сервером `iron.ieasytech.com/ad_video_support/google/`.

## Монетизація

- 40 товарів: `gog3_item*`, `gog3_general_pack_1..3`, `gog3_medal_*`, `gog3_medal_package_*`, `gog3_special_package_*`.
- Чек передається в нативний код, як в EW7.

## Сервери

- `iron.ieasytech.com`: статистика `/statistics/google/`, вікова перевірка `/age/?game=iron`, реклама, share.
- `world.gog3.easytechgame.com/gog3`: онлайн-частина.
- `idcert.ieasytech.cn/authentication/{check,identity,localcheck,useraction}`: китайська перевірка реального імені
  (в рушії, для CN-збірок).
- `ew6w.ieasytech.com/upgrade/google/`: оновлення.

## Безпека і приватність

| # | Знахідка | Ризик |
|---|---|---|
| 1 | `base-config cleartextTrafficPermitted="true"` (HTTP дозволено всюди), такий самий конфіг, як в EW7 | Середній |
| 2 | OpenSSL 1.1.1k, EOL (CVE-2021-3711, CVE-2022-0778, CVE-2023-0286) | Середній, теоретичний |
| 3 | **libpng 1.2.56** (2015, гілка 1.2 закрита). Відомі вади, напр. CVE-2016-10087 | Низький: PNG завантажуються з власних ресурсів |
| 4 | `android_id`, AAID; код для IMEI і SIM лишився, але без READ_PHONE_STATE не працює | Стандартний трекінг |
| 5 | Залишок налагодження `btn_cheat_unlock_exarmy` | Інформаційно |
| 6 | `unzipAPK` без захисту від zip-slip (не викликається), `allowBackup="true"` | Дуже низький |
| 7 | Експортований `com.facebook.FacebookContentProvider` | Стандартний для Facebook SDK |

Шкідливого коду не знайдено. Динамічне завантаження коду є лише у стандартних SDK (Meta AN, GMS).
`Runtime.exec` використовується лише для `getprop`/`/proc/version`.

## Порівняння з European War 7 (3.6.0)

| | Glory of Generals 3 | European War 7 |
|---|---|---|
| Розмір | 108 МБ | 515 МБ |
| Рушій | `libiron.so`, GLES2 | `libew7.so`, GLES2/3, OpenSL |
| Рекламних і трекінгових SDK | ~7 | ~11 (+AppsFlyer, Mintegral, Chartboost) |
| READ_PHONE_STATE | ні | так |
| Товарів IAP | 40 | 78 |
| Шифрування даних | JSON і рядки так, мапи `.btl` ні | JSON так |
| Застарілі бібліотеки | OpenSSL 1.1.1k, libpng 1.2.56 | OpenSSL 1.1.1k |
