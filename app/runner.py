"""runner.py —— ansible-runner 封装层（核心：把 CLI 运维能力变成可调用函数）

对应命令行：
    ansible-playbook -i inventory/hosts project/deploy-nginx.yml -e "app_version=1.0.0"

private_data_dir 目录约定（服务器上）：
    /opt/ops/runner/project/    放 playbook
    /opt/ops/runner/inventory/  放主机清单
"""
from pathlib import Path

import ansible_runner

# 服务器上的绝对路径；本地调试时改成你自己的路径
PRIVATE_DATA_DIR = Path("/opt/ops/runner")


def run_playbook(playbook: str, extravars: dict[str, str] | None = None) -> dict:
    """执行指定 playbook，返回 {status, rc, stats}。

    Args:
        playbook: 相对 <private_data_dir>/project/ 的文件名，如 "deploy-nginx.yml"
        extravars: 运行时变量，对应命令行 -e '{"key": "value"}'

    Returns:
        {"status": "successful|failed|canceled|timeout",
         "rc": 退出码, "stats": 每台主机统计}
    """
    r = ansible_runner.run(
        private_data_dir=str(PRIVATE_DATA_DIR),
        playbook=playbook,
        extravars=extravars or {},
    )
    return {
        "status": r.status,
        "rc": r.rc,
        "stats": r.stats,   # {'ok': 1, 'changed': 0, ...}
    }
