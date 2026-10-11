#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LiveDoc 生成器 v0.2

读一份 .livedoc 规格 -> 拉数据源 -> 渲染两种产物：
  1. output/<name>.html          活文档预览（数据卡片 + 讲稿 + 来源标注）
  2. output/<name>.jimeng.md     给即梦的数字分身分镜讲稿

核心卖点：数据源是「声明式」的。数据变了，重跑本脚本，产物自动更新——
这就是和「死 PPT 转视频」的本质区别。

用法：
  python generator.py                                  # demo 模式（脱敏，可公开）
  python generator.py --live                           # 真实模式（拉真数据，产物勿公开）
  python generator.py ../spec/quarterly-report.livedoc # 指定规格

Token 获取优先级：
  1. 环境变量 MCD_MCP_TOKEN
  2. ~/.workbuddy/mcp.json（WorkBuddy 本机连接器配置）
"""

import os
import re
import json
import sys
import html
import datetime
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SPEC = ROOT / "spec" / "mcd-weekly.livedoc"
OUT_DIR = ROOT / "output"

# MCP 服务端点映射（可用环境变量 MCD_MCP_URL 覆盖）
MCP_SERVERS = {
    "mcd-mcp": os.environ.get("MCD_MCP_URL", "https://mcp.mcd.cn"),
}


# ---------- 加载与取值 ----------

def load_spec(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _nested_get(obj, path: str):
    """支持 'a.b.c' 点路径取值；取不到返回 None。"""
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def load_mcp_token() -> str | None:
    """读 MCP token：环境变量优先，其次本机 WorkBuddy 连接器配置。"""
    env = os.environ.get("MCD_MCP_TOKEN")
    if env:
        return env.strip()
    cfg = Path.home() / ".workbuddy" / "mcp.json"
    if cfg.exists():
        try:
            raw = cfg.read_text(encoding="utf-8")
            m = re.search(r'"Authorization"\s*:\s*"Bearer\s+([^"]+)"', raw)
            if m:
                return m.group(1)
        except OSError:
            pass
    return None


# ---------- 数据源拉取 ----------

def mcp_call(url: str, token: str, tool: str, args: dict, timeout: int = 25) -> str:
    """调用 MCP tools/call，返回拼接后的文本内容。"""
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool, "arguments": args or {}},
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    if "error" in res:
        raise RuntimeError(str(res["error"])[:200])
    parts = []
    for c in res.get("result", {}).get("content", []):
        if c.get("type") == "text":
            parts.append(c.get("text", ""))
    return "\n".join(parts) if parts else json.dumps(res.get("result"), ensure_ascii=False)


def extract_fields(text: str, rules: dict) -> dict:
    """按规则从文本抽取字段：正则取分组，或 count 计数。"""
    out = {}
    for key, rule in (rules or {}).items():
        try:
            if isinstance(rule, dict):
                if rule.get("op") == "count":
                    out[key] = len(re.findall(rule.get("pattern", ""), text))
                else:
                    out[key] = None
            else:
                m = re.search(rule, text)
                out[key] = m.group(1).strip() if m else None
        except re.error as e:
            print(f"  [warn] 抽取规则 {key} 正则有误：{e}")
            out[key] = None
    return out


def compute_fields(data: dict, rules: dict) -> None:
    """派生字段：从已有字段算出新值（如到期天数）。"""
    for key, rule in (rules or {}).items():
        op = rule.get("op")
        src = str(data.get(rule.get("from", ""), "") or "")
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", src)
        if op == "last_date":
            data[key] = dates[-1] if dates else None
        elif op == "days_until":
            if dates:
                try:
                    d = datetime.date.fromisoformat(dates[-1])
                    data[key] = (d - datetime.date.today()).days
                except ValueError:
                    data[key] = None
            else:
                data[key] = None


def fetch_all(spec: dict, live: bool) -> tuple[dict, list]:
    """拉取全部数据源，返回 (数据字典, 来源说明列表)。失败一律回退 fallback。"""
    dss = spec.get("data_sources")
    if not dss and spec.get("data_source"):
        dss = [spec["data_source"]]

    data: dict = {}
    sources: list = []
    token = load_mcp_token() if live else None

    for ds in (dss or []):
        sid = ds.get("id", ds.get("tool", "?"))
        dtype = ds.get("type", "mock")
        fb = dict(ds.get("fallback", {}) or {})

        # demo 模式：不联网，直接用脱敏示例值
        if not live or dtype == "mock":
            data.update(fb)
            sources.append(f"demo（脱敏示例）· {sid}")
            continue

        if dtype == "http":
            url = ds.get("url", "")
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "LiveDoc"})
                with urllib.request.urlopen(req, timeout=12) as resp:
                    blob = json.loads(resp.read().decode("utf-8"))
                for binding, path in (ds.get("fields", {}) or {}).items():
                    v = _nested_get(blob, path)
                    data[binding] = v if v is not None else fb.get(binding)
                sources.append(f"http 实时 · {url}")
            except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError) as e:
                print(f"  [warn] http 拉取失败（{e}），回退示例值")
                data.update(fb)
                sources.append(f"http 失败回退 · {sid}")

        elif dtype == "mcp":
            server = ds.get("server", "")
            url = ds.get("url") or MCP_SERVERS.get(server)
            tool = ds.get("tool", "")
            if not token:
                print(f"  [warn] 未取到 MCP token，{sid} 回退示例值")
                data.update(fb)
                sources.append(f"mcp 无 token 回退 · {tool}")
                continue
            if not url:
                print(f"  [warn] 未知 MCP server {server}，{sid} 回退示例值")
                data.update(fb)
                sources.append(f"mcp 未知端点回退 · {tool}")
                continue
            try:
                text = mcp_call(url, token, tool, ds.get("args", {}))
                vals = extract_fields(text, ds.get("extract", {}))
                for k, v in vals.items():
                    data[k] = v if v is not None else fb.get(k)
                    if v is None:
                        print(f"  [warn] 字段 {k} 未从返回中抽到，用示例值")
                sources.append(f"mcp 实时 · {tool}")
            except (urllib.error.URLError, urllib.error.HTTPError, OSError, RuntimeError, ValueError) as e:
                print(f"  [warn] mcp 调用失败（{e}），回退示例值")
                data.update(fb)
                sources.append(f"mcp 失败回退 · {tool}")

    compute_fields(data, spec.get("compute", {}))
    return data, sources


# ---------- 渲染 ----------

def bind(text: str, data: dict) -> str:
    out = text
    for k, v in data.items():
        out = out.replace("{" + k + "}", str(v if v is not None else "—"))
    return out


def render_html(spec: dict, data: dict, sources: list, ts: str, live: bool,
                sensitive: bool = True) -> str:
    meta = spec.get("meta", {})
    title = html.escape(meta.get("title", "LiveDoc"))
    avatar = html.escape(meta.get("avatar", ""))

    warn = ""
    if live and sensitive:
        warn = ('<div class="warn">⚠️ 真实模式产出：含个人账户券信息，'
                '<b>请勿公开分享本页</b>。要发布请用 <code>--demo</code> 重新生成。</div>')

    cards = "\n".join(
        f'<div class="card"><div class="num">{html.escape(str(v))}</div>'
        f'<div class="label">{html.escape(k)}</div></div>'
        for k, v in data.items()
    )

    shots = "\n".join(
        f'<li><b>第{i}镜 · {html.escape(seg.get("shot",""))}</b>'
        f'<p class="speak">{html.escape(bind(seg.get("speak",""), data))}</p>'
        f'<p class="meta">镜头：{html.escape(bind(seg.get("camera",""), data))}'
        f'<br>视觉：{html.escape(bind(seg.get("visual",""), data))}</p></li>'
        for i, seg in enumerate(spec.get("script", []), 1)
    )

    src_html = "\n".join(f"<li>{html.escape(s)}</li>" for s in sources)

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · LiveDoc 预览</title>
<style>
  body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
         margin:0; background:#0c1118; color:#e8edf2; padding:32px; }}
  h1 {{ font-size:22px; font-weight:600; margin:0 0 4px; }}
  .sub {{ color:#7e8a99; font-size:13px; margin-bottom:20px; }}
  .warn {{ background:#3a2418; border:1px solid #7a4a2a; color:#ffb27a;
           padding:10px 14px; border-radius:10px; font-size:13px; margin-bottom:20px; }}
  .cards {{ display:flex; flex-wrap:wrap; gap:14px; margin-bottom:24px; }}
  .card {{ background:#161d27; border:1px solid #25303d; border-radius:14px;
          padding:18px 26px; min-width:110px; }}
  .num {{ font-size:30px; font-weight:600; color:#46d3a0; font-variant-numeric:tabular-nums;
          word-break:break-all; }}
  .label {{ font-size:12px; color:#7e8a99; margin-top:6px; }}
  .doc {{ background:#121922; border:1px solid #25303d; border-radius:14px;
          padding:20px 26px; margin-bottom:18px; }}
  .doc h2 {{ font-size:15px; color:#9fb0c0; margin:0 0 12px; font-weight:600; }}
  ol {{ margin:0; padding-left:18px; }}
  li {{ margin-bottom:16px; line-height:1.6; }}
  .speak {{ color:#e8edf2; margin:4px 0; }}
  .meta {{ color:#7e8a99; font-size:12px; margin:2px 0; }}
  .src {{ color:#7e8a99; font-size:12px; line-height:1.8; }}
  .live {{ color:#46d3a0; font-size:12px; margin-top:14px; }}
</style></head>
<body>
<h1>{title}</h1>
<div class="sub">LiveDoc 活文档 · 数字分身：{avatar} · 生成于 {html.escape(ts)}</div>
{warn}
<div class="cards">{cards}</div>
<div class="doc"><h2>数字分身讲稿（{len(spec.get('script',[]))} 镜）</h2>
<ol>{shots}</ol>
<div class="live">数据变了？重跑 <code>generator.py</code>，卡片与讲稿同步刷新——这就是「活文档」。</div>
</div>
<div class="doc"><h2>数据来源</h2>
<ul class="src">{src_html}</ul>
</div>
</body></html>"""


def render_jimeng(spec: dict, data: dict, live: bool, sensitive: bool = True) -> str:
    meta = spec.get("meta", {})
    if not live:
        mode_txt = "demo 脱敏示例"
    elif sensitive:
        mode_txt = "真实数据（含个人信息，勿公开）"
    else:
        mode_txt = "真实数据（公开数据源，可分享）"
    lines = [
        f"# 即梦数字分身分镜讲稿 · {meta.get('title','')}",
        "",
        f"- 数字分身：`{meta.get('avatar','')}`",
        f"- 总镜数：{len(spec.get('script',[]))}",
        f"- 数据快照：{json.dumps(data, ensure_ascii=False)}",
        f"- 模式：{mode_txt}",
        "",
        "> 每段对应即梦一镜。讲稿已用实时数据填充，`{占位符}` 已替换。",
        "",
    ]
    for i, seg in enumerate(spec.get("script", []), 1):
        lines += [
            f"## 第 {i} 镜 · {seg.get('shot','')}",
            "",
            f"**讲稿（口播）**：{bind(seg.get('speak',''), data)}",
            "",
            f"**镜头**：{bind(seg.get('camera',''), data)}",
            f"**视觉**：{bind(seg.get('visual',''), data)}",
            "",
            "---",
            "",
        ]
    return "\n".join(lines)


# ---------- 主流程 ----------

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    live = "--live" in sys.argv

    spec_path = Path(args[0]) if args else DEFAULT_SPEC
    if not spec_path.exists():
        print(f"[error] 找不到规格文件：{spec_path}")
        sys.exit(1)

    mode = "真实模式（--live）" if live else "demo 模式（脱敏示例）"
    print(f"[1/4] 读取规格：{spec_path.name}　模式：{mode}")
    spec = load_spec(spec_path)

    print(f"[2/4] 拉取数据 ...")
    data, sources = fetch_all(spec, live)
    print(f"      数据：{json.dumps(data, ensure_ascii=False)}")
    for s in sources:
        print(f"      来源：{s}")

    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 含个人数据（sensitive）的真实产物隔离到 output/live/（已 gitignore），
    # 公开数据源的真实产物可直接留在 output/ 供分享
    sensitive = bool(spec.get("meta", {}).get("sensitive", True))
    out_dir = (OUT_DIR / "live") if (live and sensitive) else OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = spec_path.stem

    print(f"[3/4] 渲染 HTML 预览 -> {out_dir.relative_to(ROOT)}/{stem}.html")
    (out_dir / f"{stem}.html").write_text(
        render_html(spec, data, sources, ts, live, sensitive), encoding="utf-8")

    print(f"[4/4] 渲染即梦讲稿 -> {out_dir.relative_to(ROOT)}/{stem}.jimeng.md")
    (out_dir / f"{stem}.jimeng.md").write_text(
        render_jimeng(spec, data, live, sensitive), encoding="utf-8")

    print(f"\n完成。产物在 {out_dir}/")
    if live and sensitive:
        print("⚠️  真实模式产物含个人数据，请勿公开分享。")
    print("打开 .html 看活文档；.jimeng.md 直接喂给即梦做数字分身视频。")


if __name__ == "__main__":
    main()
