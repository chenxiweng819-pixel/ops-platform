import shutil
from pathlib import Path
from typing import Callable, Dict, Optional

import ansible_runner

PRIVATE_DATA_DIR = Path("/opt/ops/runner")


def run_playbook(playbook: str,
                 extravars: Optional[Dict[str, str]] = None,
                 ident: Optional[str] = None,
                 limit: Optional[str] = None,
                 on_status: Optional[Callable[[str], None]] = None) -> dict:
    r = ansible_runner.run(
        private_data_dir=str(PRIVATE_DATA_DIR),
        playbook=playbook,
        extravars=extravars or {},
        ident=ident,                 # 产物目录 artifacts/<job_id>，日志和任务一一对应
        limit=limit,                 # 等价于 ansible-playbook --limit，失败主机定向重试
        suppress_env_files=True,     # 不把 extravars 落盘到共享的 env/extravars
        rotate_artifacts=200,        # 只保留最近 200 次运行的产物，防止磁盘被占满
        timeout=1800,                # 单次部署最长 30 分钟，超时 status=timeout
        quiet=True,                  # 不把 Ansible 输出刷到 uvicorn 日志
        status_handler=(lambda data, runner_config: on_status(data["status"]))
        if on_status else None,
    )
    return {"status": r.status, "rc": r.rc, "stats": r.stats or {}}


def runner_ready() -> dict:
    return {
        "project_dir": (PRIVATE_DATA_DIR / "project").is_dir(),
        "inventory": (PRIVATE_DATA_DIR / "inventory").exists(),
        "ansible_playbook": shutil.which("ansible-playbook") is not None,
    }
