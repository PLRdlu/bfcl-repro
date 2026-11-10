"""
把真实运行日志 + 真实分数 CSV 渲染成一张"终端结果卡片"HTML，再用 Chrome 截图。

为什么这么做：交付要求里要「results 文件或终端结果截图」。分数本身来自
score/*.csv 与 result/*.json（原始产物都在仓库里），这里只是把同样的数据
渲染成一张可贴进飞书文档的图，**不手工输入任何数字**。

用法：
    python tools/make_result_card.py
# 然后用 Chrome 截图：
    chrome --headless=new --screenshot=docs/终端结果截图.png --window-size=1280,1000 \
           file:///D:/bfcl-repro/docs/_result_card.html
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# 按运行先后拼接：run_full.log = A 组 + B 组，mt_eval.log = 后补的 multi_turn_base
LOG_FILES = ("run_full.log", "mt_eval.log")
OUT_HTML = ROOT / "docs" / "_result_card.html"
SUBTITLE = (
    "DeepSeek-V4.1-Flash (FC) &nbsp;|&nbsp; bfcl-eval 2026.3.23 &nbsp;|&nbsp; Python 3.11.9 &nbsp;|&nbsp; "
    "5 类别 1740 条全量 &nbsp;|&nbsp; 2026-11-10 &nbsp;|&nbsp; 下列内容由运行日志与 score/*.csv 自动渲染"
)

KEEP = re.compile(
    r"(Running full test cases|✅ Test completed|100%\|.*\|\s*\d+/\d+|"
    r"🏁 Evaluation completed|🦍 Model|🔍 Running test)"
)
PROGRESS = re.compile(r"100%\|[^|]*\|\s*(\d+)/(\d+)")

lines, seen = [], set()
for log_name in LOG_FILES:
    log_path = ROOT / log_name
    if not log_path.exists():
        continue
    raw = log_path.read_text(encoding="utf-8", errors="replace").replace("\r", "\n")
    for line in raw.split("\n"):
        line = line.strip()
        if not line or not KEEP.search(line):
            continue
        # tqdm 的进度行只保留「每个总数最后一次 100%」，并且压成一行摘要
        m = PROGRESS.search(line)
        if m:
            done, total = m.group(1), m.group(2)
            if total in ("1", "0"):
                # 「Number of models evaluated: 1/1」这类汇总进度没有信息量
                continue
            key = f"__progress_{total}"
            snippet = f"  [进度] {done}/{total} 条完成"
            if key in seen:
                idx = [i for i, l in enumerate(lines) if l.endswith(f"/{total} 条完成")]
                if idx:
                    lines[idx[-1]] = snippet
                continue
            seen.add(key)
            line = snippet
        if line in seen:
            continue
        seen.add(line)
        lines.append(line)

csv_rows = {}
for name in ("data_non_live.csv", "data_live.csv", "data_multi_turn.csv"):
    rows = (ROOT / "score" / name).read_text(encoding="utf-8").strip().splitlines()
    csv_rows[name] = rows

term_html = "\n".join(
    f'<div class="ln{" ok" if "✅" in l else ""}">{html.escape(l)}</div>' for l in lines
)

tables = ""
for name, rows in csv_rows.items():
    head = rows[0].split(",")
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r.split(",")) + "</tr>"
        for r in rows[1:]
    )
    tables += (
        f'<div class="card"><div class="cap">score/{name}</div>'
        f'<table><thead><tr>'
        + "".join(f"<th>{html.escape(h)}</th>" for h in head)
        + f"</tr></thead><tbody>{body}</tbody></table></div>"
    )

OUT_HTML.write_text(
    f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin:0; padding:28px 32px 32px; width:1280px;
         font-family:"Segoe UI","Microsoft YaHei",sans-serif; background:#f4f6f8; color:#1f2328; }}
  h1 {{ font-size:20px; margin:0 0 4px; }}
  .sub {{ font-size:13px; color:#5b6572; margin-bottom:18px; }}
  .term {{ background:#12161c; border-radius:10px; padding:16px 18px; font-family:Consolas,"Cascadia Mono",monospace;
          font-size:13px; line-height:1.75; color:#c9d4e0; white-space:pre-wrap; word-break:break-all; }}
  .term .ok {{ color:#5fd18a; }}
  .cap {{ font-size:12px; color:#5b6572; margin:18px 0 6px; font-family:Consolas,monospace; }}
  table {{ width:100%; border-collapse:collapse; background:#fff; font-size:13px;
          box-shadow:0 1px 2px rgba(0,0,0,.07); border-radius:8px; overflow:hidden; }}
  th,td {{ padding:7px 10px; text-align:left; border-bottom:1px solid #eaeef2; }}
  th {{ background:#eef2f6; font-weight:600; color:#33404f; font-size:12px; }}
  td:nth-child(n+3) {{ font-family:Consolas,monospace; }}
  tbody tr:last-child td {{ border-bottom:none; }}
</style></head>
<body>
  <h1>BFCL v4 本地复现 · 终端结果</h1>
  <div class="sub">{SUBTITLE}</div>
  <div class="term">{term_html}</div>
  {tables}
</body></html>
""",
    encoding="utf-8",
)

print(f"[OK] {OUT_HTML}")
for l in lines:
    print("  ", l)
