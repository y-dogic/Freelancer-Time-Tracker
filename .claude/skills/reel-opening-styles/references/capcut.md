# Doing the 6 openings by hand (CapCut / 剪映, Premiere, Final Cut)

Use this when there is no shell to render with (claude.ai chat, phone), or the person wants to edit it themselves. Give the hook script, the chosen style, a second-by-second timeline, and the steps below for their editor.

Term map for other editors: mask (蒙版) = shape mask / track matte. Auto cut-out (智能抠像) = Remove Background (CapCut desktop), Rotobrush (After Effects) or Magnetic Mask (Final Cut). Text animation preset (文字动画) = text animator / MOGRT. Keyframe (关键帧) = keyframe.

Timeline template:
```
0.0–1.0s  Beat 1 "…"   | background: … | person: … | text: small white, fade-in
1.0–2.3s  Beat 2 "…?"  | … | text: accent color, medium
2.3–4.5s  Beat 3 "…N…" | <the transition event lands on this cut> | number: huge, accent, pop-in
```

## Style 1: darkened background + person mask (背景压暗，人物蒙版動畫)
1. Bottom track: the clip (or a moody image). Lower brightness/exposure to about 40%.
2. Overlay the same clip with a circle mask (圓形蒙版) on face and shoulders, with slight feathering. Pop it in with a scale keyframe.
3. Beat 2: keyframe the mask smaller, and pop in a large grey "?" beside it.
4. Beat 3: split the clip. On the second half, remove the mask, apply auto cut-out (智能摳像) and add a white stroke (描邊) for a sticker look. Pop in the big accent number.

## Style 2: cut-out on a themed background + torn-paper reveal (人物摳像，背景做蒙版動畫)
1. Tracks, bottom to top: the real clip, a themed background image/video, and the clip with auto cut-out.
2. Give the themed background a linear mask. Keyframe it to wipe upward on beat 3, and overlay a torn-paper PNG along the mask edge.
3. Beats 1–2 are white text at the top. Beat 3: a huge accent number rises in at the bottom (keep it above y≈1500, the app's caption area).

## Style 3: opening spotlight + person cut-out (開場聚光燈特效，人物摳像動畫)
1. Duplicate the clip: original below, auto cut-out above.
2. Put the big keyword (e.g. "5秒") between the two tracks so the head overlaps the bottom of the letters. The rest of the line goes above the cut-out.
3. Add a spotlight/vignette (聚光燈 / 暗角) for beats 1–2, and keyframe it off on beat 3 with a slight zoom-in.

## Style 4: black poster + type hierarchy + mask (文字大小排版，人物蒙版摳像動畫)
1. A black solid background. The clip goes on top in a rounded-rectangle mask.
2. Beat 2: keyframe the mask into a circle and move it up.
3. Stack the text in clear size steps (about 1× / 1.5× / 4×). Only the pain line and the subline under the number get the accent color, and the number is white.

## Style 5: flash-in text + face focus (開場閃現動畫，人物聚焦特效)
1. The topic text uses a "flash/閃現" in-animation over the chest, not the face.
2. Beat 2: a radial vignette (or 聚焦 / 局部聚光) around the face darkens the rest. The red text glitches out at the end of the beat.
3. Beat 3: cut the vignette off with a quick white flash, and pop in the big number.

## Style 6: TV texture + text animation presets (畫面電視紋理，文字動畫預設)
1. Add a TV/VHS/scanline effect (電視紋理 / 老電視) at low intensity, with a short power-on squash at the start.
2. Vertical text (豎排) with a per-character typewriter preset (打字機 / 逐字): the topic on the left in white, the pain line on the right in red. English uses horizontal typing.
3. Beat 3: blur the footage, and put the number huge in the centre with the subline.
