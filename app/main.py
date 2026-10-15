import json
import sqlite3
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

from runner import run_playbook, runner_ready

DB_FILE = Path(__file__).parent / "jobs.db"
_submit_lock = threading.Lock()          # 保证“检查有无进行中任务 + 插入新任务”是原子的


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE, timeout=10)   # 每次新建连接，线程安全；写锁等待最多 10 秒
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY, playbook TEXT, version TEXT, target TEXT,
            status TEXT, rc INTEGER, stats TEXT,
            created TEXT, started TEXT, finished TEXT)""")
        # 进程重启后，上次没跑完的任务不会再有人更新，显式标记为 lost
        conn.execute("UPDATE jobs SET status='lost', finished=? "
                     "WHERE status IN ('queued','running')", (now(),))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="一键式部署", lifespan=lifespan)


class DeployRequest(BaseModel):
    # 只允许版本号常见字符，挡住 {{ }} 之类的模板表达式和路径符号
    app_version: str = Field(..., pattern=r"^[0-9A-Za-z][0-9A-Za-z._-]{0,31}$")
    # 白名单：只能触发登记过的剧本
    playbook: Literal["deploy-nginx.yml"] = "deploy-nginx.yml"
    # 可选：只对部分主机执行（失败主机重试用）
    limit: Optional[str] = Field(None, pattern=r"^[A-Za-z0-9_.:,-]{1,128}$")


def _set(job_id: str, **cols) -> None:
    keys = ", ".join(f"{k}=?" for k in cols)
    with db() as conn:
        conn.execute(f"UPDATE jobs SET {keys} WHERE job_id=?", (*cols.values(), job_id))


def _execute(job_id: str, playbook: str, app_version: str, limit: Optional[str]) -> None:
    _set(job_id, status="running", started=now())
    try:
        result = run_playbook(playbook, {"app_version": app_version},
                              ident=job_id, limit=limit,
                              on_status=lambda s: _set(job_id, status=s))
        _set(job_id, status=result["status"], rc=result["rc"],
             stats=json.dumps(result["stats"]), finished=now())
    except Exception as e:                       # runner 自身抛异常也要落库，不能让任务“消失”
        _set(job_id, status="error", stats=json.dumps({"error": str(e)}), finished=now())


@app.post("/deploy", status_code=202)
def deploy(body: DeployRequest, background: BackgroundTasks):
    target = f"{body.playbook}|{body.limit or 'all'}"
    with _submit_lock:
        with db() as conn:
            busy = conn.execute("SELECT job_id FROM jobs WHERE target=? AND status IN "
                                "('queued','starting','running')", (target,)).fetchone()
            if busy:
                raise HTTPException(409, f"同一目标已有任务在执行：{busy['job_id']}")
            job_id = uuid.uuid4().hex
            conn.execute("INSERT INTO jobs (job_id, playbook, version, target, status, created) "
                         "VALUES (?,?,?,?,?,?)",
                         (job_id, body.playbook, body.app_version, target, "queued", now()))
    background.add_task(_execute, job_id, body.playbook, body.app_version, body.limit)
    return {"job_id": job_id, "status": "queued"}


@app.get("/status")
def status():
    checks = runner_ready()
    with db() as conn:
        n = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    return {"status": "ok" if all(checks.values()) else "degraded",
            "checks": checks, "jobs_recorded": n}


@app.get("/jobs")
def jobs(limit: int = 50):
    with db() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created DESC LIMIT ?",
                            (min(limit, 500),)).fetchall()
    return [dict(r) for r in rows]


@app.get("/jobs/{job_id}")
def job_detail(job_id: str):
    with db() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "job not found")
    return dict(row)
