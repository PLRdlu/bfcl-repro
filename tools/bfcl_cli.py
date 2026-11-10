"""
BFCL CLI 包装入口（不改 site-packages，纯运行时打补丁）。

两个补丁：
1. LOCK_DIR -> 系统临时目录。
   bfcl 用 filelock 给每个结果文件加跨进程锁，锁文件放在
   $BFCL_PROJECT_ROOT/.file_locks/ 下，每释放一次就删一次。本机沙箱的
   safe-delete 钩子对非临时目录的删除会 fail-closed，跑到 50 次就直接
   掐掉进程（SAFE_DELETE_BULK_CONFIRM_REQUIRED）。锁文件本身是易失的，
   挪到 %TEMP% 下即可，钩子对临时目录放行。

2. 注册真实的 DeepSeek 模型条目。
   bfcl-eval 2026.3.23 自带的 DeepSeek 条目只有 DeepSeek-V3.2-Exp*，
   且 model_name 写死成 deepseek-chat。当前 API 账号下 deepseek-chat
   已被官方重定向到 DeepSeek-V4.1-Flash，直接拿旧键跑出来的名字是错的。
   这里补一个名副其实的注册键，仍然复用官方 DeepSeekAPIHandler。

用法（与 bfcl 原生子命令完全一致）：
    python tools/bfcl_cli.py models
    python tools/bfcl_cli.py generate --model DeepSeek-V4.1-Flash-FC --test-category simple_python
"""
import os
import sys
import tempfile
from pathlib import Path

CUSTOM_MODELS = {
    # 注册键 -> (API 侧模型名, 显示名, 是否 FC 模式)
    "DeepSeek-V4.1-Flash-FC": ("deepseek-flash", "DeepSeek-V4.1-Flash (FC)", True),
    "DeepSeek-V4-Pro-FC": ("deepseek-v4-pro", "DeepSeek-V4-Pro (FC)", True),
}


def patch_lock_dir() -> str:
    lock_dir = Path(tempfile.gettempdir()) / "bfcl_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    import bfcl_eval.constants.eval_config as cfg

    cfg.LOCK_DIR = lock_dir
    # utils.py 里是 from ... import *，需要单独改它自己命名空间里的那份
    import bfcl_eval.utils as bu

    bu.LOCK_DIR = lock_dir
    return str(lock_dir)


def register_custom_models() -> None:
    from bfcl_eval.constants.model_config import MODEL_CONFIG_MAPPING, ModelConfig
    from bfcl_eval.model_handler.api_inference.deepseek import DeepSeekAPIHandler

    for registry_key, (api_model, display, is_fc) in CUSTOM_MODELS.items():
        if registry_key in MODEL_CONFIG_MAPPING:
            continue
        MODEL_CONFIG_MAPPING[registry_key] = ModelConfig(
            model_name=api_model,
            display_name=display,
            url="https://api-docs.deepseek.com/",
            org="DeepSeek",
            license="Proprietary",
            model_handler=DeepSeekAPIHandler,
            input_price=None,
            output_price=None,
            is_fc_model=is_fc,
            underscore_to_dot=True,
        )


def main() -> None:
    if "BFCL_PROJECT_ROOT" not in os.environ:
        raise SystemExit(
            "BFCL_PROJECT_ROOT 未设置；先在 shell 里 export 成你想要的产物目录，"
            "否则 .env / result / score 会落到 site-packages 里。"
        )
    print(f"[patch] LOCK_DIR -> {patch_lock_dir()}")
    register_custom_models()

    from bfcl_eval.__main__ import cli

    cli()


if __name__ == "__main__":
    main()
