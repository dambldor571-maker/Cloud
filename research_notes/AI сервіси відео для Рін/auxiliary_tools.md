# Auxiliary tools for anime-character clip production (motion transfer, matting, native alpha, Live2D-style alternatives) — state as of 2026-10-22

Scope note: research was done on 2026-10-22 under a tool-call budget. Most pricing figures come from third-party resellers and aggregators rather than official pricing pages, and they conflict. Every claim below is dated by its source where possible. Items not researched in this pass (RVM, DomoAI, Hedra, Inochi2D, Spine, VRoid/VRM, Runway Remove Background, Unscreen alternatives, AE Roto Brush export details) are listed under Gaps rather than filled in from memory.

## (A) Motion transfer: can the owner perform a gesture on webcam and transfer it full-body to the anime character with a static camera?

### Takeaway
Yes, mostly. The best fit is **Kling Motion Control (2.6/3.0)**, which the owner already pays for. It takes a reference video plus a character image and transfers the body motion. **Wan2.2-Animate (Move mode)** is the local, free option, but it needs roughly 24 GB of VRAM (8 GB with slow GGUF builds). **Runway Act-Two** is a poor fit for full body: its character-image rules say waist-up at most, so full-body shots fall outside them. I found no independent evidence on how accurately any of these tools transfer fingers. Hands remain the main risk.

### Cited Findings
**Kling Motion Control**
- Kling's motion control takes a reference video and a character image. The character's actions follow the reference video and its appearance follows the image. Recommended reference: a single subject, 3–30 s, no cuts, no camera movement — [Oakgen guide (2026)](https://oakgen.ai/blog/kling-motion-control-guide); [Vercel AI Gateway listing](https://vercel.com/ai-gateway/models/kling-v3.0-motion-control)
- Kling 2.6 vs 3.0: 2.6 gives up to 10 s of output and takes 1 character image. 3.0 gives up to 15 s, takes up to 7 character images in the web UI (1 per API request), adds native lip-sync (CN/EN/JP/KR/ES), and claims "deep visual anchoring" for subject consistency — [Atlas Cloud guide](https://www.atlascloud.ai/blog/guides/kling-ai-motion-control)
- Input tips from the same guide: 2–5 s reference clips work best. The reference person should have similar body proportions and framing to the character. Avoid occlusion (hands crossing the body, overlapping limbs), because it causes limb artifacts. Stabilize the footage. Keep the face frontal to limit face drift. Complex backgrounds can cause failures, and the prompt influences background and lighting. Motion Control needs an image input; it does not work in text-to-video mode — [Atlas Cloud guide](https://www.atlascloud.ai/blog/guides/kling-ai-motion-control)
- API pricing conflicts across resellers, all per second of output:
  - Kling 3.0 Motion Control: $0.13 — [Vercel](https://vercel.com/ai-gateway/models/kling-v3.0-motion-control)
  - Kling 3.0: $0.071 (Standard) / $0.095 (Pro) — [Atlas Cloud](https://www.atlascloud.ai/blog/guides/kling-ai-motion-control)
  - fal list prices: $0.168 for V3 Pro and $0.112 for V2.6 Pro; about 44 credits per second of reference video for V3 Pro — [Oakgen](https://oakgen.ai/blog/kling-motion-control-guide)
  - Kling 2.6: about $0.067 at 720p — [Evolink](https://evolink.ai/kling-v2-6-motion-control)
  - One site says "5 s × 11 credits/s" and that Motion Control pricing "increased by 50%" — [kling3.io](https://kling3.io/motion-control). This is a third-party site and unverified.
- Free tier: about 66 daily credits on kling.ai, according to one review — [max-productive.ai review (2026)](https://max-productive.ai/ai-tools/kling-ai/). The costgoat page is titled "Cost per Video Second (Oct 2026)" — [costgoat](https://costgoat.com/pricing/kling)
- The guide does not cover hand/finger accuracy, anime-style fidelity, keeping a solid green background, or output resolution — [Atlas Cloud guide](https://www.atlascloud.ai/blog/guides/kling-ai-motion-control)

**Runway Act-Two**
- Act-Two maps body posture and gestures from a driving video onto a character, including shoulder and torso orientation and lower-body posture where visible. Body Control is on by default and only works with a character image — [aiwiki](https://aiwiki.ai/wiki/runway_act_two); [Fuser guide](https://fuser.studio/articles/runway-act-two-guide)
- Requirements and limits, all from the [Fuser guide](https://fuser.studio/articles/runway-act-two-guide) (undated; its sample images are dated 2026-09-28):
  - Driving video: 3–30 s, one person, waist-up at most, face visible throughout, one continuous take. Hands should be in frame at the start, ideally palms toward the camera.
  - Character image: a recognisable face, a single subject, **waist-up at most**. "Full-body shots, wide shots and profiles that hide the face fall outside Runway's rules."
  - Output: 24 fps. Aspect ratios include 720:1280 (vertical), plus 1280:720, 960:960, 1104:832, 832:1104 and 1584:672.
  - No text prompt and one character per run. High Expression Intensity can introduce artifacts.
- Cost: 5 credits per second, with a 3 s minimum (15 credits) — [Fuser guide](https://fuser.studio/articles/runway-act-two-guide); [aimlapi](https://aimlapi.com/models/runway-act-two)
- Dollar price conflicts: about $0.05/s — [ReelPulse](https://reelpulse.net/guides/runway-ai-pricing-api-for-short-drama); about $0.065/s — [aimlapi](https://aimlapi.com/models/runway-act-two)
- Plan access is unclear: one comparison says a "Professional tier" is required — [Atlabs](https://www.atlabs.ai/blog/runway-act-two-vs-luma-modify-video). A review lists it among paid-plan features — [beststacked](https://beststacked.com/reviews/runway)
- One secondary blog claims "finger-level tracking" and says clear palm views avoid blurring. It is unverified and not Runway's documentation — [Oreate AI](https://discover.oreateai.com/discover/why-runway-acttwo-is-the-real-breakthrough-for-ai-motion-capture-in-2025)

**Wan2.2-Animate (open weights, local or ComfyUI)**
- Two modes. **Move** animates the character image with motion from a driving video. **Mix** replaces a character in existing footage. ComfyUI supports it natively — [ComfyUI docs](https://docs.comfy.org/tutorials/video/wan/wan2-2-animate); [ComfyUI blog](https://blog.comfy.org/p/wan22-animate-and-qwen-image-edit-2509); [comfy.org workflow](https://www.comfy.org/workflows/template_purz_wan22_animate_auto_character_replace/)
- Hardware:
  - 24 GB of VRAM is commonly recommended — [Hivenet](https://www.hivenet.com/post/wan-2-2-cloud-gpu-comfyui)
  - GGUF-quantised builds bring it down to about 8 GB, but run slower — [wink.ai](https://wink.ai/blog/wan-2-2-animate)
  - Keep resolution around 720p and under 150 frames to avoid instability. Width and height must be multiples of 16. On an RTX 4090, about 240 frames was one user's maximum — [comfy.org workflow](https://comfy.org/workflows/template_purz_wan22_animate_auto_character_replace-f49b24114ea9/); [Next Diffusion](https://www.nextdiffusion.ai/tutorials/how-to-use-wan-2-2-animate-in-comfyui-for-character-animations)
- None of these sources report on hand quality — (search 2026-10-22, no results)

**Viggle**
- "Mix" transfers motion from an uploaded reference video onto the character in your image. Other features: Animate, Move, Real-Time Swap. There are 8,000+ motion templates. Weak point: background artifacts in complex interactions — [uravation guide (2026)](https://uravation.com/media/viggle-ai-complete-guide-2026/); [tooliverse review (2026)](https://tooliverse.ai/tools/viggle)
- Pricing (third-party, unverified): freemium at $0–63.99/month, API about $0.01/s — [tooliverse](https://tooliverse.ai/tools/viggle). The official API terms need direct confirmation — [uravation](https://uravation.com/media/viggle-ai-complete-guide-2026/)
- Not positioned as an anime specialist. A CyberLink article calls DomoAI the "Cost Performance King" for 2D and stylized content and says it respects the original art style — [CyberLink (2026)](https://www.cyberlink.com/blog/cool-video-effects/5093/viggle-ai-alternative). This is a competitor-adjacent blog, so treat it with caution.

### Inferences
- For this project (full body, static camera, vertical 1080×1920), **Kling Motion Control** is the most natural add-on to the existing Kling workflow:
  - The owner records himself full-body against a plain wall, with a static phone or webcam on a tripod and 2–5 s takes, and feeds that clip plus the keyframe pose image on #00FF00.
  - Whether the solid green background survives is not documented. The prompt should restate "flat solid #00FF00 background", and this needs testing.
- **Act-Two is mismatched with the project.** It is built for waist-up acting and facial performance. It could still be useful for close-up talking or expression clips, if any exist.
- **Wan-Animate is the only no-per-clip-cost route**, but it is realistic only if the owner's GPU has 16–24 GB or more (GPU unknown). Otherwise a rented cloud GPU (RunPod-style) is needed.
- **Hand accuracy:**
  - The owner should perform gestures with hands visible, not crossing the body, and slower than the final timing. The anime timing step (holds and variable frame timing) can then restore snap.
  - Slower source motion also reduces the motion blur that causes the yellow-hands despill issue (see B).
  - Webcam footage (low fps, motion blur) is a weaker driver than a phone shooting at 30–60 fps. This is general video practice, not sourced.

### Gaps
- No independent tests of finger or hand accuracy for any of these tools, and none specific to anime full-body characters.
- No official kling.ai or runwayml.com pricing page was fetched. All dollar figures are reseller numbers and conflict.
- DomoAI, Hedra and other character animators (e.g., Higgsfield, Pika) were not researched in this pass. Hedra is, from prior knowledge, mostly talking-head and lip-sync oriented (unverified).
- Whether Kling Motion Control keeps a uniform #00FF00 background is unknown.

## (B) Video background removal and matting with alpha: which tools handle hair, motion blur and semi-transparency best, and how do they compare with chroma key on green?

### Takeaway
For flat-colour anime on a generated #00FF00 background, a well-tuned chroma key remains the baseline. The AI matting candidate with the strongest claims on hair, motion blur and semi-transparency is **MatAnyone 2** (CVPR 2026, open source, ComfyUI nodes). The usual pipeline is a SAM 3/3.1 mask, then MatAnyone 2 for a soft alpha. **BEN v2** (MIT) outputs video with alpha directly. **BiRefNet** is image-only and runs per frame. None of these has been evaluated on anime content.

The yellow-hands problem is a despill colour problem, not a matte problem. The likely fixes are:
- restoring luminance after despill;
- extending edge colour;
- applying a separate despill or an AI matte only on blurred hand regions.

### Cited Findings
**MatAnyone 2**
- CVPR 2026 paper (NTU S-Lab and SenseTime). It uses a learned Matting Quality Evaluator to push past "segmentation-like" hard edges. The new real-world dataset VMReal includes "large-motion hair dynamics" — [CVPR 2026 paper](https://openaccess.thecvf.com/content/CVPR2026/papers/Yang_MatAnyone_2_Scaling_Video_Matting_via_a_Learned_Quality_Evaluator_CVPR_2026_paper.pdf); [alphaXiv 2512.11782](https://www.alphaxiv.org/abs/2512.11782)
- Third-party write-ups say it recovers fine hair, produces smooth semi-transparency and handles motion-blurred content. These claims rest mostly on the authors' own qualitative comparisons — [gaga.art](https://gaga.art/blog/matanyone-2/); [aifilms](https://studio.aifilms.ai/blog/matanyone-2-video-matting). A "real-time" claim is commentary, not measured — [Glen Rhodes](https://glenrhodes.com/matanyone-2-eliminates-the-green-screen-with-real-time-ai-video-background-removal/)
- Availability: code and a Gradio demo on GitHub; community ComfyUI node — [spiritform/comfy-matanyone2](https://github.com/spiritform/comfy-matanyone2); hosted online — [Beeble](https://beeble.ai/models/matanyone)
- MatAnyone v1 claimed better boundary alpha than MaGGIe (self-reported) — [MatAnyone paper](https://arxiv.org/pdf/2501.14677)

**SAM 3 / 3.1**
- SAM 3 does text-prompted detection and tracking in video. Its tracker inherits SAM 2's memory bank. Its masks are binary and need a matting step for soft edges. A 2026 article suggests SAM 3 masks as the first-frame input to MatAnyone 2 — [aifilms SAM 3](https://studio.aifilms.ai/blog/meta-sam3-text-segmentation-tracking)
- SAM 3.1 was released 2026-03-27. SAM 3 has 848M parameters. It uses Meta's SAM License with gated checkpoints. SAM 3.1 adds "Object Multiplex" for joint multi-object tracking — [invideo comparison (2026)](https://invideo.io/blog/ai-background-removal-models/)

**Other models**

All rows below come from the [invideo comparison (2026)](https://invideo.io/blog/ai-background-removal-models/).

| Model | License | Video and alpha | Edge quality and speed |
|---|---|---|---|
| **BEN v2** | MIT, open weights, 94.6M params | Video with alpha output, exported as MP4 or WebM with alpha; up to 4K | Rated "excellent". Confidence-guided matting reprocesses low-confidence pixels such as hair and fur |
| **BiRefNet** | MIT | Image-focused, no native video | About 17 FPS at 1024² on an RTX 4090; 2048² high-res variant; general, portrait and matting variants |
| **Bria RMBG-2.0 / Video BG Removal v3** | Weights CC-BY-NC; commercial use via a Bria agreement | Video, including a realtime variant | Rated "strong" (BiRefNet-based) |
| **Pixelcut** | Proprietary API | Frame-by-frame video with transparent-background output | Free web tier |

- Also relevant: VideoMaMa, mask-guided video matting with a generative prior, 2026 — [arXiv 2601.14255](https://arxiv.org/pdf/2601.14255); "Segment and Matte Anything in a Unified Model", 2026 — [arXiv 2601.12147](https://arxiv.org/html/2601.12147v1). Not evaluated here.
- None of the search results evaluated anime or cel-shaded content — (search 2026-10-22)

**DaVinci Resolve and After Effects**
- Magic Mask 2 in DaVinci Resolve 20 requires the paid Studio version — [Larry Jordan](https://larryjordan.com/articles/separate-foreground-from-background-using-magic-mask-2-in-davinci-resolve-20/)
- Resolve 20.2.3 made Magic Mask up to 4x faster on Windows Intel GPUs. It lists only VP8 decode for WebM/MKV, so VP9-alpha export was not confirmed — [Neowin changelog](https://www.neowin.net/amp/davinci-resolve-2023/)
- Tip: render the matte out to avoid retracking — [creativevideotips](https://creativevideotips.com/tutorials/never-retrack-magic-mask)
- Resolve can't add a second mask to the same node, so it needs parallel nodes, unlike After Effects rotoscoping — [Storyblocks](https://www.storyblocks.com/resources/blog/how-to-rotoscope-in-davinci-resolve)

**Fixing despill discoloration (the yellow motion-blurred hands)**
- Contaminated edges are "a color problem, not alpha matte issue". Suggested fixes: grade the edges using the inverted alpha as a mask, or extend the solid core colours outward into the edge before premultiplying — [Blackmagic forum](https://forum.blackmagicdesign.com/viewtopic.php?p=1141022)
- Despill removes green, which darkens the area. Fixes: add luminance back (a "Plus" merge in Nuke), or use a custom-colour despill that adds a sampled target colour back — [Lynda/LinkedIn Nuke course](https://www.lynda.com/Nuke-tutorials/Adjusting-spill-luminance-color/450278/547253-4.html); [creativevideotips despill masterclass](https://creativevideotips.com/tutorials/advanced-green-screen-despill-masterclass). The spillSoup gizmo "re-introduces neutralized luminance" — [Nukepedia spillSoup](https://www.nukepedia.com/tools/gizmos/channel/spillsoup-seamless-artist-friendly-spill/)
- Global red/yellow despill compensation can tint skin, because it is not targeted — [Aximmetry forum](https://my.aximmetry.com/post/4998-keyer-questionbalancing-yellow-preservat)
- Stacking multiple IBKColour nodes helps alpha on motion-blurred plates — [arts.ac.uk blog](https://23008828.myblog.arts.ac.uk/?p=728)

**Playback format check**
- Media players often fail to show transparency correctly. OBS is a better place to check alpha in a MOV — [Live2D community](https://community.live2d.com/discussion/comment/4389)

### Inferences
- **Why the hands turn yellow.** Motion-blurred hands are a 50/50 mix of skin and #00FF00. A standard despill clamps G down to about max(R,B). Skin is R-dominant, so the pixel ends up with R high, G at a moderate clamp and B low, which reads as yellow/orange. It also loses luminance.
- **Fixes in order of effort:**
  1. Despill with luminance restore, or a custom-colour despill whose target is the skin tone.
  2. Edge colour extension: unpremultiply, then fill the edge RGB from the solid core, so semi-transparent pixels take the hand's own colour.
  3. A separate garbage-matted despill pass on the hand region only.
  4. An AI matte (MatAnyone 2 or BEN v2) used only for the alpha, with RGB taken from colour-extended core pixels.

  An AI matte alone will not fix the colour, because the blurred pixels still contain green.
- **Changing the generated background could also help.** A background colour farther from skin and hair, such as pure blue #0000FF or magenta, would make blurred skin contaminate a channel skin lacks. This would need testing for hair colour and for whether the outfit contains blue. Unsourced reasoning.
- **AI matting vs chroma key for this project.** AI matting mainly helps on noisy or non-uniform backgrounds. With a clean generated flat green, chroma key will usually give sharper anime line edges. AI mattes risk soft or "segmentation-like" edges and temporal flicker on cel art, and no source tested anime.
- **Output formats for a Windows overlay:** a PNG sequence as the master; WebM VP9 with alpha for Chromium/Electron playback; ProRes 4444 as an editing intermediate only. BEN v2 exports WebM with alpha natively. The MoniV app (see D) imports transparent VP9 WebM.

### Gaps
- RobustVideoMatting (RVM) was not researched in this pass. From prior knowledge it is an older (2021) real-time human matting model, likely weaker than MatAnyone 2 and human-photo oriented (unverified).
- Runway "Remove Background", Unscreen alternatives and After Effects Roto Brush 3 export settings were not researched.
- ProRes 4444 and VP9-alpha export support in Resolve and AE was not confirmed by any fetched source.
- No VRAM figures were found for MatAnyone 2.
- No benchmark on anime, cel-shaded or green-screen-generated footage exists in the sources found.

## (C) Native transparent (alpha) video generation in 2026: what exists and how mature is it?

### Takeaway
Native RGBA video generation exists, but only as research or open-weights models, not mature commercial features. The leader is **Wan-Alpha** (WeChatCV, CVPR 2026 Highlight, MIT). It is text-to-video only and low resolution: 832×480, 81 frames, inference examples on 8 GPUs. Its image-to-video weights are still unreleased as a to-do item. **Wan-Alpha++** (image-to-video RGBA) appeared on 2026-10-19 with partial checkpoints.

**TransPixar** is the older CogVideoX-5B-based option; its closed version runs in Adobe Firefly. None of these can yet replace the Kling + chroma key pipeline for a consistent character at 1080×1920.

### Cited Findings
- Wan-Alpha timeline — [GitHub WeChatCV/Wan-Alpha](https://github.com/WeChatCV/Wan-Alpha):
  - v1.0 on 2025-09-30, on Wan2.1-14B-T2V
  - v2.0 on 2025-12-16
  - accepted to CVPR 2026 on 2026-02-21
  - training code and datasets released 2026-03-10
  - VAE checkpoints released 2026-03-17
  - Wan-Alpha++ paper and "normal RGBA video" checkpoints released 2026-10-19, in a separate repository
- Wan-Alpha specs and status — [GitHub](https://github.com/WeChatCV/Wan-Alpha):
  - License: MIT.
  - Image-to-Video is still an unchecked to-do item.
  - The official ComfyUI version is "coming soon", though a ComfyUI model is linked on Hugging Face.
  - Inference example: 832×480, 81 frames, run across 8 GPUs with FSDP and Ulysses sharding. VRAM is not stated.
  - Output: RGBA video and PNG frames. The teaser shows semi-transparent objects, glow and fine hair. Anime is not mentioned.
- The arXiv version reports 480×832, 81 frames at 16 FPS, with 4 sampling steps. The method encodes alpha into the RGB latent space via a VAE — [arXiv 2509.24979](https://arxiv.org/html/2509.24979v1)
- Hugging Face: [htdong/Wan-Alpha](https://huggingface.co/htdong/Wan-Alpha). The Wan-Alpha-I2V / Wan-Alpha++ page says normal RGBA checkpoints are released and "Effect RGBA Video" checkpoints are still to-do — [htdong/Wan-Alpha-I2V](https://huggingface.co/htdong/Wan-Alpha-I2V)
- TransPixar extends pretrained video diffusion transformers to RGBA with LoRA fine-tuning while keeping RGB capability — [TransPixar paper](https://wileewang.github.io/TransPixar/paper/paper.pdf)
- The Wan-Alpha paper describes TransPixeler as state of the art at its time. Its open-source version is built on CogVideoX-5B, and a closed version is accessed via Adobe Firefly — [arXiv 2509.24979](https://arxiv.org/html/2509.24979v1); [TransPixeler arXiv 2501.03006](https://arxiv.org/pdf/2501.03006)
- Newer research: "Alpha as an Efficiency Signal: Visibility-Routed RGBA Image-to-Video Generation" (arXiv 2608.xxxxx, i.e., August 2026) — [arXiv 2608.09355](https://arxiv.org/pdf/2608.09355). Details not checked.

### Inferences
- **Maturity is low for this use case.** The gaps are the resolution (480p vs the 1080×1920 target), the missing or partial image-to-video (character identity from a still is essential here), the multi-GPU reference inference, and no evidence on anime characters.
- **Native alpha is worth watching, not adopting, as of October 2026.** The practical "native alpha" today is still generating on a flat key colour and keying, which is what the owner does.
- **Possible near-term test:** Wan-Alpha++ image-to-video, once ComfyUI support and single-GPU recipes appear.
- **Adobe Firefly** may expose the TransPixeler-derived capability commercially. Its current status and resolution were not verified.

### Gaps
- No commercial generator (Kling, Runway, Veo, Sora, Pika, Luma) was confirmed to output alpha video as of October 2026. Not specifically searched beyond the above, so treat this as unknown, not a negative finding.
- Wan-Alpha++ resolution, VRAM and quality are unknown.
- Adobe Firefly's transparent-video feature status in 2026 is unverified.

## (D) Alternatives to video clips: Live2D-style rigs with AI assistance, Inochi2D, Spine, VRoid/VRM

### Takeaway
AI now produces a **layered PSD draft** from one anime image: **See-through**, SIGGRAPH 2026, up to 23 layers with inpainted hidden parts. It is not a rigged model. Rigging in **Live2D Cubism** (whose AI features semi-automate facial movement, deformers, sway physics and lip-sync) still takes substantial manual work.

A rig gives real interactivity (cursor-following gaze, lip-sync, idle physics) with tiny storage. But a full-body office-lady rig with walking, heels and large gestures is far harder than a VTuber bust rig. Pre-rendered transparent WebM clips are simpler to produce with the current pipeline and are already used by at least one Windows desktop-mascot app.

### Cited Findings
**See-through (layer decomposition from a single image)**
- SIGGRAPH 2026 paper and code. It decomposes one anime illustration into up to 23 layers (hair, face, eyes, clothing, accessories…) with inferred stacking order and inpainted occluded regions. Training data was bootstrapped from commercial Live2D models — [arXiv 2602.03749](https://arxiv.org/abs/2602.03749); [GitHub shitagaki-lab/see-through](https://github.com/shitagaki-lab/see-through)
- The README says the full image-to-Live2D pipeline "requires significantly more", because Live2D needs layers designed for specific deformation behaviour — [GitHub](https://github.com/shitagaki-lab/see-through)
- Hands-on review — [lilting.ch hands-on](https://lilting.ch/en/articles/see-through-anime-layer-decomposition):
  - Dated 2026-04-01, updated 2026-07-12. The reviewer calls it an "automatic PSD draft generator".
  - Output: a 23-layer PSD, individual PNGs and a depth PSD.
  - Run on an RTX PRO 6000 (96 GB) on RunPod. Models total about 14 GB. Needs Python 3.12, PyTorch 2.8, CUDA 12.8.
  - Inference took 2 min 5 s, about 6 min total, roughly $0.17 of GPU time plus $3.50/month for storage.
  - Failures seen: a side ponytail merged into back hair; footwear missing from the PSD (though footwear.png was output); black tights looked like missing feet on transparent backgrounds.
  - Where it breaks: complex frills, hands or props over the face, extreme perspective, heavy chibi deformation, semi-transparent or effects-heavy art.
  - Still needed afterwards: manually re-merge, split and rename layers, draw the movable parts, and set up Live2D meshes and motion ranges. The reviewer suggests pairing it with Qwen-Image-Layered for expression variants.
- Another report gives about 74 s per 1024×1024 image on an RTX 4090, plus about 10 s for depth — [search summary of note.com/awesomepapers write-ups](https://note.com/ai_driven/n/nafe907059646?hl=en). Different hardware from the lilting.ch test, so not directly comparable.
- Community tools (StretchyStudio for auto-rigging the PSD output, Anime2.5DRig for a 2.5D avatar) are listed in forks or READMEs. They are unverified, and the lilting.ch review does not mention them — [GitHub forks](https://github.com/AhmadNassar918/see-through)
- A Japanese blogger tested whether AI can "see through" one illustration to make a Live2D model — [note.com/yuuri_nerd](https://note.com/yuuri_nerd/n/n385592ecdf4e?hl=en). Not read in full.

**Live2D Cubism**
- Cubism 5.0 (2023-09) added an AI function that semi-automatically generates facial movements, plus MotionSync for lip-sync — [CGWorld](https://cgworld.jp/flashnews/202309-live2d-5.html); [Live2D 5.0 update](https://www.live2d.com/en/cubism/update/update_5_0_00/)
- Cubism 5.1 (2024-07) added AI auto-generation of deformers and sway motion — [Automaton](https://automaton-media.com/articles/newsjp/20240730-303793/); [Live2D 5.1 docs](https://docs.live2d.com/en/cubism-editor-manual/new-function5-1/)
- The current editor line is 5.3, with 5.3.03 released 2026-06-16. No 5.3-specific AI feature was found — (search summary of live2d.com, 2026-10-22)
- Pricing — [koubo.jp](https://koubo.jp/article/99033); [bestcalendar.jp](https://bestcalendar.jp/press/141596):
  - PRO is sold as annual and 3-year plans, for indie and business use.
  - Summer sale 2026: 20% off, 2026-07-17 to 2026-07-27.
  - A 2024 article put individual PRO from ¥2,080 (likely outdated) — [Automaton](https://automaton-media.com/articles/newsjp/20240730-303793/)
  - The current exact price was not confirmed.

**Desktop-mascot precedent for the video route**
- MoniV (Steam, not yet on sale) is a Windows desktop-mascot app that plays transparent WebM videos of Live2D characters. It imports transparent videos exported from nizima ACTION!! and converts from transparent VP9 WebM in-app — [Steam MoniV](https://store.steampowered.com/app/5222830/)
- A mascot-generation vendor recommends WebM plus HEVC MOV for transparent browser playback, HEVC MOV for Apple apps, and stacked MP4 (colour and alpha side by side) for Android — [masko ai](https://mcpservers.org/servers/masko-ai)

### Inferences
**Live2D rig vs pre-rendered clips for this companion app**

Rig pros:
- Gaze and head turn follow the cursor in real time.
- Lip-sync to TTS (MotionSync).
- Infinite non-repeating idle with physics on hair and skirt.
- Tiny assets (a few MB of textures plus a model file).
- Smooth blending between states, with no keyframe-pose chaining.
- Typically light GPU load when rendering a single model. Unsourced: no CPU/memory benchmark was found.

Rig cons:
- From one AI image, See-through gives only a draft PSD. The owner would still clean up layers, paint hidden areas, mesh and rig. For a full-body character with legs, heels and walking, expect days to weeks for a non-expert. My estimate, not sourced.
- Large body gestures (bowing, turning, walking) are where Live2D is weakest, and where video clips shine.
- Cubism PRO costs a subscription (the free tier has limits). Not verified here.

Video clips pros:
- Any motion the generator can do.
- Matches the current pipeline.
- Playback of VP9-alpha WebM is simple in Chromium/Electron. MoniV shows the pattern works.

Video clips cons:
- No real interactivity. Gaze-following would need many directional clips.
- Large storage: tens of MB per minute at 1080×1920 with alpha. Estimate.
- Decode cost for a 1080×1920 VP9-alpha video in an always-on-top window. Not benchmarked.
- Seams between clips.

**Hybrid option (inference).** Use pre-rendered video for big actions and idles. Use a lightweight Live2D or Inochi2D bust rig, or simple 2D layer tricks (separate eye or head layers from See-through driven by cursor position), only for the "attentive idle" state with gaze and lip-sync.

**3D route (VRoid/VRM).** It gives full interactivity and full-body motion via mocap (webcam tools exist). But re-creating an AI-generated 2D character faithfully in VRoid is a manual modelling job, and the look would shift from illustration to toon-shaded 3D. Not researched in this pass.

### Gaps
- **Inochi2D.** Open-source alternative to Live2D (Inochi Creator/Session). Current 2026 status was not researched.
- **Spine 2D** (esotericsoftware.com). Skeletal 2D animation, Essential/Professional licences. 2026 pricing and AI-assist features not researched.
- **VRoid Studio / VRM / Mate-Engine-style desktop pets.** Not researched in this pass.
- No CPU, GPU or memory benchmarks were found comparing Live2D runtime with transparent video playback in an Electron or other overlay on Windows.
- Whether See-through handles full-body characters well is unclear. The test above shows a head-crop issue and missing footwear layers. Hands and legs for full-body rigging are not covered.
- AI image-to-Live2D end-to-end auto-rigging tools as of October 2026 (e.g., StretchyStudio) are unverified.
