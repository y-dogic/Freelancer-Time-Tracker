---
name: viral-video-breakdown
description: 拆解爆款短视频 — breaks down a viral short video (Douyin/抖音, Xiaohongshu/小红书, TikTok, Bilibili, Kuaishou, 视频号, YouTube Shorts, Reels, or a local video file) by actually watching it (sampled frames + speech transcript) and analysing 选题逻辑, 脚本与画面, 开头钩子, 金句, 情绪与人群, 传播逻辑, and a reusable template. Use this whenever the user pastes a short-video share link or share text (e.g. "… https://v.douyin.com/xxx/ 复制此链接，打开Dou音搜索…", xhslink.com, xiaohongshu.com/explore/…), drops a video file, or asks to 拆解/分析/复盘 a video, find out why a video went viral (为什么会火/爆), extract its script, hook or 金句, or learn a 爆款模板 to copy — even if they only paste the link with no instruction.
---

# 爆款视频拆解 (Viral video breakdown)

The goal is a breakdown a content operator can act on: why this video worked, and how to reuse
the mechanism. It has to be grounded in what is actually in the video, not guessed from the title.
So the order is: get the video → turn it into frames + transcript → watch/read all of it → analyse.

## Step 1 — Prepare the video

`<skill-dir>` below is the base directory shown when this skill loads.

```bash
python3 <skill-dir>/scripts/prepare.py "<the user's pasted text, verbatim>" --out ./video-breakdown/<short-name>
```

- Pass the pasted share text as-is; the script finds the URL inside it. A local file path also works.
- It downloads with yt-dlp, detects cuts, samples ~72 frames (every 0.5s for the first 5s, then one
  per cut plus uniform fill), builds timestamped contact sheets, transcribes speech with
  faster-whisper, and writes `summary.md`. The downloaded video is deleted afterwards unless
  `--keep-video` (useful if you expect to zoom into a section later).
- Useful flags: `--max-frames 100` for long videos (>3 min), `--lang auto` for non-Mandarin speech,
  `--whisper-model medium` if the transcript is poor, `--scene-threshold 0.2` if cuts are under-detected.
- Missing tools: `pip install -U yt-dlp faster-whisper pillow numpy`, and ffmpeg via the OS package
  manager. The first transcription downloads the whisper model (~460 MB for `small`).

### If the download fails (`DOWNLOAD_FAILED`)

Douyin and Xiaohongshu often refuse anonymous downloads, especially from cloud servers. Don't try
to defeat that: no reverse-engineered signature APIs, captcha solving, or scraping workarounds.
They're brittle, and they get around the platform's access controls. Instead, offer the user the
legitimate routes the script prints, in this order:

1. **Their own browser's cookies** (works when running on their computer, logged into the site in
   that browser): re-run with `--cookies-from-browser chrome` (or edge/safari/firefox).
2. **A cookies.txt export** from their browser: `--cookies /path/cookies.txt`.
3. **Save the video in the app** (抖音: 分享 → 保存本地; 小红书: 长按 → 保存视频) and pass the file path.
   Then ask for the numbers visible in the app (点赞/评论/收藏/转发, 发布时间, 粉丝数), because a local
   file carries no stats.

If the user can't do any of these right now, you can still analyse from screenshots or a screen
recording they send. Say clearly that the result is then partial.

## Step 2 — Watch the whole video

Read `summary.md` first (stats, specs, cut rhythm, file list). Then:

1. Look at `sheets/hook.jpg`: the opening at 0.5s resolution, which is where most of the craft is.
2. Look at **every** `sheets/sheet_NN.jpg`, in order. Don't stop after the first few. The structure,
   the turn, and the ending live in the middle and the end.
3. Read `transcript.txt` in full. If there is none (no faster-whisper, or music-only), read the
   burned-in subtitles and on-screen text from the frames instead. Most Douyin and Xiaohongshu videos have them.
4. Open individual files in `frames/` when a tile is too small to read text or judge a shot.
   If you kept the video and need more detail on a section, extract a denser range:
   `ffmpeg -ss 30 -to 40 -i video.mp4 -vf fps=2,scale=360:-2 frames/dense_%03d.jpg`.

Whisper mishears names, numbers and slang. Cross-check against the on-screen subtitles and prefer
the subtitles when they disagree. Whisper ignores music, so you can't identify the BGM from audio.
Use the `track` metadata if present, otherwise say it's unknown.

## Step 3 — Analyse and write the report

Read `references/framework.md`. It has the seven dimensions from the user's breakdown method, the
guiding questions for each, how to read engagement ratios, and the report template. Follow its
section order:

1. 选题逻辑 — 核心命题, 目标人群, 为什么值得做, 提供什么价值
2. 脚本与画面 — script tree with timestamps, a chapter table, and how shots and cuts serve the script
3. 完整的开头 — hook type, beat-by-beat opening, the turn into the body, suspense and retention devices
4. 金句 — verbatim quotable lines plus one sentence that names the theme
5. 情绪与人群 — who is moved, which emotions in what arc, whether a way out is offered
6. 传播逻辑 — data → signals → content mechanisms → uncertainties
7. 可复用的框架逻辑 — fill-in templates for 选题/开头/主题/金句/钩子/结尾 and what to borrow first

Principles that make the report trustworthy:
- **Cite evidence.** Quote the actual line, give the approximate timestamp, and describe the actual frame.
  "开头 0:00-0:03 大字卡「提升幸运的6个方法」+ 口播…" is useful. "开头很吸引人" is not.
- **Separate observation from inference.** Timings are approximate (约). Camera movement inferred from
  sampled frames is "未逐帧核验". Never invent stats. With no data, the 传播逻辑 section gives
  hypotheses and says which numbers would confirm them.
- **State coverage up front**: duration, how many frames were read, transcript vs subtitles. For example:
  "约 8 分 46 秒，读取 72 张画面及语音转写".
- **Make section 7 practical.** If the user told you their niche or account, adapt the templates to it.
  Otherwise ask at the end whether they'd like the templates applied to their own topic.

**Language**: write in the language the user writes in. If they only pasted a Chinese share link, write
in Simplified Chinese. Keep the framework's Chinese section names either way, because they're the user's working vocabulary.

**Output**: save the report as `breakdown.md` in the work directory, and also give it in the reply
(the full report, not a summary of it). The frames are small. Mention the work directory in case
the user wants to delete it.

## Several videos at once

For a comparison (e.g. "these 3 videos all went viral, what do they share?"), prepare each into its own
`--out` folder, write a short breakdown of each, then add a 共性 section that compares 选题, hook type,
structure, length/rhythm and 传播 signals, and ends with one combined template.
