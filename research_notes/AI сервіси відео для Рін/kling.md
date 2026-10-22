# Kling AI video model family (Kuaishou), state as of 22 Oct 2026, for anime-character clip production

Scope: models and modes relevant to producing short, chained, loopable full-body clips of one anime character on #00FF00, with a static camera and exact start/end poses. Research date: 2026-10-22. The official API docs and developer pricing pages (kling.ai/document-api, kling.ai/dev/pricing) are rendered by JavaScript and came back empty through the fetch tool, so some official figures below are quoted through search snippets or third-party pages. Each such case is marked.

## 1. Which Kling models/modes exist now and what each supports

### Takeaway
As of late Oct 2026 the main lineup is: **Kling 4.0** (full release on the web app around 15 Oct 2026; developer API still "coming soon"), **Kling 4.0 Flash** (720p, first frame only, no multi-keyframes), **Kling VIDEO 3.0** and **VIDEO 3.0 Omni** (successors to 2.6 and O1; start+end frame, Elements, multi-shot, native audio toggle), **Motion Control 3.0** (a reference video drives the character), plus legacy 2.6/2.5 Turbo/2.1/1.6/O1, which are still sold through API resellers. Kling 4.0 is the only model with multiple keyframes: up to 10 per clip. How they are placed in time is not documented anywhere I could find.

### Cited Findings

**Kling 4.0 / 4.0 Flash, release and access**
- Kling's official blog (dated 30 Sep 2026) says 4.0 Flash went to "a limited group of early-access users on September 28". At that point the full 4.0 was to "officially launch in October". — [Kling blog: Kling 4.0 vs 3.0](https://kling.ai/blog/kling-4-vs-3)
- A Kling post on 28 Sep 2026 said "Kling 4.0 Flash is live now for Ultra Yearly subscribers". The full 4.0 has been "fully available October 15, 2026, on kling.ai and through MCP and CLI". Enterprise/developer API access is "coming soon", with no model ID or rate given (article last reviewed 17 Oct 2026). — [CellCog](https://cellcog.ai/blog/kling-4-0/)
- Kie.ai also reports full availability to all users on 15 Oct 2026, sourced to an X user (@0xLogicrw), so it is a report rather than an official statement. It says the developer API is "Coming soon" and that MCP and CLI are live. — [kie.ai release analysis](https://kie.ai/blog/kling-4-0-release-analysis-30-second-clips-keyframes-pricing)
- PiAPI's Kling page lists "Kling 4 coming soon". — [PiAPI](https://piapi.ai/kling-api)
- Sources disagree on the announcement date. Morphic says 27 Sep 2026 and most others say 28 Sep. — [Morphic](https://morphic.com/resources/models/kling-4); [DEV Community, 14 Oct 2026](https://dev.to/neuraitool/kling-40-explained-keyframes-omni-reference-and-what-changed-in-ai-video-53ee)

**Kling 4.0, multi-keyframe control**
- Official blog: Kling 3.0 "supports Start & End Frames but not multiple keyframes". Kling 4.0 "supports up to 10 keyframe images placed along the timeline". The example shows keyframes at 0 s, 6 s, 12 s, 20 s and 28 s, which suggests they can be put at arbitrary timestamps. — [Kling blog](https://kling.ai/blog/kling-4-vs-3)
- One third-party studio UI (JXP) describes "Keyframes to Video" as "a first frame with up to 8 middle frames and an optional last frame", which makes 10 in total. — [JXP Kling 4.0](https://www.jxp.com/kling/kling-4-0)
- Kie.ai cites the same start + 8 mid + end layout from a community post and says Kling has not confirmed it. Timestamps, per-keyframe prompts and spacing rules are "not stated". — [kie.ai](https://kie.ai/blog/kling-4-0-release-analysis-30-second-clips-keyframes-pricing)
- DEV Community says each keyframe "acts like a storyboard panel with its own description" and that you can revise one shot without regenerating the whole clip. This is a secondary claim with no primary source. — [DEV Community](https://dev.to/neuraitool/kling-40-explained-keyframes-omni-reference-and-what-changed-in-ai-video-53ee)
- Morphic: "Up to 10, plus first and last frame control. You upload the frames the clip must hit, and the motion fills in between." — [Morphic](https://morphic.com/resources/models/kling-4)
- Kling 4.0 Flash keyframes: "First frame only". — [CellCog](https://cellcog.ai/blog/kling-4-0/)

**Kling 4.0, other specs**
- Duration is 3–30 s in a single pass for 4.0 and 3–20 s for Flash. — [Kling blog](https://kling.ai/blog/kling-4-vs-3); [CellCog](https://cellcog.ai/blog/kling-4-0/)
- Resolution: the official spec lists 720p, 1080p and 4K, and adds 10-bit HDR at 1080p/4K, which is still marked "coming soon". Flash is 720p 8-bit SDR only. — [Kling blog](https://kling.ai/blog/kling-4-vs-3); [CellCog](https://cellcog.ai/blog/kling-4-0/)
  - Conflict: kie.ai says only 720p and 1080p were live at launch. JXP's studio offers only 720p/1080p even though the official spec lists 4K. Morphic renders drafts at 720p and finals at 1080p. — [kie.ai](https://kie.ai/blog/kling-4-0-release-analysis-30-second-clips-keyframes-pricing); [JXP](https://www.jxp.com/kling/kling-4-0); [Morphic](https://morphic.com/resources/models/kling-4)
- Aspect ratios are 21:9 (new), 16:9, 1:1, 9:16 and smart/auto. — [CellCog](https://cellcog.ai/blog/kling-4-0/); [JXP](https://www.jxp.com/kling/kling-4-0)
- Frame rate: none of the sources gives a figure for 4.0.
- References: up to 15 combined assets, meaning up to 10 images, up to 7 subjects (up to 3 of them video-based), up to 5 reference videos totalling 30 s, and voice references. — [Kling blog](https://kling.ai/blog/kling-4-vs-3)
- Uploads (on JXP's front-end): PNG/JPEG and MP4/MOV, shortest side at least 700 px, at most 100 MB each. — [JXP](https://www.jxp.com/kling/kling-4-0)
- Prompt length is up to 8,000 tokens (JXP says 8,000 characters). — [Kling blog](https://kling.ai/blog/kling-4-vs-3); [JXP](https://www.jxp.com/kling/kling-4-0)
- Audio is two-channel stereo with "improved lip-sync accuracy". JXP found no audio toggle in its UI. — [Kling blog](https://kling.ai/blog/kling-4-vs-3); [JXP](https://www.jxp.com/kling/kling-4-0)
- Video editing: up to 5 input clips (30 s combined). Editable items include "expressions, body movement, characters, objects, backgrounds, camera position and movement". — [Kling blog](https://kling.ai/blog/kling-4-vs-3)
- Video extension to 2 minutes is "coming soon". — [Morphic](https://morphic.com/resources/models/kling-4)
- Negative prompt and cfg for 4.0 are not mentioned in any source (official blog, CellCog, kie.ai, JXP, Morphic).

**Kling VIDEO 3.0 and 3.0 Omni**
- Official guide (6 Feb 2026): VIDEO 2.6 was upgraded to VIDEO 3.0, and VIDEO O1 to VIDEO 3.0 Omni. Duration is 3–15 s. Start & End Frames-to-Video is supported. Start Frame + Element Reference is 3.0 only. Multi-shot comes in two forms: automatic, and "Custom Multi-Shot" with a duration per shot. Audio can be set to Native Audio or No Native Audio, with optional voice tone control. — [Kling VIDEO 3.0 Model Guide](https://kling.ai/quickstart/klingai-video-3-model-user-guide)
- Official comparison (3 Jul 2026): 3.0 is "prompt-led". Omni is "reference-driven" and adds multi-image reference, video element reference and element voice control. Both support start/end frames. — [Kling blog: VIDEO 3.0 vs Omni 3.0](https://kling.ai/blog/kling-v3-vs-o3-comparison-guide)
- Elements are built from 2–4 reference images, or from a character video. 3.0 can bind up to 3 elements in start-frame or start+end-frame generation, and the elements must appear in the reference frames. In 3.0 Omni and O1 you can upload at most 4 images/elements alongside a video, or 7 without one. — [Kling Element Library guide / O1 guide via search snippets](https://kling.ai/quickstart/klingai-element-library-3-user-guide); [O1 guide](https://kling.ai/quickstart/klingai-video-o1-user-guide)
- In O1 and Omni you tag uploaded images as the opening and closing frames inside the prompt. "Generation with only an end frame is not supported for now". — [Kling VIDEO O1 User Guide (search snippet)](https://kling.ai/quickstart/klingai-video-o1-user-guide)
  - Conflict: Higgsfield says Kling 3.0 lets you "constrain the model using only an end frame". — [Higgsfield search snippet](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation)
- 4K: "30 credits per second" for the VIDEO 3.0 series, subscriber-only (official blog, 28 Jul 2026). — [Kling 3.0 Credit Cost guide](https://kling.ai/blog/kling-video-3-0-credit-cost-guide)
- Official API (3.0 Omni image-to-video): inputs are typed as prompt, first_frame, last_frame and element inside a `contents` array, with elements referenced as @tags. The prompt "can include positive and negative descriptions", with a 3072-character cap (2500 recommended). The text-to-video endpoint has a separate `negative_prompt` (≤2500 chars), and the docs recommend writing negatives as negative sentences inside the positive prompt. All of this comes from search snippets because the pages render client-side. — [Kling API: 3.0 Omni Image to Video](https://kling.ai/document-api/api/video/3-0-omni/image-to-video); [Kling API: Omni Video](https://kling.ai/document-api/apiReference/model/OmniVideo)

**Motion Control (reference video drives the character)**
- Motion Control 3.0 compared with 2.6: up to 7 character reference images in the web UI (2.6 takes 1), output up to 15 s (2.6: 10 s), and native lip-sync. The API accepts one character image per request. The web UI has a strength slider, which third-party APIs map to cfg_scale (0–1). Recommended reference clips are 2–5 s. Article dated 14 Jul 2026. — [Atlas Cloud guide](https://www.atlascloud.ai/blog/guides/kling-ai-motion-control)
- `character_orientation`: "video" follows the reference motion (max 30 s), and "image" keeps the pose of the source artwork (max 10 s). These are aggregator docs, not official. There is also a keep-original-audio boolean that defaults to true. Std is 720p and Pro is 1080p. — [MuAPI](https://muapi.ai/ar/playground/kling-v3.0-std-motion-control); [Unifically](https://unifically.com/models/kling-3.0-motion-control)
- Advice for the character image: head, shoulders and torso should be clearly visible. — [Unifically](https://unifically.com/models/kling-3.0-motion-control)

**Motion Brush / camera control**
- Motion Brush paints directional vectors (left/right/up/down/zoom). The guide does not say which 2026 models support it. — [Atlas Cloud](https://www.atlascloud.ai/blog/guides/kling-ai-motion-control)
- fal's Kling 3.0 Pro spec table lists camera control as unavailable. It appears only in the V1 legacy endpoints. — [fal: Seedance 2.0 vs Kling 3.0, 20 Apr 2026](https://fal.ai/learn/tools/seedance-2-0-vs-kling-3-0)

**Legacy models still sold (API resellers)**
- PiAPI sells Kling 3.0, 3.0 Omni, 2.6, 2.5, 2.5 Turbo Pro, 2.1 Master, 1.6, O1, Motion Control, AI Avatar, Effects, Lip Sync, Sound and Virtual Try-On. — [PiAPI](https://piapi.ai/kling-api)
- fal (via CostGoat, 21 Oct 2026) lists 27–29 Kling endpoints, including v2.5-turbo, v2.6, o1, v3, "v3 Turbo", "o3" (= 3.0 Omni), v3 4K and AI Avatar. — [CostGoat](https://costgoat.com/pricing/kling)

### Inferences
- **Kling 4.0 multi-keyframes are the closest feature to this project's "pose graph".** One 30 s generation could pass through, for example, base pose → gesture A → base pose → gesture B → base pose, and then be cut into separate clips at the keyframe timestamps. Two things are unverified: how exactly each keyframe is hit (the owner's ~99% silhouette match was measured on 3.0, not 4.0), and whether timestamps are user-settable in the web UI. Test this before relying on it.
- Flash is not useful here because it takes a first frame only.
- For chained clips today, the proven option is still 3.0 / 3.0 Omni start+end frames. Omni lets you add a character Element to strengthen identity across dozens of clips.
- Motion Control 3.0 with `character_orientation=image` (≤10 s) could curb the invented "wide arm swings": you supply your own subtle reference motion (yourself on video, or a 3D mannequin render). Motion Control does not take an end frame in the sources found, so end-pose fidelity would rely on the reference video ending in the base pose.
- The model behind "v3 Turbo" on fal is not described in any source I found. Treat it as a faster 3.0 variant (unverified).

### Gaps
- Kling 4.0: how keyframe timestamps are set in the web UI (drag on a timeline or fixed spacing?), minimum spacing, whether each keyframe takes its own prompt, fps, and whether a negative prompt or cfg is exposed. No primary documentation was found.
- Whether Motion Brush exists in any 2026 model on the official site. My background knowledge (unverified, pre-2026) is that it was tied to the 1.x models.
- Whether 2.6/2.5/2.1 are still selectable on the official kling.ai web app (as opposed to API resellers).
- Official input image limits for 3.0. The owner's "2 MP" figure was not confirmed or refuted. Common reseller docs list JPEG/PNG/WebP via URL and give no size cap.

## 2. Resolution, fps, duration, aspect ratio, 4K, input limits per model

### Takeaway
3.0/Omni: 3–15 s in 1 s steps, 720p (std) or 1080p (pro), 4K at 30 credits/s on the web, 16:9/9:16/1:1, and the output aspect follows the start image. 4.0: 3–30 s, 720p/1080p (4K listed, but some front-ends don't offer it), 9:16 available. Flash: 3–20 s, 720p only. No source states the fps. The owner measured 24 fps on 3.0.

### Cited Findings
- fal Kling 3.0 Pro I2V `duration` is an enum of 3–15 s, with a default of "5". Multi-prompt shot durations run 1–15 s. — [fal API](https://fal.ai/models/fal-ai/kling-video/v3/pro/image-to-video/api)
- Kling 3.0 Pro is up to 1080p with aspect ratios 16:9, 9:16 and 1:1. — [fal blog](https://fal.ai/learn/tools/seedance-2-0-vs-kling-3-0)
- On Replicate, `mode` = standard (720p) or pro (1080p). `aspect_ratio` (16:9, 9:16, 1:1) "is ignored when a start image is used". — [Replicate kling-v3-video](https://replicate.com/kwaivgi/kling-v3-video)
- The RunComfy skill lists an output `aspect_ratio` enum of 16:9, 9:16, 1:1, 4:3, 3:4 and 21:9, plus an end frame via `tail_image_url`, and accepts JPEG/PNG/WebP over an HTTPS URL. This is third-party. — [mcpservers mirror of RunComfy skill](https://mcpservers.org/es/agent-skills/runcomfy-com/kling-3-0)
- fal has separate "v3 4K" image-to-video and text-to-video endpoints at $0.42/s. — [CostGoat](https://costgoat.com/pricing/kling)
- Kling 4.0 specs: see section 1.

### Inferences
- For 1080×1920 9:16, give 3.0 a 9:16 start image. The output follows the start image's aspect ratio, which matches the owner's 1080×1920 result.
- 4K is possible on 3.0 (web, or fal's v3 4K endpoint), but at about 3.75× the 1080p silent price. For a desktop companion, 1080p is probably enough.
- The 5.04 s the owner measured is consistent with "5 s" being slightly overshot, about 121 frames at 24 fps. Plan to trim or retime.

### Gaps
- No primary source gives the fps for any model. The 24 fps figure is the owner's own measurement.

## 3. Pricing: credits, subscriptions, API, resellers, watermark

### Takeaway
On the web app, 3.0 costs 6 credits/s at 720p and 8 at 1080p without audio, and 9 and 12 with native audio (official). A silent 5 s 1080p clip is therefore 40 credits. Plans run Standard 660 credits/month (from $6.99 first month, $8.80 after), Pro 3,000 ($25.99 → $32.56), Premier 8,000 and Ultra 26,000. Per-second API prices on fal for 3.0 Pro are about $0.112 silent and $0.168 with audio. Kling 4.0 web credits are disputed: one report says 10 and 15 credits/s at 720p/1080p. Its official API rate card shows 1.0 and 1.5 "units"/s, but the API itself is not yet generally available.

### Cited Findings
- **Official 3.0 web credits/s:** Native Audio is 12 (1080p) and 9 (720p). No Native Audio is 8 and 6. Voice Tone Control adds 2. Examples: 5 s 1080p with audio = 60 credits, 5 s 720p silent = 30. — [Kling VIDEO 3.0 Model Guide, 6 Feb 2026](https://kling.ai/quickstart/klingai-video-3-model-user-guide)
- **3.0 Omni with a video input:** silent output costs 16 credits/s at 1080p and 12 at 720p (third-party summary of the official guide). — [search summary citing virse.ai/projedefteri](https://www.virse.ai/blog/kling-3-0-pricing)
- **4K (3.0 series):** 30 credits/s, subscriber-only. — [Kling credit cost guide, 28 Jul 2026](https://kling.ai/blog/kling-video-3-0-credit-cost-guide)
- **Subscription plans (official, 28 Jul 2026), first-subscription price → renewal, credits/month, best $/100 credits:** Basic $0 with no monthly credits. Standard $6.99 → $8.80, 660 credits, $1.33. Pro $25.99 → $32.56, 3,000, $1.09. Premier $64.99 → $80.96, 8,000, $1.01. Ultra $127.99 → $159.99, 26,000, $0.62. — [Kling credit cost guide](https://kling.ai/blog/kling-video-3-0-credit-cost-guide)
- **Basic (free) tier:** the page does not list 1080p or watermark removal for Basic. Watermark removal is a benefit of Standard and higher. Free output is "not for commercial use". — [Kling credit cost guide](https://kling.ai/blog/kling-video-3-0-credit-cost-guide)
- **Kling 4.0 web credits (reported, not official):** 15 credits/s at 1080p and 10 at 720p (the 720p figure is arithmetic). A 30 s 1080p clip is 450 credits, which one reviewer put at about 16 yuan. — [kie.ai](https://kie.ai/blog/kling-4-0-release-analysis-30-second-clips-keyframes-pricing)
  - Conflict: JXP's own front-end charges 5 and 7 of *its* credits/s at 720p/1080p, or 4 and 6 with a reference video. These are JXP's credits, not Kling's. A different snippet attributed to JXP gave 2/3 and 3/4. — [JXP](https://www.jxp.com/kling/kling-4-0)
  - The 4.0 Flash price was "not officially published" as of 14 Oct 2026. — [DEV Community](https://dev.to/neuraitool/kling-40-explained-keyframes-omni-reference-and-what-changed-in-ai-video-53ee)
- **Official API rate card (Kling dev pricing, via search snippet):** Kling 4.0 is 1.0 unit/s at 720p and 1.5 units/s at 1080p. Input-video variants are 0.6 and 0.9 units/s. No 4K price is listed, and the dollar value of a unit is not stated. API packages run from $9.80 to $7,560 (prepaid). — [Kling API Pricing](https://kling.ai/dev/pricing); [search summary of cost guides](https://www.cloudzero.com/blog/kling-ai-pricing/)
- **Reseller rate for Kling 4.0:** Unifically charges $0.1134/s (Standard, 720p) and $0.1701/s (Pro, 1080p). This is unverified. — [Unifically](https://unifically.com/blogs/kling-4.0)
- **fal per-second prices, as of 21 Oct 2026:** v2.5-turbo Std I2V $0.042. v2.5-turbo Pro and v2.6 Pro I2V $0.070. v3 Std and o1 Std $0.084 (up to $0.154 with voice control). o3 Std $0.084 (up to $0.112 with audio). v3 Pro $0.112 (up to $0.196 with voice control). o3 Pro $0.112 (up to $0.140 with audio). v3 Turbo Std $0.112, v3 Turbo Pro $0.140. v3 4K and o3 4K $0.420. — [CostGoat (fal live prices)](https://costgoat.com/pricing/kling)
- **fal 3.0 Pro with Elements (Apr 2026):** $0.224 silent, $0.336 with audio, $0.392 with voice control. Motion control is $0.168/s. Without elements: $0.112, $0.168, $0.196. — [fal blog](https://fal.ai/learn/tools/seedance-2-0-vs-kling-3-0)
- **PiAPI:** Kling 3.0 $0.10–0.20/s, 3.0 Omni $0.10–0.15/s, O1 $0.39–1.04 per generation, 2.6 $0.20–0.66 per 5 s, Motion Control $0.065–0.26/s, Lip Sync $0.10 per 5 s. — [PiAPI](https://piapi.ai/kling-api)
- **Atlas Cloud:** Kling 3.0 at $0.071/s Std and $0.095/s Pro. — [Atlas Cloud](https://www.atlascloud.ai/blog/guides/kling-ai-motion-control)

### Inferences
- **Web cost for this project:** a silent 3.0 clip at 1080p is 8 cr/s, so 5 s = 40 credits and 10 s = 80 credits. The Pro plan (3,000 cr) gives about 75 five-second takes, rerolls included. Ultra gives about 650.
- **API cost:** a silent 5 s fal v3 Pro take is about $0.56. Using a character Element doubles that to about $1.12. A Std (720p) take is about $0.42, which suits pose and motion tests.
- **Turn audio off:** native audio raises the web credit cost by 50%. It probably also encourages speech (see section 4), so switching it off saves money and is likely to help with the mouth problem.

### Gaps
- The official dollar value of an API "unit", and an official 4.0 4K credit rate.
- Official per-second web credits for Kling 4.0 and 4.0 Flash: no primary source found.
- Replicate's per-second price for kling-v3 did not appear on the model page (it was quoted secondhand as $0.168/s).

## 4. Strengths and weaknesses for anime, consistency, hands, mouth, blur; prompt techniques; loops

### Takeaway
I found no independent 2026 test of Kling on anime characters, hands or motion blur. The vendor says 3.0 "locks" identity through Elements. For the talking problem, the levers with sources behind them are: native audio OFF, no dialogue in the prompt, `negative_prompt`/cfg (API only), and Motion Control with a calm reference video. For a static camera, plain phrases such as "static camera, locked-off, no camera movement" are reported to work best. Loops come from using the same image as both start and end frame. No Kling-specific loop guide was found.

### Cited Findings
- Kling's pages claim 3.0 lets users "strictly lock a character's appearance" from one photo or multiple angles. This is marketing, not a test result. — [search summary of kling.ai Motion Control page](https://kling.ai/feature/ai-motion-control)
- Kling 3.0's features include character persistence through elements and multi-character coreference. — [fal blog](https://fal.ai/learn/tools/seedance-2-0-vs-kling-3-0)
- Dialogue "influences mouth movement and subtle head motion". Advice: lock identity and motion first, then add native audio, and keep dialogue to 1–2 sentences. — [search summary of Kling 3.0 guides (magichour/oakgen)](https://magichour.ai/blog/how-to-use-kling-30)
- Static-camera wording reported in guides:
  - "static lock — no camera movement at all" as a camera option — [magichour](https://magichour.ai/blog/kling-30-reference-guide)
  - "Static camera shot, stable framing, no camera movement" — [RunDiffusion](https://www.rundiffusion.com/kling-3-0-pro-ai-tool)
  - "Locked-off camera … no camera movement" — [PicassoIA](https://blog.picassoia.com/es/kling-3-0-tricks-smoother-video)
  - "Simple, explicit directions produce more stable results than complex cinematic language" — [search summary](https://oakgen.ai/blog/kling-3-prompting-guide)
- For image-to-video, describe "motion and continuation, not starting state". — [Mootion guide](https://mootion.com/ugc/en/use-case/kling-3-0-image-to-video-guide)
- Kling's API docs recommend expressing negatives as negative sentences inside the positive prompt. — [Kling API Omni Video (snippet)](https://kling.ai/document-api/apiReference/model/OmniVideo)
- On fal, Kling 3.0 Pro has `negative_prompt` (default "blur, distort, and low quality") and `cfg_scale` (0–1, default 0.5, higher means closer prompt adherence). `generate_audio` defaults to **true**, so it must be set to false explicitly. — [fal API](https://fal.ai/models/fal-ai/kling-video/v3/pro/image-to-video/api); [fal blog](https://fal.ai/learn/tools/seedance-2-0-vs-kling-3-0)
- Motion blur tip (from realistic-video prompting): keep blur in the background so the subject stays sharp. — [Atlas Cloud prompts guide](https://www.atlascloud.ai/hi/blog/guides/mastering-kling-3.0-10-advanced-ai-video-prompts-for-realistic-human-motion)
- 4.0's long clips: kie.ai suggests testing for identity drift in frames 20–30. This is a recommended test, not a documented defect. One subjective comparison says Kling has stronger "motion and attack impact" while Seedance is "more stable". — [kie.ai](https://kie.ai/blog/kling-4-0-release-analysis-30-second-clips-keyframes-pricing)
- General loop practice: the last frame must lead back to the first, drop the duplicated seam frame, and avoid easing at the seam. — [Novedge C4D tip](https://novedge.com/blogs/design-news/cinema-4d-tip-cinema-4d-seamless-loop-animation-workflow); [Adobe community](https://community.adobe.com/questions-529/how-to-create-seamless-looping-animation-41126)

### Inferences
- **Mouth or talking suppression, in order of what to try:**
  1. Native audio OFF ("No Native Audio" on the web, `generate_audio=false` on the API). The audio model is the most likely driver of the lip movement the owner sees.
  2. Never mention speech, voice, expression change or "mouth" in the positive prompt. Mentioning "mouth closed" may itself draw attention to the mouth (an inference, not verified).
  3. On the API, use `negative_prompt` "talking, speaking, lip movement, open mouth, lip sync, chewing" and a higher `cfg_scale` (around 0.7–0.8).
  4. Use Motion Control from a reference video where the mouth stays still.
  5. As a fallback, composite or freeze the face region in post. Because the camera is static and the background is green, a face patch from the start frame could be warped or held.
- **Wide arm swings:** prompt the amplitude explicitly ("small, subtle, slow movement; arms stay close to body; minimal gesture") and keep clips short (3–5 s). Fewer seconds between fixed start and end frames leaves less room for invented motion (inference). A higher cfg_scale on the API may also help. Motion Control is the deterministic route.
- **Motion blur on fast hands:** request "slow, deliberate hand movement", and add "motion blur" to the negative prompt on the API. Generating at 4K and downscaling might reduce smear, but this is untested.
- **Seamless idle loop:** use the same image as start and end frame on 3.0 (or as first and last keyframe on 4.0), with a prompt such as "gentle breathing, slight shoulder rise, otherwise still". Then drop the last frame when looping. Since end-frame fidelity is ≈99% silhouette, a 2–4-frame crossfade at the seam may still be needed.
- **Anime style:** no independent evidence either way. The owner's tests are the best data available.

### Gaps
- No Reddit or community thread with a tested phrase that reliably stops Kling from talking was retrieved. Search results lacked Reddit hits.
- No independent anime-specific or hands-specific benchmark for Kling 3.0 or 4.0 was found.

## 5. Official site vs third-party front-ends (Artlist, Freepik, Higgsfield, Morphic, etc.)

### Takeaway
Front-ends expose subsets of the features. The API (official, fal, Replicate) exposes `negative_prompt`, `cfg_scale`, `generate_audio` and `end_image`. Consumer front-ends often hide negative prompt and cfg, as the owner saw on Artlist. Higgsfield supports start/end frames for Kling 3.0, but only under its "General" preset. Morphic offers Kling 4.0 at 720p drafts and 1080p finals. JXP's studio exposes 4.0 keyframes but not 4K.

### Cited Findings
- On Higgsfield, start/end frames work only with the General preset, and the Kling 3.0 guide says you can use "only an end frame". — [Higgsfield search snippets](https://higgsfield.ai/blog/Kling-Start-End-Frames); [Higgsfield 3.0 guide](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation)
- ComfyUI's Kling 3.0 First-Last-Frame node exposes `negative_prompt` and `cfg_scale`, and Comfy's Higgsfield-routed examples pass `"cfg_scale": 0.5`. — [RunComfy node](https://www.runcomfy.com/comfyui-nodes/ComfyUI/kling-first-last-frame-node); [Comfy docs Higgsfield BYOK](https://docs.comfy.org/ja/development/comfy-router/higgsfield-byok.md)
- Replicate's kling-v3-video exposes mode, duration, aspect_ratio, generate_audio, negative_prompt and multi_prompt. — [Replicate](https://replicate.com/kwaivgi/kling-v3-video)
- On Morphic, Kling 4.0 is live with drafts at 720p and finals at 1080p, and 4.0 generations are 10% off. Flash was "coming soon" there. — [Morphic](https://morphic.com/resources/models/kling-4)
- JXP's 4.0 studio offers 720p/1080p only (no 4K). Free vouchers cover 720p, text-to-video, 5 s only. — [JXP](https://www.jxp.com/kling/kling-4-0)
- The Motion Control web UI has a strength slider and allows multiple character images. The API takes 1 image, with strength mapped to cfg_scale. — [Atlas Cloud](https://www.atlascloud.ai/blog/guides/kling-ai-motion-control)

### Inferences
- **For this project, the official API or fal/Replicate is strictly better than Artlist** for 3.0 start+end frame work. It adds negative_prompt, cfg_scale and an explicit audio-off switch, and it allows batch scripting of dozens of clips. 4.0 keyframes for now require the official web app, MCP/CLI, or a front-end such as JXP or Morphic.

### Gaps
- No source was found on what Freepik or Artlist expose for Kling 3.0 or 4.0 (negative prompt, cfg, end frame, audio toggle).
- Whether the official kling.ai web UI for 3.0 has a negative-prompt field or cfg ("creativity") slider in Oct 2026 is unconfirmed. Older Kling versions (1.x–2.x, pre-2026, from background knowledge) had both. The 3.0 user guide doesn't mention them.

## 6. Transparent/alpha output or background removal

### Takeaway
None of the sources mentions native alpha output for any Kling model. The workflow remains a solid-colour background followed by external keying or matting.

### Cited Findings
- No official alpha export was found. Kling's "create transparent background" explore page is a user gallery and describes no export option. — [kling.ai explore page (search summary)](https://kling.ai/explore/create_transparent_background_free)
- A third-party service, VideoBGRemover, markets Kling-video background removal with WebM/MOV/PNG alpha export. This is the vendor's own claim. — [VideoBGRemover](https://videobgremover.com/ai-video/kling)

### Inferences
- The owner's approach (#00FF00 plus chroma key) stays the right one, since the owner reports the green stays clean on 3.0. Watch for green spill on the light-blue shirt and tan pantyhose, and for edges softened by motion blur on fast hands. Blur is a keying problem as well as a quality one.

### Gaps
- Whether Kling 4.0's video-editing mode (which can change "backgrounds") could output a cleaner key plate: untested and undocumented.
