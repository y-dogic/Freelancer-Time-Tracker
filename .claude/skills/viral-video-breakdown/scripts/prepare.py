#!/usr/bin/env python3
"""Turn a short-video share link (or a local video file) into material an agent can read.

Produces, inside --out:
  summary.md            overview: metadata, engagement stats + ratios, specs, shot rhythm, file index
  meta.json             raw metadata (title, author, counts, ...) when downloaded from a link
  shots.json            detected cut timestamps + rhythm stats
  sheets/hook.jpg       dense contact sheet of the first seconds (the hook)
  sheets/sheet_NN.jpg   contact sheets covering the whole timeline, each tile stamped with its time
  frames/               the individual sampled frames (t_MMmSS.s.jpg)
  transcript.txt        timestamped speech transcript (if faster-whisper is installed)
  transcript.json       same, with segment-level detail

Usage:
  python prepare.py "<pasted share text or URL or /path/to/video.mp4>" --out ./breakdown
  python prepare.py "<link>" --cookies-from-browser chrome     # use your logged-in browser
  python prepare.py "<link>" --cookies cookies.txt             # Netscape cookies file

Exit codes: 0 ok, 2 download failed (see printed guidance), 3 bad input / missing ffmpeg.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

URL_RE = re.compile(r"https?://[^\s，。！？、；：“”‘’（）【】《》<>\"'`]+")
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".flv", ".avi"}


# ---------------------------------------------------------------- helpers
def run(cmd, check=True, capture=True):
    return subprocess.run(cmd, check=check, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None)


def fmt_t(sec):
    sec = max(0.0, float(sec))
    m, s = divmod(sec, 60)
    return f"{int(m):02d}:{s:04.1f}"


def need(binary):
    if shutil.which(binary) is None:
        print(f"ERROR: `{binary}` not found. Install ffmpeg (brew install ffmpeg / apt install ffmpeg).",
              file=sys.stderr)
        sys.exit(3)


# ---------------------------------------------------------------- input / download
def resolve_input(raw):
    """Return ('file', Path) or ('url', str)."""
    p = Path(raw.strip()).expanduser()
    if p.exists() and p.is_file():
        return "file", p
    m = URL_RE.search(raw)
    if not m:
        print("ERROR: no URL or existing video file found in the input.", file=sys.stderr)
        sys.exit(3)
    return "url", m.group(0).rstrip(".,!?)")


DOWNLOAD_HELP = """
DOWNLOAD_FAILED
The platform refused an anonymous download (Douyin and Xiaohongshu usually do this from
servers / without cookies). Legitimate ways to continue -- pick one:

  1. Run on the user's own computer with their logged-in browser's cookies:
       python prepare.py "<link>" --cookies-from-browser chrome   (or edge / safari / firefox)
  2. Export cookies.txt from the browser (e.g. the "Get cookies.txt LOCALLY" extension) and pass:
       python prepare.py "<link>" --cookies /path/to/cookies.txt
  3. Save the video in the app (Douyin: 分享 → 保存本地; Xiaohongshu: 长按 → 保存视频),
     then run:  python prepare.py /path/to/video.mp4
     -- and ask the user for the visible stats (点赞/评论/收藏/转发, 发布时间, 粉丝数).

Also make sure yt-dlp is current:  pip install -U yt-dlp
"""


def download(url, out, cookies=None, browser=None):
    if shutil.which("yt-dlp") is None:
        print("ERROR: yt-dlp is not installed. Run: pip install -U yt-dlp", file=sys.stderr)
        print(DOWNLOAD_HELP)
        sys.exit(2)
    cmd = ["yt-dlp", "--no-playlist", "--no-warnings", "--write-info-json",
           "-f", "bv*+ba/b", "--merge-output-format", "mp4",
           "-o", str(out / "video.%(ext)s"), url]
    if cookies:
        cmd[1:1] = ["--cookies", str(Path(cookies).expanduser())]
    if browser:
        cmd[1:1] = ["--cookies-from-browser", browser]
    r = run(cmd, check=False)
    vids = [p for p in out.glob("video.*") if p.suffix.lower() in VIDEO_EXTS]
    if r.returncode != 0 or not vids:
        print((r.stderr or r.stdout or "").strip()[-1500:], file=sys.stderr)
        print(DOWNLOAD_HELP)
        sys.exit(2)
    meta = {}
    infos = list(out.glob("video*.info.json"))
    if infos:
        info = json.loads(infos[0].read_text(encoding="utf-8"))
        keep = ["id", "title", "description", "uploader", "uploader_id", "channel",
                "channel_follower_count", "upload_date", "timestamp", "duration",
                "view_count", "like_count", "comment_count", "repost_count",
                "favorite_count", "save_count", "webpage_url", "extractor", "tags", "track", "artist"]
        meta = {k: info.get(k) for k in keep if info.get(k) not in (None, "", [])}
        infos[0].unlink()
    meta["source_url"] = url
    return vids[0], meta


# ---------------------------------------------------------------- analysis
def probe(video):
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(video)])
    d = json.loads(r.stdout)
    v = next((s for s in d["streams"] if s.get("codec_type") == "video"), {})
    a = next((s for s in d["streams"] if s.get("codec_type") == "audio"), None)
    fps = v.get("avg_frame_rate", "0/1")
    try:
        n, dd = fps.split("/")
        fps = round(float(n) / float(dd), 2) if float(dd) else None
    except Exception:
        fps = None
    w, h = int(v.get("width", 0)), int(v.get("height", 0))
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = abs(int(sd["rotation"]))
    if rot in (90, 270):
        w, h = h, w
    return {"duration": float(d["format"].get("duration", 0)), "width": w, "height": h,
            "fps": fps, "has_audio": a is not None}


def detect_shots(video, duration, threshold):
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-an",
             "-vf", f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"], check=False)
    cuts = sorted({round(float(m), 2) for m in re.findall(r"pts_time:([0-9.]+)", r.stderr or "")})
    cuts = [c for c in cuts if 0.15 < c < duration - 0.1]
    bounds = [0.0] + cuts + [duration]
    lengths = [round(b - a, 2) for a, b in zip(bounds, bounds[1:]) if b - a > 0]
    stats = {
        "threshold": threshold,
        "cut_count": len(cuts),
        "shot_count": len(lengths),
        "avg_shot_sec": round(sum(lengths) / len(lengths), 2) if lengths else None,
        "longest_shot_sec": max(lengths) if lengths else None,
        "cuts_in_first_3s": sum(1 for c in cuts if c <= 3),
        "cuts_per_10s_by_window": [sum(1 for c in cuts if i * 10 <= c < (i + 1) * 10)
                                   for i in range(int(math.ceil(duration / 10)) or 1)],
    }
    return cuts, lengths, stats


def plan_frames(duration, cuts, max_frames, hook_secs):
    """Dense sampling of the hook, one frame just after every cut, uniform fill elsewhere."""
    hook_end = min(hook_secs, duration)
    hook = [round(t * 0.5, 2) for t in range(int(hook_end / 0.5) + 1) if t * 0.5 < duration - 0.05]
    budget = max(8, max_frames - len(hook))
    body = [round(min(c + 0.25, duration - 0.05), 2) for c in cuts if c > hook_end]
    step = max(1.0, (duration - hook_end) / max(1, budget))
    t = hook_end + step / 2
    while t < duration - 0.05:
        body.append(round(t, 2))
        t += step
    body = sorted(set(body))
    # thin out neighbours closer than 0.6s, then downsample uniformly to the budget
    thinned = []
    for t in body:
        if not thinned or t - thinned[-1] >= 0.6:
            thinned.append(t)
    if len(thinned) > budget:
        idx = [round(i * (len(thinned) - 1) / (budget - 1)) for i in range(budget)]
        thinned = [thinned[i] for i in sorted(set(idx))]
    return hook, thinned


def grab(video, t, dest, width):
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video),
         "-frames:v", "1", "-vf", f"scale={width}:-2", "-q:v", "3", str(dest)], check=False)
    return dest.exists()


def contact_sheet(items, dest, cols, title):
    from PIL import Image, ImageDraw, ImageFont
    imgs = [(t, Image.open(p).convert("RGB")) for t, p in items]
    tw, th = imgs[0][1].size
    rows = math.ceil(len(imgs) / cols)
    pad, label, head = 6, 26, 40
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, head + rows * (th + label + pad) + pad), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    font = None
    for cand in ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "/System/Library/Fonts/PingFang.ttc",
                 "C:/Windows/Fonts/msyh.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if os.path.exists(cand):
            try:
                font = ImageFont.truetype(cand, 20)
                break
            except Exception:
                pass
    font = font or ImageFont.load_default()
    draw.text((pad, 8), title, fill=(255, 220, 90), font=font)
    for i, (t, im) in enumerate(imgs):
        r, c = divmod(i, cols)
        x, y = pad + c * (tw + pad), head + r * (th + label + pad)
        sheet.paste(im.resize((tw, th)), (x, y + label))
        draw.text((x + 2, y + 2), fmt_t(t), fill=(255, 255, 255), font=font)
    sheet.save(dest, quality=85)


def transcribe(video, out, model_name, lang):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None, "faster-whisper not installed (pip install faster-whisper) -- read burned-in subtitles from the frames instead."
    wav = out / "audio.wav"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-vn", "-ac", "1",
         "-ar", "16000", str(wav)])
    try:
        model = WhisperModel(model_name, device="auto", compute_type="int8")
        kw = dict(vad_filter=True, beam_size=5)
        if lang and lang != "auto":
            kw["language"] = lang
        if lang in ("zh", "auto"):
            kw["initial_prompt"] = "以下是普通话的句子，请使用简体中文和标点符号。"
        # decode the wav ourselves: avoids PyAV version clashes inside faster-whisper
        import wave
        import numpy as np
        with wave.open(str(wav), "rb") as wf:
            pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        segs, info = model.transcribe(pcm.astype(np.float32) / 32768.0, **kw)
        segs = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segs]
    except Exception as e:  # model download blocked, etc.
        return None, f"transcription failed: {e}"
    finally:
        wav.unlink(missing_ok=True)
    (out / "transcript.json").write_text(json.dumps(
        {"language": info.language, "segments": segs}, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "transcript.txt").write_text(
        "\n".join(f"[{fmt_t(s['start'])}-{fmt_t(s['end'])}] {s['text']}" for s in segs) + "\n", encoding="utf-8")
    chars = sum(len(re.sub(r"\s", "", s["text"])) for s in segs)
    return {"language": info.language, "segments": len(segs), "chars": chars}, None


def ratios(meta):
    like = meta.get("like_count") or 0
    out = {}
    for k, label in [("comment_count", "评论/点赞"), ("repost_count", "转发/点赞"),
                     ("favorite_count", "收藏/点赞"), ("save_count", "收藏/点赞")]:
        if like and meta.get(k) is not None:
            out[label] = f"{meta[k] / like:.1%}"
    if meta.get("view_count") and like:
        out["点赞/播放"] = f"{like / meta['view_count']:.2%}"
    if meta.get("channel_follower_count") and like:
        out["点赞/粉丝"] = f"{like / meta['channel_follower_count']:.2f}x"
    return out


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="pasted share text, a URL, or a local video path")
    ap.add_argument("--out", default="./video-breakdown", help="working directory to write into")
    ap.add_argument("--cookies", help="Netscape cookies.txt for the platform")
    ap.add_argument("--cookies-from-browser", dest="browser", help="chrome / edge / safari / firefox ...")
    ap.add_argument("--max-frames", type=int, default=72, help="total frame budget (default 72)")
    ap.add_argument("--hook-secs", type=float, default=5, help="seconds sampled densely at the start")
    ap.add_argument("--scene-threshold", type=float, default=0.3, help="cut sensitivity 0-1 (lower = more cuts)")
    ap.add_argument("--frame-width", type=int, default=360)
    ap.add_argument("--whisper-model", default="small", help="tiny/base/small/medium/large-v3")
    ap.add_argument("--lang", default="zh", help="speech language, or 'auto'")
    ap.add_argument("--no-transcribe", action="store_true")
    ap.add_argument("--keep-video", action="store_true", help="keep the downloaded video afterwards")
    a = ap.parse_args()

    need("ffmpeg")
    need("ffprobe")
    out = Path(a.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    kind, src = resolve_input(a.input)
    meta = {}
    if kind == "url":
        print(f"[1/5] downloading {src}")
        video, meta = download(src, out, a.cookies, a.browser)
        (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        video = src
        print(f"[1/5] using local file {video}")

    spec = probe(video)
    dur = spec["duration"]
    if dur <= 0:
        print("ERROR: could not read the video duration (file broken or not a video).", file=sys.stderr)
        sys.exit(3)

    print("[2/5] detecting cuts")
    cuts, lengths, shot_stats = detect_shots(video, dur, a.scene_threshold)
    (out / "shots.json").write_text(json.dumps({"cuts": cuts, "shot_lengths": lengths, **shot_stats},
                                               ensure_ascii=False, indent=1), encoding="utf-8")

    print("[3/5] sampling frames")
    frames_dir, sheets_dir = out / "frames", out / "sheets"
    for d in (frames_dir, sheets_dir):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir()
    hook_ts, body_ts = plan_frames(dur, cuts, a.max_frames, a.hook_secs)
    got_hook, got_body = [], []
    for ts, bucket in ((hook_ts, got_hook), (body_ts, got_body)):
        for t in ts:
            p = frames_dir / f"t_{int(t // 60):02d}m{t % 60:04.1f}s.jpg"
            if grab(video, t, p, a.frame_width):
                bucket.append((t, p))

    print("[4/5] building contact sheets")
    sheets = []
    if got_hook:
        contact_sheet(got_hook, sheets_dir / "hook.jpg", 5, f"HOOK  0:00-{fmt_t(hook_ts[-1])}  (every 0.5s)")
        sheets.append("sheets/hook.jpg")
    per = 12
    for i in range(0, len(got_body), per):
        chunk = got_body[i:i + per]
        name = f"sheet_{i // per + 1:02d}.jpg"
        contact_sheet(chunk, sheets_dir / name, 4, f"{fmt_t(chunk[0][0])} - {fmt_t(chunk[-1][0])}")
        sheets.append(f"sheets/{name}")

    tr, tr_err = None, "skipped (--no-transcribe)"
    if not a.no_transcribe and spec["has_audio"]:
        print("[5/5] transcribing speech (first run downloads the whisper model)")
        tr, tr_err = transcribe(video, out, a.whisper_model, a.lang)
    elif not spec["has_audio"]:
        tr_err = "video has no audio track"

    # ------------------------------------------------ summary.md
    L = ["# Video prep summary", ""]
    if meta:
        L += ["## Metadata (from platform)", ""]
        for k in ["title", "description", "uploader", "channel_follower_count", "upload_date",
                  "view_count", "like_count", "comment_count", "repost_count", "favorite_count",
                  "save_count", "tags", "track", "source_url"]:
            if k in meta:
                L.append(f"- **{k}**: {meta[k]}")
        r = ratios(meta)
        if r:
            L += ["", "Engagement ratios: " + " · ".join(f"{k} {v}" for k, v in r.items())]
        missing = [k for k in ["like_count", "comment_count", "repost_count", "favorite_count"] if k not in meta]
        if missing:
            L += ["", f"_Not provided by the platform: {', '.join(missing)} -- ask the user if needed._"]
    else:
        L += ["## Metadata", "", "_Local file: no platform stats. Ask the user for 点赞/评论/收藏/转发, "
              "发布时间, 账号粉丝数 if they want the 传播逻辑 section grounded in data._"]
    orient = "vertical" if spec["height"] > spec["width"] else "horizontal"
    L += ["", "## Specs", "",
          f"- duration {fmt_t(dur)} ({dur:.1f}s), {spec['width']}x{spec['height']} {orient}, {spec['fps']} fps, "
          f"audio: {'yes' if spec['has_audio'] else 'no'}",
          "", "## Edit rhythm (automatic cut detection -- approximate)", "",
          f"- {shot_stats['shot_count']} shots, average {shot_stats['avg_shot_sec']}s, "
          f"longest {shot_stats['longest_shot_sec']}s, {shot_stats['cuts_in_first_3s']} cuts in the first 3s",
          f"- cuts per 10s window: {shot_stats['cuts_per_10s_by_window']}",
          "- note: talking-head videos with jump cuts or zoom-punch-ins may under-detect; "
          "slideshow/transition-heavy videos may over-detect. Trust the frames over the numbers.",
          "", "## Transcript", ""]
    if tr:
        L.append(f"- transcript.txt: {tr['segments']} segments, ~{tr['chars']} chars, language {tr['language']}"
                 f" (≈{tr['chars'] / max(dur, 1) * 60:.0f} chars/min speaking pace)")
    else:
        L.append(f"- none: {tr_err}")
    L += ["", "## Files to read", "", *[f"- {s}" for s in sheets],
          f"- frames/ ({len(got_hook) + len(got_body)} individual frames, open one for detail)",
          "- shots.json (all cut timestamps)"]
    if tr:
        L.append("- transcript.txt")
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    if kind == "url" and not a.keep_video:
        video.unlink(missing_ok=True)
    print(f"\nDONE -> {out}/summary.md")
    print("\n".join(L))


if __name__ == "__main__":
    main()
