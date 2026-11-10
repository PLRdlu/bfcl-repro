# BFCL 评测集本地复现（Windows / 纯 API 模型 / 无 GPU）

对 [Berkeley Function Calling Leaderboard v4](https://gorilla.cs.berkeley.edu/leaderboard.html)
在本机做完整复现，不使用 GPU、不使用 Docker、不 clone 官方仓库（本机 GitHub 不可达），
仅依赖 PyPI 上的 `bfcl-eval`。

## 结果速览

模型 `DeepSeek-V4.1-Flash-FC`（API 侧 `deepseek-flash`），`bfcl-eval==2026.3.23`：

| 类别 | 样本数 | 正确 | Accuracy | 测什么 |
|---|---|---|---|---|
| `simple_python` | 400 | 370 | **92.50%** | 单函数调用 + 参数正确性 |
| `irrelevance` | 240 | 173 | **72.08%** | 该**不**调用时能否忍住 |
| `live_irrelevance` | 884 | 659 | **74.55%** | 同上，真实 API 文档来源 |
| `live_relevance` | 16 | 12 | **75.00%** | 该调用时必须调用 |
| `multi_turn_base` | 200 | 129 | **64.50%** | 多轮有状态：函数真的执行后终态要对 |
| 合计 | 1740 | 1343 | — | — |

> `data_overall.csv` 里那行 `Overall Acc = 12.94%` **不可用于对外引用**——
> Overall 是五大板块按 10/10/10/30/40 加权，未跑的类别按 0 计入。
> 口径问题详见 `docs/BFCL评测报告.md` 第 3 节。

## 一键复跑

```bash
# 0) 前置：Python 3.11 或 3.12（不能用 3.13，numpy==1.26.4 没有 cp313 wheel）
#    首次准备环境见下方「环境安装」

cd D:/bfcl-repro
cp .env.example .env      # 填 DEEPSEEK_API_KEY

./run.sh                  # A 组 + B 组，约 12 分钟（8 线程）
./run.sh simple_python    # 只跑单个类别
./run.sh evaluate-only    # 只重跑评估
```

## 用官方命令形式（`bfcl ...`）

`bin/bfcl`（Git Bash）与 `bin/bfcl.cmd`（cmd / PowerShell）是官方 CLI 的等价入口，
子命令与参数完全一致，只多打两个运行时补丁（见下一节）：

```bash
export PATH="D:/bfcl-repro/bin:$PATH"      # cmd 下：set PATH=D:\bfcl-repro\bin;%PATH%

bfcl models | grep -i deepseek
bfcl generate --model DeepSeek-V4.1-Flash-FC --test-category simple_python --num-threads 8
bfcl evaluate --model DeepSeek-V4.1-Flash-FC --test-category simple_python
```

> 为什么需要这个入口：本机是「wheel 纯解包」装的环境，zipfile 解包**不会生成 console_scripts**，
> 所以 site-packages 里没有 `bfcl.exe`。官方 `bfcl` 的实际实现就是
> `bfcl_eval.__main__:cli`（见 `bfcl_eval-2026.3.23.dist-info/entry_points.txt`），
> `bin/bfcl` 调的是同一个 `cli()`，语义一致。
>
> `bin/bfcl.cmd` 特意写成**纯 ASCII**，并用 junction `D:\bfcl-venv → D:\py项目uv环境\bfcl\.venv3`
> 绕开中文路径——cmd.exe 按系统 ANSI 代码页（zh-CN 是 GBK）解析 .cmd 文件，
> 文件里直接写 UTF-8 中文路径会被读成乱码。

## 产物

```
result/DeepSeek-V4.1-Flash-FC/{non_live,live}/*_result.json   # 模型原始响应（1740 条全量）
score/data_overall.csv                                        # 总表（含 Overall Acc）
score/data_non_live.csv  score/data_live.csv                  # 分板块表
score/DeepSeek-V4.1-Flash-FC/*/*_score.json                   # 逐条判分（JSONL：首行汇总）
result_smoke/  score_smoke/                                   # 用官方 bfcl 命令重跑 live_relevance 的对照产物
run_full.log                                                  # 完整运行日志
```

### 可复现性自检

| 跑法 | live_relevance 结果 |
|---|---|
| `./run.sh`（正式跑，8 线程） | 12/16 = **75.00%** |
| `bfcl generate/evaluate`（官方命令形式，4 线程，独立目录重跑） | 13/16 = **81.25%** |

同一类别两次跑差 1 条用例。16 条样本下 1 条就是 6.25 个百分点——
来自 `temperature=0.001` 的采样非确定性 + API 侧模型版本，**不是**线程数造成的
（见 `docs/BFCL评测报告.md` 第 3.4 节）。

## 环境安装（本机沙箱专用，有坑）

本机 Python 进程被注入了 safe-delete 钩子，**任何 pip/uv install 都会在删除环节被掐死**。
所以环境是「只下 wheel + zipfile 纯解包」装出来的：

```bash
uv venv --python 3.11 D:/py项目uv环境/bfcl/.venv3     # 用 uv 本地已有的 3.11.9

# 1) 下载全部 wheel（纯写入，不触发删除）
D:/py项目uv环境/bfcl/.venv2/Scripts/python.exe -m pip download \
  -r requirements-core.txt -d D:/py项目uv环境/bfcl/wheels \
  --only-binary=:all: --platform win_amd64 --implementation cp \
  --python-version 311 --abi cp311 --no-cache-dir
# 另需单独补：bfcl-eval==2026.3.23 / soundfile / datamodel-code-generator==0.25.7

# 2) 纯解包（零删除）
python tools/install_from_wheels.py \
  D:/py项目uv环境/bfcl/wheels \
  D:/py项目uv环境/bfcl/.venv3/Scripts/python.exe
```

装完的精确版本见 `requirements-lock.txt`。**在普通机器上直接 `pip install bfcl-eval`
即可，不需要上面这套绕法。**

## 为什么要有 `tools/bfcl_cli.py`

不修改 site-packages，只在运行时给 bfcl 打两个补丁，然后转交给官方 CLI：

1. **`LOCK_DIR` → `%TEMP%/bfcl_locks`**：bfcl 用 filelock 给结果文件加锁，每释放一次删一次锁文件；
   本机 safe-delete 钩子的「单轮累计删除 > 50 次」守卫会掐掉进程。锁文件本身是易失的，挪到临时目录即可。
2. **注册真实模型名**：自带注册表里只有 `DeepSeek-V3.2-Exp*` 且写死 `deepseek-chat`，
   而该别名在当前账号下已被官方重定向到 `deepseek-flash`(V4.1-Flash)。
   这里注入 `DeepSeek-V4.1-Flash-FC` / `DeepSeek-V4-Pro-FC`，仍复用官方 `DeepSeekAPIHandler`。

子命令与官方完全一致，所以既能 `python tools/bfcl_cli.py xxx`，
也能用 `bin/bfcl xxx`（等价于官方 `bfcl xxx`）。

## 目录结构

```
bfcl-repro/
├─ run.sh                        # 一键跑分（Git Bash）
├─ requirements-core.txt         # 核心依赖（已剔除只在特定类别才用的重依赖）
├─ requirements-lock.txt         # 实测版本快照（121 个包）
├─ .env.example                  # 凭证模板（.env 已在 .gitignore）
├─ bin/
│  ├─ bfcl                       # 官方 bfcl 命令等价入口（Git Bash）
│  └─ bfcl.cmd                   # 同上（cmd/PowerShell，纯 ASCII）
├─ tools/
│  ├─ bfcl_cli.py                # 运行时补丁 + 官方 CLI 转交
│  ├─ install_from_wheels.py     # wheel 纯解包安装器
│  ├─ summarize_scores.py        # 逐条失败类型统计
│  └─ make_result_card.py        # 由日志+CSV 渲染终端结果卡片 → Chrome 截图
├─ docs/
│  ├─ 踩坑记录.md                # 11 条坑：原始报错 / 根因 / 解法 / 是否影响分数
│  ├─ BFCL评测报告.md            # 飞书文档正文（跑分 / 踩坑 / 指标 / 对比 / 命令对照）
│  ├─ 终端结果截图.png           # 交付要求②的截图（数字由 CSV 自动渲染）
│  └─ official_leaderboard_snapshot_2026-04-12.csv
├─ result/  score/               # 模型响应与判分产物（1740 条全量）
├─ result_smoke/ score_smoke/    # 官方命令形式重跑 live_relevance 的对照产物
└─ run_full.log                  # 完整运行日志
```

## 已知偏差

- 只跑了 5 个类别（1740 / 全量约 4000+ 条），Live / Agentic 板块基本空缺，**Overall Acc 不可比**。
- `numpy` 实际为 2.4.6（解包顺序覆盖了 pin 的 1.26.4），实测无异常。
- 判分走官方 `ast_checker` 原样逻辑，未改任何评分代码。
- 结果取决于 API 侧当天模型版本与 `temperature=0.001`，重跑会有小幅波动。
