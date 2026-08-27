from pathlib import Path
from typing import Dict, Optional
import ansible_runner

PRIVATE_DATA_DIR =Path("/opt/ops/runner")

def run_playbook(playbook: str, extravars: Optional[Dict[str, str]] = None  )  -> dict:
    r = ansible_runner.run(
        private_data_dir=str(PRIVATE_DATA_DIR),
        playbook=playbook,
        extravars=extravars or {},

    )
    return {
    "status": r.status,
    "rc": r.rc,
    "stats": r.stats,
    }
