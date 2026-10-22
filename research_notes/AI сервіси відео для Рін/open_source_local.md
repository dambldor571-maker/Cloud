# Open-source / locally runnable AI video generation and anime in-betweening (state as of 2026-10-22)

Scope: open-weight video models (Wan, HunyuanVideo, LTX, CogVideoX, Mochi), anime in-betweening tools (ToonCrafter, AnimateDiff+SparseCtrl, Framer, AniDoc/LVCD and newer papers), ComfyUI workflows, quantization, LoRA training, alpha video, hosted APIs. These were judged against the "Rin" desktop-companion use case: an adult anime office lady, full body, static camera, 9:16, green screen or alpha, clips that start and end on exact shared keyframe poses, seamless loops, consistent identity, and no unwanted mouth movement.

Note on sourcing: about 17 searches and fetches were made. Many sources are secondary blogs, such as RunPod guides, community sites and third-party summaries. Where I add facts from my pre-2026 background knowledge that I did not re-verify in this session, they appear only under **Inferences** or **Gaps** and are marked "(background knowledge, unverified)".

---

## 1. Which open models are actually available in Oct 2026 (the Wan, LTX and Hunyuan landscape)

### Takeaway
The newest downloadable Wan is still the **Wan 2.2 family**, plus some later special-purpose releases. Wan 2.5, 2.6, 2.7 and 3.0 are **API-only**. The newest strong open model is **LTX-2, then LTX-2.3 and LTX-2.5**, from Lightricks. HunyuanVideo 1.5 (8.3B) is open, but its license excludes the EU, UK and South Korea.

### Cited Findings
**Wan (Alibaba)**
- Wan 2.1 was released in Feb 2025 under Apache 2.0. Wan 2.2 was released on 28 Jul 2025 under Apache 2.0 and is called "the newest Wan that anyone outside Alibaba can download" (article dated 2026-09-06). — [howaiworks.ai](https://howaiworks.ai/blog/alibaba-wan-open-weights-stopped-at-2-2)
- API-only (no weights): Wan 2.5-Preview (24 Sep 2025), Wan 2.6 (announced 16 Dec 2025), Wan 2.7 (a four-model suite, video announcement 7 Apr 2026) and Wan 3.0 (public beta early Aug 2026, write-up 13 Aug 2026). A Hugging Face search for "Wan2.7" returned an empty array. Wan-AI on HF has 27 repos, all Wan 2.1, Wan 2.2, Wan-Animate-2 or Wan-Dancer-14B. — [howaiworks.ai, 2026-09-06](https://howaiworks.ai/blog/alibaba-wan-open-weights-stopped-at-2-2)
- RunPod's guide (updated 2026-09-13) confirms that Wan 2.5, 2.6 and 2.7 have "no public weights" and are available only via hosted APIs. It lists the published Wan 2.2 variants as TI2V-5B, I2V-A14B, T2V-A14B, S2V-14B and Animate-14B. Wan 2.7 API clips are 720p or 1080p, 2–15 s. — [RunPod, Wan 2.7 guide](https://www.runpod.io/articles/guides/wan-2-7-runpod)
- **Conflict:** a MindStudio page claims Wan 2.5 is Apache 2.0 open source. Several other sources contradict it, and 8frame published a correction retracting the same claim. Treat Wan 2.5+ as closed. — [MindStudio](https://www.mindstudio.ai/blog/what-is-wan-2-5-video-open-source) vs [8frame](https://www.8frame.co/blog/is-wan-3-open-source), [wan27.org](https://wan27.org/blog/wan-2-5-open-source-guide)
- Newer open Wan-family releases: **Wan-Dancer-14B**, a music-to-dance model (Jul 2026, Apache 2.0), and **Wan-Animate-2 (Wan2.2-Animate-2-14B)**, a character-animation model (Aug 2026, Apache 2.0, weights and inference code). — [howaiworks.ai](https://howaiworks.ai/blog/alibaba-wan-open-weights-stopped-at-2-2). **Conflict or uncertainty:** RunPod (Sept 2026) names "Wan2.2-Animate-14B (November 2025)" as the most recent release on HF, and a search for "Wan2.2-Animate-2" found no other confirming source. Wan-Animate-2's existence and capabilities are unverified beyond one blog. — [RunPod](https://www.runpod.io/articles/guides/wan-2-7-runpod)
- Wan 2.2 is a mixture-of-experts model with 27B total parameters and 14B active, plus a 5B dense TI2V model. It is Apache 2.0. Wan 2.5+ are "API-first". — [Fora Soft, 2026-06-01](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/self-hosting-hunyuanvideo-cogvideox-mochi-ltx)

**LTX (Lightricks)**
- LTX-2 was "fully open-sourced on 6 January 2026, including weights, inference code, and training code". It has 14B video plus 5B audio parameters (19B total) and supports native 4K at 50 fps with synchronized audio. — [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/self-hosting-hunyuanvideo-cogvideox-mochi-ltx)
- ComfyUI had day-0 native support for LTX-2 (blog dated 6 Jan 2026). Features include "keyframe-driven generation" and Canny/Depth/Pose video-to-video control templates. NVFP4 and NVFP8 checkpoints are on HF, and NVFP4 is claimed to use 60% less VRAM and run up to 3x faster on NVIDIA-optimized ComfyUI. — [Comfy blog](https://blog.comfy.org/p/ltx-2-open-source-audio-video-ai)
- LTX-2.3 (22B) was released in March 2026. **LTX-2.5** (22B, open weights, gated HF repo) was released on 11 Aug 2026. It offers native 4K HDR, up to 50 fps, native multishot, and Image-to-Video and First/Last-Frame-to-Video ComfyUI templates. — [RunPod LTX-2.5 blog, published 2026-08-12, updated 2026-10-15](https://www.runpod.io/blog/ltx-2-5-the-open-weights-world-model-built-for-speed-and-how-to-run-it-on-runpod); [VentureBeat](https://venturebeat.com/technology/ltx-2-5-can-generate-a-10-second-ai-video-from-an-image-in-just-6-8-seconds-on-nvidia-superchips-and-its-open-weights)

**HunyuanVideo (Tencent)**
- HunyuanVideo 1.5 was released in Nov 2025 with an 8.3B backbone (down from 13B) and supports T2V and I2V. — [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/self-hosting-hunyuanvideo-cogvideox-mochi-ltx)
- It generates at 480p or 720p, with built-in super-resolution to 1080p. — [search summary of sonusahani / immers.cloud](https://sonusahani.com/blogs/hunyuanvideo-1-5)
- The official HF README describes a 480p I2V step-distilled model (8 or 12 steps recommended) that generates "within 75 seconds" on a single RTX 4090. — [HF tencent/HunyuanVideo-1.5 README commit](https://huggingface.co/tencent/HunyuanVideo-1.5/commit/b71eee25cef8fbff6ed1b7b2620996e63f67eb03)

**CogVideoX and Mochi**
- CogVideoX comes in 2B and 5B sizes plus a refreshed 1.5. Its "sweet spot" is 6 s clips at 720×480. 2B is Apache 2.0, while 5B has its own CogVideoX license. — [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/self-hosting-hunyuanvideo-cogvideox-mochi-ltx)
- Mochi 1 (Genmo) is 10B and Apache 2.0. Its HF card is still "mochi-1-preview", and there is no 2026 status update. — [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/self-hosting-hunyuanvideo-cogvideox-mochi-ltx)

### Inferences
- For this project the realistic open candidates are **Wan 2.2 (A14B I2V/FLF2V, Fun-InP, VACE-Fun, Animate)**, the **Wan 2.1 VACE/FLF2V** models that are still widely used, and **LTX-2.x**. CogVideoX and Mochi are effectively legacy: lower resolution, no keyframe-native workflows of note, and little 2026 community activity. HunyuanVideo 1.5 is usable but has less keyframe and control tooling than Wan.
- The Wan 2.2 A14B ecosystem (LoRAs, Kijai's WanVideoWrapper, LightX2V speed LoRAs, GGUF) is by far the most mature for anime character work, despite being from mid-2025. (Background knowledge plus the ComfyUI docs and Civitai workflows cited below.)
- HunyuanVideo license warning: if the owner is in the EU, UK or South Korea (Ukraine is not excluded), the Tencent Hunyuan Community License excludes those territories. See section 7.

### Gaps
- I could not confirm Wan-Animate-2 from a primary source (HF or GitHub). Verify on huggingface.co/Wan-AI before planning around it.
- No primary source was read for HunyuanVideo-Avatar or HunyuanVideo-I2V specifics. From background knowledge (unverified): HunyuanVideo-I2V came out in Mar 2025 and HunyuanVideo-Avatar (audio-driven talking and singing) in May 2025. Avatar is lip-sync oriented, so it is the opposite of the "no mouth movement" need.

---

## 2. First+last frame and multiple keyframes: which models, and how exact is the end-frame match?

### Takeaway
First-last-frame (FLF) is mature in **Wan 2.1 FLF2V, Wan 2.2 14B FLF (native ComfyUI), Wan 2.2 Fun-InP, Wan VACE (any-frame masks), LTX-2/2.3/2.5 (FLF and keyframe guides) and ToonCrafter/Framer (2-frame interpolation)**. Multiple intermediate keyframes work best with **VACE**, using a control video plus mask where any frame index can be pinned, or with **LTX keyframe conditioning** (first, middle, last). No source quantified end-frame exactness. In practice it is "very close but not pixel-identical", so the standard trick is to overwrite the first and last frames with the original keyframe images in post.

### Cited Findings
- The official ComfyUI Wan2.2 14B first-last-frame example loads one image as the start and another as the end. — [ComfyUI docs Wan2.2](https://docs.comfy.org/tutorials/video/wan/wan2_2)
- A Civitai "Wan2.2 First-Last Frame to Video (GGUF) 4 Steps" workflow uses GGUF Q8_0 models in a high-noise/low-noise dual-stage setup with 4-step LightX2V LoRAs from Kijai/WanVideo_comfy. A 5B FLF2V workflow also exists. — [Civitai 1944974](https://civitai.com/models/1944974/wan22-first-last-frame-to-video-gguf-4-steps); [Civitai 1897497](https://civitai.com/models/1897497/wan22-5b-first-last-frame-to-video-flf2v)
- One guide recommends at least an RTX 4090 (24 GB) for the FP8 FLF setup, with a GGUF variant for lower VRAM. — [Stable Diffusion Art / Next Diffusion via search](https://stable-diffusion-art.com/wan-2-2-first-last-frame-video/)
- An official ComfyUI template exists for "Wan2.1 VACE First-Last Frame", alongside a VACE Reference-to-Video template. — [comfy.org workflow](https://comfy.org/workflows/video_wan_vace_flf2v-45c0ce6bcf2e/); [comfy.org ref2v](https://comfy.org/workflows/video_wan_vace_14B_ref2v-83ff3768d42b/)
- The WanVaceToVideo node requires dimensions divisible by 16 and a 4n+1 frame count. Workflows support "custom keyframe sequences". A community extension provides a "Wan First/Middle/Last Frame to Video (Experimental)" node. TrimVideoLatent trims length. — [ComfyUI WanVaceToVideo docs](https://docs.comfy.org/built-in-nodes/conditioning/video-models/wan-vace-to-video); [ComfyUI-Wan-VACE-Prep](https://comfy.icu/extension/stuttlepress__ComfyUI-Wan-VACE-Prep); [Phr00t custom VACE node](https://huggingface.co/Phr00t/WAN2.2-14B-Rapid-AllInOne/blob/main/Custom-Advanced-VACE-Node/README.md)
- A Wan2.2 VACE-Fun model exists. A RunComfy workflow covers it, and fal hosts `wan-22-vace-fun-a14b/pose`. — [RunComfy](https://www.runcomfy.com/comfyui-workflows/wan2-2-vace-fun-in-comfyui-image-animation-workflow); [fal](https://fal.ai/models/fal-ai/wan-22-vace-fun-a14b/pose)
- Alibaba also has an API-side "wan2.2-kf2v-flash" (keyframe-to-video) model. — [Alibaba Cloud Model Studio](https://www.alibabacloud.com/help/en/model-studio/wan2-2-kf2v-flash)
- LTX: keyframe conditioning lets you set frames the clip must pass through. The LTX-2 FLF workflow conditions on two images plus an optional middle frame, and LTX-2.3 FLF workflows exist. — [RunComfy LTX-2 FLF](https://www.runcomfy.com/comfyui-workflows/ltx-2-first-last-frame-in-comfyui-audio-visual-motion-control); [RunComfy LTX-2.3 FLF](https://www.runcomfy.com/comfyui-workflows/ltx-2-3-first-last-frame-in-comfyui-keyframe-to-smooth-video); [Comfy LTX workflows](https://comfy.org/workflows/model/ltx/)
- LTX-2.5 ships an FLF2V ComfyUI template. — [RunPod LTX-2.5](https://www.runpod.io/blog/ltx-2-5-the-open-weights-world-model-built-for-speed-and-how-to-run-it-on-runpod)
- Research on end-frame adherence shows the problem is real: EF-VI (arXiv 2505.21205) is specifically about "Enhancing End-Frame Injection for Video Inbetweening". Frame-wise Conditions-Driven inbetweening (arXiv 2412.11755, CVPR 2025) interpolates matched-line conditions frame by frame and can add pose skeletons. — [EF-VI](https://arxiv.org/pdf/2505.21205); [FCVG 2412.11755](https://arxiv.org/html/2412.11755v1)

### Inferences
- **End-frame exactness:** in Wan FLF2V, Fun-InP and VACE, the end frame is a latent condition that is VAE-encoded and decoded. The last generated frame typically matches pose and composition closely but can show slight colour/brightness shifts, line softening or small drift. (Background knowledge; no quantitative source found.) For chained clips on a green background, **replace frame 0 and frame N with the exact keyframe PNGs** and, if needed, cross-fade 1–2 frames. With anime held-frame timing (on twos or threes), this is invisible.
- Seamless loop: run FLF with first frame = last frame = the same keyframe. Wan FLF is known to sometimes produce "near-static" output when start and end are identical, so add a mid keyframe via VACE, or loop A→B→A as two clips. (Background knowledge, unverified.)
- Multiple intermediate keyframes: in VACE you build a control video where frames at chosen indices hold your keyframe images, with a mask marking the remaining frames as "generate". The same mechanism allows pose maps on the in-between frames. This is the most flexible open approach. LTX-2.x keyframe guides are the second option.
- Wan output length per pass: A14B native is ~81 frames at 16 fps (~5 s), and 5B TI2V is ~121 frames at 24 fps (~5 s). (Background knowledge, unverified.) Wan-Animate's extension step is 77 frames ≈ 4.81 s (implying 16 fps), per [ComfyUI docs](https://docs.comfy.org/tutorials/video/wan/wan2-2-animate). Clips of 3–10 s therefore fit in one or two FLF segments chained through shared keyframes, which suits the project's architecture.

### Gaps
- No measured data (PSNR/SSIM or community tests) on how exactly Wan, LTX or VACE reproduce the last frame.
- I did not verify whether LTX-2.5 supports arbitrary multi-index keyframes beyond first/middle/last in ComfyUI.

---

## 3. Pose and motion control (DWPose/OpenPose, reference video) for exact arm motions

### Takeaway
The best open options for dictating exact motion are **Wan VACE** (pose, depth or other control video plus reference image), **Wan 2.2 Fun Control / VACE-Fun**, **Wan 2.2 Animate "Move" mode** (DWPose body and face extracted from a driving video, applied to a reference character image) and **LTX-2 Pose/Depth/Canny v2v templates**. Pose following is reported as precise. Depth is reported as more stable than pose.

### Cited Findings
- VACE workflows use OpenPose keypoints via DWPreprocessor as the control signal. One guide says "depth control is more stable than pose control". Another reports that output follows the OpenPose preprocessor precisely. Control videos are preprocessed with comfyui_controlnet_aux. Official docs suggest 640×640 for a first run. — [ComfyUI VACE docs](https://docs.comfy.org/tutorials/video/wan/vace); [comfyui.org VACE guide](https://comfyui.org/en/wan2-1-vace-video-transformation-workflow); [Next Diffusion VACE](https://www.nextdiffusion.ai/tutorials/wan-vace-in-comfyui-ai-video-generation-with-full-control)
- Wan2.2-Animate has two modes. **Move** animates a reference image with motion from a driving video (similar to Wan2.2 Fun Control). **Mix** replaces the character in a video with the reference character. The DWPose Estimator converts the driving video into **pose and face control videos**. It "accurately reproduces the movements and facial expressions from the reference video". Dimensions must be multiples of 16. Video Extend adds 77 frames per group. Model files include an FP8 build (`Wan2_2-Animate-14B_fp8_e4m3fn_scaled_KJ`), the bf16 original, and the lightx2v 4-step LoRA. — [ComfyUI docs Wan2.2 Animate](https://docs.comfy.org/tutorials/video/wan/wan2-2-animate)
- Wan2.2-Animate is 14B and Apache 2.0, includes a relighting LoRA, and the Wan team recommends multi-GPU for 720p production throughput. — [aifilms](https://studio.aifilms.ai/blog/wan-2-2-animate); [Hugging Face demo space](https://snaseem2026-wan2-2-animate-improvements.hf.space)
- LTX-2 ships Canny, Depth and Pose video-to-video templates. — [Comfy blog](https://blog.comfy.org/p/ltx-2-open-source-audio-video-ai)
- Pose-skeleton conditioning for keyframe interpolation is also in research: FCVG (2412.11755) and PoseFuse3D-KI (2506.03119, 3D human guidance with normals and depth). — [FCVG](https://arxiv.org/html/2412.11755v1); [PoseFuse3D-KI](https://arxiv.org/pdf/2506.03119)

### Inferences
- **Mouth-movement risk:** Wan-Animate transfers facial expressions from the driving video's face track. If the driving actor is still-mouthed, or the face input is bypassed, mouth motion should be suppressed. With plain I2V or FLF, prompting such as "mouth closed" plus negative prompts "talking, speaking" helps, but nothing guarantees it. A robust fix is to composite a held mouth or face layer in post, which is cheap with chroma-key and anime flat shading. (Inference, unverified.)
- A good pipeline for exact arm motions: record yourself or a 3D mannequin (Blender/Mixamo) doing the gesture, extract DWPose, then feed VACE (pose control plus pinned first and last keyframe frames) or Wan-Animate Move (reference = Rin keyframe). A 3D-rendered pose and depth sequence keeps the camera perfectly static.
- Anime limb proportions (long legs, small head) can confuse DWPose retargeting from a real human. Depth or line-art control from a 3D model of the character may track better. (Inference.)

### Gaps
- No source evaluated Wan-Animate or VACE pose following specifically on anime characters.
- Unverified whether Wan-Animate-2 (Aug 2026) improves face control or offers a "no expression transfer" switch.

---

## 4. VRAM, speed, quantization (GGUF/fp8), and the upscale/interpolation chain

### Takeaway
Wan 2.2 A14B at 720p is comfortable on 24 GB (FP8) and workable on 12–16 GB with GGUF (Q4–Q6) plus block-swap or offload and 4-step LightX2V LoRAs. 8 GB means the Wan 5B, very small resolutions, or cloud. LTX-2/2.5 wants 24 GB+ in practice, with a 16 GB floor only for distilled or quantized builds. HunyuanVideo 1.5 runs at about 14–16 GB in FP8. No open model renders native 1080p 9:16 at 24 fps cheaply, so plan on **720p generation, then upscaling, then (optional) frame interpolation**.

### Cited Findings
- **Wan:** the 5B dense model runs on an 8 GB card at 720p. 14B is in the 24–48 GB tier, and full precision needs 60 GB+. — [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/self-hosting-hunyuanvideo-cogvideox-mochi-ltx). "Quantized 14B variants fit on a 24 GB card." — [RunPod](https://www.runpod.io/articles/guides/wan-2-7-runpod)
- **LTX-2:** Lightricks' ComfyUI extension lists 32 GB+ VRAM and 100 GB+ disk. The 19B dev model is 43.3 GB in BF16, 27.1 GB in FP8 and 20 GB in FP4. 24 GB is the practical floor. — [localaimaster LTX-2 guide](https://localaimaster.com/blog/ltx-2-local-setup-guide). The bf16 checkpoint wants 32 GB+. FP8 is "tight on a 16 GB card once you push past a few seconds", and 24 GB is suggested for FP8 or distilled at 720p. — [RunPod LTX-2 guide](https://www.runpod.io/articles/guides/comfyui-ltx-2-runpod)
- **LTX-2.5:** the distilled model has a 16 GB floor on RTX cards (quantized also 16 GB). 48 GB is recommended for comfortable use, and 80–96 GB for the full bf16 distilled pipeline. The distilled bf16 pack is about 66 GiB on disk. A Comfy-only int8 variant exists. A vendor benchmark shows a 10 s, 24 fps clip in 6.8 s on 2× GB200, and 23.7 s at 1080p via API. — [RunPod LTX-2.5](https://www.runpod.io/blog/ltx-2-5-the-open-weights-world-model-built-for-speed-and-how-to-run-it-on-runpod)
- **LTX-Video (older, 2B/13B):** distilled fits 8–16 GB and 13B fits 24–48 GB. It generates 30 fps at 1216×704. — [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/self-hosting-hunyuanvideo-cogvideox-mochi-ltx)
- **HunyuanVideo 1.5:** about 24–28 GB at full precision, ~14–16 GB in FP8 and ~8–12 GB with offloading. About 75 s per short 480p clip on an RTX 4090. — [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/self-hosting-hunyuanvideo-cogvideox-mochi-ltx); [HF README](https://huggingface.co/tencent/HunyuanVideo-1.5/commit/b71eee25cef8fbff6ed1b7b2620996e63f67eb03). 720p at 14–16 GB is "functional but slow with offloading". — [search summary, thundercompute/packet.ai](https://packet.ai/blog/video-generation-gpu-requirements-ltx-hunyuan-wan)
- **CogVideoX 5B:** ~8 GB with suitable settings. **Mochi:** ~60 GB full precision, ~22 GB in bf16, and under 20 GB with the ComfyUI-optimized build. — [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/self-hosting-hunyuanvideo-cogvideox-mochi-ltx)
- **ToonCrafter:** ~24 GB officially (users report 24–27 GB), which the community has reduced to ~10 GB. The Kijai fp16 ComfyUI build lists 12 GB. — [ToonCrafter GitHub](https://github.com/Doubiiu/ToonCrafter)
- **Wan-Animate:** the ComfyUI docs give no VRAM figure and only advise a small resolution on the first run. — [ComfyUI docs](https://docs.comfy.org/tutorials/video/wan/wan2-2-animate)
- **Anime upscaling on 12 GB:** a 2026 comparison of PID 1.5, SeedVR2 and ESRGAN for anime upscaling ran on an RTX 4070 SUPER (12 GB) in ComfyUI. — [TNSOR_WORKS note.com](https://note.com/tnsor_works/n/nc30ebcc5a08c?hl=en)
- **Cloud rental (RunPod Community Cloud, Sept 2026):** RTX 4090 24 GB from $0.34/h, RTX 5090 32 GB from $0.69/h, L40S 48 GB from $0.79/h, A100 80 GB from $1.19/h, H100 80 GB from $1.99/h. — [RunPod](https://www.runpod.io/articles/guides/wan-2-7-runpod)

### Inferences
- **VRAM tier guidance (synthesis; partly background knowledge):**
  - **8 GB:** Wan 2.2 5B TI2V/FLF (720p), CogVideoX 5B, ToonCrafter (community low-VRAM), and Wan 14B only via GGUF Q3/Q4 with heavy offload at 480p (slow; Wan2GP "GPU-poor" app is an option, background knowledge). Use the cloud for real production.
  - **12 GB:** Wan 2.2 14B GGUF Q4/Q5 plus LightX2V 4-step at 480–720p (several minutes per clip, background knowledge), ToonCrafter, HunyuanVideo 1.5 with offload.
  - **16 GB:** Wan 14B GGUF Q6/Q8 or FP8 with block-swap at 720p, LTX-2.5 distilled or quantized (floor), HunyuanVideo 1.5 FP8.
  - **24 GB (4090/3090):** Wan 14B FP8 at 720p comfortably, VACE, Animate, LTX-2 FP8 at 720p, and Wan LoRA training.
  - **32 GB (5090) or a rented 48–80 GB card:** LTX-2.x at higher resolution or length, and faster iteration.
- **Resolution chain for ≥1080p 9:16:** generate at 720×1280 (Wan native 720p, vertical supported, dimensions divisible by 16), then upscale with an anime-suited model (ESRGAN anime variants, SeedVR2 or PID per the 12 GB comparison above) to 1080×1920. Interpolation (RIFE/GIMM-VFI via ComfyUI-Frame-Interpolation, background knowledge) is mostly **unnecessary** here: Wan A14B's 16 fps is close to anime "on ones/twos" anyway, and the project wants variable timing. Instead, select or hold frames (retime to 24 fps with holds on twos or threes) rather than interpolating to buttery smoothness.

### Gaps
- No measured per-clip generation times for Wan 2.2 14B at 720p on 12, 16 or 24 GB cards were retrieved in this session. Community figures (roughly 2–10 min per 5 s clip with 4-step LoRAs on a 4090, background knowledge) are unverified.
- No direct source on GIMM-VFI or RIFE quality on anime line art was retrieved.

---

## 5. Character LoRA training for video models (Wan LoRA): effort and data

### Takeaway
Wan 2.1/2.2 character LoRAs are well established. They are trained with **musubi-tuner (kohya-ss)** or **AI Toolkit (ostris)**, or as a hosted service on fal. An image-only character LoRA (≈20–50 captioned images of the character) needs about 12 GB minimum. Video LoRAs need about 24 GB, and in practice 24–32 GB with block-swap plus 64 GB system RAM. This is the key tool for keeping Rin's identity consistent across dozens of clips.

### Cited Findings
- Musubi-tuner is "purpose-built for Wan 2.1/2.2, HunyuanVideo, FramePack, with VRAM-saving features (FP8, block-swap)". It requires latent and text-encoder pre-caching. Datasets are images with per-image .txt captions. — [HF forum notes (John6666) on Wan 2.2 LoRA training](https://huggingface.co/datasets/John6666/forum1/blob/e2772d17729a88bbc2d7379c6220c46b85ef5a31/wan22_lora_training.md)
- The guideline is ~20–50 high-quality images with detailed captions (another tool cites 15–30). Default hyperparameters are rank 32, alpha 16, LR ≈ 2e-4 and batch 1–2 on 16–24 GB, with higher rank for detailed identity. — [same HF notes](https://huggingface.co/datasets/John6666/forum1/blob/e2772d17729a88bbc2d7379c6220c46b85ef5a31/wan22_lora_training.md)
- VRAM: an image LoRA needs ~12 GB and a video LoRA has a ~24 GB floor. A forum user says at least 12 GB, preferably 24 GB. A Windows user training a Wan 2.2 I2V LoRA needed `--blocks_to_swap 16` even with 32 GB. Musubi guidance is ~24 GB VRAM plus 64 GB RAM as a comfortable floor for video. — [HF forum thread](https://discuss.huggingface.co/t/wan-lora-traning/167838); [note.com Windows 11 musubi guide (Japanese)](https://note.com/memiha_kabano/n/n4faa25186d61?hl=en)
- AI Toolkit and Musubi Tuner are recommended as the two main tools. — [HF forum](https://discuss.huggingface.co/t/wan-lora-traning/167838)
- A ComfyUI node for "Realtime LoRA Trainer (Wan 2.2 – Musubi Tuner)" exists. — [comfy.icu](https://comfy.icu/node/MusubiWanLoraTrainer)
- Hosted training is available: fal `wan-22-trainer/t2v-a14b` and `wan-22-image-trainer`. — [fal trainer](https://fal.ai/models/fal-ai/wan-22-trainer/t2v-a14b/playground); [fal image trainer](https://fal.ai/models/fal-ai/wan-22-image-trainer/api)
- LTX-2 shipped with training code. — [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/self-hosting-hunyuanvideo-cogvideox-mochi-ltx)
- Wan-Alpha accepts LoRAs via `--lora_path` on top of Wan2.1-T2V-14B, so it is a LoRA-on-base architecture. — [HF htdong/wan-alpha-v2.0](https://huggingface.co/htdong/wan-alpha-v2.0)

### Inferences
- With I2V, FLF or VACE, identity mostly comes from the **input keyframe images**, which the user controls (they can be drawn or generated with an image model and character LoRA, such as Illustrious/NoobAI SDXL anime models). A video LoRA mainly helps the **in-between frames** keep face, outfit and proportions under motion and turns, so it is optional but valuable when chaining dozens of clips. A practical dataset is 30–60 images of Rin (full-body, varied poses, the exact outfit, green background) plus optionally 10–20 short clips of her moving.
- Wan 2.2 A14B has high-noise and low-noise experts. Community practice trains LoRAs for both, or mainly the low-noise one for identity. (Background knowledge, unverified.)
- Rented-GPU cost for one LoRA is likely a few dollars, e.g. a few hours on a $0.34–0.79/h 4090 or L40S. (Inference from RunPod prices.)

### Gaps
- No anime-specific Wan LoRA training guide was retrieved. Effects of anime flat shading on training are unknown.
- Training times (hours per LoRA) were not found in a cited source.

---

## 6. Native alpha / transparent video generation

### Takeaway
**Wan-Alpha** (open, Apache 2.0) generates true RGBA video. It is **text-to-video only** (no I2V or keyframe conditioning yet) at about 832×480 and 81 frames, so it cannot serve the keyframe-chained workflow. For this project, **flat green background plus chroma key** remains the practical route, or matting in post.

### Cited Findings
- Wan-Alpha learns RGB and alpha jointly, with a VAE that encodes alpha into the RGB latent. It is based on Wan2.1-T2V-14B and handles semi-transparency, glow and hair. The paper is arXiv 2509.24979, "Video Generation with Stable Transparency via Shiftable RGB-A Distribution Learner". v1.0 was released 2025-09-30. — [HF Wan-Alpha README](https://huggingface.co/htdong/Wan-Alpha/blob/main/README.md); [ComfyUI Wan-Alpha tutorial](https://docs.comfy.org/tutorials/video/wan/wan-alpha)
- v2.0 was released 2025-12-16. It uses Wan2.1-T2V-14B plus a Lightx2v acceleration LoRA, and is **T2V only, with I2V on the to-do list**. The example is 832×480, 81 frames. The license is Apache-2.0. The official ComfyUI version for v2.0 is "coming soon", while a v1.0 ComfyUI model exists. — [HF htdong/wan-alpha-v2.0](https://huggingface.co/htdong/wan-alpha-v2.0); [HF Wan-Alpha_ComfyUI](https://huggingface.co/htdong/Wan-Alpha_ComfyUI)
- ComfyUI has a `SaveVideoRGBA` node. Wan2GP supports "alpha2" (outputs a zip of RGBA frames). — [RunComfy SaveVideoRGBA](https://www.runcomfy.com/comfyui-nodes/SaveVideoRGBA); [HF Wan2GP alpha2.json](https://huggingface.co/vidfom/ltx2/blob/main/Wan2GP/defaults/alpha2.json)

### Inferences
- Green-screen caveats: Wan and other models can tint skin and hair with green spill, add shadows or floor gradients, and occasionally move the "camera". Prompting "flat solid #00FF00 background, no shadow, static camera", plus a keyframe image that already has the flat green background, helps. Spill suppression in post (FFmpeg/After Effects/DaVinci keyer) is still needed. Anime hard edges key well. Alternatively use a video matting model (BiRefNet/RMBG/MatAnyone-style, background knowledge) on any background. (Inference.)
- Pick a key colour absent from the character. If Rin wears green, use magenta or blue. (Inference.)

### Gaps
- Unverified whether a Wan-Alpha I2V or VACE variant was released between Dec 2025 and Oct 2026. Not found.
- No LTX- or Hunyuan-based alpha model found.

---

## 7. Anime-specific in-betweening tools (ToonCrafter, AnimateDiff+SparseCtrl, Framer, AniDoc, LVCD, newer)

### Takeaway
Anime-specific interpolators are **low-resolution research tools** (e.g. ToonCrafter: 512×320, 16 frames, last code update May 2024). Framer is SVD-based. AniDoc and LVCD are line-art colourization rather than in-betweening. In Oct 2026 they are far below Wan 2.2 FLF/VACE in resolution and stability. They are useful only for short 2-keyframe in-betweens, or as a stylistic experiment. General video models with FLF or VACE, conditioned on hand-picked anime keyframes, are the better in-betweening engine.

### Cited Findings
- **ToonCrafter** (SIGGRAPH Asia 2024, Apache-2.0) generates up to 16 frames at 512×320. It supports sparse sketch guidance and colourization. It takes ~24 s on an A100 at 50 DDIM steps and ~24 GB VRAM (community builds ~10–12 GB). ComfyUI nodes: Kijai's ComfyUI-DynamiCrafterWrapper (pruned fp16) and AIGODLIKE's ComfyUI-ToonCrafter. The authors say "success rate is not guaranteed" and call it "research exploration". The last dated changelog entry is 2024-05-29. — [GitHub Doubiiu/ToonCrafter](https://github.com/Doubiiu/ToonCrafter); [arXiv 2405.17933](https://arxiv.org/pdf/2405.17933)
- **Framer** (ICLR 2025) does interpolation between two images with user-editable keypoint trajectories, plus an "autopilot" mode that matches keypoints via SIFT-like matching. It is fine-tuned from Stable Video Diffusion on OpenVid-1M with last-frame synthesis. Code is at aim-uofa/Framer. No ComfyUI integration was found. — [ICLR 2025 proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/hash/801ec05b0aae9fcd2ef35c168bd538e0-Abstract-Conference.html); [Moonlight review](https://themoonlight.io/review/framer-interactive-frame-interpolation)
- **AniDoc** does line-art animation colourization with a reference character. It reportedly outperforms LVCD, ID-Animator and ToonCrafter on colourization, and unlike LVCD it does not need a colourized first frame. — [ResearchGate AniDoc](https://www.researchgate.net/publication/394617088_AniDoc_Animation_Creation_Made_Easier); [Liner review](https://liner.com/review/anidoc-animation-creation-made-easier)
- **Generative Inbetweening** (arXiv 2408.15239, ICLR 2025) adapts an I2V model to keyframe interpolation. **FCVG** (2412.11755, CVPR 2025) is frame-wise condition-driven inbetweening. **MotionBridge** (2412.13190) is inbetweening with flexible controls. **SketchKeyAnime** (arXiv 2606.19958, ~Jun 2026) is "Reference-anchored Sparse Key-Sketch Animation Synthesis" and reviews AnimeInterp, EISAI and TPS line inbetweening as prior anime work. — [FCVG](https://arxiv.org/html/2412.11755v1); [MotionBridge](https://arxiv.org/html/2412.13190v1); [SketchKeyAnime](https://arxiv.org/pdf/2606.19958); [AceVFI survey](https://arxiv.org/pdf/2506.01061)

### Inferences
- **AnimateDiff + SparseCtrl** (background knowledge, unverified this session) is SD1.5-based. It takes RGB or scribble sparse keyframes at chosen frame indices over 16-frame windows, works at ~512 px, and has strong anime LoRA availability but flicker and identity drift. In 2026 it is a legacy option, superseded by Wan VACE.
- LVCD (SIGGRAPH 2024) and AniDoc (Dec 2024, SVD-based) colourize sketch sequences (background knowledge). They would fit a pipeline where the user draws rough line-art in-betweens, but that is more manual work than this project needs.
- "Sakuga"-named models: I found no verifiable open "Sakuga" in-betweening model. The name mostly refers to anime datasets (e.g. Sakuga-42M, background knowledge). Treat any such claims cautiously.
- SketchKeyAnime (2026) is the most relevant new research but probably has no consumer ComfyUI integration. Code availability is unverified.

### Gaps
- No 2026 ComfyUI-integrated anime-specific interpolation model was found to beat Wan or LTX FLF.
- No VRAM or availability details were found for SketchKeyAnime, AniDoc or LVCD ComfyUI nodes.

---

## 8. Licensing for personal use

### Takeaway
All candidates are fine for personal use. Wan 2.1/2.2 (and Animate, Alpha, Dancer), Mochi, ToonCrafter and CogVideoX-2B are Apache 2.0. LTX-2.x uses the LTX community license, which is free under $10M annual revenue and allows private use. HunyuanVideo uses the Tencent Hunyuan Community License, which **excludes the EU, UK and South Korea**.

### Cited Findings
- Wan 2.1/2.2 are Apache 2.0. — [howaiworks](https://howaiworks.ai/blog/alibaba-wan-open-weights-stopped-at-2-2); [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/self-hosting-hunyuanvideo-cogvideox-mochi-ltx)
- LTX: companies under $10M annual revenue can use it commercially at no cost under the community license, and those above need a paid agreement. Revenue is counted across the whole corporate group. Private use is allowed. — [ltx.io license](https://ltx.io/model/license); [canirun.ai summary](https://canirun.ai/license/ltx-2-community/); [st-hakky guide](https://book.st-hakky.com/en/data-science/ltx-2-5-commercial-license-guide). **Conflict:** Fora Soft calls LTX-2 "Apache 2.0" but also applies the $10M threshold, which is inconsistent. The official LTX license page is the authority. — [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/self-hosting-hunyuanvideo-cogvideox-mochi-ltx)
- HunyuanVideo (original and 1.5): the Tencent Hunyuan Community License excludes the EU, UK and South Korea. It permits research and personal use and restricts commercial deployment. — [chatforest review](https://chatforest.com/reviews/hunyuanvideo-tencent-open-source-video-generation/); [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/self-hosting-hunyuanvideo-cogvideox-mochi-ltx)
- CogVideoX: 2B is Apache 2.0 and 5B has a custom license. Mochi is Apache 2.0. — [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/self-hosting-hunyuanvideo-cogvideox-mochi-ltx)
- ToonCrafter and Wan-Alpha are Apache-2.0. — [ToonCrafter GitHub](https://github.com/Doubiiu/ToonCrafter); [HF wan-alpha-v2.0](https://huggingface.co/htdong/wan-alpha-v2.0)

### Inferences
- Adult (non-explicit) office-lady content is a non-issue for local open models. Hosted APIs (fal, Replicate, Alibaba) apply their own content filters, which may block suggestive outfits. Local generation avoids this. (Inference.)
- Hosted APIs could also count as "data leaving the PC". This doesn't matter for personal use, but is worth noting.

### Gaps
- I did not read the full Tencent or LTX license texts in this session. Only summaries were used.

---

## 9. Hosted APIs of open models (fal.ai, Replicate) and cloud GPUs

### Takeaway
If the owner's GPU is weak, the cheapest path is renting a 24–48 GB GPU on RunPod ($0.34–0.79/h) and running ComfyUI with Wan 2.2 FLF/VACE/Animate. Per-clip APIs (fal, Replicate) are convenient: Wan 2.2 costs about $0.04–0.40 per second of video depending on mode and tier (sources conflict). The FLF on Replicate is about $0.19 per run. APIs give less control over VACE masks, LoRAs and seeds.

### Cited Findings
- fal Wan 2.2 A14B is listed at $0.10/s by one fal roundup. Another comparison lists Standard at $0.20 (480p) or $0.40 (720p) per generated second, and Turbo at $0.05 or $0.10 per video. **These conflict.** — [fal learn](https://fal.ai/learn/tools/ai-video-generators); [aiidelist comparison](https://aiidelist.com/blog/cheapest-wan-2-2-api-pricing-2026)
- Wan 2.2 Animate on fal costs $0.04/s at 480p and $0.08/s at 720p, normalized to 16 fps (per a third-party blog). — [aireiter guide](https://aireiter.com/blog/wan2-2-animate-guide); [muapi comparison](https://muapi.ai/comparison/wan2.2-animate)
- Replicate `lucataco/wan-2.2-first-last-frame` costs ~$0.19 per run. — [Replicate](https://internal.replicate.com/lucataco/wan-2.2-first-last-frame)
- fal hosts Wan 2.2 VACE-Fun pose and Wan 2.2 LoRA trainers. — [fal VACE-Fun pose](https://fal.ai/models/fal-ai/wan-22-vace-fun-a14b/pose); [fal trainer](https://fal.ai/models/fal-ai/wan-22-trainer/t2v-a14b/playground)
- RunPod GPU prices are in section 4. RunPod also has a guide for LTX-2 in ComfyUI. — [RunPod LTX-2](https://www.runpod.io/articles/guides/comfyui-ltx-2-runpod)

### Inferences
- For dozens of 3–10 s clips with many iterations (expect 3–10 tries per clip), a rented 4090 or 5090 running ComfyUI is likely cheaper and more controllable than per-second APIs. At ~$0.34–0.69/h and a few minutes per 5 s clip, iterations cost cents. (Inference.)

### Gaps
- I could not open fal's own FLF and Animate pricing pages to confirm current rates.

---

## 10. Realistic quality assessment vs top commercial services (anime full-body clips)

### Takeaway
As of Oct 2026, open models (Wan 2.2 and LTX-2.5) trail the newest closed models (Wan 2.7 and 3.0 API, plus commercial services covered by other researchers) in raw motion quality, resolution and prompt adherence. They **win on control**: exact first and last frames, pose-driven motion, pinned keyframes, character LoRAs, no content filters and unlimited iteration. For short, static-camera, full-body anime clips on green that are chained via shared keyframes, a Wan 2.2 FLF/VACE plus LoRA pipeline is a credible, arguably best-fit approach. Expect manual cleanup: first/last frame replacement, spill removal, occasional hand or face artifacts, and retiming.

### Cited Findings
- Wan 2.2 scores about 86.2% on VBench vs about 84.3% for Sora on the same scorecard, and is "strongest on faces, skin, hair, and multi-subject prompts". These are vendor or aggregated benchmark numbers. — [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/self-hosting-hunyuanvideo-cogvideox-mochi-ltx)
- LTX-2.5 had a 67% win rate in LTX's own blind preference tests. LTX describes its artifact benchmarks as "preliminary" (vendor claim). — [RunPod LTX-2.5](https://www.runpod.io/blog/ltx-2-5-the-open-weights-world-model-built-for-speed-and-how-to-run-it-on-runpod)
- ToonCrafter's authors state the "success rate is not guaranteed". — [ToonCrafter GitHub](https://github.com/Doubiiu/ToonCrafter)
- Alibaba's newest Wan (2.6, 2.7, 3.0) and its keyframe-to-video API (wan2.2-kf2v-flash) are closed or API-only. — [howaiworks](https://howaiworks.ai/blog/alibaba-wan-open-weights-stopped-at-2-2); [Alibaba Cloud](https://www.alibabacloud.com/help/en/model-studio/wan2-2-kf2v-flash)

### Inferences
- **Recommended open pipeline (synthesis):**
  1. Design Rin keyframes as stills, drawn or made with an SDXL anime model plus character LoRA, at 720×1280 on flat green.
  2. Optionally train a Wan 2.2 character LoRA with musubi-tuner or AI Toolkit on 30–60 images (24 GB local or rented).
  3. For each clip, use Wan 2.2 FLF (2 keyframes) or Wan VACE (first, mid and last keyframes pinned, with DWPose or depth control from a 3D mannequin for exact arm motion). Use LightX2V 4-step LoRAs for speed, plus GGUF or FP8 depending on VRAM.
  4. Overwrite the first and last frames with the exact keyframe PNGs.
  5. Retime from 16 fps to 24 fps with holds on twos or threes (pick frames rather than interpolate).
  6. Upscale to 1080×1920 with an anime upscaler (ESRGAN anime, SeedVR2 or PID).
  7. Chroma-key, suppress spill and export as WebM VP9 or ProRes 4444 with alpha.
- **Risks:** subtle colour or line shifts between clips (fix with colour matching in post), green spill, hand or finger artifacts on full body at 720p (the character is small in frame, so the face gets few pixels; consider generating at 720×1280 and checking face fidelity), and unwanted mouth motion (prompting plus a held mouth layer in post).
- LTX-2.5 is a strong alternative for speed and higher native resolution, but has a less mature anime LoRA and VACE-style tooling ecosystem (inference). The audio-generation focus is irrelevant here, and lip-sync tendencies could even work against the "no mouth movement" need.

### Gaps
- No side-by-side anime full-body benchmark (open vs Kling, Veo, Seedance, Hailuo, etc.) was found. Quality comparisons rest on general benchmarks and inference.
- No user reports specifically on Wan FLF loops with identical start and end frames for anime characters were retrieved.
