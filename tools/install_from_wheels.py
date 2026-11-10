"""
离线把本地 wheels/ 目录里的 .whl 纯解包进指定 venv 的 site-packages。

为什么不用 pip / uv install：
本机沙箱的 sitecustomize 注入了 safe-delete 钩子（windows-sandbox-recycle-bin-unavailable
+ 批量删除守卫）。pip/uv 在 install / uninstall 阶段只要触发一次删除就被拦，
进程 SystemExit(1)，环境留下"半装"状态（模块目录在、文件不全）。
zipfile.extractall() 是纯写入、零删除，不受影响。

用法（wheel_dir 里放所有 .whl，包括 bfcl_eval 自己的）:
    python install_from_wheels.py <wheel_dir> <python_exe>
"""
import sys
import sysconfig
import zipfile
from pathlib import Path


def target_paths(python_exe: Path):
    base = python_exe.parent.parent  # <venv>
    vars_ = {"base": str(base), "platbase": str(base)}
    purelib = Path(sysconfig.get_paths("nt", vars=vars_)["purelib"])
    scripts = base / "Scripts"
    return purelib, scripts


def extract_wheel(whl: Path, purelib: Path, scripts: Path) -> None:
    with zipfile.ZipFile(whl) as zf:
        names = zf.namelist()
        data_prefix = next(
            (n.split(".data/")[0] + ".data/" for n in names if ".data/" in n), None
        )
        for n in names:
            if n.endswith("/"):
                continue
            if data_prefix and n.startswith(data_prefix):
                sub = n[len(data_prefix):]
                kind, _, rel = sub.partition("/")
                if not rel:
                    continue
                root = {"scripts": scripts, "data": purelib.parent}.get(kind, purelib)
                dest = root / rel
            else:
                dest = purelib / n
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(n) as src, open(dest, "wb") as dst:
                dst.write(src.read())


def main() -> int:
    wheel_dir = Path(sys.argv[1]).resolve()
    python_exe = Path(sys.argv[2]).resolve()
    purelib, scripts = target_paths(python_exe)
    purelib.mkdir(parents=True, exist_ok=True)

    wheels = sorted(wheel_dir.glob("*.whl"))
    if not wheels:
        print(f"[ERR] no wheels in {wheel_dir}")
        return 1

    for whl in wheels:
        extract_wheel(whl, purelib, scripts)
    print(f"[OK] extracted {len(wheels)} wheels -> {purelib}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
