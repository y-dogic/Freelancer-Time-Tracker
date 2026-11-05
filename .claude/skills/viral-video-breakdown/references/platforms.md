# Platform guide

How each platform's data, packaging and norms change the analysis, plus download notes.
Read only the section(s) for the platform(s) at hand. Benchmarks are rough and vary a lot by niche
and account size, so treat them as directional and say so in the report.

## Contents
- 抖音 Douyin / TikTok
- 小红书 Xiaohongshu (RED)
- 视频号 WeChat Channels
- 快手 Kuaishou
- B站 Bilibili
- YouTube (Shorts and long-form)
- Instagram Reels / Facebook
- X (Twitter) / LinkedIn
- Download notes (all platforms)

---

## 抖音 Douyin / TikTok
- **Distribution**: an interest-based recommendation feed served in traffic pools. Completion rate,
  replays, and early interaction decide whether a video gets pushed to the next pool. Followers matter little.
- **Data**: likes, comments, shares, saves (收藏). Views are usually hidden on Douyin but visible on TikTok.
  Read likes against followers to judge breakout. A high share count suggests 社交货币, and a high
  save count suggests 干货.
- **Packaging**: the first frame is the cover in the feed, so the hook *is* the packaging. Hashtags and
  the caption steer which interest groups and searches the video reaches (抖音搜索 is big).
- **Norms**: 7-60s dominates, but 1-3 min+ 口播/知识 does well when retention is designed in. Sound and
  trend tie-ins matter (TikTok trending sounds). Check `track` in the metadata.

## 小红书 Xiaohongshu (RED)
- **Distribution**: a two-column feed where the user *chooses* to click. Cover plus title decide
  click-through. Search is a major, long-lived traffic source, so keywords in the title, body and tags matter.
- **Data**: likes, saves (收藏), comments, shares. **收藏/点赞 is the key ratio**: high means
  utility content with a long tail. Comments often ask for links, details or templates.
- **Packaging**: analyse `thumbnail.jpg` (the cover): big title text, before/after, a face, a list
  promise. Also check how well the title matches the cover.
- **Norms**: 种草, tutorials, 干货 lists, life aesthetics, 真实分享 tone. Many posts are 图文 (image
  posts) rather than video. For those, ask for screenshots and apply the same lenses without the editing analysis.

## 视频号 WeChat Channels
- **Distribution**: a social graph first. Friends' likes (点赞 means "recommend to friends") push
  content through WeChat circles, then algorithmic expansion follows. It skews to an older, mass audience.
- **Data**: likes (❤ + 👍), comments, shares/forwards, saves. A **high forward rate** is the main breakout signal.
- **Norms**: content that people forward to family groups and Moments: wisdom, health, emotion,
  current affairs, local life. Downloads usually aren't possible, so ask for a saved file or a screen recording.

## 快手 Kuaishou
- **Distribution**: more weight on the creator-fan relationship (老铁 culture) and community trust than
  on Douyin. Lower-tier cities and an authentic, down-to-earth tone.
- **Data**: likes, comments, shares. Comment culture is strong.
- **Norms**: real life, skills, rural content, 直播 tie-ins, 带货 built on trust.

## B站 Bilibili
- **Distribution**: a recommendation feed plus subscriptions, with strong community norms. Long-form
  (5-20 min+) is common.
- **Data**: views (播放), likes, 投币 (coins), 收藏, shares, comments, **弹幕**. 一键三连 (like + coin +
  save together) signals deep approval. Coins/views is a quality signal. Not all of these numbers come
  through the downloader, so ask the user for the ones on the page if they matter.
- **弹幕**: `danmaku.txt` shows where viewers reacted and what they said. Use it for 情绪, 笑点, 高能时刻,
  and to see which lines became memes.
- **Packaging**: cover plus title, often playful and in-joke heavy. Series and UP主 persona matter.

## YouTube (Shorts and long-form)
- **Shorts**: a feed like TikTok. The swipe-away rate and the loop matter. Views are visible.
- **Long-form**: click-through rate (thumbnail + title) × average view duration drives distribution.
  The first 30s retention is critical. Chapters and end screens shape the session.
- **Data**: views, likes, comments (no saves or shares exposed). views/subscribers shows reach beyond the
  base. likes/views ≈ 2-5% is typical, and higher means strong approval. comments/views shows
  discussion. views/day versus age separates trend spikes from evergreen search traffic.
- **Packaging**: analyse `thumbnail.jpg`: a face and emotion, 3 words of text or fewer, contrast,
  the curiosity gap. Look at title-thumbnail complementarity (they shouldn't say the same thing).
- **Captions**: YouTube usually has captions, which the script uses before whisper. Auto-generated
  captions have no punctuation and can mishear terms.

## Instagram Reels / Facebook
- **Distribution**: an interest feed (Reels tab) plus the social graph. Shares to Stories and DMs
  ("sends") are a strong ranking signal.
- **Data**: views/plays, likes, comments. Shares and saves are often visible only to the creator, so
  ask the user if it's their own video.
- **Norms**: aesthetic, polished visuals, text-on-screen for sound-off viewing, trending audio.

## X (Twitter) / LinkedIn
- **X**: autoplay muted in the timeline, so the first frame plus burned-in captions matter. The
  quote-tweet and reply dynamics drive spread. Look at reposts and quotes.
- **LinkedIn**: a professional audience that watches sound-off. Text hooks on screen and an
  insight-first structure work. Comments weigh heavily in distribution.

---

## Download notes (all platforms)

The script uses yt-dlp, which supports 1,000+ sites. When a site blocks anonymous or cloud
downloads, the legitimate fixes are the same everywhere: the user's own browser cookies, a
cookies.txt, or a saved file / screen recording. Don't work around a platform's access controls
(signature APIs, captcha solving, scraping tricks).

| Platform | Typical behaviour |
|---|---|
| Douyin, Kuaishou | Need cookies. Datacenter IPs are blocked |
| Xiaohongshu | Often needs cookies. Image posts aren't video |
| 视频号 | Not downloadable by tools: use a saved file or screen recording |
| Bilibili | Works logged out at lower quality. Some regions are geo-blocked |
| YouTube | Works from home IPs. Cloud IPs get "not a bot" checks or 403s. Captions often still arrive (partial evidence) |
| Instagram, Facebook, LinkedIn | Usually need login cookies |
| TikTok, X, Vimeo | Usually work. Some posts need cookies |

When the script exits with `PARTIAL_EVIDENCE` (metadata, captions or cover arrived but the video didn't),
you can already analyse 选题, the script, 金句, packaging and 传播 from those files. Label the
visual sections as pending, and ask for the file to complete them.
