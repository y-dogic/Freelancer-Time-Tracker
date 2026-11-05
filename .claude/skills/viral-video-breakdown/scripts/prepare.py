#!/usr/bin/env python3
"""Turn a video share link (any yt-dlp-supported platform) or a local file into material an agent can read.

Writes into --out:
  summary.md          start here: metadata, engagement ratios, specs, edit rhythm, speech density,
                      pauses, transcript source, file index
  meta.json           platform metadata (title, author, counts, chapters, ...) when downloaded
  thumbnail.jpg       the cover / thumbnail the platform shows (when available)
  shots.json          cut timestamps, shot list, rhythm stats
  shotlist.md         分镜表 skeleton: one row per shot with time, length, frame, overlapping speech
  sheets/hook.jpg     dense contact sheet of the opening
  sheets/sheet_NN.jpg contact sheets across the timeline, every tile stamped with its time
  frames/             individual frames (t_MMmSS.ss.jpg)
  transcript.txt/json speech transcript -- platform captions first, faster-whisper as fallback
  danmaku.txt         Bilibili bullet-comment peaks (when available)

Usage:
  python prepare.py "<pasted share text | URL | /path/video.mp4>" --out ./video-breakdown/name
  python prepare.py "<link>" --cookies-from-browser chrome      # use your logged-in browser
  python prepare.py "<link>" --start 1:30 --end 2:10            # focus on a section
  python prepare.py "<link>" --timestamps 0:12,0:47 --keep-video # add frames at exact moments

Exit codes: 0 ok, 2 download failed (guidance printed), 3 bad input / missing ffmpeg.

Caption-first transcripts, near-duplicate frame removal, cue timestamps and focus windows are
ideas borrowed from bradautomates/claude-video (MIT); this is an independent implementation.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

URL_RE = re.compile(r"https?://[^\s，。！？、；：“”‘’（）【】《》<>\"'`]+")
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".flv", ".avi", ".ts"}
CJK_RE = re.compile(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]")


# ---------------------------------------------------------------- helpers
def run(cmd, check=True):
    return subprocess.run(cmd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          encoding="utf-8", errors="replace")


def fmt_t(sec):
    sec = max(0.0, float(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:04.1f}" if h else f"{int(m):02d}:{s:04.1f}"


def parse_t(v):
    if v is None or v == "":
        return None
    parts = [float(p) for p in str(v).strip().split(":")]
    sec = 0.0
    for p in parts:
        sec = sec * 60 + p
    return sec


def speech_units(text):
    """CJK characters + latin words: a language-neutral measure of how much is said."""
    cjk = len(CJK_RE.findall(text))
    words = len(re.findall(r"[A-Za-z0-9À-ÿ'’-]+", CJK_RE.sub(" ", text)))
    return cjk + words, ("chars" if cjk >= words else "words")


def need(binary):
    if shutil.which(binary) is None:
        print(f"ERROR: `{binary}` not found. Install ffmpeg (brew install ffmpeg / apt install ffmpeg / "
              "winget install ffmpeg).", file=sys.stderr)
        sys.exit(3)


# ---------------------------------------------------------------- input / platform
def resolve_input(raw):
    p = Path(raw.strip().strip('"').strip("'")).expanduser()
    if p.exists() and p.is_file():
        return "file", p
    m = URL_RE.search(raw)
    if not m:
        print("ERROR: no URL or existing video file found in the input.", file=sys.stderr)
        sys.exit(3)
    return "url", m.group(0).rstrip(".,!?)")


PLATFORMS = [
    ("douyin", ("douyin.com", "iesdouyin.com"), "抖音 Douyin"),
    ("tiktok", ("tiktok.com",), "TikTok"),
    ("xiaohongshu", ("xiaohongshu.com", "xhslink.com"), "小红书 Xiaohongshu"),
    ("bilibili", ("bilibili.com", "b23.tv"), "B站 Bilibili"),
    ("kuaishou", ("kuaishou.com", "gifshow.com", "chenzhongtech.com"), "快手 Kuaishou"),
    ("weixin", ("weixin.qq.com", "channels.weixin", "finder.video.qq.com"), "视频号 WeChat Channels"),
    ("youtube", ("youtube.com", "youtu.be"), "YouTube"),
    ("instagram", ("instagram.com",), "Instagram"),
    ("facebook", ("facebook.com", "fb.watch"), "Facebook"),
    ("x", ("twitter.com", "x.com"), "X / Twitter"),
    ("linkedin", ("linkedin.com",), "LinkedIn"),
    ("vimeo", ("vimeo.com",), "Vimeo"),
]


def platform_of(url):
    host = (urlparse(url).hostname or "").lower()
    for key, domains, label in PLATFORMS:
        if any(host == d or host.endswith("." + d) or d in host for d in domains):
            return key, label
    return "other", host or "unknown"


PLATFORM_TIPS = {
    "douyin": "Douyin almost always needs cookies (even logged-out ones) and blocks datacenter IPs.",
    "xiaohongshu": "Xiaohongshu often needs cookies; 图文 notes (image posts) are not videos -- ask for screenshots.",
    "kuaishou": "Kuaishou often needs cookies or a saved file.",
    "weixin": "视频号 links usually can't be downloaded by any tool -- save the video in WeChat or screen-record it.",
    "youtube": "\"Sign in to confirm you're not a bot\" means YouTube is blocking this IP: use browser cookies "
               "or run on your own computer.",
    "instagram": "Instagram usually requires login cookies.",
    "facebook": "Facebook usually requires login cookies.",
    "x": "X/Twitter videos may need login cookies for sensitive or protected posts.",
    "linkedin": "LinkedIn usually requires login cookies.",
    "bilibili": "Bilibili works without login at lower quality; cookies unlock HD and some subtitles.",
}


def failure_help(stderr, platform):
    low = (stderr or "").lower()
    if any(s in low for s in ("sign in", "login", "log in", "not a bot", "cookies", "authentication")):
        cause = "The platform wants authentication (cookies) for this request."
    elif re.search(r"\b429\b", low) or "too many requests" in low or "rate" in low and "limit" in low:
        cause = "The platform is rate-limiting; wait a while before retrying."
    elif re.search(r"\b403\b", low) or "forbidden" in low:
        cause = "403 Forbidden: usually an outdated yt-dlp or a blocked IP. Update yt-dlp and retry once."
    elif "unsupported url" in low:
        cause = "yt-dlp has no extractor for this site/link."
    elif "geo" in low or "not available in your country" in low:
        cause = "The video is geo-restricted from this location."
    elif "private" in low or "removed" in low or "unavailable" in low:
        cause = "The video is private, deleted, or otherwise unavailable."
    else:
        cause = "See the yt-dlp error above."
    tip = PLATFORM_TIPS.get(platform, "")
    return f"""
DOWNLOAD_FAILED
Cause: {cause}
{('Platform note: ' + tip) if tip else ''}
Legitimate ways to continue -- pick one:
  1. Run on the user's own computer with their logged-in browser's cookies:
       python prepare.py "<link>" --cookies-from-browser chrome   (or edge / safari / firefox)
  2. Export cookies.txt from the browser (e.g. the "Get cookies.txt LOCALLY" extension):
       python prepare.py "<link>" --cookies /path/to/cookies.txt
  3. Save the video from the app (or screen-record it) and pass the file:
       python prepare.py /path/to/video.mp4
     -- then ask the user for the visible stats (views/likes/comments/saves/shares, post date, followers).
Also keep yt-dlp current:  pip install -U yt-dlp
"""


# ---------------------------------------------------------------- download
def ytdlp_base(cookies, browser):
    if shutil.which("yt-dlp") is None:
        print("ERROR: yt-dlp is not installed. Run: pip install -U yt-dlp", file=sys.stderr)
        sys.exit(2)
    cmd = ["yt-dlp", "--no-playlist", "--no-warnings"]
    if cookies:
        cmd += ["--cookies", str(Path(cookies).expanduser())]
    if browser:
        cmd += ["--cookies-from-browser", browser]
    return cmd


def pick_caption(info, pref):
    """Choose one caption track in the spoken language. Returns (key, kind, provenance) or None."""
    skip = {"live_chat", "danmaku", "rechat", "comments"}
    manual = {k: v for k, v in (info.get("subtitles") or {}).items() if v and k not in skip}
    auto = {k: v for k, v in (info.get("automatic_captions") or {}).items() if v and k not in skip}
    origs = sorted(k for k in auto if k.endswith("-orig"))

    def base(k):
        k = k.removesuffix("-orig")
        k = k[3:] if k.startswith("ai-") else k  # Bilibili AI subtitles: ai-zh
        return k.split("-")[0].lower()

    lang = pref if pref != "auto" else (origs[0][:-5] if origs else info.get("language"))
    if lang:
        want = lang.split("-")[0].lower()
        for tracks, kind in ((manual, "manual"), (auto, "auto")):
            cands = [k for k in tracks if base(k) == want]
            if cands:
                cands.sort(key=lambda k: (not k.endswith("-orig"), k != lang, len(k)))
                return cands[0], kind, ("original language" if pref == "auto" else "requested language")
    if pref == "auto" and manual:
        # unknown spoken language: a manual track is still better than nothing; label it
        key = sorted(manual, key=lambda k: (base(k) not in ("zh", "en"), k))[0]
        return key, "manual", "language unverified"
    return None


def fetch(url, out, cookies, browser, sub_pref, want_captions):
    base = ytdlp_base(cookies, browser)
    _, plat_label = platform_of(url)
    platform = platform_of(url)[0]
    r = run(base + ["-J", url], check=False)
    if r.returncode != 0 or not r.stdout.strip().startswith("{"):
        print((r.stderr or "").strip()[-1500:], file=sys.stderr)
        print(failure_help(r.stderr, platform))
        sys.exit(2)
    info = json.loads(r.stdout)
    if info.get("_type") == "playlist" and info.get("entries"):
        info = next(e for e in info["entries"] if e)
    info_path = out / "_info.json"
    info_path.write_text(json.dumps(info), encoding="utf-8")

    cap = pick_caption(info, sub_pref) if want_captions else None
    has_danmaku = bool((info.get("subtitles") or {}).get("danmaku"))
    cmd = base + ["--load-info-json", str(info_path), "-f",
                  "bv*[height<=1080]+ba/b[height<=1080]/bv*+ba/b", "--merge-output-format", "mp4",
                  "--write-thumbnail", "--convert-thumbnails", "jpg", "-o", str(out / "video.%(ext)s")]
    langs = []
    if cap:
        cmd += ["--write-subs"] if cap[1] == "manual" else ["--write-auto-subs"]
        langs.append(re.escape(cap[0]))
    if has_danmaku:
        cmd += ["--write-subs"]
        langs.append("danmaku")
    if langs:
        cmd += ["--sub-langs", ",".join(f"^{l}$" for l in langs), "--sub-format", "vtt/srt/best"]
    r = run(cmd, check=False)
    vids = [p for p in out.glob("video.*") if p.suffix.lower() in VIDEO_EXTS and ".f" not in p.stem[5:]]
    media_err = None
    if not vids:
        # media blocked but metadata worked: still collect captions + thumbnail as partial evidence
        media_err = r.stderr or "no video file produced"
        partial = [c for c in cmd if c not in ("--merge-output-format", "mp4")]
        fi = partial.index("-f")
        del partial[fi:fi + 2]
        run(partial[:1] + ["--skip-download"] + partial[1:], check=False)
    info_path.unlink(missing_ok=True)

    thumb = next(iter(sorted(out.glob("video*.jpg"))), None)
    if thumb:
        thumb.replace(out / "thumbnail.jpg")
    sub_file = None
    if cap:
        sub_file = next((p for p in out.glob(f"video.{cap[0]}.*") if p.suffix in (".vtt", ".srt", ".json")), None)
    dm_file = next(iter(out.glob("video.danmaku.*")), None) if has_danmaku else None

    keep = ["id", "title", "description", "uploader", "uploader_id", "channel", "channel_follower_count",
            "upload_date", "timestamp", "duration", "view_count", "like_count", "dislike_count",
            "comment_count", "repost_count", "favorite_count", "save_count", "concurrent_view_count",
            "tags", "categories", "chapters", "track", "artist", "webpage_url", "extractor_key", "language"]
    meta = {k: info.get(k) for k in keep if info.get(k) not in (None, "", [])}
    if meta.get("description") and len(meta["description"]) > 1500:
        meta["description"] = meta["description"][:1500] + " …"
    if meta.get("chapters"):
        meta["chapters"] = [{"start": c.get("start_time"), "title": c.get("title")} for c in meta["chapters"]]
    meta.update(source_url=url, platform=plat_label)
    if media_err:
        return None, meta, (sub_file, cap), dm_file, (media_err, platform)
    return vids[0], meta, (sub_file, cap), dm_file, None


# ---------------------------------------------------------------- captions / danmaku
def parse_subs(path):
    txt = path.read_text(encoding="utf-8", errors="replace")
    segs = []
    if path.suffix == ".json":  # Bilibili JSON subtitles
        try:
            for b in json.loads(txt).get("body", []):
                segs.append({"start": float(b["from"]), "end": float(b["to"]), "text": b["content"].strip()})
            return segs
        except Exception:
            return []
    tre = re.compile(r"((?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3})\s*-->\s*((?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3})")
    prev_lines = []
    for block in re.split(r"\n\s*\n", txt.replace("\r", "")):
        lines = block.strip().split("\n")
        idx = next((i for i, l in enumerate(lines) if tre.search(l)), None)
        if idx is None:
            continue
        m = tre.search(lines[idx])
        a, b = (parse_t(x.replace(",", ".")) for x in m.groups())
        body = [re.sub(r"<[^>]+>|\{\\[^}]+\}", "", l).strip() for l in lines[idx + 1:]]
        body = [l for l in body if l]
        new = [l for l in body if l not in prev_lines]  # YouTube auto-captions roll lines forward
        prev_lines = body
        if new:
            segs.append({"start": round(a, 2), "end": round(b, 2), "text": " ".join(new)})
    merged = []
    for s in segs:
        if merged and s["text"] == merged[-1]["text"]:
            merged[-1]["end"] = s["end"]
        else:
            merged.append(s)
    return merged


def danmaku_report(path, duration):
    raw = path.read_text(encoding="utf-8", errors="replace")
    items = []
    for p, text in re.findall(r'<d p="([^"]+)"[^>]*>(.*?)</d>', raw, re.S):
        try:
            items.append((float(p.split(",")[0]), re.sub(r"\s+", " ", text).strip()))
        except ValueError:
            pass
    if not items:
        return None
    win = 10 if duration <= 300 else 30
    n = int(math.ceil(duration / win)) or 1
    buckets = [[] for _ in range(n)]
    for t, s in items:
        buckets[min(n - 1, int(t // win))].append(s)
    peaks = sorted(range(n), key=lambda i: -len(buckets[i]))[:6]
    L = [f"# Bilibili 弹幕 (bullet comments): {len(items)} total, {win}s windows", "",
         "counts per window: " + str([len(b) for b in buckets]), "", "## Peak moments"]
    for i in sorted(peaks):
        common = {}
        for s in buckets[i]:
            common[s] = common.get(s, 0) + 1
        top = sorted(common.items(), key=lambda kv: -kv[1])[:10]
        L.append(f"\n### {fmt_t(i * win)}-{fmt_t((i + 1) * win)}  ({len(buckets[i])} comments)")
        L += [f"- {s}" + (f"  ×{c}" if c > 1 else "") for s, c in top]
    return "\n".join(L) + "\n", len(items)


# ---------------------------------------------------------------- media analysis
def probe(video):
    d = json.loads(run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams",
                        "-show_format", str(video)]).stdout)
    v = next((s for s in d["streams"] if s.get("codec_type") == "video"), {})
    a = next((s for s in d["streams"] if s.get("codec_type") == "audio"), None)
    try:
        n, dd = v.get("avg_frame_rate", "0/1").split("/")
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
    return {"duration": float(d["format"].get("duration", 0) or 0), "width": w, "height": h, "fps": fps,
            "has_audio": a is not None}


def detect_shots(video, duration, threshold):
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-an",
             "-vf", f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"], check=False)
    cuts = sorted({round(float(m), 2) for m in re.findall(r"pts_time:([0-9.]+)", r.stderr or "")})
    cuts = [c for c in cuts if 0.15 < c < duration - 0.1]
    dedup = []
    for c in cuts:  # flashes/glitch effects can fire several "cuts" within a few frames
        if not dedup or c - dedup[-1] >= 0.2:
            dedup.append(c)
    cuts = dedup
    bounds = [0.0] + cuts + [duration]
    shots = [{"start": round(a, 2), "end": round(b, 2), "len": round(b - a, 2)}
             for a, b in zip(bounds, bounds[1:]) if b - a > 0]
    lengths = [s["len"] for s in shots]
    win = 10 if duration <= 180 else (30 if duration <= 900 else 60)
    stats = {
        "threshold": threshold, "cut_count": len(cuts), "shot_count": len(shots),
        "avg_shot_sec": round(sum(lengths) / len(lengths), 2) if lengths else None,
        "median_shot_sec": sorted(lengths)[len(lengths) // 2] if lengths else None,
        "longest_shot_sec": max(lengths) if lengths else None,
        "cuts_in_first_3s": sum(1 for c in cuts if c <= 3),
        "window_sec": win,
        "cuts_per_window": [sum(1 for c in cuts if i * win <= c < (i + 1) * win)
                            for i in range(int(math.ceil(duration / win)) or 1)],
    }
    return cuts, shots, stats


def detect_pauses(video, duration):
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-vn",
             "-af", "silencedetect=noise=-35dB:d=0.5", "-f", "null", "-"], check=False)
    durs = [float(x) for x in re.findall(r"silence_duration: ([0-9.]+)", r.stderr or "")]
    return {"pauses_over_0.5s": len(durs), "total_silence_sec": round(sum(durs), 1),
            "longest_pause_sec": round(max(durs), 1) if durs else 0,
            "silence_pct": round(100 * sum(durs) / max(duration, 1), 1)}


def plan_frames(start, end, cuts, budget, hook_secs, hook_step, cues):
    hook = []
    if start <= 0.05:
        t = 0.0
        while t <= min(hook_secs, end - 0.05) + 1e-6:
            hook.append(round(t, 2))
            t += hook_step
    hook_end = hook[-1] if hook else start
    room = max(8, budget - len(hook) - len(cues))
    body = [round(min(c + 0.25, end - 0.05), 2) for c in cuts if hook_end < c < end]
    step = max(0.5, (end - hook_end) / room)
    t = hook_end + step / 2
    while t < end - 0.05:
        body.append(round(t, 2))
        t += step
    thinned = []
    for t in sorted(set(body)):
        if not thinned or t - thinned[-1] >= 0.6:
            thinned.append(t)
    return hook, thinned, room


def grab(video, t, dest, width):
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video),
         "-frames:v", "1", "-vf", f"scale={width}:-2", "-q:v", "3", str(dest)], check=False)
    return dest.exists()


def thumb16(path):
    from PIL import Image
    return list(Image.open(path).convert("RGB").resize((16, 16)).getdata())


def near_dup(a, b, thr=2.0):
    diff = sum(abs(x - y) for pa, pb in zip(a, b) for x, y in zip(pa, pb))
    return diff / (16 * 16 * 3) <= thr


def load_font(size):
    from PIL import ImageFont
    for cand in ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "/System/Library/Fonts/PingFang.ttc",
                 "/System/Library/Fonts/STHeiti Medium.ttc", "C:/Windows/Fonts/msyh.ttc",
                 "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if os.path.exists(cand):
            try:
                return ImageFont.truetype(cand, size)
            except Exception:
                pass
    return ImageFont.load_default()


def contact_sheet(items, dest, cols, title, cue_set=()):
    from PIL import Image, ImageDraw
    imgs = [(t, Image.open(p).convert("RGB")) for t, p in items]
    tw, th = imgs[0][1].size
    rows = math.ceil(len(imgs) / cols)
    pad, label, head = 6, 26, 40
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, head + rows * (th + label + pad) + pad), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    font = load_font(20)
    draw.text((pad, 8), title, fill=(255, 220, 90), font=font)
    for i, (t, im) in enumerate(imgs):
        r, c = divmod(i, cols)
        x, y = pad + c * (tw + pad), head + r * (th + label + pad)
        sheet.paste(im.resize((tw, th)), (x, y + label))
        draw.text((x + 2, y + 2), fmt_t(t) + ("  ★cue" if t in cue_set else ""),
                  fill=(255, 140, 140) if t in cue_set else (255, 255, 255), font=font)
    sheet.save(dest, quality=85)


def whisper(video, out, model_name, lang):
    try:
        from faster_whisper import WhisperModel
        import numpy as np
        import wave
    except ImportError:
        return None, "faster-whisper not installed (pip install faster-whisper) -- read on-screen subtitles instead"
    wav = out / "_audio.wav"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-vn", "-ac", "1",
         "-ar", "16000", str(wav)])
    try:
        with wave.open(str(wav), "rb") as wf:  # decode ourselves: avoids PyAV version clashes
            audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        model = WhisperModel(model_name, device="auto", compute_type="int8")
        if lang == "auto":
            try:
                lang = model.detect_language(audio)[0]
            except Exception:
                lang = None
        # short VAD-split segments keep per-shot speech and density accurate
        kw = dict(vad_filter=True, vad_parameters={"max_speech_duration_s": 8}, beam_size=5, language=lang)
        if lang == "zh":
            kw["initial_prompt"] = "以下是普通话的句子，请使用简体中文和标点符号。"
        segs, info = model.transcribe(audio, **kw)
        segs = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segs]
        return {"segments": segs, "language": info.language, "source": f"faster-whisper ({model_name})"}, None
    except Exception as e:
        return None, f"transcription failed: {e}"
    finally:
        wav.unlink(missing_ok=True)


def slice_text(seg, a, b):
    """The part of a segment's text spoken between a and b, assuming an even speaking rate."""
    span = seg["end"] - seg["start"]
    text = seg["text"]
    if span <= 0 or (a <= seg["start"] and b >= seg["end"]):
        return text
    cjk = speech_units(text)[1] == "chars"
    toks = list(text) if cjk else text.split()
    i0 = round(max(0.0, (a - seg["start"]) / span) * len(toks))
    i1 = round(min(1.0, (b - seg["start"]) / span) * len(toks))
    return ("" if cjk else " ").join(toks[i0:i1]).strip()


def density(segs, duration, win):
    n = int(math.ceil(duration / win)) or 1
    units = [0.0] * n
    unit_name = "chars"
    total = 0
    for s in segs:
        u, unit_name = speech_units(s["text"])
        total += u
        a, b = s["start"], max(s["end"], s["start"] + 0.01)
        for i in range(int(a // win), min(n, int(b // win) + 1)):
            ov = min(b, (i + 1) * win) - max(a, i * win)
            if ov > 0:
                units[i] += u * ov / (b - a)
    per_min = [round(u * 60 / win) for u in units]
    return total, unit_name, per_min


def ratios(meta):
    like = meta.get("like_count") or 0
    views = meta.get("view_count") or 0
    out = {}
    for k, label in [("comment_count", "评论/点赞 comments/likes"), ("repost_count", "转发/点赞 shares/likes"),
                     ("favorite_count", "收藏/点赞 saves/likes"), ("save_count", "收藏/点赞 saves/likes")]:
        if like and meta.get(k) is not None:
            out[label] = f"{meta[k] / like:.1%}"
    if views and like:
        out["点赞/播放 likes/views"] = f"{like / views:.2%}"
    if views and meta.get("comment_count") is not None:
        out["评论/播放 comments/views"] = f"{meta['comment_count'] / views:.2%}"
    fol = meta.get("channel_follower_count")
    if fol:
        if views:
            out["播放/粉丝 views/followers"] = f"{views / fol:.2f}x"
        elif like:
            out["点赞/粉丝 likes/followers"] = f"{like / fol:.2f}x"
    ts = meta.get("timestamp")
    if not ts and meta.get("upload_date"):
        try:
            ts = time.mktime(time.strptime(meta["upload_date"], "%Y%m%d"))
        except Exception:
            ts = None
    if ts:
        days = max(1.0, (time.time() - ts) / 86400)
        out["发布天数 days live"] = f"{days:.0f}"
        if views:
            out["日均播放 views/day"] = f"{views / days:,.0f}"
    return out


def save_transcript(out, tr):
    (out / "transcript.json").write_text(json.dumps(tr, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "transcript.txt").write_text("\n".join(
        f"[{fmt_t(s['start'])}-{fmt_t(s['end'])}] {s['text']}" for s in tr["segments"]) + "\n", encoding="utf-8")


def partial_exit(out, meta, sub, fail):
    """Video file blocked, but metadata (and maybe captions/cover) arrived: save them, then exit 2."""
    err, platform = fail
    sub_file, cap = sub
    have = ["meta.json"]
    if sub_file and sub_file.exists():
        segs = parse_subs(sub_file)
        sub_file.unlink(missing_ok=True)
        if segs:
            save_transcript(out, {"segments": segs, "language": cap[0],
                                  "source": f"platform captions ({cap[1]}, {cap[0]}, {cap[2]})"})
            have.append("transcript.txt")
    if (out / "thumbnail.jpg").exists():
        have.append("thumbnail.jpg")
    L = ["# Video prep summary -- PARTIAL (video file could not be downloaded)", "",
         "No frames: visuals, shots and editing cannot be analysed yet. Available: " + ", ".join(have), "",
         f"## Metadata ({meta.get('platform')})", ""]
    L += [f"- **{k}**: {meta[k]}" for k in ["title", "uploader", "channel_follower_count", "upload_date",
                                            "duration", "view_count", "like_count", "comment_count",
                                            "repost_count", "favorite_count", "tags", "source_url"] if k in meta]
    r = ratios(meta)
    if r:
        L += ["", "Engagement: " + " · ".join(f"{k} {v}" for k, v in r.items())]
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print((err or "").strip()[-800:], file=sys.stderr)
    print(failure_help(err, platform))
    print("PARTIAL_EVIDENCE saved in", out, "->", ", ".join(["summary.md"] + have))
    sys.exit(2)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="pasted share text, a URL, or a local video path")
    ap.add_argument("--out", default="./video-breakdown", help="working directory (re-runs reuse it)")
    ap.add_argument("--cookies", help="Netscape cookies.txt")
    ap.add_argument("--cookies-from-browser", dest="browser", help="chrome / edge / safari / firefox[:profile]")
    ap.add_argument("--max-frames", type=int, help="frame budget (default scales with duration: 48-120)")
    ap.add_argument("--hook-secs", type=float, help="opening window sampled densely (default 5s, 15s if >3min)")
    ap.add_argument("--start", help="focus window start (SS, MM:SS, HH:MM:SS)")
    ap.add_argument("--end", help="focus window end")
    ap.add_argument("--timestamps", help="comma-separated moments to always capture, e.g. 0:12,1:05")
    ap.add_argument("--no-dedup", action="store_true", help="keep near-identical frames")
    ap.add_argument("--scene-threshold", type=float, default=0.3, help="cut sensitivity 0-1 (lower = more cuts)")
    ap.add_argument("--frame-width", type=int, help="tile width px (default 360 vertical / 480 horizontal)")
    ap.add_argument("--sub-lang", default="auto", help="caption language to prefer (default: spoken language)")
    ap.add_argument("--no-captions", action="store_true", help="ignore platform captions, use whisper")
    ap.add_argument("--no-transcribe", action="store_true", help="no whisper fallback")
    ap.add_argument("--whisper-model", default="small", help="tiny/base/small/medium/large-v3")
    ap.add_argument("--lang", default="auto", help="spoken-language hint for whisper (zh, en, ja...)")
    ap.add_argument("--keep-video", action="store_true", help="keep the downloaded video for later re-runs")
    a = ap.parse_args()

    need("ffmpeg")
    need("ffprobe")
    out = Path(a.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    kind, src = resolve_input(a.input)

    meta, sub, dm_file = {}, (None, None), None
    existing = [p for p in out.glob("video.*") if p.suffix.lower() in VIDEO_EXTS]
    if kind == "url" and existing:
        video = existing[0]
        print(f"[1/6] reusing {video.name} already in {out}")
        if (out / "meta.json").exists():
            meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    elif kind == "url":
        print(f"[1/6] fetching {src}  ({platform_of(src)[1]})")
        video, meta, sub, dm_file, fail = fetch(src, out, a.cookies, a.browser, a.sub_lang, not a.no_captions)
        (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        if fail:
            partial_exit(out, meta, sub, fail)
    else:
        video = src
        print(f"[1/6] using local file {video}")

    spec = probe(video)
    dur = spec["duration"]
    if dur <= 0:
        print("ERROR: could not read the video duration (broken file or not a video).", file=sys.stderr)
        sys.exit(3)
    vertical = spec["height"] >= spec["width"]
    start = max(0.0, parse_t(a.start) or 0.0)
    end = min(dur, parse_t(a.end) or dur)
    if end <= start:
        print("ERROR: --end must be after --start.", file=sys.stderr)
        sys.exit(3)
    span = end - start
    budget = a.max_frames or (48 if span <= 60 else 72 if span <= 180 else 100 if span <= 600 else 120)
    long_form = dur > 180
    hook_secs = a.hook_secs if a.hook_secs is not None else (15 if long_form else 5)
    hook_step = 1.0 if long_form else 0.5
    width = a.frame_width or (360 if vertical else 480)
    cues = sorted({round(min(max(parse_t(x), 0), dur - 0.05), 2)
                   for x in (a.timestamps or "").split(",") if x.strip()})

    print("[2/6] detecting cuts and pauses")
    cuts, shots, shot_stats = detect_shots(video, dur, a.scene_threshold)
    pauses = detect_pauses(video, dur) if spec["has_audio"] else None

    print("[3/6] sampling frames")
    frames_dir, sheets_dir = out / "frames", out / "sheets"
    for d in (frames_dir, sheets_dir):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir()
    hook_ts, body_ts, room = plan_frames(start, end, cuts, budget, hook_secs, hook_step, cues)

    def path_for(t):
        return frames_dir / f"t_{int(t // 60):02d}m{t % 60:05.2f}s.jpg"

    got_hook = [(t, path_for(t)) for t in hook_ts if grab(video, t, path_for(t), width)]
    got_body = [(t, path_for(t)) for t in body_ts if grab(video, t, path_for(t), width)]
    dropped = 0
    if not a.no_dedup and got_body:
        try:
            kept, last = [], None
            for t, p in got_body:
                th = thumb16(p)
                if last is not None and near_dup(th, last):
                    p.unlink(missing_ok=True)
                    dropped += 1
                    continue
                kept.append((t, p))
                last = th
            got_body = kept
        except Exception:
            pass
    if len(got_body) > room:  # downsample evenly to the budget
        idx = sorted({round(i * (len(got_body) - 1) / (room - 1)) for i in range(room)})
        keep = {got_body[i][0] for i in idx}
        for t, p in got_body:
            if t not in keep:
                p.unlink(missing_ok=True)
        got_body = [x for x in got_body if x[0] in keep]
    got_cues = [(t, path_for(t)) for t in cues if grab(video, t, path_for(t), width)]
    timeline = sorted({t: (t, p) for t, p in got_body + got_cues}.values())

    print("[4/6] building contact sheets")
    sheets = []
    cols_hook = 5 if vertical else 4
    if got_hook:
        contact_sheet(got_hook, sheets_dir / "hook.jpg", cols_hook,
                      f"OPENING 0:00-{fmt_t(hook_ts[-1])}  (every {hook_step:g}s)")
        sheets.append("sheets/hook.jpg")
    per, cols = (12, 4) if vertical else (12, 3)
    cue_set = set(cues)
    for i in range(0, len(timeline), per):
        chunk = timeline[i:i + per]
        name = f"sheet_{i // per + 1:02d}.jpg"
        contact_sheet(chunk, sheets_dir / name, cols, f"{fmt_t(chunk[0][0])} - {fmt_t(chunk[-1][0])}", cue_set)
        sheets.append(f"sheets/{name}")

    print("[5/6] transcript")
    tr, tr_note = None, None
    sub_file, cap = sub
    if (out / "transcript.json").exists() and kind == "url" and existing:
        tr = json.loads((out / "transcript.json").read_text(encoding="utf-8"))
    elif sub_file and sub_file.exists():
        segs = parse_subs(sub_file)
        if segs:
            tr = {"segments": segs, "language": cap[0],
                  "source": f"platform captions ({cap[1]}, {cap[0]}, {cap[2]})"}
        sub_file.unlink(missing_ok=True)
    if tr is None and not a.no_transcribe and spec["has_audio"]:
        print("      no usable captions -> faster-whisper (first run downloads the model)")
        tr, tr_note = whisper(video, out, a.whisper_model, a.lang)
    elif tr is None:
        tr_note = "video has no audio track" if not spec["has_audio"] else "skipped (--no-transcribe)"
    if tr:
        save_transcript(out, tr)

    dm = None
    if dm_file and dm_file.exists():
        res = danmaku_report(dm_file, dur)
        if res:
            (out / "danmaku.txt").write_text(res[0], encoding="utf-8")
            dm = res[1]
        dm_file.unlink(missing_ok=True)

    print("[6/6] shot list + summary")
    segs = tr["segments"] if tr else []
    frame_ts = sorted(t for t, _ in got_hook + timeline)
    for s in shots:
        inside = [t for t in frame_ts if s["start"] <= t < s["end"]]
        mid = (s["start"] + s["end"]) / 2
        s["frame"] = path_for(min(inside, key=lambda t: abs(t - mid))).name if inside else None
        s["speech"] = " ".join(filter(None, (slice_text(x, s["start"], s["end"]) for x in segs
                                             if x["start"] < s["end"] and x["end"] > s["start"])))
    (out / "shots.json").write_text(json.dumps({"cuts": cuts, "shots": shots, **shot_stats},
                                               ensure_ascii=False, indent=1), encoding="utf-8")
    SL = ["# 分镜表 skeleton (auto)", "",
          "Time/length/frame/speech are pre-filled. Fill 景别 (shot size), 运镜 (camera move), 画面 (what's on "
          "screen), 字幕/花字 (on-screen text), 转场 (transition) and 作用 (job in the script) by looking at the frames.",
          "Cut detection is approximate: merge or split rows when the frames disagree.", "",
          "| # | time | len | frame | speech | 景别 | 运镜 | 画面 | 字幕/花字 | 转场 | 作用 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, s in enumerate(shots[:150], 1):
        sp = (s["speech"][:60] + "…") if len(s["speech"]) > 60 else s["speech"]
        SL.append(f"| {i} | {fmt_t(s['start'])}-{fmt_t(s['end'])} | {s['len']}s | {s['frame'] or '-'} | "
                  f"{sp.replace('|', '/')} | | | | | | |")
    if len(shots) > 150:
        SL.append(f"\n_{len(shots) - 150} more shots omitted -- group them by section instead of per shot._")
    (out / "shotlist.md").write_text("\n".join(SL) + "\n", encoding="utf-8")

    # ------------------------------------------------ summary.md
    L = ["# Video prep summary", ""]
    if meta:
        L += [f"## Metadata ({meta.get('platform', 'platform')})", ""]
        for k in ["title", "uploader", "channel_follower_count", "upload_date", "view_count", "like_count",
                  "comment_count", "repost_count", "favorite_count", "save_count", "tags", "categories",
                  "track", "source_url"]:
            if k in meta:
                L.append(f"- **{k}**: {meta[k]}")
        if meta.get("description"):
            L.append(f"- **description**: {meta['description'][:400]}")
        if meta.get("chapters"):
            L.append("- **chapters**: " + " · ".join(f"{fmt_t(c['start'] or 0)} {c['title']}" for c in meta["chapters"]))
        r = ratios(meta)
        if r:
            L += ["", "Engagement: " + " · ".join(f"{k} {v}" for k, v in r.items())]
        missing = [k for k in ["view_count", "like_count", "comment_count", "repost_count", "favorite_count"]
                   if k not in meta]
        if missing:
            L += ["", f"_Not provided by the platform: {', '.join(missing)} -- ask the user if they matter._"]
        if (out / "thumbnail.jpg").exists():
            L.append("- cover/thumbnail saved: thumbnail.jpg")
    else:
        L += ["## Metadata", "", "_Local file: no platform stats. Ask for views/likes/comments/saves/shares, "
              "post date and follower count if the 传播 section should be grounded in data._"]
    L += ["", "## Specs", "",
          f"- duration {fmt_t(dur)} ({dur:.1f}s), {spec['width']}x{spec['height']} "
          f"{'vertical' if vertical else 'horizontal'}, {spec['fps']} fps, audio: {'yes' if spec['has_audio'] else 'no'}",
          f"- frames read: {len(got_hook)} opening + {len(timeline)} timeline"
          + (f" ({dropped} near-duplicates removed)" if dropped else "")
          + (f", {len(got_cues)} cue frames ★" if got_cues else "")
          + (f"; focus window {fmt_t(start)}-{fmt_t(end)}" if (start > 0 or end < dur) else ""),
          "", "## Edit rhythm (automatic cut detection -- approximate)", "",
          f"- {shot_stats['shot_count']} shots, average {shot_stats['avg_shot_sec']}s, median "
          f"{shot_stats['median_shot_sec']}s, longest {shot_stats['longest_shot_sec']}s, "
          f"{shot_stats['cuts_in_first_3s']} cuts in the first 3s",
          f"- cuts per {shot_stats['window_sec']}s window: {shot_stats['cuts_per_window']}",
          "- talking-head jump cuts / punch-in zooms may under-detect; heavy transitions may over-detect. "
          "Trust the frames over the numbers. Per-shot rows: shotlist.md"]
    if pauses:
        L += ["", "## Audio pauses (silencedetect, -35 dB, ≥0.5s)", "",
              f"- {pauses['pauses_over_0.5s']} pauses, {pauses['total_silence_sec']}s total "
              f"({pauses['silence_pct']}% of runtime), longest {pauses['longest_pause_sec']}s",
              "- background music masks pauses, so near-zero silence can mean wall-to-wall BGM, not tight editing."]
    L += ["", "## Transcript", ""]
    if tr:
        total, unit, per_min = density(tr["segments"], dur, shot_stats["window_sec"])
        L += [f"- source: {tr['source']}; language {tr.get('language')}; {len(tr['segments'])} segments, "
              f"~{total} {unit} (≈{total * 60 / max(dur, 1):.0f} {unit}/min overall)",
              f"- speech density per {shot_stats['window_sec']}s window ({unit}/min): {per_min}"]
        if "whisper" in tr["source"]:
            L.append("- whisper mishears names/numbers/slang: cross-check against on-screen subtitles")
    else:
        L.append(f"- none: {tr_note}. Read burned-in subtitles / on-screen text from the frames.")
    if dm:
        L.append(f"- Bilibili 弹幕: {dm} bullet comments, peaks in danmaku.txt")
    L += ["", "## Files to read", "", *[f"- {s}" for s in sheets]]
    if (out / "thumbnail.jpg").exists():
        L.append("- thumbnail.jpg (cover)")
    L += [f"- frames/ (open single frames for detail)", "- shotlist.md, shots.json"]
    if tr:
        L.append("- transcript.txt")
    if dm:
        L.append("- danmaku.txt")
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    if kind == "url" and not a.keep_video:
        video.unlink(missing_ok=True)
    print(f"\nDONE -> {out}/summary.md\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
