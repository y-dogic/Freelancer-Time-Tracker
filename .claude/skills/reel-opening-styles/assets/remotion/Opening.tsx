// Six opening styles for a talking-head reel (the first ~3-6 s).
// Copied into <remotion>/src/opening/ by `opening.py setup`; rendered from src/opening/index.ts.
// Coordinates are 1080x1920 screen pixels; times in props are seconds on the clip's timeline.
import React from "react";
import {
  AbsoluteFill,
  Easing,
  Img,
  OffthreadVideo,
  continueRender,
  delayRender,
  interpolate,
  random,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// Fonts are local files (public/opening/fonts/, downloaded by `opening.py setup`): no network at render time.
const FONT_FILES: [string, string, string][] = [
  ["OpeningSans", "700", "opening/fonts/sans-700.ttf"],
  ["OpeningSans", "900", "opening/fonts/sans-900.ttf"],
  ["OpeningSerif", "900", "opening/fonts/serif-900.ttf"],
];
if (typeof document !== "undefined") {
  for (const [family, weight, file] of FONT_FILES) {
    const handle = delayRender(`font ${family} ${weight}`);
    const face = new FontFace(family, `url(${staticFile(file)})`, { weight });
    face
      .load()
      .then(() => {
        (document.fonts as unknown as { add: (f: FontFace) => void }).add(face);
        continueRender(handle);
      })
      .catch((e) => {
        console.warn(`font ${file} missing, falling back to system fonts`, e);
        continueRender(handle);
      });
  }
}
const sans = `OpeningSans, "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif`;
const serif = `OpeningSerif, "Noto Serif TC", "Songti TC", serif`;

export const W = 1080;
export const H = 1920;
export const FPS = 30;

export type Face = { cx: number; cy: number; w: number; h: number };
export type OpeningProps = {
  style: number; // 1..6
  clip: string; // path inside public/, the opening segment (1080x1920, 30 fps)
  matte?: string; // alpha WebM of the cut-out person, same timeline as clip (styles 1-3)
  background?: string; // style 2: image/video to put behind the cut-out person
  durationSec: number;
  topic: { text: string; at: number };
  pain: { text: string; at: number; big?: string }; // big: a word of `text` to enlarge (style 3 behind the head)
  promise: { at: number; lead?: string; number: string; unit?: string; sub?: string };
  face?: Face;
  accent?: string;
  ink?: string;
  vertical?: boolean; // style 6: vertical text (default: on for CJK text)
};

export const openingDefaults: OpeningProps = {
  style: 1,
  clip: "opening/clip.mp4",
  durationSec: 5,
  topic: { text: "知識類口播", at: 0.1 },
  pain: { text: "5秒完播率低？", at: 1.1, big: "5秒" },
  promise: { at: 2.3, lead: "試試這", number: "6", unit: "種", sub: "畫面剪輯效果" },
  face: { cx: 540, cy: 760, w: 300, h: 380 },
};

// ---------- helpers ----------
const isCJK = (s: string) => /[぀-ヿ㐀-鿿豈-﫿]/.test(s);
const textWidth = (s: string, size: number) =>
  [...s].reduce((a, c) => a + (isCJK(c) ? 1 : c === " " ? 0.3 : /[A-Z0-9]/.test(c) ? 0.66 : 0.56), 0) * size;
const fit = (s: string, size: number, maxW: number) => Math.min(size, Math.floor(maxW / Math.max(1, textWidth(s, 1))));
const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));
const ease = Easing.out(Easing.cubic);
const lerp = (f: number, a: number, b: number, from: number, to: number) =>
  interpolate(f, [a, b], [from, to], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });

const usePop = (start: number, damping = 14) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - start, fps, config: { damping, mass: 0.6, stiffness: 180 } });
};

const Clip: React.FC<{ src: string; style?: React.CSSProperties }> = ({ src, style }) => (
  <OffthreadVideo src={staticFile(src)} muted style={{ width: W, height: H, objectFit: "cover", ...style }} />
);
const Matte: React.FC<{ src: string; style?: React.CSSProperties }> = ({ src, style }) => (
  <OffthreadVideo src={staticFile(src)} transparent muted style={{ position: "absolute", width: W, height: H, ...style }} />
);
const isVideo = (p: string) => /\.(mp4|mov|webm|m4v)$/i.test(p);

type TxtProps = {
  x: number;
  y: number;
  size: number;
  color: string;
  family?: string;
  weight?: number;
  align?: "left" | "center" | "right";
  opacity?: number;
  scale?: number;
  origin?: string;
  style?: React.CSSProperties;
  children: React.ReactNode;
};
const Txt: React.FC<TxtProps> = ({ x, y, size, color, family = sans, weight = 900, align = "left", opacity = 1, scale = 1, origin, style, children }) => (
  <div
    style={{
      position: "absolute",
      left: align === "center" ? x - 1000 : align === "right" ? x - 2000 : x,
      width: align === "left" ? undefined : 2000,
      top: y,
      fontFamily: family,
      fontWeight: weight,
      fontSize: size,
      lineHeight: 1,
      color,
      whiteSpace: "nowrap",
      textAlign: align,
      opacity,
      transform: `scale(${scale})`,
      transformOrigin: origin ?? (align === "center" ? "50% 50%" : align === "right" ? "100% 50%" : "0% 50%"),
      ...style,
    }}
  >
    {children}
  </div>
);

// Where text can go: above the head (from y 250) or in the chest zone (chin + 60 .. 1480).
const zones = (face: Face) => {
  const top = { y0: 250, y1: face.cy - face.h / 2 - 60 };
  const chest = { y0: face.cy + face.h * 0.62 + 60, y1: 1480 };
  return { top, chest, best: top.y1 - top.y0 >= chest.y1 - chest.y0 ? top : chest };
};

// The promise block: small lead, huge number (+unit), small sub. Returns height used.
const Promise3: React.FC<{
  p: OpeningProps["promise"];
  x: number;
  y: number;
  maxH: number;
  start: number;
  numColor: string;
  ink: string;
  subColor?: string;
  align?: "left" | "center";
  maxW?: number;
}> = ({ p, x, y, maxH, start, numColor, ink, subColor, align = "left", maxW = 900 }) => {
  const pop = usePop(start, 11);
  const frame = useCurrentFrame();
  if (frame < start) return null;
  const numStr = p.number + (p.unit ?? "");
  const leadSize = p.lead ? 54 : 0;
  const subSize = p.sub ? fit(p.sub, 50, maxW) : 0;
  let num = fit(numStr, 300, maxW);
  num = Math.min(num, Math.max(120, (maxH - leadSize - subSize - 30) / 0.95));
  const unitSize = Math.round(num * 0.72);
  const total = leadSize + num * 0.95 + subSize + 30;
  const cx = align === "center" ? x : x;
  return (
    <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H }}>
      {p.lead ? (
        <Txt x={cx} y={y} size={leadSize} color={ink} weight={700} align={align} opacity={lerp(frame, start, start + 6, 0, 1)}>
          {p.lead}
        </Txt>
      ) : null}
      <div
        style={{
          position: "absolute",
          left: align === "center" ? 0 : cx - 8,
          width: align === "center" ? W : undefined,
          top: y + leadSize + 4,
          textAlign: align,
          fontFamily: serif,
          fontWeight: 900,
          color: numColor,
          lineHeight: 0.95,
          whiteSpace: "nowrap",
          transform: `scale(${interpolate(pop, [0, 1], [1.6, 1])})`,
          transformOrigin: align === "center" ? "50% 60%" : "15% 60%",
          opacity: interpolate(pop, [0, 0.3], [0, 1], { extrapolateRight: "clamp" }),
        }}
      >
        <span style={{ fontSize: num }}>{p.number}</span>
        {p.unit ? <span style={{ fontSize: unitSize, marginLeft: 6 }}>{p.unit}</span> : null}
      </div>
      {p.sub ? (
        <Txt
          x={cx}
          y={y + leadSize + num * 0.95 + 18}
          size={subSize}
          color={subColor ?? ink}
          weight={700}
          align={align}
          opacity={lerp(frame, start + 5, start + 11, 0, 1)}
        >
          {p.sub}
        </Txt>
      ) : null}
      <div data-h={total} />
    </div>
  );
};

// Stacked beats 1-2 (topic small, pain bigger) at a zone; hidden from `hideAt`.
const Beats12: React.FC<{
  props: OpeningProps;
  x: number;
  y: number;
  painColor: string;
  hideAt: number;
  painSize?: number;
  topicSize?: number;
  align?: "left" | "center";
}> = ({ props, x, y, painColor, hideAt, painSize = 88, topicSize = 64, align = "left" }) => {
  const frame = useCurrentFrame();
  const ink = props.ink ?? "#ffffff";
  const t1 = Math.round(props.topic.at * FPS);
  const t2 = Math.round(props.pain.at * FPS);
  if (frame >= hideAt) return null;
  const tSize = fit(props.topic.text, topicSize, 900);
  const pSize = fit(props.pain.text, painSize, 920);
  return (
    <>
      <Txt x={x} y={y + lerp(frame, t1, t1 + 8, 24, 0)} size={tSize} color={ink} weight={700} align={align} opacity={lerp(frame, t1, t1 + 8, 0, 1)}>
        {props.topic.text}
      </Txt>
      {frame >= t2 ? (
        <Txt x={x} y={y + tSize + 22 + lerp(frame, t2, t2 + 8, 24, 0)} size={pSize} color={painColor} align={align} opacity={lerp(frame, t2, t2 + 6, 0, 1)}>
          {props.pain.text}
        </Txt>
      ) : null}
    </>
  );
};

// ---------- Style 1: darkened background + circle mask, then sticker cut-out ----------
const Style1: React.FC<{ p: OpeningProps; face: Face }> = ({ p, face }) => {
  const frame = useCurrentFrame();
  const accent = p.accent ?? "#E8364A";
  const ink = p.ink ?? "#ffffff";
  const b2 = Math.round(p.pain.at * FPS);
  const b3 = Math.round(p.promise.at * FPS);
  const r0 = clamp(face.h * 1.15, 200, 460);
  const enter = usePop(0, 16);
  let r = r0 * enter;
  if (frame >= b2) r = lerp(frame, b2, b2 + 9, r0, r0 * 0.68);
  const q = usePop(b2, 10);
  const z = zones(face);
  const fig = usePop(b3, 12);
  const sticker = "drop-shadow(5px 0 0 #fff) drop-shadow(-5px 0 0 #fff) drop-shadow(0 5px 0 #fff) drop-shadow(0 -5px 0 #fff)";
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <Clip src={p.clip} style={{ filter: "brightness(0.38) saturate(0.75)" }} />
      {frame < b3 ? (
        <AbsoluteFill style={{ clipPath: `circle(${r}px at ${face.cx}px ${face.cy}px)` }}>
          <Clip src={p.clip} />
        </AbsoluteFill>
      ) : p.matte ? (
        <AbsoluteFill style={{ transform: `scale(${interpolate(fig, [0, 1], [0.93, 1])})`, transformOrigin: `${face.cx}px ${face.cy}px` }}>
          <Matte src={p.matte} style={{ filter: sticker }} />
        </AbsoluteFill>
      ) : (
        <AbsoluteFill style={{ clipPath: `circle(${lerp(frame, b3, b3 + 10, r0 * 0.68, 2300)}px at ${face.cx}px ${face.cy}px)` }}>
          <Clip src={p.clip} />
        </AbsoluteFill>
      )}
      {frame >= b2 && frame < b3 ? (
        <Txt
          x={clamp(face.cx + r0 * 0.55, 80, 860)}
          y={face.cy - r0 * 0.68 - 250}
          size={260}
          color="#bdbdbd"
          family={serif}
          scale={interpolate(q, [0, 1], [0.3, 1])}
          opacity={interpolate(q, [0, 0.4], [0, 1], { extrapolateRight: "clamp" })}
          origin="30% 90%"
        >
          ?
        </Txt>
      ) : null}
      <Beats12 props={p} x={70} y={z.best.y0} painColor={accent} hideAt={b3} />
      <Promise3 p={p.promise} x={70} y={z.best.y0} maxH={Math.max(300, z.best.y1 - z.best.y0)} start={b3} numColor={accent} ink={ink} />
    </AbsoluteFill>
  );
};

// ---------- Style 2: cut-out person over a themed background, torn-paper reveal ----------
const tornPoints = (y: number, seed: string, amp: number) => {
  const pts: string[] = [];
  const n = 36;
  for (let i = 0; i <= n; i++) {
    const x = (i / n) * W;
    const j = (random(`${seed}-${i}`) - 0.5) * 2 * amp + Math.sin(i * 0.9) * amp * 0.4;
    pts.push(`${x.toFixed(0)}px ${(y + j).toFixed(0)}px`);
  }
  return pts;
};
const Style2: React.FC<{ p: OpeningProps; face: Face }> = ({ p, face }) => {
  const frame = useCurrentFrame();
  const accent = p.accent ?? "#E8364A";
  const ink = p.ink ?? "#ffffff";
  const b3 = Math.round(p.promise.at * FPS);
  const tearY = frame < b3 ? H + 120 : lerp(frame, b3, b3 + 12, H + 120, -160);
  const above = tornPoints(tearY, "tear", 26);
  const bgClip = `polygon(0px -200px, ${W}px -200px, ${[...above].reverse().join(", ")})`;
  const paperTop = tornPoints(tearY - 10, "tear", 26);
  const paperBot = tornPoints(tearY + 26, "paper", 30);
  const paperClip = `polygon(${paperTop.join(", ")}, ${[...paperBot].reverse().join(", ")})`;
  const z = zones(face);
  const bg = p.background;
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <Clip src={p.clip} />
      {tearY > -150 ? (
        <>
          <AbsoluteFill style={{ clipPath: bgClip }}>
            {bg ? (
              isVideo(bg) ? (
                <OffthreadVideo src={staticFile(bg)} muted style={{ width: W, height: H, objectFit: "cover" }} />
              ) : (
                <Img src={staticFile(bg)} style={{ width: W, height: H, objectFit: "cover" }} />
              )
            ) : (
              // No themed background given: a dark "studio" backdrop built from the clip's own colors,
              // clearly different from the real room so the torn-paper reveal still reads as a scene change.
              <AbsoluteFill>
                <Clip src={p.clip} style={{ filter: "blur(60px) brightness(0.4) saturate(1.4)", transform: "scale(1.3)" }} />
                <AbsoluteFill
                  style={{
                    background: `radial-gradient(ellipse at ${face.cx}px ${face.cy}px, rgba(255,255,255,0.10), rgba(0,0,0,0) 45%), linear-gradient(165deg, rgba(18,22,38,0.88), rgba(52,24,28,0.82))`,
                  }}
                />
                <AbsoluteFill style={{ background: "repeating-linear-gradient(90deg, rgba(255,255,255,0.025) 0 2px, rgba(0,0,0,0) 2px 9px)" }} />
              </AbsoluteFill>
            )}
          </AbsoluteFill>
          {frame >= b3 ? (
            <AbsoluteFill style={{ clipPath: paperClip, backgroundColor: "#f2ede3", filter: "drop-shadow(0 6px 10px rgba(0,0,0,.4))" }} />
          ) : null}
          {p.matte ? <Matte src={p.matte} /> : null}
        </>
      ) : null}
      <Beats12 props={p} x={70} y={z.top.y1 - z.top.y0 >= 200 ? z.top.y0 : z.chest.y0} painColor={ink} hideAt={b3} painSize={92} />
      <Promise3
        p={{ ...p.promise, lead: undefined }}
        x={70}
        y={Math.max(z.chest.y0, 1080)}
        maxH={1490 - Math.max(z.chest.y0, 1080)}
        start={b3 + 2}
        numColor={accent}
        ink={ink}
      />
    </AbsoluteFill>
  );
};

// ---------- Style 3: opening spotlight + big word behind the person ----------
const Style3: React.FC<{ p: OpeningProps; face: Face }> = ({ p, face }) => {
  const frame = useCurrentFrame();
  const accent = p.accent ?? "#E8364A";
  const ink = p.ink ?? "#ffffff";
  const b2 = Math.round(p.pain.at * FPS);
  const b3 = Math.round(p.promise.at * FPS);
  const R = clamp(face.h * 1.05, 220, 520);
  const spotR = lerp(frame, 0, 10, 0, R);
  const spotOpacity = frame < b3 ? 1 : lerp(frame, b3, b3 + 8, 1, 0);
  const zoom = frame < b3 ? lerp(frame, 0, b3, 1.0, 1.04) : lerp(frame, b3, b3 + 8, 1.04, 1.14);
  const big = p.pain.big && p.pain.text.includes(p.pain.big) ? p.pain.big : "";
  // Take the big word out of the line only when it starts it ("5秒" + "完播率低"); mid-sentence the line stays whole.
  const rest = big && p.pain.text.startsWith(big) ? p.pain.text.slice(big.length).trim() : p.pain.text;
  const bigSize = big ? fit(big, 330, 900) : 0;
  const faceTop = face.cy - face.h / 2;
  const bigY = faceTop - bigSize * 0.72;
  const bigPop = usePop(b2, 13);
  const z = zones(face);
  const chestY = z.chest.y0;
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <AbsoluteFill style={{ transform: `scale(${zoom})`, transformOrigin: `${face.cx}px ${face.cy}px` }}>
        <Clip src={p.clip} />
        {frame >= b2 && frame < b3 && big ? (
          <Txt
            x={face.cx}
            y={bigY}
            size={bigSize}
            color={accent}
            family={serif}
            align="center"
            scale={interpolate(bigPop, [0, 1], [1.25, 1])}
            opacity={interpolate(bigPop, [0, 0.3], [0, 1], { extrapolateRight: "clamp" })}
          >
            {big}
          </Txt>
        ) : null}
        {p.matte && frame < b3 + 8 ? <Matte src={p.matte} /> : null}
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          opacity: spotOpacity,
          background: `radial-gradient(circle at ${face.cx}px ${face.cy + face.h * 0.25}px, rgba(0,0,0,0) ${spotR}px, rgba(0,0,0,0.82) ${spotR * 1.75 + 1}px)`,
        }}
      />
      {frame < b3 ? (
        <>
          <Txt x={face.cx} y={chestY + lerp(frame, 0, 8, 20, 0)} size={fit(p.topic.text, 70, 900)} color={ink} align="center" opacity={lerp(frame, Math.round(p.topic.at * FPS), Math.round(p.topic.at * FPS) + 8, 0, 1)}>
            {p.topic.text}
          </Txt>
          {frame >= b2 ? (
            <Txt
              x={face.cx}
              y={big ? bigY + bigSize * 0.62 : chestY + 96}
              size={fit(rest, 84, 900)}
              color={ink}
              align="center"
              opacity={lerp(frame, b2 + 3, b2 + 9, 0, 1)}
            >
              {rest}
            </Txt>
          ) : null}
        </>
      ) : (
        <Promise3 p={p.promise} x={70} y={Math.max(chestY, 1020)} maxH={1490 - Math.max(chestY, 1020)} start={b3 + 3} numColor={accent} ink={ink} />
      )}
    </AbsoluteFill>
  );
};

// ---------- Style 4: black poster, size-hierarchy type, rounded-rect -> circle mask ----------
const Style4: React.FC<{ p: OpeningProps; face: Face }> = ({ p, face }) => {
  const frame = useCurrentFrame();
  const accent = p.accent ?? "#E8364A";
  const ink = p.ink ?? "#ffffff";
  const b2 = Math.round(p.pain.at * FPS);
  const b3 = Math.round(p.promise.at * FPS);
  const k = lerp(frame, b2, b2 + 10, 0, 1);
  const enter = usePop(0, 18);
  const w = interpolate(k, [0, 1], [820, 560]);
  const h = interpolate(k, [0, 1], [900, 560]);
  const radius = interpolate(k, [0, 1], [44, 280]);
  const cy = interpolate(k, [0, 1], [1070, 900]);
  const targetFace = interpolate(k, [0, 1], [330, 250]);
  const s = clamp(targetFace / face.h, 0.55, 1.6);
  const faceY = cy - h / 2 + interpolate(k, [0, 1], [300, 250]);
  const tx = 540 - face.cx * s;
  const ty = faceY - face.cy * s;
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <div
        style={{
          position: "absolute",
          left: 540 - w / 2,
          top: cy - h / 2 + interpolate(enter, [0, 1], [80, 0]),
          width: w,
          height: h,
          borderRadius: radius,
          overflow: "hidden",
          opacity: interpolate(enter, [0, 0.5], [0, 1], { extrapolateRight: "clamp" }),
        }}
      >
        <div style={{ position: "absolute", left: tx - (540 - w / 2), top: ty - (cy - h / 2), width: W, height: H, transform: `scale(${s})`, transformOrigin: "0 0" }}>
          <Clip src={p.clip} />
        </div>
      </div>
      <Beats12 props={p} x={80} y={260} painColor={accent} hideAt={99999} painSize={112} topicSize={78} />
      <Promise3
        p={{ ...p.promise, lead: undefined }}
        x={540}
        y={cy + h / 2 - 90}
        maxH={1490 - (cy + h / 2 - 90)}
        start={b3}
        numColor={ink}
        ink={ink}
        subColor={accent}
        align="center"
      />
    </AbsoluteFill>
  );
};

// ---------- Style 5: flash-in text + face focus ----------
const Style5: React.FC<{ p: OpeningProps; face: Face }> = ({ p, face }) => {
  const frame = useCurrentFrame();
  const accent = p.accent ?? "#E8364A";
  const ink = p.ink ?? "#ffffff";
  const t1 = Math.round(p.topic.at * FPS);
  const b2 = Math.round(p.pain.at * FPS);
  const b3 = Math.round(p.promise.at * FPS);
  const z = zones(face);
  const y = clamp(z.chest.y0, 900, 1300);
  const strobe = (start: number) => {
    const d = frame - start;
    if (d < 0) return 0;
    return [1, 0.15, 1, 0.4, 1][d] ?? 1;
  };
  const focus = frame >= b2 && frame < b3 ? lerp(frame, b2, b2 + 6, 0, 1) : 0;
  const R = clamp(face.h * 0.95, 200, 480);
  const glitch = frame >= b3 - 6 && frame < b3;
  const jx = glitch ? (random(`g${frame}`) - 0.5) * 36 : 0;
  const flash = frame >= b3 ? interpolate(frame - b3, [0, 2, 7], [0, 0.55, 0], { extrapolateRight: "clamp" }) : 0;
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <Clip src={p.clip} />
      <AbsoluteFill
        style={{
          opacity: focus,
          background: `radial-gradient(circle at ${face.cx}px ${face.cy}px, rgba(0,0,0,0) ${R}px, rgba(0,0,0,0.66) ${R + 70}px)`,
        }}
      />
      {frame < b2 ? (
        <Txt x={70} y={y} size={fit(p.topic.text, 76, 900)} color={ink} opacity={strobe(t1)}>
          {p.topic.text}
        </Txt>
      ) : null}
      {frame >= b2 && frame < b3 ? (
        <Txt
          x={70 + jx}
          y={y}
          size={fit(p.pain.text, 92, 920)}
          color={accent}
          opacity={glitch ? (frame % 2 ? 0.35 : 0.9) : strobe(b2)}
          style={glitch ? { clipPath: `inset(${(random(`c${frame}`) * 40).toFixed(0)}% 0 ${(random(`d${frame}`) * 40).toFixed(0)}% 0)` } : undefined}
        >
          {p.pain.text}
        </Txt>
      ) : null}
      <Promise3 p={{ ...p.promise, lead: undefined }} x={70} y={y - 40} maxH={1490 - (y - 40)} start={b3} numColor={ink} ink={ink} />
      <AbsoluteFill style={{ opacity: flash, background: `radial-gradient(circle at 50% 45%, rgba(255,240,220,1), rgba(255,240,220,0.3) 70%)`, mixBlendMode: "screen" }} />
    </AbsoluteFill>
  );
};

// ---------- Style 6: TV texture + text animation presets ----------
const Typed: React.FC<{ text: string; start: number; perChar?: number }> = ({ text, start, perChar = 2 }) => {
  const frame = useCurrentFrame();
  const n = Math.max(0, Math.floor((frame - start) / perChar) + 1);
  const chars = [...text];
  return (
    <>
      {chars.map((c, i) => (
        <span key={i} style={{ opacity: i < n ? 1 : 0, display: "inline-block", transform: i === n - 1 ? "scale(1.25)" : "none" }}>
          {c === " " ? "\u00A0" : c}
        </span>
      ))}
    </>
  );
};
const Style6: React.FC<{ p: OpeningProps; face: Face }> = ({ p, face }) => {
  const frame = useCurrentFrame();
  const accent = p.accent ?? "#E8364A";
  const ink = p.ink ?? "#ffffff";
  const t1 = Math.round(p.topic.at * FPS);
  const b2 = Math.round(p.pain.at * FPS);
  const b3 = Math.round(p.promise.at * FPS);
  const vertical = p.vertical ?? (isCJK(p.topic.text) && isCJK(p.pain.text));
  const on = lerp(frame, 0, 6, 0.02, 1);
  const blur = frame >= b3 ? lerp(frame, b3, b3 + 8, 0, 16) : 0;
  const dim = frame >= b3 ? lerp(frame, b3, b3 + 8, 1, 0.55) : 1;
  const roll = ((frame * 23) % (H + 300)) - 150;
  const noise = 0.05 + random(`n${frame}`) * 0.05;
  const vStyle: React.CSSProperties = { writingMode: "vertical-rl", textOrientation: "upright", letterSpacing: 6 };
  const tSize = vertical ? clamp(Math.floor(1150 / [...p.topic.text].length), 70, 130) : fit(p.topic.text, 80, 900);
  const pSize = vertical ? clamp(Math.floor(1150 / [...p.pain.text].length), 70, 130) : fit(p.pain.text, 96, 920);
  const z = zones(face);
  const hy = z.top.y1 - z.top.y0 > 260 ? z.top.y0 : z.chest.y0;
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <AbsoluteFill style={{ transform: `scaleY(${on})`, filter: `brightness(${interpolate(on, [0.02, 1], [3, 1])})` }}>
        <Clip src={p.clip} style={{ filter: `saturate(0.8) contrast(1.08) blur(${blur}px) brightness(${dim})`, transform: blur ? "scale(1.05)" : undefined }} />
        <AbsoluteFill style={{ background: "repeating-linear-gradient(0deg, rgba(0,0,0,0.28) 0px, rgba(0,0,0,0.28) 2px, rgba(0,0,0,0) 2px, rgba(0,0,0,0) 5px)" }} />
        <div style={{ position: "absolute", left: 0, top: roll, width: W, height: 140, background: "linear-gradient(rgba(255,255,255,0), rgba(255,255,255,0.07), rgba(255,255,255,0))" }} />
        <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.55) 100%)" }} />
        <AbsoluteFill style={{ backgroundColor: "#fff", opacity: noise, mixBlendMode: "overlay" }} />
      </AbsoluteFill>
      {frame < b3 ? (
        vertical ? (
          <>
            <div style={{ position: "absolute", left: 50, top: 240, fontFamily: serif, fontWeight: 900, fontSize: tSize, color: ink, lineHeight: 1, ...vStyle }}>
              {frame >= t1 ? <Typed text={p.topic.text} start={t1} /> : null}
            </div>
            <div style={{ position: "absolute", left: 930 - pSize, top: 300, fontFamily: serif, fontWeight: 900, fontSize: pSize, color: accent, lineHeight: 1, ...vStyle }}>
              {frame >= b2 ? <Typed text={p.pain.text} start={b2} /> : null}
            </div>
          </>
        ) : (
          <>
            <Txt x={70} y={hy} size={tSize} color={ink} family={serif}>
              {frame >= t1 ? <Typed text={p.topic.text} start={t1} perChar={1} /> : null}
            </Txt>
            <Txt x={70} y={hy + tSize + 24} size={pSize} color={accent} family={serif}>
              {frame >= b2 ? <Typed text={p.pain.text} start={b2} perChar={1} /> : null}
            </Txt>
          </>
        )
      ) : (
        <Promise3 p={p.promise} x={540} y={560} maxH={760} start={b3 + 2} numColor={accent} ink={ink} align="center" />
      )}
    </AbsoluteFill>
  );
};

export const Opening: React.FC<OpeningProps> = (props) => {
  const face = props.face ?? openingDefaults.face!;
  const S = [Style1, Style2, Style3, Style4, Style5, Style6][clamp(Math.round(props.style), 1, 6) - 1];
  return <S p={props} face={face} />;
};
