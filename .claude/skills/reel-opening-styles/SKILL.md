---
name: reel-opening-styles
description: Edit the first 3–6 seconds of a talking-head Reel / Short / TikTok / Douyin / 小紅書 video into a stronger opening (開場). Offers 6 opening edit styles (開場畫面剪輯效果), renders a side-by-side preview of all 6 on the person's own footage, recommends the best fit, then renders the chosen opening in Remotion and splices it onto the reel. The styles are circle mask, torn-paper reveal, spotlight + word behind the head, black type poster, flash-in + face focus, TV texture. Also gives the 3-beat hook script (audience → pain → numbered promise). Use this whenever someone wants a better reel opening or hook, says 5-second retention / 完播率 is low, asks to edit or redo the intro of a 口播 / talking-head / knowledge video, wants opening options or "which opening fits my video", or uploads a vertical talking-head clip and asks to make the start more engaging, even if they don't say "hook". Works alongside it-reelsmaker (this skill does the opening, that one the rest of the edit).
---

# Reel Opening Styles (6種開場畫面)

Talking-head videos (口播) lose most viewers in the first 5 seconds because the opening is a static person talking. The fix is to make the *first 3–6 seconds* move visually while the words land one beat at a time. This skill does that edit for real: it previews all 6 styles on the person's footage, recommends one, renders it, and puts it back on the reel.

## The hook script: 3 beats

Every style animates the same three beats, each shown as on-screen text while it is spoken:

| Beat | Job | Example | Text treatment |
|---|---|---|---|
| 1 **Who/what** (~1 s) | Name the audience or topic so the right people stop | 知識類口播 / "Talking-head creators" | small, white |
| 2 **Pain** (~1–1.5 s) | The problem they already feel | 5秒完播率低？ / "Losing viewers in 5s?" | medium, accent color |
| 3 **Promise + number** (~1.5–2 s) | A specific, countable fix | 試試這**6種**畫面剪輯效果 | number HUGE, rest small |

The visual event of each style (mask change, reveal, flash) lands on the cut into beat 3, because motion on a beat change is what resets attention.

On-screen text comes from what the speaker actually says in their opening. Condense it, don't invent. The number must be true to the video: "6種" only if the video really covers 6. If the opening has no pain or number to work with, propose a text and say it isn't in the speech, or suggest re-recording the first line. The person decides.

## The 6 styles

| # | Style | Look | Best when | Needs cut-out |
|---|---|---|---|---|
| 1 | 背景壓暗，人物蒙版動畫 | dim background, speaker in a circle that shrinks under a "?", then a full cut-out with a white sticker outline + giant number | moody or premium topics, question hooks, a background worth hiding | yes (else the circle expands instead) |
| 2 | 人物摳像，背景做蒙版動畫 | speaker cut out onto a different backdrop, then a torn-paper wipe reveals the real room | messy or plain room, a strong scene change, a themed image to show | **yes** |
| 3 | 開場聚光燈，人物摳像動畫 | spotlight opens on the face, the pain keyword sits **behind the head**, then lights up with a punch-in | calm wall behind the head, a cinematic feel, a strong 1–2-word keyword | **yes** for text-behind-head |
| 4 | 文字大小排版，人物蒙版 | black poster, bold text in size steps, speaker in a rounded window that becomes a circle | text-heavy or list hooks, bad backgrounds, clean minimal brands | no |
| 5 | 開場閃現，人物聚焦 | text flashes in, face spotlight on the pain, then a flash cut to a big number | footage that already looks good, energetic delivery, fastest to make | no |
| 6 | 畫面電視紋理，文字動畫預設 | scanline TV look, typed text (vertical for Chinese/Japanese), blur + giant centered number | editorial/retro taste, low-res footage, Chinese vertical type | no |

## Workflow: editing the opening in Claude

Needs a shell with ffmpeg, Node.js 18+ and Python 3.9+ (Claude Code). With no shell (claude.ai chat, phone), don't pretend to render. Write the hook and recommend a style, then give the hand-edit steps from `references/capcut.md`.

Script: `python3 "${CLAUDE_SKILL_DIR}/scripts/opening.py"` (called `opening.py` below). Use a work folder per reel, e.g. `edit/<id>/opening` with it-reelsmaker or `<video stem>-opening/` otherwise. Talk to the person in their language.

**1. Setup (once per Remotion project).** `opening.py setup --remotion <dir>` copies the composition to `<dir>/src/opening/` and downloads Noto Sans/Serif fonts to `public/opening/fonts/` (`--script tc|sc|hk|jp|kr`, default `tc`; use `sc` for Simplified Chinese hooks). If the folder has no Remotion project, it creates a minimal one and runs `npm install`. With it-reelsmaker, point it at that project's `remotion_dir`. Fonts are local on purpose: headless Chrome often can't fetch Google Fonts behind proxies. Python needs: `pip install "opencv-python-headless<5" Pillow` (OpenCV 5 dropped the face cascade), plus `faster-whisper` for word timings and `"rembg[cpu,cli]"` + `rembg d u2net_human_seg` for cut-outs.

**2. Analyze.** `opening.py analyze <video> --work W [--seconds 6]` makes a 1080×1920 30 fps clip of the opening, measures the face box (median over frames), background busyness and brightness, and prints a fit ranking with reasons. The ranking is a heuristic, a starting point for your own judgment. Look at `W/sheet.jpg` yourself. `--seconds` must cover the whole hook: if the promise is spoken at 5.5 s, use 7.

**3. Words → hook.** `opening.py words --work W [--language zh]` gives word timings. Write `W/hook.json`:
```json
{
  "topic":   {"text": "知識類口播", "at": 0.1},
  "pain":    {"text": "5秒完播率低？", "at": 1.2, "big": "5秒"},
  "promise": {"at": 2.5, "lead": "試試這", "number": "6", "unit": "種", "sub": "畫面剪輯效果"},
  "durationSec": 4.6,
  "accent": "#E8364A"
}
```
- Each `at` is the start time of the word that beat begins on (from `words.json`). `promise.at` is the moment the number/promise is spoken.
- `durationSec` is the end of the promise phrase + ~0.6 s, and no longer than the analyzed clip. After it, the original video continues untouched.
- `pain.big` is the 1–2-word keyword style 3 puts behind the head. Pick the punchiest word, ideally the one that starts the line.
- Optional: `face` {cx, cy, w, h} to override the measured box, `background` (an image/video path for style 2's backdrop), `ink`, `vertical` (style 6). With a brand profile from it-reelsmaker, take the accent from the brand.
- Keep texts short: topic ≤ ~8 CJK characters / 3 English words, pain ≤ ~10 / 5.

**4. Cut-out (if previewing styles 1–3).** `opening.py matte --work W` runs rembg at about 1 s per frame on CPU (a 6 s clip takes about 3 min). Start it in the background as soon as analysis is done, and write the hook meanwhile. Open `W/check.jpg`: furniture or wall stuck to the person shows on both halves, so prefer styles 4–6 if it's bad. Skip the cut-out entirely if the person already chose style 4, 5 or 6.

**5. Preview all 6 and recommend.** `opening.py props --work W --hook W/hook.json`, then `opening.py preview --work W --remotion <dir>` (about 40 s). This writes `W/preview.jpg`: 6 columns with the pain beat on top and the promise beat below. **Look at it before showing it**: no text over the face, the number readable, nothing important below y≈1500 or in the right 120 px (app UI). Send it to the person (SendUserFile, display render). In the same message:
- one line per style on how it looks *on their footage*;
- your **recommendation** plus one alternative, each with a one-sentence why, combining the fit ranking, what you see in the preview, and the video's tone/brand (a calm premium coach ≠ an energetic tips channel);
- ask which one to render with AskUserQuestion (≤ 4 options: your top 3 + "another style / change the text").

**6. Render and splice.** `opening.py render --work W --remotion <dir> --style N --source <video> --out <out.mp4>` renders the opening (about 1 min). It replaces the first `durationSec` of the source with it, keeps the source's full audio, and re-encodes the rest at 1080×1920. It also writes `<out>.sheet.jpg`. Check the sheet, then send the video. Revisions (text, timing, accent, style) mean editing `hook.json`, then `props`, then `render` again.

**With it-reelsmaker:** do its edit first, then apply the opening to its **render** before mastering: `--source out/<render>.mp4`, then run `master_audio.py` on the spliced file. In the reel's plan, hide its subtitles and hook for the opening span (`visual_plan.py hide-subs … --from 0 --to <durationSec>`, no `--hook`). This skill's beats replace them, and two layers of text would collide. Analyze the rough cut (`final.mp4`) so beat times match the edited timeline.

## Quality checks before sending

- Text never covers the face (60 px margin). The layouts place text using the face box. If a still shows overlap, fix `face` in hook.json or shorten the text.
- One accent color, one number. The number is the biggest thing on screen in beat 3.
- Each beat's text appears on its spoken word (±2 frames).
- Styles 1–3: no chopped-off limb or stuck furniture visible in the cut-out over the new background (`check.jpg`, stills).
- The splice point is invisible: no jump in framing at `durationSec`. If the speaker moves a lot there, end the opening at a pause.
- The video still makes sense with the sound off.

## Without footage

If the person only wants ideas or a plan: write their 3 beats, recommend a style and an alternative from the table, and give a second-by-second timeline plus editor steps from `references/capcut.md`.
