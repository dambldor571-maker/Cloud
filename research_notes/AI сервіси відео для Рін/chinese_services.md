# Chinese commercial AI video generators (non-Kling) for anime-companion clip production — state as of 22 Oct 2026

Scope: Vidu (ShengShu), Hailuo / MiniMax (H3 = "Hailuo 03"), PixVerse (V6), Seedance (ByteDance; BytePlus ModelArk/LAS, Dreamina/CapCut), Alibaba Wan (2.7 / 3.0 on Model Studio), Tencent Hunyuan, plus brief mentions of other Chinese entries on leaderboards (Alibaba-ATH HappyHorse, Sand.ai MAGI-2).
Project requirements used to judge fit: 3–10 s clips, 24 fps, >=1080p, vertical 9:16, flat #00FF00 background, static camera, full body, exact start/end keyframe poses (chaining), identity consistency across dozens of clips, seamless loops, no unwanted mouth movement, anime-style fidelity, personal use.

Note on sources: most price/param data for these services comes from third-party API resellers and blogs. Primary sources actually read: Vidu platform pricing page (platform.vidu.com), Alibaba Cloud blog (Wan 3.0), Dreamina pricing page, Artificial Analysis leaderboard, fal.ai Seedance 2.0 llms.txt, MiniMax official FL2V doc (via search snippet only). Everything else is secondary and flagged.

## 1. Current models/versions and control features (I2V, first+last frame, multi-keyframe, reference/character consistency, negative prompt, static camera, motion control, loop)

### Takeaway
Every service in scope now supports image-to-video with first+last frame (FLF) control, which is the core requirement for chaining clips on shared keyframe poses; none documents true multi-keyframe (3+ intermediate keyframes) or a dedicated loop mode. The main structural problem: on Seedance 2.x and MiniMax H3, FLF and reference-image (character consistency) modes are mutually exclusive in the same request, and Vidu exposes them as separate endpoints too — so for chained clips identity must come from the keyframe images themselves (which, for this project, is actually fine because the keyframes are pre-drawn).

### Cited Findings

**Vidu (ShengShu)**
- Model lineup listed on Vidu API platform (Oct 2026): Vidu Q4 preview, Q3, Q2, Q1 video models; also S2 Avatar / S2 Editing streaming models — [Vidu platform docs nav](https://platform.vidu.com/docs/start-end-to-video)
- Vidu Q4 Preview released 7 Oct 2026 as a public preview ahead of full Q4; available on web and API; up to 15 image references and 3 audio references; 2K/4K with 10-bit color on higher tiers; up to 16 s; multi-shot — [Unite.AI](https://www.unite.ai/vidu-releases-q4-preview-of-next-generation-flagship-ai-video-model/), [Eachlabs blog](https://www.eachlabs.ai/blog/vidu-q4-preview-15-references-3-voices)
- Q4 Preview modes in the official pricing table: only Image-to-video and Reference-to-video (no start-end / FLF listed for Q4 as of 22 Oct 2026) — [Vidu pricing](https://platform.vidu.com/docs/overview/pricing). Eachlabs also says start/end frame support for Q4 is "not stated" and output keeps the source image aspect ratio — [Eachlabs](https://www.eachlabs.ai/blog/vidu-q4-preview-15-references-3-voices)
- Q3 family (official pricing table): `viduq3-pro` and `viduq3-turbo` support Image-to-video, Text-to-video and **First-last frame**, 1–16 s; `viduq3-pro-fast` image-to-video only; reference-to-video via `viduq3`, `viduq3-turbo`, `viduq3-mix` (3–16 s) — [Vidu pricing](https://platform.vidu.com/docs/overview/pricing)
- Start-End API endpoint: `POST /ent/v2/start-end2video` for Q3 Turbo, Q3 Pro Fast, Q3 Pro — [Vidu API ref](https://platform.vidu.com/docs/api-reference/video-models/vidu-q3/start-end-to-video)
- Q3 Reference-to-Video: global launch press release 13 Apr 2026; combine subjects, environments, costumes, props, styles; company claims No.1 on SuperCLUE reference-to-video leaderboard (company-reported) — [TechNode](https://technode.global/?p=120646)
- Q3 / Q3-Mix reference-to-video takes 1–4 reference images (reseller listings) — [Atlas Cloud Q3 ref](https://www.atlascloud.ai/models/vidu/q3/reference-to-video), [Atlas Cloud Q3-Mix](https://www.atlascloud.ai/models/vidu/q3-mix/reference-to-video); older Vidu (Q2/Q1 era) reference feature supported up to 7 reference images — [search summary of Vidu sources](https://technode.global/?p=120646); WaveSpeed lists `vidu/q3-ad` with 1–7 refs and `reference-to-image-q2` with 1–7 refs — [WaveSpeed Vidu collection](https://wavespeed.ai/collections/vidu)
- Vidu Q2 video-extend endpoints add 1–7 s with an **optional end-frame image** (useful for "extend to a target pose") — [WaveSpeed Vidu collection](https://wavespeed.ai/collections/vidu)
- Vidu Q1 had a dedicated "Text-to-video (Anime)" style option (fixed 5 s, 1080p) — [Vidu pricing](https://platform.vidu.com/docs/overview/pricing)
- Vidu promoted an "AI solution for animated series production" at SXSW (March 2026) — [TechNode](https://technode.global/prnasia/vidu-unveils-the-worlds-first-ai-solution-for-animated-series-production-at-sxsw-2026/)

**MiniMax / Hailuo**
- MiniMax H3 (also called "Hailuo 03" / Hailuo 3.0) launched 31 Jul 2026; API model id `MiniMax-H3` — [reAPI guide, 1 Aug 2026](https://reapi.ai/blog/hailuo-h3-minimax-h3-api-guide)
- H3 modes: T2V, I2V with first frame, last frame, or both; reference-to-video with up to 9 images, 3 videos, 3 audio clips (each ref video/audio 2–15 s, total capped 15 s); **FLF inputs cannot be combined with reference arrays** in the same request — [reAPI](https://reapi.ai/blog/hailuo-h3-minimax-h3-api-guide)
- No dedicated static-camera setting documented for H3; camera is controlled via prompt text — [reAPI](https://reapi.ai/blog/hailuo-h3-minimax-h3-api-guide)
- MiniMax H3 Max: release 26 Aug 2026 (Runware); optional first+last frame guidance (`frameImages` distinct from `referenceImages`) — [Runware H3 Max](https://runware.ai/docs/models/minimax-h3-max.md); Evolink: H3 Max supports first-frame-only and first+last, not last-only — [Evolink H3 Max docs](https://evolink.ai/docs/en/api-manual/video-series/minimax/minimax-h3/h3-max/minimax-h3-max-image-to-video.md)
- ComfyUI has a MiniMax H3 first/last-frame node; output follows aspect ratio of the supplied images; frames must be >=256×256 — [ComfyUI docs](https://docs.comfy.org/built-in-nodes/MinimaxHailuo03FirstLastFrameNode.md)
- Official MiniMax FL2V doc (`POST /v1/video_generation`, `first_frame_image`) lists 768P and 1080P for the FL2V mode but the example names MiniMax-Hailuo-02, not H3 — [MiniMax FL2V doc](https://platform.minimax.io/docs/api-reference/video-generation-fl2v.md)
- WaveSpeed (verified 6 Aug 2026): not every access route exposes FLF mode for H3; FLF "constrains the animation far more than a single prompt", suits shots that "must land on an exact final frame"; frames must match aspect ratio/resolution expected by endpoint; mismatched frames can look unstable — [WaveSpeed H3 FLF](https://wavespeed.ai/blog/minimax-h3/minimax-h3-first-last-frame-api/)
- Open weights: MiniMax said H3 weights would arrive "in the coming days"; not confirmed published as of 1 Aug 2026 — [reAPI](https://reapi.ai/blog/hailuo-h3-minimax-h3-api-guide), [EvoLink/search summary](https://evolink.ai/hailuo-3)

**PixVerse**
- PixVerse V6 (AA lists release Mar 2026) — [Artificial Analysis](https://artificialanalysis.ai/video/leaderboard/image-to-video)
- V6 image-to-video params (Magnific API reference): `image_url` (first frame), optional `last_frame_image` (transition to last frame), **`negative_prompt`**, `duration` 1–15 s (integer; V5.5 was only 5/8/10), `resolution` 360p/540p/720p/1080p, `aspect_ratio` incl. `social_story_9_16`, `seed`, **`style` incl. `anime`**, `camera_movement` incl. **`fix_bg`** (plus zooms/pans), `generate_audio_switch` (default false), `generate_multi_clip_switch` (default false), `thinking_type` prompt-rewrite (enabled/disabled/auto) — [Magnific PixVerse V6 create](https://docs.magnific.com/api-reference/image-to-video/pixverse-v6/create.md)
- Dedicated V6 Transition endpoint (first + end image interpolation), 1–15 s, up to 1080p, audio off by default — [WaveSpeed V6 Transition](https://wavespeed.ai/models/pixverse/pixverse-v6/transition), [Magnific transition](https://docs.magnific.com/api-reference/image-to-video/pixverse-v6-transition/overview); ComfyUI V6 FLF node keeps first-frame aspect ratio — [ComfyUI](https://docs.comfy.org/built-in-nodes/PixverseV6FirstLastFrameNode.md)
- V6 "Fusion" multi-image reference: up to 7 references (Empirio), `img_references` (APIMart); video-reference fusion costs 2× credits — [Empirio](https://empiriolabs.ai/models/pixverse-v6), [APIMart](https://apimart.ai/blog/pixverse-v6-ai-video-generator-reviewed), [VidCost](https://vidcost.com/api/pixverse-api/)
- PixVerse also offers a "swap" model on fal (character/subject swap) — [fal pixverse swap](https://fal.ai/models/fal-ai/pixverse/swap)

**Seedance (ByteDance)**
- BytePlus LAS model ids (article 26 Aug 2026): Seedance 2.5 `dreamina-seedance-2-5-260628` (launched 31 Jul 2026), 2.0 `dreamina-seedance-2-0-260128`, 2.0 Fast `...-fast-260128`, 2.0 Mini `...-mini-260615`; all support T2V, first-frame and first/last-frame I2V, combined references, video editing — [aifreeapi](https://www.aifreeapi.com/en/posts/seedance-video-models-2026)
- References: 2.0 family up to 9 images + 3 videos + 3 audio; 2.5 up to 30 images + 10 videos + 10 audio — [aifreeapi](https://www.aifreeapi.com/en/posts/seedance-video-models-2026); Dreamina page: up to 12 refs (9 img/3 video/3 audio) — [Dreamina pricing](https://dreamina.capcut.com/seedance/seedance-2-0-pricing)
- 2.5 adds timestamp-level editing and names **green-screen**, camera-perspective and reference-based editing; 2.0 multi-shot up to 15 s — [aifreeapi](https://www.aifreeapi.com/en/posts/seedance-video-models-2026)
- BytePlus-aligned API docs (PR merged 14 Oct 2026): `last_frame` requires `first_frame`; **first/last frames cannot be mixed with reference inputs** (three input modes mutually exclusive); `seed` not in official 2.0-series support list; for 2.5 FLF tasks only `ratio: adaptive` allowed; `return_last_frame` returns a JPEG of the final frame (`metadata.last_frame_url`) — [SolveaCX docs PR #20](https://github.com/SolveaCX/docs/pull/20)
- Two-frame mode: second image `role: last_frame`; if aspect ratios differ, first frame wins and last frame is center-cropped — [Pixazo](https://www.pixazo.ai/models/seedance)
- fal Seedance 2 I2V inputs: `image_url`, `end_image_url`, `resolution`, `duration` (auto/4–15), `aspect_ratio` (auto, 21:9…9:16), `generate_audio` (default **true**), `bitrate_mode`, `codec` (H264/H265); **no `camera_fixed`, no negative prompt, no seed input** — [fal Seedance 2 I2V](https://fal.ai/models/bytedance/seedance-2.0/image-to-video/llms.txt)
- Real-person portrait references need identity verification/authorization (not relevant for anime char) — [aifreeapi](https://www.aifreeapi.com/en/posts/seedance-video-models-2026)

**Alibaba Wan (commercial, Model Studio)**
- Wan 2.7 (AA: Apr 2026): 2–10 s clips, steerable with first-frame and last-frame images, generates audio — [OpenRouter Wan 2.7](https://openrouter.ai/alibaba/wan-2.7)
- Wan 3.0 (Alibaba blog 13 Aug 2026; AA: Aug 2026): up to 30 s single generation + extension; 480P/720P/1080P; inputs text, image, audio, video, documents; reference-to-video consistency for characters, props, space, style (no count given); video editing without full regen — [Alibaba Cloud blog](https://www.alibabacloud.com/blog/wan3-0-30-second-ai-video-generation-from-any-input_603452)
- Wan 3.0 Prime (faster variant) on fal: T2V and **first-frame** I2V only — [search summary citing fal/llm-stats](https://llm-stats.com/blog/research/wan-3.0-launch)
- No source confirmed FLF for Wan 3.0 itself — [same search](https://openrouter.ai/alibaba/wan-3.0)

**Tencent Hunyuan**
- Only HunyuanVideo 1.5 (open-weights model) found as hosted API: fal $0.075/s, up to 121 frames at 480p, "more resolutions arriving soon" — [fal HunyuanVideo 1.5](https://fal.ai/models/fal-ai/hunyuan-video-v1.5/text-to-video); no Tencent Cloud official commercial price list found; no Hunyuan entry on AA I2V leaderboard (Oct 2026) — [Artificial Analysis](https://artificialanalysis.ai/video/leaderboard/image-to-video)

**Other Chinese entries on AA I2V board (Oct 2026)**
- HappyHorse-1.1 (Alibaba-ATH, Jun 2026, Elo 1061, $9.90/min) and HappyHorse-1.0 (Apr 2026, 1042); MAGI-2 Preview (Sand.ai, open weights, Aug 2026, 1046, price "coming soon") — [Artificial Analysis](https://artificialanalysis.ai/video/leaderboard/image-to-video)

### Inferences
- For chained clips with exact start/end poses, the FLF endpoints are the right tool everywhere: Vidu Q3 Pro/Turbo start-end, MiniMax H3 / H3 Max FLF, PixVerse V6 `last_frame_image`/Transition, Seedance 2.0 `first_frame`+`last_frame`, Wan 2.7 FLF. Since the keyframe images already carry the character's identity, reference-to-video modes (which cannot be combined with FLF on Seedance and H3) are less critical for this pipeline; they matter mainly for generating the keyframe stills or for free-form clips.
- Seamless loops: no dedicated loop mode was found on any service; the standard workaround is FLF with identical first and last image (pose A → A). Fidelity of the end frame then determines whether a visible pop occurs; plan for cross-fade or frame-matching cleanup.
- Static camera: only PixVerse exposes an explicit camera parameter (`fix_bg`, semantics presumably "fixed background/static" — not verified in official PixVerse docs). For Seedance 2.x, H3, Vidu Q3, Wan, static camera must be requested in prompt text. A flat #00FF00 background with no texture gives the model little parallax reference, which generally helps keep the camera still but can also cause the "camera" to drift without visual cue.
- Unwanted mouth movement: several models generate audio by default (Seedance fal `generate_audio=true`; Vidu Q3/Q4 native audio; H3 native stereo audio). Turning audio off (PixVerse default off; Seedance `generate_audio:false`) plausibly reduces spontaneous lip-flap; negative prompt "talking, mouth moving" only available explicitly on PixVerse V6.
- Seedance's `return_last_frame` is useful for verifying how close the generated last frame landed to the target keyframe.

### Gaps
- No official Vidu Q3 start-end parameter list could be retrieved (doc page truncated): unknown whether `movement_amplitude`, negative prompt, seed are exposed for Q3 (they existed on older Vidu APIs per general knowledge, unverified here).
- Whether MiniMax H3 exposes `prompt_optimizer` / camera instructions / negative prompt officially — not confirmed.
- Whether Seedance 2.0 on BytePlus still has the Seedance 1.x `camera_fixed` flag — not documented in fal or the BytePlus-aligned PR; treat as unavailable.
- Multi-keyframe (>2 keyframes in one generation): no service in scope documents it. Seedance 2.5 "timestamp-level editing" may be adjacent but not equivalent — unverified.
- Motion control from reference video: Seedance 2.x/H3 accept reference videos (up to 3), PixVerse fusion accepts video refs, Wan 3.0 accepts video input — but whether these act as pose/motion transfer (vs. style/content reference) is not documented in sources read.
- PixVerse official (platform.pixverse.ai) docs not retrieved; `fix_bg` meaning unconfirmed.

## 2. Output specs: resolution, fps, duration, aspect ratios, input limits

### Takeaway
1080p 9:16 is available on Vidu Q3/Q4, PixVerse V6, Seedance 2.0 (not Fast/Mini/2.5 on the direct BytePlus route), Wan 2.7/3.0; MiniMax H3 offers "2K" and 768p tiers (H3 Max is 480p/768p only), so H3's real 1080p-class FLF output is uncertain. Only Seedance confirms native 24 fps; fps is undocumented for the others in sources found.

### Cited Findings
- **Vidu**: Q4 Preview 540p/720p/1080p/2K/4K, 3–16 s (pricing page) — [Vidu pricing](https://platform.vidu.com/docs/overview/pricing); Eachlabs says Q4 I2V 3–16 s, ref-to-video 1–16 s (conflicts with pricing page which says 3–16 s for Q4 overall) — [Eachlabs](https://www.eachlabs.ai/blog/vidu-q4-preview-15-references-3-voices). Q3 pro/turbo 540p/720p/1080p, 1–16 s; Q3 reference/mix 3–16 s; Q1 fixed 5 s 1080p — [Vidu pricing](https://platform.vidu.com/docs/overview/pricing). WaveSpeed lists `vidu/q3/image-to-video-pro` at 720p/1080p/2K/4K — [WaveSpeed](https://wavespeed.ai/collections/vidu). Concurrency up to 5 tasks/account — [Vidu pricing](https://platform.vidu.com/docs/overview/pricing)
- **MiniMax H3**: up to 2K, 768p tier; 4–15 s whole seconds; aspect ratios 21:9, 16:9, 4:3, 1:1, 3:4, 9:16; I2V takes orientation from input image (no ratio param); MP4 with native stereo audio; fps not stated — [reAPI](https://reapi.ai/blog/hailuo-h3-minimax-h3-api-guide). Other summaries say 5–15 s — [OpenRouter/search summary](https://openrouter.ai/minimax/hailuo-3). H3 Max (Evolink): 5–15 s, **480p or 768p** only — [Evolink](https://evolink.ai/docs/en/api-manual/video-series/minimax/minimax-h3/h3-max/minimax-h3-max-image-to-video.md). AA lists "MiniMax H3 (768p)" — [AA](https://artificialanalysis.ai/video/leaderboard/image-to-video). APIMart lists 512p/768p/1080p price tiers for "Hailuo 03" (conflicts with 768p/2K tiers elsewhere) — [APIMart](https://apimart.ai/blog/hailuo-03-minimax-3-0-api-pricing-features-how-to-access)
- **PixVerse V6**: 360p/540p/720p/1080p; 1–15 s; ratios 16:9, 4:3, 1:1, 3:4, 9:16 (+2:3, 3:2, 21:9 on T2V); transition endpoint has a shorter ratio list / follows first frame; no fps setting found — [Magnific](https://docs.magnific.com/api-reference/image-to-video/pixverse-v6/create.md), [search summary of Magnific/ComfyUI](https://docs.comfy.org/built-in-nodes/PixverseV6FirstLastFrameNode.md)
- **Seedance**: 2.5 → 480p/720p, 4–30 s, 24 fps; 2.0 → 480p/720p/1080p/4K, 4–15 s, 24 fps; 2.0 Fast and Mini → 480p/720p, 4–15 s, 24 fps (BytePlus LAS) — [aifreeapi](https://www.aifreeapi.com/en/posts/seedance-video-models-2026); same per-model resolution limits in BytePlus-aligned docs (default 720p) — [SolveaCX PR](https://github.com/SolveaCX/docs/pull/20); fal token formula uses ×24 (fps) — [fal](https://fal.ai/models/bytedance/seedance-2.0/image-to-video/llms.txt). Third-party platforms may advertise 4K for 2.5 (likely upscaling) — [aifreeapi](https://www.aifreeapi.com/en/posts/seedance-video-models-2026). Input images jpeg/png/webp, 300–6000 px, <=30 MB — [EvoLink](https://evolink.ai/seedance-2-0). Dreamina paid plans list "up to 60 FPS" — [Dreamina pricing](https://dreamina.capcut.com/seedance/seedance-2-0-pricing)
- **Wan**: 2.7 → 2–10 s, 720P/1080P priced tiers — [OpenRouter](https://openrouter.ai/alibaba/wan-2.7), [Model Studio pricing via search](https://www.alibabacloud.com/help/en/model-studio/model-pricing); 3.0 → 480P/720P/1080P, up to 30 s; fps/aspect ratios not stated — [Alibaba blog](https://www.alibabacloud.com/blog/wan3-0-30-second-ai-video-generation-from-any-input_603452)
- **HunyuanVideo 1.5 (fal)**: 480p, up to 121 frames — [fal](https://fal.ai/models/fal-ai/hunyuan-video-v1.5/text-to-video)

### Inferences
- Seedance 2.0 is the only option where 1080p, 9:16, and native 24 fps are all explicitly documented — directly matching the project spec. For others, expect 24 or 25/30 fps and plan for conform/retime; test before committing.
- For 3–10 s clips all services' duration ranges are adequate; PixVerse (1–15 s) and Vidu Q3 (1–16 s) allow the shortest clips (useful for short transitions/idles).
- MiniMax H3 at 768p would need upscaling to reach >=1080p; its "2K" tier is the only path to native >1080p and it is unclear whether 2K is available in FLF mode.

### Gaps
- Native fps for Vidu Q3/Q4, MiniMax H3, PixVerse V6, Wan 3.0 — not found.
- Exact pixel dimensions for 9:16 1080p on each service (e.g., 1080×1920) — not confirmed.
- Whether Vidu Q3 start-end allows explicit 9:16 or always follows the input image ratio — not confirmed.

## 3. Anime/2D quality, hands, identity drift, unwanted lip movement

### Takeaway
There is no independent, rigorous anime-specific benchmark; general I2V arena (AA, Oct 2026) puts MiniMax H3, Seedance 2.5/2.0 and Wan 3.0 at the top and Vidu Q3/PixVerse V6 mid-pack. Anime-specific blog rankings (mostly vendor-written) consistently praise Vidu for anime line quality; PixVerse's own blog praises PixVerse while an independent-ish Mage blog rates PixVerse weakest on consistency. No source evaluates hands or unwanted lip movement — must be tested.

### Cited Findings
- AA-Video-I2V v1.1 (with audio) top entries: MiniMax H3 768p 1140 (#1), FLUX 3 Max 1138, Seedance 2.5 1138 (#3), Gemini Omni Flash 1.1 1132, Wan 3.0 1127 (#5), MiniMax H3 Max (fal) 1125, Seedance 2.0 1121 (#7), … HappyHorse-1.1 1061, MAGI-2 Preview 1046, Wan 2.7 1034 (#13), Veo 3.1 1028, **PixVerse V6 1024 (#15)**, **Vidu Q3 Pro 1016 (#17)**, Kling 3.0 Omni 1004, Kling 3.0 Pro 1000 (anchor), Vidu Q3 Turbo 967; 95% CIs about ±15–19 Elo; page shows no explicit date but includes Oct 2026 releases — [Artificial Analysis](https://artificialanalysis.ai/video/leaderboard/image-to-video)
- Arena.ai (21 Sep 2026 snapshot) also ranks MiniMax H3 #1 (1495, different scale); an Aug 2026 invideo article had Seedance #1 (older) — [search summary: arena.ai](https://arena.ai/leaderboard/video/image-to-video), [invideo](https://invideo.io/blog/best-ai-video-model/)
- Mage blog (28 Aug 2026; Mage ranks itself #1; methodology undisclosed): Vidu anime style 5/5, consistency 4/5, "keeps line quality through motion"; Seedance 2.5 4/5 style, 3/5 consistency; PixVerse 3/5 style, 2/5 consistency ("weakest here"), free renders watermarked and capped at 540p; no claims on hands or lip sync; drift "creeps in by shot 3" when re-uploading stills (vendor claim) — [Mage blog](https://blog.mage.space/article/best-ai-anime-video-generators-2026/bf8ac529-3376-4bc0-b243-6a74ca6e6f52)
- PixVerse's own blog ranking praises PixVerse line work/2D and says Hailuo leads image-to-anime consistency (vendor source) — [PixVerse blog](https://pixverse.ai/en/blog/best-ai-anime-video-generators-2026)
- Hailuo 2.3 described as strong for anime, ink-wash and game-CG styles — [Atlas Cloud Vidu Q3 guide](https://www.atlascloud.ai/blog/tips/vidu-q3-api-guide), [noviai](https://www.noviai.ai/video-tips/chinese-image-to-video-ai/)
- Vidu Q3 native audio: "dialogue and music are not primary strengths" — [Atlas Cloud](https://www.atlascloud.ai/blog/tips/vidu-q3-api-guide)
- Search for lip-movement comparisons across these services returned no data — [search summary](https://techsy.io/en/blog/best-ai-video-models)

### Inferences
- For this project (anime, pre-drawn keyframes, mostly idle/gesture motion), Vidu Q3 Pro start-end and Seedance 2.0 FLF are the strongest candidates to test first: Vidu for anime style retention, Seedance for overall motion quality + 1080p/24 fps; MiniMax H3 is top on general arena but its resolution tiers are a problem; PixVerse V6 is the cheapest with the most explicit controls (anime style, negative prompt, fixed camera) but reported weaker consistency.
- Because audio-generating models are trained to make characters speak/sing, unwanted lip movement risk is likely higher when audio is enabled; disabling audio and prompting "closed mouth, silent" is the first mitigation. Unverified.
- Identity drift across dozens of clips is mostly mitigated by FLF from fixed keyframes; drift risk is concentrated in the middle frames of longer (8–10 s) clips.

### Gaps
- No controlled tests of hands, full-body anime proportions, mid-clip identity drift, or lip movement for any of these models.
- No independent anime-specific benchmark found (AA arena is general content with audio).
- End-frame fidelity (pixel-level match to provided last frame) is not quantified by any source for any service.

## 4. Pricing and API availability (official + fal/Replicate/WaveSpeed etc.)

### Takeaway
Per-second 1080p API prices (Oct 2026): PixVerse V6 ~$0.08–0.12/s; Vidu Q3 Pro ~$0.10–0.16/s (Turbo ~$0.06/s; off-peak half price); Wan 2.7 $0.15/s, Wan 3.0 $0.20/s; MiniMax H3 $0.09/s at 768p, $0.13–0.18/s at 2K; Seedance 2.0 ~$0.34–0.37/s official BytePlus but $0.68/s on fal. Dreamina web subscriptions make Seedance much cheaper per second than its API. Reseller prices diverge widely; official sheets preferred.

### Cited Findings
**Vidu (official, platform.vidu.com, 1 credit = 0.03125 RMB)** — [Vidu pricing](https://platform.vidu.com/docs/overview/pricing)
- Q4 Preview (I2V & reference): 4K 78 cr/s, 2K 38, 1080p 24, 720p 19, 540p 9 credits/s
- Q3-pro (I2V/T2V/first-last frame): 1080p 24 cr/s (off-peak 12), 720p 20 (10), 540p 9 (5)
- Q3-turbo (I2V/T2V/first-last frame): 1080p 13 (off-peak 7), 720p 12, 540p 7 (4)
- Q3 reference-to-video: viduq3 1080p 15 (7), turbo 1080p 13 (7), mix 1080p 29 (no off-peak)
- Off-peak note on page applies to pro/turbo "only when the audio parameter is true" (ambiguous wording); failed generations incl. moderation rejections not charged
- Reseller prices: Atlas Cloud Q3-Pro start-end $0.07 (540p) / $0.15 (720p) / $0.16 (1080p) per s; Q3-Turbo start-end $0.034/s (resolution unclear) — [Atlas Cloud Q3-Pro start-end](https://www.atlascloud.ai/models/vidu/q3-pro/start-end-to-video); AA lists Vidu Q3 Pro at $9.60/min 1080p (= $0.16/s), Q3 Turbo $3.90/min — [AA](https://artificialanalysis.ai/video/leaderboard/image-to-video); WaveSpeed lists flat "from" prices (q3-pro start-end $0.25, q3-turbo start-end $0.30, q3 start-end $0.35; units likely per run/base) — [WaveSpeed](https://wavespeed.ai/collections/vidu); fal lists Q3 reference mix at $0.07/s (aggregator claim) — [verna.one](https://verna.one/models/vidu-q3-reference-to-video-mix)
- Q4 launch price conflict: "from $0.014/s" (PR Newswire/Unite.AI) vs "from 0.09 yuan/s" (IT之家/AIbase) — [Unite.AI](https://www.unite.ai/vidu-releases-q4-preview-of-next-generation-flagship-ai-video-model/), [AIbase](https://news.aibase.com/news/31524), [fairsonline](https://www.fairsonline.org/vidu-launches-q4-preview-ai-video-model-0014-second)

**MiniMax H3**
- Official pay-as-you-go: $0.13/s 2K, $0.09/s 768p; first 5 input images free then $0.04 each; input video billed by duration at output rate — [reAPI](https://reapi.ai/blog/hailuo-h3-minimax-h3-api-guide); conflicting figure: $0.183/s 2K, $0.113/s 768p from a MiniMax model page — [search summary](https://evolink.ai/hailuo-3); fal reported at $0.26/s 2K (2× official) — [search summary](https://www.dreampixelforge.com/blog/minimax-h3); AA: H3 768p $5.40/min (= $0.09/s), H3 Max (fal) $5.76/min — [AA](https://artificialanalysis.ai/video/leaderboard/image-to-video); reAPI $0.119/s 2K, $0.074/s 768p — [reAPI](https://reapi.ai/blog/hailuo-h3-minimax-h3-api-guide)
- Hailuo web plans (official terms, last updated 14 Jul 2025): Standard $14.99/mo 1,000 credits, Pro $54.99/4,500, Master $119.99/10,000, Max $199.99/20,000; an Aug 2026 check reported Master 10,500 credits and Max $184/27,000 (conflict); old Unlimited plan only for Hailuo 01; an Oct 2026 review says H3 on web is metered in seconds (~143 s of 768p on Standard) — [aiarty/search summary](https://www.aiarty.com/ai-video-generator/hailuo-ai-pricing.htm), [magichour](https://magichour.ai/blog/hailuo-23-pricing)

**PixVerse V6**
- 1080p: ~$0.080/s without audio, $0.102/s with audio (18 / 23 credits/s at ~$0.00444/credit, citing official page) — [VidCost](https://vidcost.com/api/pixverse-api/); WaveSpeed/Atlas transitions $0.090/s (no audio), $0.115/s (audio) — [WaveSpeed](https://wavespeed.ai/models/pixverse/pixverse-v6/transition); Empirio $0.24/s (outlier) — [Empirio](https://empiriolabs.ai/models/pixverse-v6); APIMart $0.064–0.08/s — [APIMart](https://apimart.ai/model/pixverse-v6); AA $6.90/min 1080p (= $0.115/s) — [AA](https://artificialanalysis.ai/video/leaderboard/image-to-video); video-reference Fusion = 2× credits — [VidCost](https://vidcost.com/api/pixverse-api/)

**Seedance**
- BytePlus token billing: tokens = (input video s + output s) × W × H × fps / 1024; ~$0.07/s 480p, ~$0.15/s 720p, ~$0.37/s 1080p, ~$0.78/s 4K for 2.0; Fast ~$0.12/s 720p; $7.00/M tokens (no video input) / $4.30/M (with video input) for 2.0 at 480/720p — [Framesurfer, Sep 2026](https://framesurfer.com/blogs/seedance-2-0-pricing); BytePlus LAS "enhanced operator" $0.303/s × resolution factor (10 s 720p: 2.0 $3.03, 2.5 ~$4.62) — [aifreeapi](https://www.aifreeapi.com/en/posts/seedance-video-models-2026) (note: conflicts with Framesurfer's ~$0.15/s 720p — different BytePlus route/operator)
- fal Seedance 2 I2V: $0.3034/s 720p, $0.682/s 1080p; 480p $0.014/1k tokens; 4K $0.008/1k tokens — [fal](https://fal.ai/models/bytedance/seedance-2.0/image-to-video/llms.txt); AA lists Seedance 2.0 at $22.45/min, 2.5 at $24.60/min — [AA](https://artificialanalysis.ai/video/leaderboard/image-to-video); EvoLink $0.199/s 720p, $0.497/s 1080p — [EvoLink](https://evolink.ai/seedance-2-0); failed generations not billed — [Camclo3d](https://camclo3d.com/blog/seedance-pricing)
- Dreamina web (US pricing page dated 21 Oct 2026): Basic $15/mo (list $18; first month $0.29 promo, US eligible payment only) 1,575 credits; Standard $36 (list $42) 3,885; Advanced 8.6K $79; … Ultra $520/59,000. 720p credits/s: Seedance 2.0 Pro 17, Fast 8, Mini 5; Basic ≈ 19 ten-second Fast-720p videos/mo; paid tiers: watermark removal, higher res, up to 60 fps, fast queue — [Dreamina pricing](https://dreamina.capcut.com/seedance/seedance-2-0-pricing). Europe-specific review: Basic €17/mo, Standard €31/mo — [search summary: aimiracle](https://www.aimiracle.ai/ai-tool-review/dreamina-ai-review). Free tier 225 daily tokens, watermarked — [higgsfield/search summary](https://higgsfield.ai/blog/seedance-2-0-pricing-2026)

**Wan**
- Model Studio international: Wan 2.7 $0.10/s 720P, $0.15/s 1080P (China Beijing ~$0.086 / $0.143) — [Model Studio pricing via search](https://www.alibabacloud.com/help/en/model-studio/model-pricing); Wan 3.0 $0.05 / $0.10 / $0.20 per s (480/720/1080P), also in "Token Plan" — [Alibaba blog](https://www.alibabacloud.com/blog/wan3-0-30-second-ai-video-generation-from-any-input_603452); one review cites discounted $0.035/$0.07/$0.14 (unverified) — [kingy.ai](https://kingy.ai/blog/wan-3-0-analysis/); Wan 3.0 Prime on fal $0.068/$0.14/$0.28 per s — [llm-stats](https://llm-stats.com/blog/research/wan-3.0-launch); AA Wan 3.0 $12/min, Wan 2.7 $9/min — [AA](https://artificialanalysis.ai/video/leaderboard/image-to-video)

**Hunyuan**: fal HunyuanVideo 1.5 $0.075/s (480p); PiAPI $0.09/gen — [fal](https://fal.ai/models/fal-ai/hunyuan-video-v1.5/text-to-video), [PiAPI](https://piapi.ai/hi/hunyuan)

### Inferences
- Approx. USD conversion for Vidu official credits (assuming ~7.1 RMB/USD, my assumption): Q3-pro 1080p 24 cr/s = 0.75 RMB/s ≈ $0.105/s (off-peak ≈ $0.053/s); Q3-turbo 1080p ≈ $0.057/s (off-peak ≈ $0.031/s); Q4 Preview 1080p ≈ $0.105/s, 4K ≈ $0.34/s. A 6 s 1080p Q3-pro start-end clip ≈ $0.63 (≈ $0.32 off-peak). Note AA/Atlas show $0.16/s for Q3 Pro 1080p, so the official USD rate for non-China accounts may differ from the RMB credit table.
- Example budget for 50 clips × 6 s at 1080p (300 s output, before rerolls): PixVerse V6 ≈ $24–35; Vidu Q3 Pro ≈ $16 (off-peak) to $48; Wan 2.7 ≈ $45; Wan 3.0 ≈ $60; Seedance 2.0 BytePlus ≈ $110, fal ≈ $205; MiniMax H3 768p ≈ $27 (needs upscale), 2K ≈ $39–55. Rerolls (realistically 3–5× per accepted clip) multiply these.
- For Seedance, the Dreamina web subscription is far cheaper per second than API (Pro 720p 17 cr/s ≈ $0.16/s at Basic list price; 1080p rates not listed), but web workflows are manual and resolution/credit rates above 720p are unclear.

### Gaps
- Official Vidu USD pricing for international accounts (only RMB credits found), Vidu web subscription plans (vidu.com/pricing not retrieved).
- Official PixVerse API credit price per USD (VidCost figure ~$0.00444/credit is secondary).
- Seedance 1080p credit rate on Dreamina; whether Dreamina web exposes first+last frame for 2.0 (pricing page silent).
- Replicate availability/prices for H3, Vidu Q3/Q4, PixVerse V6, Seedance 2.x not checked (only older hailuo-02-fast seen on Replicate — [Replicate](https://replicate.com/minimax/hailuo-02-fast/versions/897cec901da07edb7e59df66e2592aef4e26b9058c08dacdd77c0b5c41f9568d/api)).

## 5. Access from Ukraine/EU (web availability, payment)

### Takeaway
No source states availability or blocking for Ukraine specifically for any of these services. Dreamina lists 34 European markets for its Basic offer (UK, DE, FR, IT, ES named) and EUR pricing exists; reports on Seedance availability in Europe conflict. API routes via global aggregators (fal, WaveSpeed, Atlas Cloud, OpenRouter) and the providers' international platforms (platform.vidu.com, api.minimax.io, BytePlus, Alibaba Cloud international) are the most likely workable paths, but this is unverified for Ukraine.

### Cited Findings
- Dreamina Basic offer region list: 34 European markets incl. UK, Germany, France, Italy, Spain "and others"; 21 Americas markets; Mexico inactive; eligibility depends on market, account, payment method — [Dreamina pricing](https://dreamina.capcut.com/seedance/seedance-2-0-pricing) (page text truncated; Ukraine not confirmed either way)
- Conflicting third-party claims: Seedance 2.0 inaccessible in "parts of Europe" vs available in "130+ countries including most of Europe" — [search summary: higgsfield](https://higgsfield.ai/blog/best-platforms-to-access-seedance-2-0), [Atlas Cloud](https://www.atlascloud.ai/blog/case-studies/how-to-use-seedance-2)
- Wan 2.7 has separate International vs China (Beijing) price lists on Model Studio — [Model Studio pricing via search](https://www.alibabacloud.com/help/en/model-studio/model-pricing)
- Vidu Q4 Preview: "final resolutions, features and terms may vary by plan and region" — [search summary of PR coverage](https://www.unite.ai/vidu-releases-q4-preview-of-next-generation-flagship-ai-video-model/)
- A targeted search for Hailuo/Vidu/PixVerse/Dreamina Ukraine restrictions found nothing — [search result](https://pixo.video/ru/alternatives/hailuo)

### Inferences
- Since all candidates are reachable through fal.ai / WaveSpeed / Atlas Cloud / OpenRouter (card payment, global), Ukraine access is likely feasible via aggregators even if a consumer web app geoblocks; personal use with no commercial distribution reduces licensing concerns.

### Gaps
- Ukraine-specific availability and payment acceptance (Ukrainian Visa/Mastercard) for vidu.com, hailuoai.video, app.pixverse.ai, dreamina.capcut.com, BytePlus, Alibaba Cloud international — not found; requires direct test.

## 6. Alpha / transparent output or background-removal features

### Takeaway
No service in scope documents alpha-channel (transparent) video output. The only related feature found is Seedance 2.5's "green-screen" editing mode (BytePlus, 720p max on the direct route). The planned #00FF00-background + chroma-key approach remains necessary.

### Cited Findings
- Seedance 2.5 adds timestamp-level editing and explicitly names green-screen, camera-perspective and reference-based editing — [aifreeapi](https://www.aifreeapi.com/en/posts/seedance-video-models-2026)
- Seedance 2.5 output on BytePlus LAS is 480p/720p only — [aifreeapi](https://www.aifreeapi.com/en/posts/seedance-video-models-2026)
- fal Seedance 2 offers codec H264/H265 and bitrate `high` (relevant to clean chroma keying; no alpha codec) — [fal](https://fal.ai/models/bytedance/seedance-2.0/image-to-video/llms.txt)

### Inferences
- Choosing high bitrate / H265 where available (Seedance via fal `bitrate_mode: high`) should reduce compression artifacts at green/character edges, improving chroma-key quality.
- Seedance 2.5 green-screen editing could be used to re-matte a clip onto green, but at 720p it fails the >=1080p requirement unless upscaled.

### Gaps
- Whether Vidu, PixVerse, MiniMax, or Wan offer background removal / matting tools in their web apps — not found in sources read.
- How well each model preserves a flat #00FF00 background without introducing gradients, shadows, or green spill on the character — no reports found; must be tested.
