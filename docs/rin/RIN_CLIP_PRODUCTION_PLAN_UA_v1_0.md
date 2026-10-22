# РІН — ПЛАН ВИРОБНИЦТВА КЛІПІВ v1.0

**Дата:** 22.10.2026
**Статус:** робочий документ; доповнює Концепцію v1.0 (розд. 9.4а, 9.5, 12.1д).
**Призначення:** шаблон промптів, журнал промптів і план кліпів першої черги — готове завдання на перші генерації.

Позначки: ЗАТВЕРДЖЕНО / РОБОЧЕ (міняється за результатами тестів).

---

## 1. ШАБЛОН ПРОМПТУ ДЛЯ KLING (РОБОЧЕ)

Промпт складається з фіксованих блоків і одного змінного — опису дії. Блоки не переписуються від кліпу до кліпу: так результати порівнювані, а журнал має сенс.

```
[ДІЯ]        ← єдиний змінний блок: одна дія, мала амплітуда, 1–3 речення
[ОБЛИЧЧЯ]    Mouth stays closed the entire time: no speaking, no lip movement.
             Calm, slightly stern neutral expression, eyes open, looking at the viewer.
[ТІЛО]       Legs, feet, hips and head position stay still. Movement is compact and
             direct, elbows stay close to the body, hands never leave the body area.
[ТЕМП]       Slow, smooth motion, sharp details, no motion blur.
[КАМЕРА]     Static camera, locked-off, no camera movement, no zoom, full body in frame.
[ФОН]        Flat solid green background, no shadows, no floor, no gradient.
[СТАЛІСТЬ]   Character, face, hair and outfit stay exactly the same.
```

**Avoid (негативний промпт; в API — поле `negative_prompt`, на сайті — в кінець промпту після слова «Avoid:»):**
```
talking, open mouth, lip sync, singing, wide arm swing, arm moving out to the side,
both arms dropping, motion blur, camera movement, zoom, pan, walking, turning around,
extra hands, deformed fingers, outfit change, open collar, unbuttoned shirt,
skirt slit on the right side, second skirt slit, background change, shadows,
glowing screen, reflections, glare, text, watermark
```

**Налаштування за замовчуванням (ЗАТВЕРДЖЕНО / РОБОЧЕ):**

| Параметр | Чернетка | Чистовик |
|---|---|---|
| Модель | Kling 3.0 **Std** | Kling 3.0 **Pro** (або 4.0 для маршрутів через ключові кадри) |
| Роздільність | 720p | 1080p |
| Тривалість | мінімальна (3 с; цикли — 5 с) | та сама, що в схваленій чернетці |
| Звук | вимкнено | вимкнено |
| Style kit / стиль | жодного | жодного |
| `cfg_scale` (API) | 0,5 → якщо модель «вигадує» — 0,7–0,8 | як у схваленій чернетці |
| Seed (API) | записати | той самий, що в чернетці |
| Кадри | 1008×1792, фон #00FF00, ≤2 МП | ті самі файли |

**Блок [ОБЛИЧЧЯ] для кліпів, де рот МАЄ рухатися** (кліп «говорить»):
```
She speaks calmly: her mouth opens and closes naturally in a steady rhythm as if talking,
no exaggerated expressions. Everything else stays still.
```

**Блок для кліпів з планшетом (П3):** додати до [ДІЯ]: `She holds a thin dark tablet in a slim dark case, screen facing her; matte screen, no screen glow, no reflections, no glare.`

### 1.1 Правила опису дії
- Одна дія. Якщо в описі з'явилося «потім» — це два кліпи.
- Дієслова малої амплітуди: *rises, lowers, tilts, shifts, glances, nods slightly*. Уникати: *swings, throws, spins, jumps*.
- Для переходу між позами описувати **кінцеву позу** так само, як вона намальована на кінцевому кадрі (рука на рівні обличчя, долоня до глядача тощо).
- Наприкінці кожного переходу: `Then she holds the final pose still.` — дає моделі час точно прийти в кінцевий кадр.
- Не згадувати емоцію, яка потребує рота (усмішка з зубами, сміх). Усмішка — лише `slight closed-mouth smile`.

---

## 2. ЖУРНАЛ ПРОМПТІВ

Формат запису: `ID кліпу | модель/режим | кадри | промпт (лише [ДІЯ]) | результат | вердикт | висновок`. Фіксовані блоки не повторюємо, лише відхилення від шаблону.

| ID | Модель | Кадри | [ДІЯ] | Результат | Вердикт | Висновок |
|---|---|---|---|---|---|---|
| office_P0_P0_idle_01 | Kling 3.0 Pro, 1080p, 5 с, через Artlist (без негативу) | П0 → П0 | «subtle idle: slow calm breathing, natural eye blinks, tiny weight shift, hair sways slightly» | фігура стабільна, фон чистий, збіг силуету 99%; **але** двічі відкриває рот (1,3–1,7 с, 3,7–4,3 с) і заплющує очі ~1 с | відхилено як idle; **прийнято як «зітхання від нудьги»** | без явного «mouth closed» модель додає розмову; «natural blinks» без «quick» дає довге заплющення |
| office_P0_P1_raise_01 | Kling 3.0, 1080p, 5 с, Artlist | П0 → П1 | «calmly uncrosses arms, right hand rises to face level, open palm, left arm relaxes down, slight reserved smile, mouth closed» | рот рухається 1,3–2,6 с; широкий змах рукою вбік перед підйомом, рука виходить за кадр; розмиття кисті (жовта після despill) | **відхилено** | «mouth closed» усередині довгого речення не працює; без «elbow close to body» модель робить театральний змах; без «no motion blur» швидкий рух розмитий |
| office_P0_P1_raise_02 | Kling 3.0, 1080p, 5 с, Artlist | П0 → П1 | окремим першим рядком «Mouth stays closed the entire time: no speaking…»; «forearm rises straight up in front of her chest, elbow close to body… no wide swing»; «no motion blur»; «holds the final pose still» | рука йде прямо, в кадрі; розмиття слабке; збіг крайніх кадрів 99%; погляд убік 0,7–3,3 с (не просили, але пасує характеру); рот 2–3 рази відкривається 3,6–4,6 с | **умовно прийнято** (рішення власника відкрите: прийняти з голосом наприкінці або перегенерувати) | окремий рядок про рот зменшує, але не прибирає рух губ → потрібен негатив і/або вищий cfg через API; «holds the final pose still» працює |

**Висновки для шаблону (вже враховані вище):** рот — окремим першим реченням + негатив; рука — «in front of her chest, elbow close to body»; темп — «slow, smooth, no motion blur»; кінець — «holds the final pose still».

**Що перевірити наступними тестами (зі звіту про сервіси):** Kling 3.0 через API з `negative_prompt` і `cfg_scale` 0,8 проти 0,5 на тій самій парі кадрів; чи вимикається звук у Kling 4.0; чи достатньо чернетки Std 720p для оцінки.

---

## 3. ПЛАН КЛІПІВ ПЕРШОЇ ЧЕРГИ

### 3.1 Пози, які потрібні першими

| Поза | Опис | Образ | Статус | Джерело |
|---|---|---|---|---|
| **П0** | руки схрещені, нейтральний погляд (хаб) | офіс | є | `kling_start_idle_1008x1792.png` |
| **П1** | права рука піднята до обличчя, долоня до глядача, легка усмішка | офіс | є | `kling_wave_peak_1008x1792.png` |
| **П2** | руки в боки, суворий погляд | офіс | **ChatGPT** | prompt у 3.4 |
| **П4** | руки опущені вздовж тіла, нейтральна (проміжна «пауза-поза»; також еталон для спіймана/збентежена) | офіс | **ChatGPT** | prompt у 3.4 |
| **П5** | руки схрещені, погляд убік, легкий рум'янець (збентежена) | офіс | **ChatGPT** | prompt у 3.4 |

П3 (планшет), домашній образ (Д0 + кава), святкові пози — друга черга.

### 3.2 Кліпи першої черги (з пріоритетами)

Нумерація — порядок роботи. «М» = виходить монтажем, без генерації. Тривалість — для генерації; у бібліотеці після ретайму вона інша.

| № | ID | Перехід | Що відбувається | Три-валість | Як отримуємо | Навіщо першим |
|---|---|---|---|---|---|---|
| 1 | office_P0_P0_idle_01 | П0→П0 цикл | дихання, одне швидке кліпання, рот закритий | 5 с | **перегенерація** (чернетка → чистовик) | грає 90% часу |
| 2 | office_P0_P0_sigh_01 | П0→П0 | зітхання від нудьги, заплющує очі | 5 с | **є** (перший тест idle) | рідкісний idle, уже готово |
| 3 | office_P0_P1_raise_01 | П0→П1 | піднімає руку | 3–5 с | є умовно / перегенерація через API | привітання, ранок |
| 4 | office_P1_P1_wave_01 | П1→П1 цикл | махає 2 рази, рот закритий | 3 с | генерація | привітання |
| 5 | office_P1_P0_lower_01 | П1→П0 | опускає руку, схрещує | 3 с | **М: реверс №3** → перевірка на око; якщо волосся/рука «відскакують» — генерація | привітання |
| 6 | office_P0_P0_talk_01 | П0→П0 цикл | рот рухається, як при мовленні | 5 с | генерація (блок [ОБЛИЧЧЯ] для мовлення) | будь-яка фраза |
| 7 | office_P0_P0_blink_look_01 | П0→П0 | коротко помічає глядача: погляд на нього і знову вбік | 3 с | генерація | наведення курсору |
| 8 | office_P0_P0_poke1_01 | П0→П0 | здивовано: легке здригання, брови вгору, «а?» (рот закритий) | 3 с | генерація | тицяння 1 |
| 9 | office_P0_P0_poke2_01 | П0→П0 | роздратовано: надуті щоки, насуплені брови | 3 с | генерація | тицяння 2–3 |
| 10 | office_P0_P0_poke3_01 | П0→П0 | відвертає голову «хмф!», потім повертає | 3 с | генерація | тицяння часто |
| 11 | office_P0_P2_hands_hips_01 | П0→П2 | розплітає руки, ставить у боки | 3 с | генерація (чернетка обов'язково — руки з перекриття) | сварить |
| 12 | office_P2_P2_scold_01 | П2→П2 цикл | легке похитування, суворий погляд, рот закритий | 5 с | генерація | сварить (емоцію дає голос) |
| 13 | office_P2_P0_return_01 | П2→П0 | опускає руки, схрещує | 3 с | **М: реверс №11** → перевірка; інакше генерація | сварить |
| 14 | office_P0_P5_shy_01 | П0→П5 | відводить погляд, легкий рум'янець | 3 с | генерація | похвала, погладжування |
| 15 | office_P5_P0_return_01 | П5→П0 | повертає погляд | 3 с | **М: реверс №14** | — |
| 16 | office_P0_P0_yawn_01 | П0→П0 | позіхає (рот відкритий — це виняток, описати явно), прикриває рукою | 3–5 с | генерація | нудьга / AFK |
| 17 | office_P0_P0_doze_01 | П0→П0 цикл | дрімає стоячи: очі заплющені, голова ледь хитається | 5 с | генерація; або **М: цикл** із середини №2 | AFK довго |
| 18 | office_P0_P4_drop_01 | П0→П4 | опускає руки вздовж тіла | 3 с | генерація | проміжна поза; вихід за кадр |
| 19 | office_P4_P0_cross_01 | П4→П0 | схрещує руки | 3 с | **М: реверс №18** | — |
| 20 | office_P4_P4_fix_shirt_01 | П4→П4 | невдоволено поправляє сорочку | 3 с | генерація | після перетягування |
| 21 | office_P4_exit_right_01 | П4→за кадр | повертається боком і виходить праворуч | 3 с | генерація | переодягання, ховання |
| 22 | office_enter_right_P4_01 | за кадр→П4 | заходить справа, стає в П4 | 3 с | **М: реверс №21** → перевірка (хода назад виглядає неприродно → генерація) | повернення |

**Разом:** 22 кліпи, з них **генерацій 15–17**, решта монтажем. З урахуванням чернеток (у середньому 2 на кліп) і чистовика: ≈ 15 × (2 × $0,25 + $0,45) ≈ **$14–16** на Kling 3.0 через API, без урахування невдалих спроб; реалістично **$25–35**.

### 3.3 Порядок роботи (ЗАТВЕРДЖЕНО)
1. Згенерувати пози П2, П4, П5 у ChatGPT (3.4), прогнати `check_pose`, вирівняти.
2. Кліпи 1, 3, 4, 6 — спершу, бо вони грають найчастіше; на них же відкалібрувати cfg і негатив через API.
3. Далі тицяння (8–10) і сварка (11–13).
4. Реверси (5, 13, 15, 19, 22) перевірити на око одразу після прямого кліпу: якщо не годиться — додати в чергу генерації.
5. Решта за списком. Кожен кліп проходить: чернетка Std 720p → картка `check_clip` → рішення → чистовик Pro 1080p → `key` → `retime` → `pack` → папка в `content/clips/`.
6. Журнал промптів (розд. 2) поповнюється після кожного дубля.

### 3.4 Prompt для ChatGPT: нові пози

Спільна частина (прикріпити `kling_start_idle_1008x1792.png`, формат portrait):
```
Use the attached image as the exact reference. Same character, same face, same art style,
same outfit, same camera, same framing and scale: full body, the character occupies the
same area of the image, feet in exactly the same place, same leg stance as in the reference.
Change only the arms and expression as described below.

Keep exactly: light-blue shirt fully buttoned including the top button, white collar and
white cuffs, small white name plate on her left chest, ID badge on an orange lanyard;
black high-waisted pencil skirt with ONE slit only, on her left side (viewer's right);
tan sheer pantyhose; black pumps with red soles; dark navy hair with a top bun and long
ponytail, side strands, turquoise eyes. Anime style, clean lines, no photorealistic skin.
Background: flat solid pure green (#00FF00), no shadows, no floor, no gradient.
No text, no watermark.
```

Змінна частина:

- **П2 (руки в боки):**
  `Both hands on her hips, elbows out, shoulders square. Stern, slightly annoyed expression: brows lowered, MOUTH CLOSED, eyes on the viewer.`
- **П4 (руки опущені):**
  `Both arms hang relaxed along her body, hands open and relaxed near her thighs. Neutral calm expression, mouth closed, eyes on the viewer.`
- **П5 (збентежена):**
  `Arms crossed exactly as in the reference. Head turned slightly away, eyes looking to the side (away from the viewer), faint blush on the cheeks, mouth closed, slightly embarrassed expression.`

Після генерації — `check_pose`: силует ніг і голови має збігатися з П0 на ≥98%, фон вирівнюється до #00FF00, розмір 1008×1792.

---

## 4. ОБЛІК (шаблон)

Таблиця ведеться у файлі `clips_ledger.csv` (або аркуші): `ID | поза_з | поза_в | теги | пріоритет | стан (план / поза / чернетка / схвалено / чистовик / у бібліотеці) | дублів | вартість | джерело (генерація / реверс №… / нарізка №…) | нотатки`.

Після кожних ~20 кліпів — перегляд: які типи дій забирають найбільше дублів і чи можна їх спростити (розд. 9.4а Концепції).
