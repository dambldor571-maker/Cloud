# Western commercial AI video generators (Veo / Gemini Omni, Sora, Runway, Luma, Pika, Midjourney) as of 22 Oct 2026, judged for chained 9:16 green-screen anime clips

Research date: 2026-10-22. The scope was 25 tool calls, so some items rest on one fetch or on third-party pages. These are flagged as such.

**Market changes since 2025 that the report writer must know:**
1. **OpenAI Sora is gone.** The app closed on 26 Apr 2026 and the Sora 2 API shut down on 24 Sep 2026.
2. **Google's Gemini API Veo 3.1 *preview* models shut down on 22 Oct 2026, the day of this research.** Google now steers developers to **Gemini Omni Flash** (`gemini-omni-1.1-flash`). Veo 3.1 GA models remain on Vertex AI, now branded "Gemini Enterprise Agent Platform", with a retirement date of "Nov 17, 2026 or later".
3. **Runway is now a multi-model aggregator.** It hosts Gen-4.5, Aleph 2.0 and Act-Two, plus Veo 3.1, Gemini Omni Flash, Kling 3.0/O3, Seedance 2/2.5, Wan 3, Hailuo 3 and others, all billed in Runway credits.
4. **Luma's current model is Ray3.2** (9 Jun 2026), with up to 16 keyframes. Ray3.14 is also on the price list.

---

## Q1. Which models and services support the needed controls (image-to-video, first+last frame, multiple keyframes, character references, video-to-video, motion transfer, loop, camera lock, negative prompt, audio on/off)?

### Takeaway
Luma Ray3.2 is the only Western model found with first-party, documented **multi-keyframe control (up to 16 keyframes per clip)**. Luma also has a historical `loop` flag. Exact first and last frames are well supported by:
- Veo 3.1 (Vertex GA)
- Gemini Omni Flash
- Runway's hosted Seedance 2.5 and Aleph 2.0
- Midjourney (`--end`, `--loop`)

Audio is a recurring problem. Gemini Omni Flash and Veo always generate audio unless the host offers a no-audio SKU. Runway's API sells Veo 3.1 *without audio* at half price, but for Omni you can only suppress audio through the prompt. Sora is no longer an option.

### Cited Findings

**Google: Veo 3.1 (Vertex AI / "Gemini Enterprise Agent Platform")**
- Model IDs and status:
  - `veo-3.1-generate-001` and `veo-3.1-fast-generate-001` are GA, released 17 Nov 2025, with retirement "Nov 17, 2026 or later".
  - `veo-3.1-lite-generate-001` is Preview, released 2 Apr 2026. The page contradicts itself on whether Lite accepts images.
  — [Vertex Veo 3.1 model page, fetched 2026-10-22](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/veo/3-1-generate)
- Supported tasks: text-to-video, image-to-video and "first and last frames to video" on all three, plus video extension. Reference images ("generate videos from references") are supported on Generate and Fast but not on Lite. Reference-image-to-video is limited to **8 s only** on Generate. — [Vertex Veo 3.1 page](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/veo/3-1-generate)
- The Vertex model page did not mention a negative prompt or a `generateAudio` toggle. Sound generation is listed as "Supported". — [Vertex Veo 3.1 page](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/veo/3-1-generate)
- Gemini API (AI Studio): `veo-3.1-generate-preview`, `veo-3.1-fast-generate-preview` and `veo-3.1-lite-generate-preview` are deprecated and **"will be shut down on October 22, 2026"**. Google recommends migrating to Gemini Omni Flash or the GA models on the Enterprise Agent Platform (page last updated 2026-10-19). — [Gemini API video docs](https://ai.google.dev/gemini-api/docs/video); [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Runway's API sells Veo 3.1 at **40 credits/s with audio and 20 credits/s without audio**, and Veo 3.1 Fast at 15 credits/s with audio and 10 credits/s without, at $0.01 per credit. So a no-audio Veo path exists through Runway. — [Runway API pricing](https://docs.dev.runwayml.com/guides/pricing/)

**Google: Gemini Omni Flash (`gemini-omni-1.1-flash`), the Veo successor in the Gemini API, Flow and Runway**
- Tasks: `text_to_video`, `image_to_video`, `reference_to_video`, `edit` and `extend`. Called through the Interactions API with `previous_interaction_id` for multi-turn. — [Gemini API Omni docs](https://ai.google.dev/gemini-api/docs/omni)
- **First and last frame interpolation:** two images plus a transition prompt. Subject reference images are supported; the example uses 2 and no maximum is stated. Video references are limited to **max 3 clips, ≤3 s each**, and their audio is ignored. Audio references are unsupported. — [Gemini API Omni docs](https://ai.google.dev/gemini-api/docs/omni)
- Reference-image limits conflict across platforms:
  - Runway: up to 10 images, 3–10 s clips
  - Runware: 7
  - Morphic: 10 images + 3 clips
  - Wink: 5

  — [search summary of Runway/Runware/Morphic/Wink pages](https://runway.com/product/models/gemini-omni); [Runware guide](https://runware.ai/docs/models/google-gemini-omni-flash/guides/reference-driven-video); [Wink review](https://wink.ai/blog/gemini-omni-flash-review)
- **Loop:** a search summary said that passing the same image as first and last frame yields a loop "per the docs' parameter examples". However, my direct fetch of the Omni doc reported that loop is "not mentioned". **These two sources conflict, so this is unverified.** — [Gemini API Omni docs](https://ai.google.dev/gemini-api/docs/omni)
- **Negative prompt is explicitly unsupported as a parameter.** Put negatives in the main prompt. System instructions, temperature and `top_p` are also unsupported. — [Gemini API Omni docs](https://ai.google.dev/gemini-api/docs/omni)
- **Audio:** there is no on/off parameter. The model "generates audio by default", and control is through the prompt (e.g. "No dialogue"). — [Gemini API Omni docs](https://ai.google.dev/gemini-api/docs/omni)
- **Video-to-video editing** works on uploaded videos (≤10 s) or on generated videos. Extension adds 10 s per step up to 40 s total, and only appends at the end. — [Gemini API Omni docs](https://ai.google.dev/gemini-api/docs/omni)
- Runway added Gemini Omni Flash generation and editing on 30 Jun 2026. — [Runway changelog](https://runway.com/changelog)

**OpenAI: Sora 2 (discontinued)**
- "The Sora 2 models and Videos API were shut down on September 24, 2026 and are no longer available", with no one-to-one replacement. The deprecation notice was dated 24 Mar 2026. — [OpenAI video generation guide](https://developers.openai.com/api/docs/guides/video-generation)
- The Sora web and app versions went offline on **26 Apr 2026**. Sora continues only as a research project on world models. — [The Decoder](https://the-decoder.com/openai-sets-two-stage-sora-shutdown-with-app-closing-april-2026-and-api-following-in-september/); [Engadget](https://engadget.com/ai/openai-is-shutting-down-its-sora-video-generation-app-211023358.html)
- Historical capabilities, for reference only:
  - `input_reference` acted as the first frame only; there was no last-frame control.
  - "Characters" were limited to non-human subjects, and uploads with human likeness were blocked by default.
  - **Input images with human faces were rejected.**
  - Content had to be suitable for under-18 audiences.
  - Audio was always generated, with no toggle.

  — [OpenAI video generation guide](https://developers.openai.com/api/docs/guides/video-generation)
- Runway added "Sora 2 Pro" as a third-party model on 20 Feb 2026 ([Runway changelog](https://runway.com/changelog)). It is **absent** from Runway's current API price list ([Runway API pricing](https://docs.dev.runwayml.com/guides/pricing/)), which is consistent with the shutdown.

**Runway (first-party models plus hosted third-party models)**
- **Gen-4.5:** image-to-video with a first-frame image was added on 21 Jan 2026. The changelog contains no Gen-4.5 last-frame or keyframe entry, and secondary sources describe only a single start image. — [Runway changelog](https://runway.com/changelog); [search summary incl. invideo/krea/openclips](https://invideo.io/blog/runway-gen-4-5-complete-guide/)
- **Aleph 2.0** launched 21 May 2026 in Edit Studio. It is an in-context video editing and restyle model: you edit one frame and the rest of the video updates to match. It reached Runway MCP on 14 Jul 2026. — [Runway changelog](https://runway.com/changelog)
- Aleph 2.0 reportedly accepts first and last frame placement, and **up to 5 frames with timestamp or named positions**. This comes from a third-party API host (Runware), not Runway's own docs. — [Runware Aleph 2.0 docs](https://runware.ai/docs/models/runway-aleph-2-0)
- **Seedance 2.5 on Runway** added first-frame, last-frame and reference-image controls on 11 Aug 2026, and 1080p on 15 Aug 2026. Seedance 2.0 Fast and Mini added keyframe support on 21 Jul 2026. — [Runway changelog](https://runway.com/changelog)
- **Act-Two** (motion transfer from a performance video) is still on the API price list at 5 credits/s, through `/v1/character_performance`. There are no 2026 changelog entries for Act-Two or an "Act-Three". — [Runway API pricing](https://docs.dev.runwayml.com/guides/pricing/); [Runway API docs nav](https://docs.dev.runwayml.com/api/); [Runway changelog](https://runway.com/changelog)
- Act-Two drives a character image or video with a performance video, transferring facial expression, body gestures and voice. Third-party specs warn of weaker transfer with occlusion or mismatched anatomy. — [Runway Academy](https://academy.runwayml.com/acttwo); [CometAPI spec](https://www.cometapi.com/models/runway/act-two/)
- The only multiple-keyframe entry in Runway's changelog is a Dec 2024 one: middle keyframes in Gen-3 Alpha Turbo. — [Runway changelog](https://runway.com/changelog)

**Luma (Ray3.2 / Ray3.14, Dream Machine app, Luma Agents API)**
- **Ray3.2** was released 9 Jun 2026. Luma's announcement says it supports "the placement of up to 16 keyframes within a single clip" and clips up to 20 s at 1080p. It adds native HDR, 16-bit EXR export, Performance Tracking and Expressive Facial Performance (up to 8 faces), and Enhanced Reframe for outpainting and background replacement. The full control surface is available as an API. — [Luma Ray3.2 announcement](https://lumalabs.ai/news/introducing-ray-3-2)
- The Ray 2-era Dream Machine API documents `frame0`/`frame1` keyframes (image URL or a generation ID) and `"loop": true`. It also documents extend forward/reverse and interpolation between two generations. That page lists only `ray-2` and `ray-flash-2`, and points to the new Luma Agents API docs for current guides. — [Luma API video docs](https://docs.lumalabs.ai/docs/video-generation)
- For Ray3.2, Scenario's integration uses `startFrame`/`endFrame` and `loop: true`. It reports that anchor frames and loop are **not available at 10 s duration** (mutually exclusive with 10 s). This is a third-party source. — [Scenario Ray 3.2 essentials](https://help.scenario.com/articles/1727809780-luma-ray-3-2-the-essentials)
- Ray3.2 is exposed through a separate **Luma Agents API** with its own keys, billing and request format. — [apiframe guide](https://apiframe.ai/guides/luma-api-guide)
- **Ray3 Modify** (18 Dec 2025) is a video-to-video model for acting-performance workflows. Secondary sources say it locks character likeness using a reference image. — [BusinessWire](https://www.businesswire.com/news/home/20251218399664/en/Luma-AI-Announces-Ray3-Modify-a-New-Model-for-Hybrid-AI-Workflows-for-Acting-Performances-Now-Available-in-Dream-Machine); [magichour review](https://magichour.ai/blog/luma-dream-machine-review)
- Luma's pricing page lists Ray3.2 Video-to-Video and Reframe pricing. It does **not** list keyframes, loop or "modify" as features of Ray3.x or of any plan. — [Luma pricing](https://lumalabs.ai/pricing)
- Camera control is done through prompt language and `concepts` (e.g. `dolly_zoom`). There is no documented "camera lock" parameter. — [Luma API video docs](https://docs.lumalabs.ai/docs/video-generation)

**Midjourney video**
- `--loop` makes the ending match the starting frame, and `--end <image URL>` sets a custom end frame (released mid-2025). — [Midjourney docs](https://docs.midjourney.com/docs/video); [Midjourney update](https://updates.midjourney.com/looping-and-end-frame-for-video-video-in-the-discord-bot/)
- Niji (the anime-focused Midjourney/Spellbrush model) has an "end frame" feature blog post. Its details were not fetched. — [nijijourney blog](https://nijijourney.com/blog/niji-end-frame)
- No 2026 "Video V2" release was found. — [search, 2026-10-22](https://docs.midjourney.com/docs/video)

**Pika**
- The only verifiable 2026 item found is a Sep 2026 plan change: the commercial license was removed from the Free and Starter plans, and priority queue and early model access became perks of the "Fancy" plan. This comes from a third-party tracker. — [PricingSaaS Pika diff 2026W39](https://pricingsaas.com/companies/pika/diffs/2026W39)
- Claims of "Pika 2.5" or a "2026 storyboard" came from one low-quality review site and could not be confirmed. — [digen.ai review](https://resource.digen.ai/pika-ai-video-generator-review-2026-2/)

### Inferences
- **Chained clips with exact start and end poses.** The best-documented first-party options are:
  - **Veo 3.1 first+last frame on Vertex.** GA, 9:16, 1080p, 24 fps, 4/6/8 s.
  - **Gemini Omni Flash first/last frame.** Through the Gemini API, Flow or Runway.
  - **Luma Ray3.2 keyframes (up to 16).** The only option offering intermediate keyframes, but reportedly not at 10 s.
  - **Runway-hosted Seedance 2.5.** First, last and reference frames.

  Midjourney `--end`/`--loop` is a cheap fallback for loops, but its resolution is likely too low (see Q2 gaps).
- **Audio and mouth movement.** Veo through Runway's no-audio SKU (20 credits/s) is the cleanest way to avoid generated speech. With Omni, audio cannot be disabled, so you must prompt "no dialogue, mouth closed" and strip the audio in post. Silencing audio does not stop lip motion, so mouth control remains prompt-dependent on every model.
- **Seamless loops.** Two routes:
  - Same-image first+last frame: Veo, Omni and Seedance. Unverified for Omni.
  - Luma or Midjourney loop flag.

  Expect a slight "settle" around the shared frame; even with exact endpoints, a few-frame crossfade may be needed.
- **Identity consistency.** Reference images (Veo 3.1 refs, Omni refs, Seedance refs) combined with a first frame are the main tool. Veo's reference-image mode is limited to 8 s and may not combine with first+last frame (unconfirmed).
- **Motion transfer.** Runway Act-Two at 5 credits/s ($0.05/s) is the cheapest performance-video route, and Luma Ray3 Modify is the alternative. Neither has documented anime-specific quality.

### Gaps
- No primary-source confirmation of a Veo 3.1 `negativePrompt` or `generateAudio` parameter on the current Vertex page. In 2025 Vertex did have `negativePrompt` and `generateAudio` (from memory), so this should be verified.
- I could not confirm whether Omni first+last frame can be combined with reference images in one request. Runway and Runware claim it can.
- Ray3.2 API parameter names and whether keyframes coexist with character references were not verified on docs.agents.lumalabs.ai, which did not surface in search.
- No vendor documents a "camera lock" parameter. Static camera relies on the prompt ("locked-off tripod shot, static camera") everywhere.
- Gen-4.5 last-frame or keyframe support: none found in Runway's own docs.
- Pika's current model lineup and features (Pikaframes, keyframes) in 2026 are unverified.

---

## Q2. Output specs: resolution, fps, duration, 9:16, input limits

### Takeaway
Four options meet 9:16 at 1080p, each with caveats:
- **Veo 3.1 GA on Vertex:** 9:16, 720p/1080p/4K output, 24 fps, 4/6/8 s, 20 MB image input.
- **Gemini Omni Flash:** 9:16, but 1080p and 4K are *upscaled* from a lower native resolution.
- **Luma Ray3.2:** native 1080p, clips up to 20 s, HDR/EXR.
- **Runway Gen-4.5:** reportedly 720×1280 vertical only for image-to-video (unverified).

### Cited Findings
- **Veo 3.1 (Vertex):**
  - Aspect ratios 9:16 and 16:9.
  - Output 720p and 1080p, plus 4K on Generate only. Input resolution 720p/1080p.
  - **24 FPS**, 4, 6 or 8 s, up to 4 outputs per prompt, MP4 output.
  - Image input up to 20 MB. Region us-central1. Quota 50 requests/min.
  - C2PA content credentials.
  - Pay-as-you-go and batch are listed as "not supported"; Provisioned Throughput and fixed quota are supported. This is odd and should be verified.

  — [Vertex Veo 3.1 page](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/veo/3-1-generate)
- **Gemini Omni Flash:**
  - `aspect_ratio` is "9:16" or "16:9" (default 16:9).
  - `resolution` is 360p, 720p (default), **1080p (upscaled)** or **4k (upscaled)**.
  - fps is not specified.
  - Uploaded videos must be ≤10 s. Extension adds 10 s per step up to 40 s.

  — [Gemini API Omni docs](https://ai.google.dev/gemini-api/docs/omni)
- **Omni on Runway:** 3–10 s clips. — [Runway Omni page via search](https://runway.com/product/models/gemini-omni)
- **Luma Ray3.2:** 1080p, up to 20 s, native HDR and 16-bit EXR. — [Luma Ray3.2 announcement](https://lumalabs.ai/news/introducing-ray-3-2)
- **Luma pricing tiers:** Draft, 540p, 720p and 1080p; there is no 4K for Ray3.x. — [Luma pricing](https://lumalabs.ai/pricing)
- **Luma 9:16:** confirmed by two third-party reviews. — [magichour](https://magichour.ai/blog/luma-dream-machine-review); [aitoolradar](https://aitoolradar.io/guides/luma-dream-machine)
- **Luma legacy API:** resolution "540p, 720p, 1080, 4k". — [Luma API video docs](https://docs.lumalabs.ai/docs/video-generation)
- **Runway Gen-4.5:** one guide says image-to-video supports 9:16 natively at **720×1280**, and that text-to-video is locked to 16:9. Krea and OpenClips list 9:16 more generally. — [invideo guide](https://invideo.io/blog/runway-gen-4-5-complete-guide/); [Krea](https://www.krea.ai/models/runway); [OpenClips](https://openclips.ai/models/runway-gen-4-5/)
- **Runway post-processing tools (API):** `/v1/video_upscale`, `/v1/video_to_hdr` and "Enhance Frame Rate". Enhance Frame Rate reached Max+ plans on 17 Sep 2026. — [Runway API docs nav](https://docs.dev.runwayml.com/api/); [Runway changelog](https://runway.com/changelog)
- **Sora (historical):** 1080×1920 portrait on sora-2-pro, 16 or 20 s. Now discontinued. — [OpenAI guide](https://developers.openai.com/api/docs/guides/video-generation)

### Inferences
- **Native 24 fps is documented only for Veo.** That matches the project's 24 fps target. For other models, plan on frame-rate conversion; ffmpeg or Runway's "Enhance Frame Rate" can do it.
- **Omni's "1080p" is upscaled**, so fine anime linework may soften compared with native 1080p from Veo Generate or Ray3.2.
- **Runway Gen-4.5 at 720×1280 is below the ≥1080p requirement.** It would need upscaling (Runway video upscale or Topaz on Pro).

### Gaps
- No fps figures for Omni, Ray3.2, Gen-4.5 or Midjourney.
- Midjourney video resolution and duration in 2026 were not verified. From 2025 memory: 480p SD / 720p HD, 5 s base, extendable to about 21 s, which is likely too low-res.
- Exact Omni base durations for image-to-video were not stated on the docs page.

---

## Q3. Anime/2D style quality, identity drift, hands, and moderation risk for an adult office-lady character (pantyhose/skirt)

### Takeaway
I found **no primary or benchmark source that specifically measures anime/2D fidelity** for these models in 2026. General arenas rank Seedance 2.0 and Gemini Omni Flash at the top, with Veo 3.1 a tier lower. Moderation risk is real on Google: forum reports describe false positives on original stylized characters. Sora's (now moot) policy rejected any face image. Runway exposes a moderation object but warns that repeated flags can suspend an account.

### Cited Findings
- **Artificial Analysis image-to-video arena (cached snapshots, dates uncertain):**
  - *With audio:* Seedance 2.0 ~1191–1192 and HappyHorse-1.0 ~1170; one later snapshot (data through Aug 2026) has MiniMax H3 at 1184 and Gemini Omni Flash at 1182; Veo 3.1 and grok-imagine-video ~1090.
  - *Without audio:* Gemini Omni Flash reported as leader at Elo 1365 in one snapshot; HappyHorse-1.0 at 1400 in another.

  The exact order varies between snapshots. — [Artificial Analysis I2V leaderboard](https://artificialanalysis.ai/video/leaderboard/image-to-video); [benchmarklist snapshot](https://benchmarklist.com/arenas/artificial_analysis_image_to_video/)
- **Veo false positives:**
  - Google developer-forum users report false positives from the celebrity-likeness filter on original, non-celebrity stylized avatars. — [Google AI dev forum "Request for Allowlist"](https://discuss.ai.google.dev/t/request-for-allowlist/137263)
  - A Veo 3.1 image-to-video anchor image was blocked as a child-safety false positive, even though it was generated by Google's own image model. — [Google AI dev forum thread](https://discuss.ai.google.dev/t/veo-3-1-image-to-video-blocks-wholesome-commercial-storyboard-child-safety-false-positive/131917)
- **Gemini Omni regional rules:** uploading or editing images containing **minors** is not supported in the EEA, Switzerland and the UK, and nor is extending uploaded videos. "Certain recognizable people" are blocked, and safety filters vary by region. — [Gemini API Omni docs](https://ai.google.dev/gemini-api/docs/omni)
- **Runway moderation:** both image and text inputs are moderated automatically. A `contentModeration` object can only relax the public-figure threshold. Repeated moderated requests can lead to account suspension. — [Runway API moderation docs](https://docs.dev.runwayml.com/api-details/moderation/)
- **Anime-specific false positives** are reported for other vendors: D-ID flagged fictional anime avatars, and OpenAI image fine-tuning misflagged cartoons at about 0.5% false positives. Both are third-party user reports. — [D-ID forum](https://docs.d-id.com/discuss/660984e2ee6027002b524c8c); [OpenAI community](https://community.openai.com/t/image-fine-tuning-false-positive-content-policy-violation/965280)
- **Sora (historical):** rejected input images with human faces and required under-18-suitable content. — [OpenAI guide](https://developers.openai.com/api/docs/guides/video-generation)

### Inferences
- **Youthful-proportion risk.** Anime characters often have youthful proportions, and the main risk is a *minor-detection* false positive, especially on Google, where child-safety blocks have hit benign images. Mitigations:
  - Draw clearly adult proportions.
  - Put explicit adult cues in the prompt: "adult woman, 28-year-old office worker".
  - Use neutral wardrobe wording, e.g. "business suit with pencil skirt and sheer tights" instead of "pantyhose".

  These mitigations are inference, not vendor guidance.
- **Account risk on Runway.** Running dozens of borderline prompts could put an account at risk under Runway's suspension policy. Test with a few prompts first.
- **Arena scores may not reflect anime quality.** Arena scores are dominated by photoreal clips, so a dedicated anime test (identity, hands, line stability on flat green) is required before committing.

### Gaps
- No 2026 anime/2D-specific benchmark or review was found for Veo 3.1, Omni, Gen-4.5, Ray3.2 or Pika.
- No data on hand quality or identity drift for these models in anime style.
- No Luma moderation documentation was found.
- No vendor statement on skirts or hosiery triggering filters. Treat this risk as unquantified.

---

## Q4. Pricing (subscriptions, credits per second, API) and availability from Ukraine/EU

### Takeaway
Cheapest per-second API paths at ≥1080p, through Runway's API at $0.01 per credit:

| Path | Price |
|---|---|
| Gemini Omni Flash 1.1 (1080p, upscaled) | 15 cr/s = $0.15/s |
| Veo 3.1 without audio | 20 cr/s = $0.20/s |
| Veo 3.1 Fast without audio | 10 cr/s = $0.10/s, resolution unspecified |

On Google directly, Veo 3.1 Fast 1080p was $0.12/s and Standard $0.40/s, but the preview SKUs ended on 22 Oct 2026. Luma Ray3.2 1080p costs about **$0.24/s on the Plus plan** (400 credits per 5 s, at $30 per 10,000 credits). Sora has no price because it no longer exists.

### Cited Findings
- **Gemini API Veo 3.1 (paid tier only, "video with audio" price):** Standard $0.40/s at 720p and 1080p, $0.60/s at 4K. Fast $0.10, $0.12 and $0.30. Lite $0.05 and $0.08. You are charged only when a video is successfully generated. **These models were shut down on 22 Oct 2026.** — [Gemini API pricing, updated 2026-10-19](https://ai.google.dev/gemini-api/docs/pricing)
- **Gemini Omni Flash API:**
  - About $0.10/s at 720p, billed as output tokens at about $17.50 per 1M. No free tier, and the model is still in preview.
  - Flow credits: AI Plus $4.99 → 200, AI Pro $19.99 → 1,000, AI Ultra $99.99 → 10,000 or $199.99 → 25,000.
  - Omni 720p costs 7, 10, 12 or 15 credits for 4, 6, 8 or 10 s. An edit is a flat 40 credits.
  - One source lists Ultra at $249.99 instead (probably outdated).

  All from third-party sources. — [eesel Omni pricing](https://www.eesel.ai/blog/gemini-omni-1-1-flash-pricing); [saascrmreview Flow pricing](https://saascrmreview.com/google-flow-pricing/); [mindstudio Flow credits](https://www.mindstudio.ai/blog/google-flow-pricing-credits-tiers-explained)
- **Runway API** ($0.01 per credit), credits per second:

  | Model | Credits/s |
  |---|---|
  | gen4.5 | 12 |
  | gen4_turbo | 5 |
  | act_two | 5 |
  | aleph2 | 28 (min 56) |
  | veo3.1 | 40 with audio / 20 without |
  | veo3.1_fast | 15 / 10 |
  | gemini_omni_flash_1.1 | 3.4 (360p) / 10 (720p) / 15 (1080p) / 30 (4K), +1 per reference image, +1 per second of input video |
  | seedance2_5 | 20 / 30 / 68 (480p/720p/1080p), +10/15/34 per second of input video; reference images free; 80-credit minimum |
  | seedance2 | 36 / 40 (1080p) / 150 (4K) |
  | kling3.0_pro | 12 without audio / 17 with |
  | hailuo3 | 10 (768p) / 15 (2K), +2 per keyframe or reference |

  Professional and HDR output surcharges add 5–40 credits/s on Gen-4.5 and Aleph 2. — [Runway API pricing](https://docs.dev.runwayml.com/guides/pricing/)
- **Runway subscriptions** (monthly / annual per month):

  | Plan | Price | Credits |
  |---|---|---|
  | Free | $0 | 125 one-time |
  | Standard | $15 / $12 | 625/mo; all models incl. Gen-4.5, Kling 3.0 |
  | Pro | $35 / $28 | 2,250/mo; adds Topaz upscale, "Unlimited" tag, Seedance 2.5 |
  | Max | $95 / $76 | 9,500/mo; HDR, ProRes, image sequences |

  Paid plans have no watermarks. — [Runway pricing](https://runway.com/pricing)
- **Runway Team plan** (self-serve, 4 Sep 2026): 6,900 shared credits per seat per month. — [Runway changelog](https://runway.com/changelog)
- **Luma subscriptions:**

  | Plan | Monthly | Annual | Credits/mo |
  |---|---|---|---|
  | Plus | $30 | $25/mo | 10,000 |
  | Pro | $90 | $75/mo | 40,000 |
  | Ultra | $300 | $250/mo | 150,000 |

  Commercial use is included from Plus. — [Luma pricing](https://lumalabs.ai/pricing)
- **Luma Ray3.2 credit costs, image-to-video (SDR):**

  | Resolution | 5 s | 10 s |
  |---|---|---|
  | Draft | 20 | 60 |
  | 540p | 50 | 150 |
  | 720p | 100 | 300 |
  | 1080p | 400 | 1,200 |

  HDR costs 2× and HDR+EXR 3×. Video-to-video at 1080p costs 144 credits/s. — [Luma pricing](https://lumalabs.ai/pricing)
- **Luma Ray3.14 credit costs:** image-to-video 80 credits/s at 1080p and 20 credits/s at 720p. — [Luma pricing](https://lumalabs.ai/pricing)
- **Luma Ray3.2 API (third-party snapshot, 19 Sep):** 1080p $1.20 per 5 s and $3.60 per 10 s; 720p $0.30 per 5 s and $0.90 per 10 s. Other sources conflict. — [WaveSpeed Luma pricing](https://wavespeed.ai/blog/cost-and-billing/luma-ai-pricing/); [developersdigest](https://www.developersdigest.tech/models/video-generation/luma)
- **EU/UK restrictions:** in the EEA, Switzerland and the UK, Gemini Omni Flash blocks uploading or editing images of minors and extending uploaded videos. — [Gemini API Omni docs](https://ai.google.dev/gemini-api/docs/omni)
- **Vertex Veo 3.1 region:** us-central1. — [Vertex Veo 3.1 page](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/veo/3-1-generate)
- **Runway regional rollout:** Seedance 2.0 became available on Unlimited and Enterprise plans *outside the US* on 7 Apr 2026, so Runway gates some models by region. — [Runway changelog](https://runway.com/changelog)

### Inferences
- **Per-clip costs** for a 6 s, 1080p, 9:16 clip:

  | Path | Cost per clip | Clips per $100 |
  |---|---|---|
  | Omni via Runway | ~$0.90 | ~110 |
  | Veo 3.1 without audio via Runway | ~$1.20 | ~80 |
  | Luma Ray3.2 on Plus | ~$1.44 | — |

  Luma Ray3.2 is closer to $1.20 for 5 s. Retries for pose fidelity will likely multiply these costs by 3–5×.
- **Luma's 1080p tier is 4× its 720p price.** Generating at 720p and upscaling may be far cheaper. Ray3.14 and Ray3.2 cost the same per second at 1080p (80 credits/s; Ray3.2's 400 credits per 5 s works out the same). The difference is that Ray3.14 bills per second, while Ray3.2 bills in 5 s and 10 s blocks, and Ray3.2's 10 s costs 3× its 5 s.
- **A single Runway subscription** covers Veo 3.1, Omni, Seedance 2.5, Kling 3.0, Act-Two and Aleph 2. This avoids a Google Cloud billing setup, which may be harder from Ukraine.

### Gaps
- **Ukraine availability was not verified** for the Gemini API, Vertex billing, Runway, Luma or Pika. I have no source for the Gemini API "available regions" list as of Oct 2026. Historically (from memory) Ukraine was a supported Gemini API region, but card and billing acceptance is unverified.
- Official Google Omni Flash pricing was not fetched directly; the $0.10/s figure comes from third parties. Official Flow or Google AI plan pricing for Oct 2026 was also not verified.
- Vertex Veo 3.1 GA per-second price was not fetched.
- Pika 2026 prices, and Midjourney plan or video GPU-minute costs, were not researched.

---

## Q5. Alpha/transparent output or built-in background removal

### Takeaway
No generator in scope outputs native alpha. **Runway has the strongest post-tools:**
- **SAM3 Video Segmentation** exports the subject as a **transparent WebM** (28 Jul 2026).
- **BiRefNet v2 background removal** in Runway MCP (15 Oct 2026).
- **ProRes 4444 / PNG-sequence export** on Pro+ plans (10 Aug 2026).

Luma Ray3.2's Enhanced Reframe can *replace* backgrounds while preserving lighting. Generating on #00FF00 and then keying remains the default path.

### Cited Findings
- **Runway, 28 Jul 2026:** SAM3 Video Segmentation exports a subject as transparent WebM, or removes the background by inverting the selection. — [Runway changelog](https://runway.com/changelog)
- **Runway, 15 Oct 2026:** BiRefNet v2 Background Removal in Runway MCP. — [Runway changelog](https://runway.com/changelog)
- **Runway, 10 Aug 2026:** ProRes 4444 and PNG-sequence export on Pro+ plans. — [Runway changelog](https://runway.com/changelog)
- The Runway pricing page lists only "HDR, ProRes, image sequences" for Max, without saying whether ProRes 4444 includes an alpha channel. — [Runway pricing](https://runway.com/pricing)
- **Luma Ray3.2 Enhanced Reframe:** extends the frame and replaces the background while preserving the original lighting. Ray3.2 also offers 16-bit EXR export. — [Luma Ray3.2 announcement](https://lumalabs.ai/news/introducing-ray-3-2)
- **Veo 3.1 and Omni:** output is video/mp4 only, with C2PA credentials on Veo. No alpha was mentioned. — [Vertex Veo 3.1 page](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/veo/3-1-generate); [Gemini API Omni docs](https://ai.google.dev/gemini-api/docs/omni)

### Inferences
- **Fallback to chroma keying.** Video models often add shading, gradients or green spill on "flat #00FF00" backgrounds, and anime hair edges spill badly. Runway's SAM3 transparent-WebM export could be a fallback to chroma keying.
- **ProRes 4444 / PNG export** may let the alpha survive into the desktop app pipeline, but only if alpha is actually carried (unverified).

### Gaps
- I could not confirm whether Runway's ProRes 4444 export carries alpha from SAM3 segmentation.
- No reports on how faithfully any model holds a flat #00FF00 background without gradients or spill.
- Pika's and Midjourney's background tools were not researched.
