"""统计各评测类别的正确/失败细节（score 文件是 JSONL：第 1 行汇总，其余每行一条用例）。

输出可直接贴进交付文档。
"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "score" / "DeepSeek-V4.1-Flash-FC"


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


for score_file in sorted(MODEL_DIR.glob("*/*_score.json")):
    lines = list(read_jsonl(score_file))
    summary, entries = lines[0], lines[1:]
    print("=" * 72)
    print(f"{score_file.parent.name}/{score_file.name}")
    print(
        f"  accuracy={summary.get('accuracy'):.4f}  "
        f"correct={summary.get('correct_count')}/{summary.get('total_count')}"
    )
    fails = [r for r in entries if not r.get("valid")]
    print(f"  detail_entries={len(entries)}  fails={len(fails)}")

    for et, n in Counter(str(r.get("error_type")) for r in fails).most_common(8):
        print(f"    {n:5d}  {et}")

    print("  --- 失败样例 2 条 ---")
    for r in fails[:2]:
        err = r.get("error")
        err = err[0] if isinstance(err, list) and err else err
        print(f"    [{r.get('id')}] {str(err)[:160]}")
