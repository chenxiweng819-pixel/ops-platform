import json
import uuid
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, Field

from runner import run_playbook

app = FastAPI(title="一键式部署")

JOBS_FILE = Path(__file__).parent / "jobs.json"


class DeployRequest(BaseModel):
    app_version: str = Field(..., description="app版本")
    playbook: str = Field("deploy-nginx.yml", description="playbook文件名")


def read_jobs():

    if JOBS_FILE.exists():
        return json.loads(JOBS_FILE.read_text())
    return []


def _run_playbook(job_id: str, playbook: str, app_version: str):
    result = run_playbook(playbook, {"app_version": app_version})
    print(f"[{job_id}] [{result['status']}] rc={result['rc']} stats={result['stats']}")

    # 原子写：先写临时文件再替换，防止写一半进程挂掉损坏 jobs.json
    jobs = read_jobs()
    jobs.append({
        "job_id": job_id,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "playbook": playbook,
        "version": app_version,
        "status": result["status"],
        "rc": result["rc"],
    })
    tmp = JOBS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(jobs, ensure_ascii=False, indent=2))
    tmp.replace(JOBS_FILE)


@app.post("/deploy")
async def deploy(body: DeployRequest, background: BackgroundTasks):
    job_id = uuid.uuid4().hex[:8]
    background.add_task(_run_playbook, job_id, body.playbook, body.app_version)
    return {"job_id": job_id, "status": "accepted", "msg": f"开始部署 {body.app_version}"}


@app.get("/status")
async def status():
    return {
        "status": "ok",
        "runner_dir_ready": JOBS_FILE.parent.exists(),
        "jobs_recorded": len(read_jobs()),
    }


@app.get("/jobs")
async def jobs():
    return read_jobs()


@app.get("/jobs/{job_id}")
async def job_detail(job_id: str):
    for j in read_jobs():
        if j.get("job_id") == job_id:
            return j
    return {"error": "job not found"}
