# Unit Workshop — документація для агентів (Codex тощо)

Окрема Windows-програма на **Godot 4.3 (Forward+)**. Вона налаштовує 3D-модель
юніта і рендерить з неї спрайти для гри Hexfront (корінь репозиторію). Працює
тільки на ПК, мобільної версії немає. Користувацька інструкція — `README.md`
поруч, тут описано технічну частину.

## Правила роботи з власником проєкту

- Спілкування українською, коротко, варіанти давати як `☐ A / ☐ B / ☐ C`,
  одне питання за раз.
- **Код міняти тільки після того, як зміни узгоджені з власником.**
- **Перед кожною збіркою `.exe` (і APK гри) питати дозволу.**
- Перед рендерами, превʼю й іншими фінальними артефактами теж питати, якщо
  власник прямо про них не просив.
- Канонічний дизайн гри: `docs/Game_Concept_Handoff_UA_v1.0.md`.
- Модель `tools/source_models/t72_rambo.glb` взята з «Rambo: The Video Game» і
  призначена **лише для особистого використання**. Її не можна публікувати і
  вбудовувати в програму. Моделі відкриваються з диска користувача під час роботи.

## Файли

| Шлях | Що це |
|---|---|
| `project.godot` | окремий проєкт (Forward+), головна сцена `main.tscn` |
| `main.gd` | UI (будується в коді), діалоги файлів, CLI-режими |
| `core/unit_studio.gd` | `class_name UnitStudio`: сцена, завантаження, частини, матеріали, поза, рендер спрайтів, `.unit.json` |
| `core/map_backdrop.gd` | `class_name MapBackdrop`: 2D-карта під прев'ю (трава, пунктирна сітка, кільце сторони) у кольорах гри |
| `core/obj_loader.gd` | `class_name ObjLoader`: простий OBJ-читач для запуску програми (Godot імпортує OBJ лише в редакторі) |
| `core/weathered.gdshader` | **симлінк** на `tools/models/weathered.gdshader` (спільний з рендером гри) |
| `assets/grass.jpg` | вирізка трави із запеченої тестової карти (`assets/maps/test_40x20/tile_0_0.jpg`), 392 px = 30 м |
| `export_presets.cfg` | пресет «Windows Desktop», x86_64, pck вбудований в exe |
| `../.gdignore` | ховає `apps/` від основного проєкту гри |
| `../../.github/workflows/unit_workshop.yml` | CI: перевірка завантаження на push, збірка exe тільки вручну |

Старий CLI-рендер `tools/render_units.gd` лишається в основному проєкті й
використовує той самий шейдер. Програма повторює його конвеєр рендера.

## Домовленості

- **Простір юніта:** +X — перед машини, +Y — вгору, метри, земля на y = 0.
  Сцена: схід = +X, північ = −Z, камера дивиться з півдня.
- **Напрямки на карті:** градуси проти годинникової стрілки від сходу.
  18 кадрів по 20° (`FRAMES`).
- **Камера:** ортографічна, `ELEVATION = 65°`. Щоб напрямок на спрайті збігся з
  напрямком на карті, модель повертають на
  `yaw_for_angle(a) = atan2(sin a / sin 65°, cos a)`.
- **Сонце:** азимут 45° (NE), висота 75°. Воно закріплене за картою, тому тінь
  у всіх кадрах падає однаково.
- **Масштаб спрайта:** `PX_PER_M = 320/11` (≈29,09). Гра малює спрайти з
  `SPRITE_SCALE = 0.3`, тобто 8,727 px/м = `Hex.SIZE 48 px / 5,5 м`.
- **Гекс:** pointy-top, R = 5,5 м, рядки odd-r. Карта в грі top-down, тому ряди
  розтягнуті на 1/sin 65° відносно 3D-проєкції.
- **Кольори** в налаштуваннях зберігаються як sRGB 0..1. У шейдер вони йдуть
  лінійними (`srgb_to_linear`).

## Будова сцени (`UnitStudio.setup`)

```
SubViewport (прев'ю, transparent_bg; під ним MapBackdrop у 2D)
├─ Camera3D (orthographic, cull_mask = 1 | LAYER_PREVIEW)
├─ DirectionalLight3D sun (тіні, PARALLEL_4_SPLITS)
├─ DirectionalLight3D fill (не світить на LAYER_PREVIEW)
├─ WorldEnvironment (sky ambient, SSAO, Filmic, adjustments)
├─ shadow catcher (LAYER_PREVIEW): прозорий, ALPHA = тінь сонця × shadow_opacity
├─ shadow_ground (LAYER_SHADOW): білий, тільки для проходу тіні під час рендера
└─ unit_root (поза: курс + зсув корпусу)
   ├─ model_fix (yaw, масштаб, центрування) → завантажена сцена
   └─ turret_pivot (поворот башти)
      └─ gun_slide (відкат)
```

- Землю прев'ю малює **2D** (`MapBackdrop`), щоб її кольори не проходили через
  3D-тонмапінг. 3D-сцена тільки кладе на неї тінь через shadow catcher.
- Рендер спрайтів іде в окремому `SubViewport` зі спільним `world_3d`. Його
  камера має `cull_mask = 1`, тож ні catcher, ні трава в кадр не потрапляють.

## Частини і башта

- `MeshInstance3D` групуються за першим словом назви (`Wheel_L_1` → `Wheel`).
  Якщо груп виходить менше трьох, групування йде за повною назвою.
- Роль групи вгадує `guess_role` за ключовими словами (англ./укр.). Ролі:
  `hull, hull_lower, turret, gun, wheel, sprocket, idler, track, other, hide`.
- **Башта** (`_build_turret`):
  - якщо у файлі є вузол, чия назва починається з `turret` (без урахування
    регістру), його півот стає центром погона (`pivot_from_file = true`), і все
    всередині нього крутиться з баштою;
  - інакше центром береться центр габаритів частин з роллю `turret`.
  - Вузли переносяться через `reparent(..., true)` і записуються в `_moved`;
    `_send_turret_home` повертає їх у зворотному порядку.
- **Відкат:** якщо є вузол `gun*`, його локальна вісь, найближча до +X юніта,
  стає `gun_axis`. `gun_slide.position = -gun_axis * крок`. Кроки:
  `recoil_steps()` = 0, ⅓, ⅔, 1 × `recoil_m`.
- Шар башти при рендері — `turret_meshes()`, тобто все, що лежить під
  `turret_pivot`.
- `auto_hull_offset`: `hull_offset_m` = мінус X центру габаритів
  корпусу й ходової. Гра зсуває спрайт уперед на цю величину, щоб на центрі
  гекса стояв корпус, а не «корпус + гармата».

## Матеріали

Кожна поверхня отримує `ShaderMaterial` з `weathered.gdshader`.

- **Наша фарба** (`own_paint`): `base_color` = колір групи.
  - Ходова (`RUNNING_GEAR`) рендериться варіантом шейдера з `shadows_disabled`
    і `lift = 0.45`.
  - Для катків `rubber_tyre` вмикається з `wheel_center` і
    `tyre_radius = 0.78 × габарит/2` окремо для кожного меша.
  - Для гусениць вмикається `track_links`.
- **Текстура файлу:** береться `albedo_texture` і normal map із матеріалу моделі
  з відтінком `tint`.
- **Зношеність:** `weathering` множить базові величини
  `{mud 0.85, dust 0.3, chip 0.8, streak 0.7}`. `mud_height` = 0 вимикає бруд.
  `roughness` передається в `paint_roughness`.
- **Власні текстури:** `textures[key]`, де `key` — ключ групи або `"*"` (вся
  модель); набір частини перекриває набір усієї моделі (`texture_set`). Мапи:
  - `albedo`, `normal`, `ao`, `roughness`, `metallic_map`;
  - значення: `tint`, `normal_strength`, `flip_green`, `ao_strength`,
    `metallic`, `uv_scale`.
  - Шахова сітка `checker` — тільки для перевірки розгортки.
- **Шейдер спільний з рендером гри.** Нові uniform-и додавати тільки зі
  значеннями за замовчуванням, які не змінюють поточний вигляд.

## Світло (`look`)

`LOOK_DEFAULTS` відповідає вигляду `tools/render_units.gd`:

| Ключ | Значення | Що це |
|---|---|---|
| `sun_energy` | 2,3 | сила сонця |
| `sun_blur` | 0,4 | м'якість тіні сонця |
| `fill_energy` | 0,4 | підсвітка з тіні |
| `ambient` | 0,32 | розсіяне світло |
| `exposure` | 1,05 | експозиція |
| `contrast` | 1,12 | контраст |
| `saturation` | 0,95 | насиченість |
| `shadow_opacity` | 0,6 | тінь на землі |
| `ao_intensity` | 7 | SSAO: тіні дрібних деталей |
| `ao_radius` | 0,25 | SSAO: радіус |
| `ao_power` | 2,2 | SSAO: різкість |
| `ao_detail` | 1 | SSAO: деталізація |
| `ao_light_affect` | 0,25 | SSAO: тіні деталей на сонці |

Застосовується через `apply_look()`. Прохід тіні тимчасово вимикає ambient,
SSAO, fill і тонмапінг, а потім відновлює їх з `look`.

## Рендер спрайтів (`render_sprites(out_dir)`)

Формат збігається з `tools/render_units.gd`, і його читає `scripts/game.gd`
(`assets/units/<name>*`).

1. **Корпус**: 18 кадрів 320×320 (суперсемплінг ×4), частини башти приховані.
   Для кожного кадру записується, куди в кадрі проєктується півот башти
   (`turret_offsets`).
2. **Башта**: 18 × 4 кадри 416×416. Корпус прихований, півот башти стоїть на
   якорі кадру. Тінь башти падає на площину на рівні низу башти.
3. **Тінь кожного кадру**: окремий прохід рендера (біла земля, тільки сонце).
   Потемніння перетворюється на альфу (`shadow_opacity`) під моделлю
   (`_under_shadow`).

Файли в `out_dir`:
- `<name>_hull_<i>.png`, `<name>_turret_<i>.png`, `<name>_turret_<i>_r<k>.png`.
  Для моделі без башти: `<name>_<i>.png`, а в json `anchor` і `directions`.
- `<name>.json`: `layers, frames, px_per_m, elevation, hull_offset_m,
  hull_anchor, turret_anchor, turret_offsets[18], recoil_steps`.
- `<name>_sheet.png`: 6×3 кадри на траві, розставлені так, як їх малює гра
  (`c + (cos a, −sin a·sin 65°)·hull_px`, башта з `turret_offsets`).
- `<name>.unit.json`: налаштування.

Рендер повільний (~10 хв на T-72 у хмарі без GPU). Основний час займають піксельні цикли на
GDScript у `_shadow_pass` і `_under_shadow`.

## `.unit.json`

```json
{
  "name": "t72_rambo", "file": "D:/models/t72.glb",
  "length_m": 9.35, "yaw": 180, "hull_offset_m": 1.35,
  "paint_source": "own", "tint": [r,g,b], "roughness": 0.82,
  "weathering": 0.6, "mud_height": 1.1,
  "parts": {"Hull": "hull", "Turret": "turret", "...": "..."},
  "part_colors": {"Hull": [r,g,b]}, "no_cast": ["Gun"],
  "textures": {"*": {"albedo": "path.png", "normal": "...", "normal_strength": 1.8}},
  "look": {"ao_intensity": 7.0, "...": "..."},
  "turret": {"pivot_m": [x, z], "pivot_from_file": true, "recoil": {"steps_m": [0, 0.127, 0.253, 0.38]}},
  "elevation": 65, "sun": {"azimuth": 45, "elevation": 75}, "frames": 18
}
```

- `from_config` зіставляє частини за ключем групи.
- Якщо `hull_offset_m` немає, зсув рахується автоматично.

## Командний рядок

```
UnitWorkshop.exe -- --model=M.glb [--config=C.unit.json] [--name=N] --out=DIR
UnitWorkshop.exe -- [--model=M.glb] [--config=C.unit.json] [--hull=deg] [--turret=deg] [--zoom=m] --shot=FILE.png
```

- `--out` рендерить спрайти і виходить.
- `--shot` зберігає знімок вікна і виходить. Це для перевірок без людини.

## Збірка і перевірка

- Локально (Linux, потрібен GPU-контекст):
  `xvfb-run -a -s "-screen 0 1920x1080x24" godot --rendering-method forward_plus --path apps/unit_workshop -- --config=... --shot=/tmp/s.png`
- Перевірка завантаження, як у CI: `godot --headless --path apps/unit_workshop --quit-after 30`.
  Помилки `mesh_get_surface_count` від dummy-рендера в headless — нормальні.
  Шукати треба `SCRIPT ERROR` і `Parse Error`.
- **CI** `.github/workflows/unit_workshop.yml`:
  - push у `apps/unit_workshop/**` або в шейдер запускає тільки перевірку
    завантаження;
  - `workflow_dispatch` експортує `UnitWorkshop.exe`, пакує в
    `UnitWorkshop.zip` і публікує в реліз `unit-workshop`.
  - Шаблони: `Godot_v4.3-stable_export_templates.tpz` → `windows_*x86_64*`.
  - **Запускати тільки з дозволу власника.**

## Стан і відомі обмеження

- Опублікований `UnitWorkshop.zip` зібраний до коміту з півотами з файлу
  (`f29b4c3`), тож ця зміна в exe ще не потрапила.
- Рельєф решітки двигуна T-72 (`t72_hull_detail.png`, `detail_rect`) є лише в
  старому CLI. У програмі його ще немає.
- FBX під час роботи програми (`FBXDocument`) перевірений лише на Linux-збірці
  редактора, у Windows-exe — не перевірений. OBJ читається без матеріалів.
- Узгоджені з власником групи налаштувань, які ще не зроблені:
  - **C**: окремі повзунки бруду, пилу, сколів, потьоків, вицвітання; кольори
    бруду й пилу, розмір плям;
  - **D**: обводка контуру, різкість після зменшення, якість згладжування,
    18/36 напрямків;
  - **E**: ланки гусениць, гума на катках, рельєф решіток і люків, наклейки.
- Щоб юніти гри виглядали однаково, світло (`look`) краще тримати однаковим
  для всіх.
