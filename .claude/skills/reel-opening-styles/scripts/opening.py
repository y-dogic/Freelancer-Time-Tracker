#!/usr/bin/env python3
"""Build a reel opening in one of 6 styles and splice it onto the reel.

Steps (run in order; WORK is a folder for this reel, e.g. edit/<id>/opening):
  setup    --remotion DIR                      copy the Opening composition into a Remotion project (creates one if missing)
  analyze  VIDEO --work WORK [--seconds 6]     1080x1920 clip of the first seconds, face box, background, fit ranking
  words    --work WORK                         word timings (faster-whisper if installed) + speech phrases (always)
  matte    --work WORK [--width 1080]          cut the person out (rembg u2net_human_seg) -> matte.webm + check.jpg
  props    --work WORK --hook hook.json        merge the hook (texts, beat times) with the analysis -> props.json
  preview  --work WORK --remotion DIR          one still per style (pain beat + promise beat) -> preview.jpg (6 columns)
  render   --work WORK --remotion DIR --style N --source VIDEO --out OUT.mp4
                                               render the opening, splice it over the reel's first seconds, keep the audio
"""
import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets" / "remotion"
W, H, FPS = 1080, 1920, 30
STYLE_NAMES = {
    1: "Darkened bg + circle mask -> sticker cut-out",
    2: "Cut-out on themed bg + torn-paper reveal",
    3: "Spotlight + big word behind the head",
    4: "Black poster: type hierarchy + rect->circle mask",
    5: "Flash-in text + face focus",
    6: "TV texture + typed (vertical) text",
}
NEEDS_MATTE = {1: "recommended", 2: "required", 3: "required for text-behind-head"}


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), file=sys.stderr)
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:stream_side_data=rotation:format=duration", "-of", "json", str(path)],
        check=True, capture_output=True, text=True).stdout
    d = json.loads(out)
    s = d["streams"][0]
    rot = 0
    for sd in s.get("side_data_list", []) or []:
        rot = int(sd.get("rotation", 0) or 0)
    w, h = s["width"], s["height"]
    if abs(rot) in (90, 270):
        w, h = h, w
    return {"width": w, "height": h, "duration": float(d["format"]["duration"])}


def load(work):
    p = Path(work) / "analysis.json"
    if not p.exists():
        sys.exit(f"no {p}: run analyze first")
    return json.loads(p.read_text())


def save(work, data):
    p = Path(work) / "analysis.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    tmp.replace(p)


def update(work, **keys):
    """Re-read analysis.json and set only these keys, so steps run in parallel (matte, props) don't clobber each other."""
    d = load(work)
    d.update(keys)
    save(work, d)


VF_COVER = f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},fps={FPS},setsar=1"


# ---------------- setup ----------------
def cmd_setup(a):
    rd = Path(a.remotion).resolve()
    if not (rd / "package.json").exists():
        rd.mkdir(parents=True, exist_ok=True)
        ver = "4.0.526"
        (rd / "package.json").write_text(json.dumps({
            "name": "reel-openings", "private": True, "version": "1.0.0",
            "dependencies": {"remotion": ver, "@remotion/cli": ver, "react": "19.2.3", "react-dom": "19.2.3"},
            "devDependencies": {"@types/react": "19.2.7", "typescript": "5.9.3"}}, indent=2))
        (rd / "tsconfig.json").write_text(json.dumps({"compilerOptions": {
            "target": "ES2022", "module": "ES2022", "moduleResolution": "bundler", "jsx": "react-jsx",
            "strict": True, "skipLibCheck": True, "esModuleInterop": True}}, indent=2))
        (rd / "public").mkdir(exist_ok=True)
        run(["npm", "install", "--no-audit", "--no-fund"], cwd=rd)
    dst = rd / "src" / "opening"
    dst.mkdir(parents=True, exist_ok=True)
    for f in ASSETS.iterdir():
        shutil.copy2(f, dst / f.name)
    (rd / "public" / "opening").mkdir(parents=True, exist_ok=True)
    fetch_fonts(rd / "public" / "opening" / "fonts", a.script)
    print(f"Opening composition installed in {dst}")


FONT_FAMILIES = {"tc": "TC", "sc": "SC", "hk": "HK", "jp": "JP", "kr": "KR"}


def fetch_fonts(dest, script):
    """Full TTFs from Google Fonts (a plain user agent gets one file per weight, not 100 subsets).
    Local files render reliably offline and behind proxies; the browser never fetches fonts."""
    import re
    import urllib.request
    dest.mkdir(parents=True, exist_ok=True)
    suf = FONT_FAMILIES.get(script, "TC")
    want = {"sans-700": (f"Noto+Sans+{suf}", 700), "sans-900": (f"Noto+Sans+{suf}", 900),
            "serif-900": (f"Noto+Serif+{suf}", 900)}
    stamp = dest / "script.txt"
    if stamp.exists() and stamp.read_text().strip() == suf and all((dest / f"{k}.ttf").exists() for k in want):
        return

    def get(url):
        if shutil.which("curl"):
            return subprocess.run(["curl", "-sSfL", "-A", "fetch", url], check=True, capture_output=True).stdout
        return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "fetch"})).read()

    for key, (fam, wt) in want.items():
        css = get(f"https://fonts.googleapis.com/css2?family={fam}:wght@{wt}").decode()
        urls = re.findall(r"url\((https://[^)]+\.ttf)\)", css)
        if not urls:
            sys.exit(f"could not get a .ttf for {fam} {wt}; put the font at {dest / (key + '.ttf')} by hand")
        (dest / f"{key}.ttf").write_bytes(get(urls[0]))
        print(f"font {key}: {fam.replace('+', ' ')} {wt}", file=sys.stderr)
    stamp.write_text(suf)


# ---------------- analyze ----------------
def cmd_analyze(a):
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    info = probe(a.video)
    secs = min(a.seconds, info["duration"])
    clip = work / "clip.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-t", f"{secs:.3f}", "-vf", VF_COVER,
         "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", clip])
    frames = work / "frames"
    shutil.rmtree(frames, ignore_errors=True)
    frames.mkdir()
    run(["ffmpeg", "-v", "error", "-i", clip, "-vf", "fps=4", "-q:v", "3", frames / "f_%03d.jpg"])
    run(["ffmpeg", "-v", "error", "-y", "-i", clip, "-vf", f"fps=12/{secs:.3f},scale=180:320,tile=6x2",
         "-frames:v", "1", work / "sheet.jpg"])

    face, bg, notes = None, {}, []
    try:
        import cv2  # noqa
        if not hasattr(cv2, "CascadeClassifier"):
            raise ImportError
        face, bg = measure(sorted(frames.glob("*.jpg")))
    except ImportError:
        notes.append('OpenCV 4 missing (pip install "opencv-python-headless<5"; 5.x has no face cascade): '
                     "face box guessed, fit ranking is rough")
    if face is None:
        face = {"cx": 540, "cy": 760, "w": 300, "h": 380, "guessed": True}
        notes.append("no face found: face box guessed; check sheet.jpg and pass face manually in hook.json")

    data = {
        "source": str(Path(a.video).resolve()), "source_size": [info["width"], info["height"]],
        "source_duration": info["duration"], "clip_seconds": secs, "clip": str(clip.resolve()),
        "face": face, "background": bg, "notes": notes,
    }
    data["fit"] = rank(data)
    save(work, data)
    print_rank(data)


def measure(paths):
    import cv2
    import numpy as np
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    boxes, lum, busy, top_busy, warm = [], [], [], [], []
    for p in paths:
        img = cv2.imread(str(p))
        if img is None:
            continue
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(g, (W // 2, H // 2))
        fs = casc.detectMultiScale(small, 1.1, 6, minSize=(60, 60))
        if len(fs):
            x, y, w, h = max(fs, key=lambda b: b[2] * b[3])  # half-res box
            boxes.append(tuple(int(v) for v in (2 * x + w, 2 * y + h, 2 * w, 2 * h)))  # full-res center x, center y, width, height
        lum.append(float(g.mean()))
        # edges on a fixed 540x960 copy so the number doesn't depend on the source resolution
        edges = cv2.Canny(cv2.GaussianBlur(small, (3, 3), 0), 50, 130)
        busy.append(float(edges.mean() / 255))
        top_busy.append(float(edges[: edges.shape[0] // 3].mean() / 255))  # mostly background above the head
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        warm.append(float(hsv[..., 1].mean()))
    face = None
    if boxes:
        med = lambda i: round(float(statistics.median([b[i] for b in boxes])), 1)  # noqa: E731
        # Haar boxes are tight (brows to mouth); the layouts expect hair-to-chin, so widen the height
        face = {"cx": med(0), "cy": med(1), "w": med(2), "h": round(med(3) * 1.25, 1),
                "samples": len(boxes), "of": len(paths)}
    bg = {
        "luma": round(statistics.mean(lum), 1) if lum else None,
        "edge_density": round(statistics.mean(busy), 4) if busy else None,
        "top_edge_density": round(statistics.mean(top_busy), 4) if top_busy else None,
        "saturation": round(statistics.mean(warm), 1) if warm else None,
    }
    return face, bg


def rank(d):
    f, bg = d["face"], d.get("background") or {}
    head_top = f["cy"] - f["h"] / 2
    headroom = head_top - 60 - 250
    # top third of the frame (background above the head); calibrated: plain room ~0.018, bookshelf ~0.044
    busy = bg.get("top_edge_density") or 0.028
    luma = bg.get("luma") or 110
    src_h = min(d["source_size"])  # short side
    face_ratio = f["h"] / H
    sc = {s: 50.0 for s in range(1, 7)}
    why = {s: [] for s in range(1, 7)}

    def add(s, v, msg):
        sc[s] += v
        why[s].append(("+" if v >= 0 else "") + f"{v:.0f} {msg}")

    if busy > 0.034:
        add(2, 18, "busy background gets replaced"); add(4, 16, "busy background hidden by black poster")
        add(1, 8, "darkening calms a busy background"); add(5, -8, "busy background stays visible")
        add(3, -10, "text behind head needs a calm wall")
    elif busy < 0.023:
        add(3, 14, "calm background suits text behind the head"); add(5, 10, "clean footage needs little treatment")
        add(6, 6, "clean frame takes the TV texture well")
    if luma > 150:
        add(3, -6, "bright frame: spotlight looks weaker"); add(1, 4, "darkening adds mood to a bright frame")
    if luma < 70:
        add(1, -6, "frame already dark"); add(3, 6, "dark frame suits a spotlight")
    if headroom < 200:
        add(3, 10, "little room above the head: word behind the head uses that space")
        add(1, -4, "text must move to the chest zone")
    else:
        add(1, 4, "room above the head for the text"); add(2, 4, "room above the head for the text")
    if face_ratio > 0.24:
        add(4, 8, "close-up crops well into the window"); add(5, 8, "close-up face: focus effect reads strongly")
        add(2, -6, "tight close-up leaves little background to swap")
    elif face_ratio < 0.14:
        add(4, 6, "wide shot: the mask window brings the face closer"); add(5, -8, "small face: focus effect is weak")
        add(1, 6, "wide shot: circle mask frames the person")
    if src_h < 1000:
        add(4, -6, "low resolution: the window upscales"); add(6, 8, "TV texture hides low resolution")
    if f.get("guessed"):
        for s in (1, 3, 5):
            add(s, -10, "face position unknown")
    for s, m in NEEDS_MATTE.items():
        if m == "required":
            why[s].append(f"needs a person cut-out (~{max(1, round(d['clip_seconds'] * 30 / 60))} min with rembg)")
    order = sorted(sc, key=lambda s: -sc[s])
    return [{"style": s, "name": STYLE_NAMES[s], "score": round(sc[s]), "why": why[s]} for s in order]


def print_rank(d):
    f = d["face"]
    print(f"\nclip: {d['clip']}  ({d['clip_seconds']:.1f}s)  source {d['source_size'][0]}x{d['source_size'][1]}")
    print(f"face: cx {f['cx']} cy {f['cy']} h {f['h']}" + ("  (GUESSED)" if f.get("guessed") else ""))
    print(f"background: {d['background']}")
    for n in d.get("notes", []):
        print("note:", n)
    print("\nFit ranking (heuristic; confirm by looking at preview.jpg):")
    for r in d["fit"]:
        print(f"  {r['score']:>3}  Style {r['style']}: {r['name']}")
        for w in r["why"]:
            print(f"         {w}")


# ---------------- words ----------------
def cmd_words(a):
    d = load(a.work)
    clip = d["clip"]
    out = {"phrases": [], "words": []}
    sd = subprocess.run(["ffmpeg", "-v", "info", "-i", clip, "-af", "silencedetect=n=-32dB:d=0.18", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    t, starts = 0.0, []
    for line in sd.splitlines():
        if "silence_end" in line:
            starts.append(float(line.split("silence_end:")[1].split("|")[0]))
    out["phrase_starts"] = [0.0] + [round(s, 2) for s in starts if s < d["clip_seconds"]]
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(a.model, device="cpu", compute_type="int8")
        import numpy as np
        pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", clip, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                             check=True, capture_output=True).stdout  # decode with ffmpeg: PyAV versions vary
        segs, _ = model.transcribe(np.frombuffer(pcm, np.float32), word_timestamps=True, language=a.language)
        for s in segs:
            out["phrases"].append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()})
            for w in s.words or []:
                out["words"].append({"w": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2)})
    except ImportError:
        out["note"] = "faster-whisper not installed: only phrase starts from silence detection"
    (Path(a.work) / "words.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps(out, ensure_ascii=False, indent=1)[:4000])


# ---------------- matte ----------------
def cmd_matte(a):
    d = load(a.work)
    work = Path(a.work)
    if not shutil.which("rembg"):
        sys.exit('rembg missing: pip install "rembg[cpu,cli]" && rembg d u2net_human_seg')
    with tempfile.TemporaryDirectory() as td:
        fin, fout = Path(td) / "in", Path(td) / "out"
        fin.mkdir(); fout.mkdir()
        run(["ffmpeg", "-v", "error", "-i", d["clip"], "-vf", f"scale={a.width}:-2", "-q:v", "2", fin / "f_%04d.jpg"])
        n = len(list(fin.glob("*.jpg")))
        print(f"cutting out {n} frames (~1 s per frame on CPU)...", file=sys.stderr)
        run(["rembg", "p", "-m", "u2net_human_seg", fin, fout])
        webm = work / "matte.webm"
        chain = (f"scale={W}:{H},split[c][a];[a]alphaextract,erosion,gblur=sigma=0.8,"
                 "tmix=frames=3:weights='1 2 1',trim=start_frame=1,setpts=PTS-STARTPTS,tpad=stop=1:stop_mode=clone[m];"
                 "[c][m]alphamerge,format=yuva420p")
        run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", fout / "f_%04d.png", "-filter_complex", chain,
             "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "3M", webm])
    mid = d["clip_seconds"] / 2
    run(["ffmpeg", "-v", "error", "-y", "-c:v", "libvpx-vp9", "-ss", f"{mid:.2f}", "-i", webm,
         "-f", "lavfi", "-i", f"color=white:s={W}x{H}", "-f", "lavfi", "-i", f"color=0x202020:s={W}x{H}",
         "-filter_complex", "[0:v]split[a][b];[1:v][a]overlay=format=auto[l];[2:v][b]overlay=format=auto[r];"
                            "[l][r]hstack,scale=1080:-2", "-frames:v", "1", work / "check.jpg"])
    update(a.work, matte=str(webm.resolve()))
    print(f"matte: {webm}\ncheck frame (look for furniture/wall stuck to the person): {work / 'check.jpg'}")


# ---------------- props ----------------
def cmd_props(a):
    d = load(a.work)
    hook = json.loads(Path(a.hook).read_text())
    for k in ("topic", "pain", "promise"):
        if k not in hook:
            sys.exit(f"hook.json needs '{k}'")
    dur = hook.get("durationSec") or round(hook["promise"]["at"] + 2.0, 2)
    dur = min(dur, d["clip_seconds"])
    props = {
        "style": hook.get("style", 1),
        "durationSec": dur,
        "topic": hook["topic"], "pain": hook["pain"], "promise": hook["promise"],
        "face": hook.get("face") or {k: d["face"][k] for k in ("cx", "cy", "w", "h")},
    }
    for k in ("accent", "ink", "vertical", "background"):
        if k in hook:
            props[k] = hook[k]
    update(a.work, props=props)
    print(json.dumps(props, ensure_ascii=False, indent=1))


def stage(d, rd, work):
    """Copy clip/matte/background into public/opening/<name>/ and return props with public paths."""
    name = Path(work).resolve().parent.name + "-" + Path(work).resolve().name
    pub = Path(rd) / "public" / "opening" / name
    pub.mkdir(parents=True, exist_ok=True)
    props = dict(d["props"])
    shutil.copy2(d["clip"], pub / "clip.mp4")
    props["clip"] = f"opening/{name}/clip.mp4"
    if d.get("matte") and Path(d["matte"]).exists():
        shutil.copy2(d["matte"], pub / "matte.webm")
        props["matte"] = f"opening/{name}/matte.webm"
    if props.get("background"):
        src = Path(props["background"])
        shutil.copy2(src, pub / ("bg" + src.suffix))
        props["background"] = f"opening/{name}/bg{src.suffix}"
    return props


def write_props(work, props, style):
    p = dict(props); p["style"] = style
    path = Path(work).resolve() / f"props-style{style}.json"
    path.write_text(json.dumps(p, ensure_ascii=False, indent=1))
    return path


# ---------------- preview ----------------
def cmd_preview(a):
    d = load(a.work)
    if "props" not in d:
        sys.exit("run props first")
    rd = Path(a.remotion).resolve()
    props = stage(d, rd, a.work)
    pr = props["promise"]["at"]
    pa = props["pain"]["at"]
    f_pain = int(round(((pa + pr) / 2) * FPS))
    f_prom = int(round(min(props["durationSec"] - 0.1, pr + 0.7) * FPS))
    styles = [int(s) for s in (a.styles.split(",") if a.styles else range(1, 7))]
    out = Path(a.work).resolve() / "preview"
    out.mkdir(exist_ok=True)
    tiles = []
    for s in styles:
        pp = write_props(a.work, props, s)
        for tag, fr in (("a", f_pain), ("b", f_prom)):
            png = out / f"s{s}{tag}.png"
            run(["npx", "remotion", "still", "src/opening/index.tsx", "Opening", png, f"--frame={fr}",
                 f"--props={pp}", "--scale=0.5", "--log=error"], cwd=rd)
            tiles.append(png)
    grid(tiles, styles, Path(a.work) / "preview.jpg", props)
    print(f"preview: {Path(a.work) / 'preview.jpg'}  (top row: pain beat, bottom row: promise beat)")


def grid(tiles, styles, dest, props):
    from PIL import Image, ImageDraw, ImageFont
    tw, th = 270, 480
    n = len(styles)
    img = Image.new("RGB", (n * (tw + 12) + 12, 2 * (th + 12) + 70), (24, 24, 24))
    dr = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    for i, s in enumerate(styles):
        x = 12 + i * (tw + 12)
        dr.text((x + 4, 18), f"Style {s}", fill=(255, 255, 255), font=font)
        for r, tag in enumerate("ab"):
            t = Image.open([p for p in tiles if p.name == f"s{s}{tag}.png"][0]).convert("RGB").resize((tw, th))
            img.paste(t, (x, 58 + r * (th + 12)))
    img.save(dest, quality=88)


# ---------------- render ----------------
def cmd_render(a):
    d = load(a.work)
    rd = Path(a.remotion).resolve()
    props = stage(d, rd, a.work)
    pp = write_props(a.work, props, a.style)
    op = Path(a.work).resolve() / f"opening-style{a.style}.mp4"
    run(["npx", "remotion", "render", "src/opening/index.tsx", "Opening", op, f"--props={pp}", "--muted",
         "--crf=16", "--log=error"], cwd=rd)
    dur = props["durationSec"]
    src = a.source or d["source"]
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fc = (f"[1:v]trim=start={dur:.4f},setpts=PTS-STARTPTS,{VF_COVER}[rest];"
          f"[0:v]fps={FPS},setsar=1[op];[op][rest]concat=n=2:v=1:a=0[v]")
    run(["ffmpeg", "-v", "error", "-y", "-i", op, "-i", src, "-filter_complex", fc, "-map", "[v]", "-map", "1:a:0?",
         "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k",
         "-movflags", "+faststart", "-shortest", out])
    sheet = out.with_suffix(".sheet.jpg")
    run(["ffmpeg", "-v", "error", "-y", "-i", out, "-t", f"{dur + 1:.2f}", "-vf",
         f"fps=12/{dur + 1:.2f},scale=180:320,tile=6x2", "-frames:v", "1", sheet])
    print(f"opening only: {op}\nreel with new opening: {out}\nopening contact sheet: {sheet}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup"); s.add_argument("--remotion", required=True)
    s.add_argument("--script", default="tc", choices=sorted(FONT_FAMILIES), help="CJK font set (default tc)")
    s.set_defaults(fn=cmd_setup)
    s = sub.add_parser("analyze"); s.add_argument("video"); s.add_argument("--work", required=True)
    s.add_argument("--seconds", type=float, default=6.0); s.set_defaults(fn=cmd_analyze)
    s = sub.add_parser("words"); s.add_argument("--work", required=True); s.add_argument("--model", default="small")
    s.add_argument("--language", default=None); s.set_defaults(fn=cmd_words)
    s = sub.add_parser("matte"); s.add_argument("--work", required=True); s.add_argument("--width", type=int, default=1080)
    s.set_defaults(fn=cmd_matte)
    s = sub.add_parser("props"); s.add_argument("--work", required=True); s.add_argument("--hook", required=True)
    s.set_defaults(fn=cmd_props)
    s = sub.add_parser("preview"); s.add_argument("--work", required=True); s.add_argument("--remotion", required=True)
    s.add_argument("--styles", default=None, help="e.g. 1,4,5 (default all)"); s.set_defaults(fn=cmd_preview)
    s = sub.add_parser("render"); s.add_argument("--work", required=True); s.add_argument("--remotion", required=True)
    s.add_argument("--style", type=int, required=True); s.add_argument("--source", default=None)
    s.add_argument("--out", required=True); s.set_defaults(fn=cmd_render)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
