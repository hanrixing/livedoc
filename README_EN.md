# LiveDoc · Living Document Generator

**Can your report video update itself?**

Turn a "dead PPT" into a "living video": feed in **layout + data declaration + script**, and get dynamic content with **live data + digital-avatar narration**.
Data changes? Re-run once — numbers and script refresh automatically. That is the essential difference from "PPT-to-video" tools.

```
layout template  ─┐
data declaration ─┼─►  LiveDoc  ─►  living doc preview (HTML)
script shots     ─┘                + digital-avatar script (Jimeng storyboard)
              ▲
        MCP / HTTP live data source
```

🇨🇳 **中文说明请见 [README.md](README.md)**

🔗 **[Live demo (no install needed)](https://hanrixing.github.io/livedoc/)** · **[Roadmap](ROADMAP.md)**

▶️ **12-second explainer video** — generated with Jimeng AI; the digital avatar narrates the script itself. Click the cover to play:

[![Click to play · 12-second explainer video](docs/screenshots/video-cover.jpg)](docs/video/mcd-weekly-demo.mp4)

![Live update: change the data source -> re-run -> numbers and script refresh](docs/screenshots/demo-live-update.gif)

---

## Why this is not another "PPT-to-video"

| | PPT-to-video tools (e.g. MoneyPrinterTurbo) | LiveDoc |
|---|---|---|
| Data | Screenshots baked into the video, stale on arrival | **Declarative sources, pulled live** |
| Narration | Robotic TTS | **Digital avatar** (your Jimeng `@avatar`) |
| Output | A dead MP4 | **Data changes → re-run → auto-updated** |
| Data protocol | Basically static files only | **Native MCP support** (verified against McDonald's official MCP) |

The intersection of *live data + real avatar + regenerable output* is currently unoccupied.

---

## Quick Start

Zero third-party dependencies — Python standard library only (3.9+):

```bash
cd livedoc
python src/generator.py                    # demo mode: sanitized samples, safe to share
python src/generator.py --live             # live mode: real data
python src/generator.py spec/mcd-weekly.livedoc --live   # specific spec
```

Outputs land in `output/`:

| File | Description |
|---|---|
| `output/<name>.html` | Living-doc preview: data cards + source attribution + full script |
| `output/<name>.jimeng.md` | Jimeng digital-avatar storyboard (one section = one shot, with narration/camera/visual) |

---

## Privacy by Design: real data never leaks by accident

This layer exists because MCP sources pull **your personal assets** (coupons in your wallet, points balance).

| Mode | Data | Output location | Public-safe? |
|---|---|---|---|
| `python generator.py` | Sanitized samples | `output/` | ✅ Yes |
| `--live` + `sensitive: true` | Your real personal data | `output/live/` (gitignored) | ❌ Local only |
| `--live` + `sensitive: false` | Public sources (e.g. GitHub API) | `output/` | ✅ Yes |

`meta.sensitive` is declared by the spec author; the generator enforces isolation and warning accordingly. Defaults to the conservative `true`.

Tokens are read from the `MCD_MCP_TOKEN` env var or `~/.workbuddy/mcp.json`, and **never written into any output file**.

---

## Two Built-in Examples

| Spec | Data source | What it demonstrates |
|---|---|---|
| `spec/quarterly-report.livedoc` | GitHub API (public) | Real Star/Fork/Issue numbers in the script; public data, safe to share |
| `spec/mcd-weekly.livedoc` | **McDonald's official MCP** (`query-my-coupons` / `available-coupons` / `campaign-calendar`) | Real coupon data + **auto-computed expiry countdown**; demonstrates sensitive-data isolation |

Verified live: all three MCP tools returned real data, and the script auto-filled into
*"You hold 1 coupon — the 9.9 Milo cocoa shaved ice expires 2026-10-12, **only 1 day left**."*

---

## Spec Format at a Glance

A `.livedoc` file is JSON with four blocks:

```json
{
  "meta":    { "title": "McdSaving Weekly", "avatar": "@your-avatar", "sensitive": true },
  "data_sources": [
    { "id": "my_coupons", "type": "mcp", "server": "mcd-mcp",
      "tool": "query-my-coupons", "args": {},
      "extract": { "coupon_count": "共\\s*(\\d+)\\s*张可用优惠券" },
      "fallback": { "coupon_count": 3 } }
  ],
  "compute": { "expiry_days": { "op": "days_until", "from": "coupon_expiry" } },
  "script":  [ { "shot": "Expiry alert", "speak": "This coupon expires in {expiry_days} days", "camera": "...", "visual": "..." } ]
}
```

- `data_sources`: `mcp` / `http` / `mock`; `extract` pulls fields from MCP text output via regex (`op: count` counts matches)
- `compute`: derived fields, e.g. days until a coupon expires
- `script`: storyboard shots; `{placeholders}` are replaced with real data

Full format definition: [`livedoc_schema.md`](livedoc_schema.md).

---

## Wiring the Digital-Avatar Layer

1. Create your digital avatar in Jimeng (App【出镜】→ record 10–15s → name it)
2. Put the avatar name into `meta.avatar` of your `.livedoc`
3. Feed each section of `<name>.jimeng.md` (narration + camera/visual) into Jimeng as per-shot prompts
4. Once rendered, the video is bound to LiveDoc's data — **data changes, re-run, regenerate**

---

## Status & Roadmap

- ✅ v0.2: MCP data sources, regex field extraction, derived computation, dual-mode privacy isolation
- ⬜ Call Jimeng's API to render automatically (currently the storyboard is pasted manually)
- ⬜ Visual editor for layout templates (currently `meta.layout` is a logical declaration)
- ⬜ More source adapters (database / Feishu sheets / enterprise BI)

---

## License

MIT © 2026 hanrixing
