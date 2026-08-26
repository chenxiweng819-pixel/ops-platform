"""运维部署 API —— 接入 ansible-runner 版本

启动（在 app/ 目录下）：
    uvicorn main:app --host 0.0.0.0 --port 8000
文档：
    http://服务器IP:8000/docs
"""
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, Field

from runner import run_playbook   # 引入 ansible-runner 封装

app = FastAPI(title="ops-platform 部署 API")


class DeployRequest(BaseModel):
    """部署请求体，Pydantic 自动做字段校验。"""
    app_version: str = Field(..., description="发布版本，如 1.0.0")
    playbook: str = Field("deploy-nginx.yml", description="project/ 下的 playbook 文件名")


def _run_playbook(playbook: str, version: str) -> None:
    """后台线程执行 playbook，打印真实结果。

    关键点：ansible_runner.run() 是同步阻塞的（跑完才返回），
    FastAPI 的 BackgroundTasks 把它丢到线程池执行，接口立即返回不卡住。
    """
    result = run_playbook(playbook, {"app_version": version})
    print(f"[{result['status']}] rc={result['rc']} stats={result['stats']}")


@app.post("/deploy")
async def deploy(body: DeployRequest, background: BackgroundTasks):
    """提交部署任务：立即返回，playbook 在后台执行。"""
    background.add_task(_run_playbook, body.playbook, body.app_version)
    return {"status": "accepted", "msg": f"开始部署 v{body.app_version}"}


@app.get("/health")
async def health():
    """存活探活接口。"""
    return {"status": "ok"}
