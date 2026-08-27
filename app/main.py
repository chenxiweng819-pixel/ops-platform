import json
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, Field

from runner import run_playbook

app = FastAPI(title="一键式部署")

JOBS_FILE = Path(__file__).parent / "jobs.json"


class DeployRequest(BaseModel):
    app_version: str = Field(..., description="app版本")
    playbook: str = Field("deploy-nginx.yml", description="...")


def read_jobs():
    
    if JOBS_FILE.exists():
        return json.loads(JOBS_FILE.read_text())
    return []


def _run_playbook(playbook: str, app_version: str):
    result = run_playbook(playbook, {"app_version": app_version})
    print(f"[{result['status']}] rc={result['rc']} stats={result['stats']}")

    
    jobs = read_jobs()
    jobs.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": app_version,
        "status": result["status"],
        "rc": result["rc"],
    })
    JOBS_FILE.write_text(json.dumps(jobs, ensure_ascii=False, indent=2))


@app.post("/deploy")
async def deploy(body: DeployRequest, background: BackgroundTasks):
    background.add_task(_run_playbook, body.playbook, body.app_version)
    return {"status": "同意", "msg": f"开始部署{body.app_version}"}


@app.get("/status")
async def status():
    return {"status": "正常"}


@app.get("/jobs")
async def jobs():
    return read_jobs()
