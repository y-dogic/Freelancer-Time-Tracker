# 拆解框架 / Breakdown framework

Seven dimensions, in report order, plus a 分镜表 and the 复盘 (review your own video) variant.
The guiding questions are prompts for thinking, not a checklist to recite. Answer the ones the
video actually gives you material for, and skip the rest rather than padding.
Platform-specific reading of data, covers and norms: `platforms.md`.

## Contents
1. 选题逻辑 · 2. 脚本与画面 (+分镜表, 转场, 信息密度) · 3. 完整的开头 · 4. 金句 · 5. 情绪与人群 ·
6. 传播逻辑 · 7. 可复用的框架逻辑 · Video-type adjustments · Long-form adjustments ·
复盘 mode (own video) · Report templates

---

## 1. 选题逻辑 — topic logic

- **核心命题**: one sentence: what is the video *really* arguing or offering? It's often different
  from the title ("提升幸运的6个方法" → "你无法决定所有条件，但可以调整自己与机会相遇的方式").
- **目标人群**: describe a *state*, not a demographic ("努力了却一直不顺的人" beats "18-30岁女性").
  List 3-4 concrete situations the viewer is in.
- **为什么值得做**: is it a perennial need (钱/健康/关系/成长/颜值/效率), a current trend, a
  counter-intuitive take on a common belief, or a big vague word turned into something actionable?
- **提供什么价值**: 实用 (steps), 认知 (a new frame), 情绪 (being seen / comforted / pumped),
  娱乐, or 社交货币 (something worth forwarding). Usually one primary plus one secondary.
- **包装**: the title, cover/thumbnail (`thumbnail.jpg`) and first frame together form the
  "click promise". Say what that promise is, and whether the video pays it off.

## 2. 脚本与画面 — script and visuals

**脚本结构**: rebuild the outline as a tree with approximate timestamps (开篇 / 前置框架 / 主体 n 点 /
结尾). Name the structure type: 总分总, 问题-原因-方案, 清单体, 故事-转折-道理, 对比/反差, 实验/挑战,
测评, 教程步骤, vlog 时间线. Note any **前置论证** (a premise that makes the main points believable),
and where the pacing changes (a story, joke or pattern break inserted to reset attention).

**章节表**: for each section give the time range, the order of content inside it (引用→定义→类比→结论…),
and what the example or visual is doing (making the abstract concrete, adding proof, adding emotion).

**分镜表 (shot list)**: `shotlist.md` comes pre-filled with time, length, frame and overlapping speech.
Fill in 景别 (特写/近景/中景/全景/远景), 运镜 (固定/推/拉/摇/移/跟/手持/变焦), 画面, 字幕/花字,
转场 and 作用. Handle size like this:
- ≤ ~40 shots: give the full table.
- More than that: give the full table for the opening plus one representative stretch, then summarise
  the rest by section ("1:10-2:30 共 18 个镜头：口播近景 + 素材插入交替，约 4s 一切").
- Merge rows when detection split one shot (zoom effects, flashes). Split rows when a jump cut
  wasn't detected.

**剪辑节奏**: use the shot stats (average/median shot length, cuts per window). Is the rhythm
constant, or does it speed up at the hook, the list items, the climax? Match the cut density
windows against the speech-density windows. A dense section with fast cuts reads as "高信息密度".

**转场**: hard cut (most common), jump cut (same framing, time skipped), match cut, whip/swipe,
zoom-punch, fade/dissolve, a graphic or sticker transition, an L/J cut (audio leads the picture).
Judge from the frames on either side of the cuts. For a transition you want to be sure of, re-run
with `--timestamps` at cut±0.2s. Say what each transition type is *for* (keeping energy, marking a new
chapter, hiding a cut).

**信息密度**: speech density (chars or words per minute, per window) plus pauses. As rough anchors,
Mandarin 口播 runs ~200-280 字/分 normal and 300+ fast. English runs ~130-160 wpm normal and 180+ fast.
Also look at visual density: the amount of on-screen text, B-roll per point, and how many ideas each
minute delivers. Point out where density drops (filler, slow intros), because that's where viewers leave.

**画面与包装**: shot types (口播, B-roll, 素材混剪, 屏幕录制, 字幕卡/大字报, 实拍演示), on-screen text
style (花字, keyword highlights, progress or chapter labels), setting, wardrobe, color, recurring
visual identity. Always say how the visuals *serve* the script, for example "每个方法出现时都有大字卡
→ 观众有进度感".

Be honest about the limits. Frames are sampled, so subtle camera moves can be missed. Write "约"
for timings, and "未逐帧核验" when camera movement is inferred.

## 3. 完整的开头 — the opening (0-15s for short videos, the first 30-60s for long-form)

- **前 3 秒的钩子** (quote the exact words plus what's on screen, from `sheets/hook.jpg`). Types:
  结果前置 / 数字承诺 / 反常识 / 痛点提问 / 身份点名 ("如果你是…") / 冲突或悬念 / 视觉奇观或反差 /
  权威背书 / 冷开场 (mid-action) / 直接展示成品. Name the visual hook and the verbal hook separately.
- **转折进入主体**: the exact line or moment where the opening hands over to the body, and what bridges the two.
- **留人机制**: open loops (a promise paid off later), progress signals (第一个…), "最后一个最重要",
  teased payoffs, and chapter cards. Where is each loop opened, and where is it closed?
- **Beat sheet**: `0:00 [画面] … / [台词] …` → `0:03 …` → `0:0x 进入主体`.

## 4. 金句 — quotable lines

- Pull the 2-5 lines most likely to be screenshotted, commented, or reused. Quote them verbatim
  from the transcript or the on-screen text, with timestamps.
- For each one, say why it works: 对仗/反转/具体化/把抽象词翻译成日常场景/替观众说出心里话/可直接套用.
- Write **one sentence that captures the whole video**. It can be the video's own line, or your
  distillation, labeled as such.

## 5. 情绪与人群 — emotion and audience

- Which **group** is moved, and which line or moment moves them.
- Which **emotions** fire, and in what sequence. For example: 焦虑/不甘 → 被理解 → 希望/掌控感 → 行动冲动.
  Others: 好奇, 爽感, 愤怒/不平, 怀旧, 治愈, 羡慕, 优越感, 认同, 笑点.
- Evidence beyond your own reading: Bilibili 弹幕 peaks (`danmaku.txt`) show where viewers actually
  reacted and what they said. Use them when present.
- **Does it offer a way out?** Concrete actions, a mindset shift, or only catharsis? Resonance plus
  something actionable is what gets videos saved and shared.

## 6. 传播逻辑 — distribution logic

Use the data in summary.md (or what the user provided). Never invent numbers. With no data, give
hypotheses and say which numbers would confirm them. Ratios mean different things on each platform.
Read them with `platforms.md`.

Generic signals:
- **saves/likes high**: utility. People save it to use later, which drives long-tail and search traffic.
- **comments/likes high**: controversy, an invitation to answer, resonance people want to voice, or a giveaway.
- **shares/likes high**: social currency: "send to someone who needs this", it speaks for me, or a couples/family/friends topic.
- **views or likes ≫ followers**: it broke out of the follower base into recommendations. Explain what
  let it travel (a broad topic, low comprehension cost, a strong hook, a trend tie-in).
- **views/day and age**: a spike-then-flat pattern means a trend hit; steady views/day means evergreen or search traffic.
- Also: length vs completion design, title/hashtags/tags (which traffic pools they target), post timing,
  BGM/trend tie-ins, the comment bait at the end, and the cover's role in click-through.

Structure this section as: 数据表现 → 读出的信号 → 驱动传播的内容机制 → 不确定之处.

## 7. 可复用的框架逻辑 — reusable framework

| 模块 | 模板 | 本视频示例 |
|---|---|---|
| 选题 | e.g. 把「大而玄的词」拆成「可执行的 N 个方法」 | 幸运 → 6 个方法 |
| 包装 (标题/封面) | … | … |
| 开头 | e.g. 数字承诺 + 反常识论断 + 权威引用 | … |
| 主题/结构 | e.g. 前置框架 + N 点清单 | … |
| 金句 | e.g. 「你无法 X，但可以 Y」 | … |
| 钩子/留人 | … | … |
| 结尾 | e.g. 回扣要点 + 拔高到认知层 + 互动引导 | … |

Then:
- **最值得借鉴的 1-3 点**, ranked, each with one sentence on *why it transfers*.
- **你可以怎么用**: 2-3 concrete adaptations. If the user told you their niche or account, apply them
  to that; otherwise give examples from a few common niches.
- **不建议照搬的地方**: elements that depend on this creator's persona, budget, or timing.

---

## Video-type adjustments

Shift the weight of the analysis by the kind of video:
- **口播/知识**: script structure, 金句, speech density, on-screen text. Camera work matters less.
- **剧情/短剧**: conflict setup, reversals per minute, character hooks, cliffhanger ending. Add a 情节节拍表.
- **Vlog/生活方式**: persona, aspiration, pacing, music, visual aesthetic, the "what's in it for me" part.
- **测评/带货/种草**: the trust-building sequence (pain point → demo → proof → price anchor → CTA),
  product shots, objection handling, and the conversion path (link, comment keyword).
- **广告/品牌片**: the brand/benefit reveal timing, the single-minded message, the CTA, and brand assets on screen.
- **教程/干货**: step clarity, whether the result is shown first, screen recording readability, save-worthiness.
- **音乐/舞蹈/挑战/meme**: the format template, the sound, how easy it is to copy (participation drives spread).

## Long-form adjustments (YouTube / Bilibili, roughly over 3 min)

- The opening covers the first 30-60s: cold open, the promise, and the "why watch to the end".
- Use the platform's chapters (in summary.md) as the skeleton when they exist.
- Retention design: re-hooks every 1-3 min, pattern interrupts, payoff placement, mid-roll sponsor
  handling, and the end screen.
- Title and thumbnail matter more than on short-video feeds: analyse `thumbnail.jpg`
  (face/emotion, text count, contrast, curiosity gap) together with the title.
- With a fixed frame budget, coverage is sparse. Say so, and re-run focused passes
  (`--start/--end`) on the sections that matter.

---

## 复盘 mode — reviewing the user's own video

Use this when the user says the video is theirs (复盘, "my video", "why didn't this work", "help me
improve"). Same evidence and the same seven lenses, but the job changes from *explaining success*
to *finding the fixes worth the most*.

1. **Ask (or infer) the goal and the context**: who it's for, what success means (views, followers,
   saves, leads/sales), how it performed against their usual videos, and the platform.
2. **Diagnose against the goal**, in this order, because the earliest drop-off costs the most:
   包装 (title/cover/first frame) → 前 3 秒 → 前 15 秒留存 → 中段密度/节奏 → 结尾与互动引导 → 选题本身.
   Tie each finding to a timestamp and to the evidence (a quote, a frame, a density dip).
3. **改进建议**, as a prioritized table:

   | 优先级 | 时间点 | 问题 | 为什么影响数据 | 具体改法 |
   |---|---|---|---|---|

   Cap it at the top 5-8, because a creator can't act on 25 notes. Mark which fixes are cheap
   (re-cut, new cover, new title) and which need a reshoot.
4. **Rewrite the opening**: give 2-3 alternative hooks (script plus visual) for the first 3-5s.
5. **What to keep**: what's already working, so they don't lose it while fixing the rest.
6. If they give a viral reference video, compare the two side by side (structure, hook, density, packaging).

---

## Report templates

Breakdown of someone else's video:

```markdown
# 爆款拆解：<视频标题>

> 来源：<平台 · 作者 · 发布时间> ｜ 时长 <mm:ss> ｜ 数据：<该平台可得的指标>
> 读取方式：<N 张画面 + 平台字幕/语音转写/画面字幕 (+弹幕)>；时间均为约数

**一句话结论**：<它为什么能火>

## 1. 选题逻辑
## 2. 脚本与画面   (含 章节表 / 分镜表 / 节奏 · 转场 · 信息密度)
## 3. 完整的开头
## 4. 金句
## 5. 情绪与人群
## 6. 传播逻辑
## 7. 可复用的框架逻辑
```

复盘 of the user's own video:

```markdown
# 视频复盘：<标题>
> 目标：<…> ｜ 表现：<数据 vs 平时> ｜ 读取方式：<…>
**一句话诊断**：<最大的问题 + 最值得改的一处>
## 改进建议（按优先级）
## 开头重写方案
## 七维诊断   (只展开有问题或值得保留的维度)
## 保留的优点
```
