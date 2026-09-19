# ops-platform 运维自动化平台

基于 FastAPI + Ansible Runner 的运维自动化 API，把 playbook 封装成可调用的 Web 接口。

## 技术栈
- FastAPI（Web API）+ Pydantic（数据校验）
- ansible-runner（Ansible Python API）
- JSON 文件持久化（部署历史 jobs.json）

## 功能
- [x] 项目骨架 / 部署服务 API
- [x] Playbook 一键触发 API（ansible-runner 接入，返回结构化 status / rc / stats）
- [x] BackgroundTasks 异步执行（响应先返回，后台执行 Playbook）
- [x] 部署历史持久化（jobs.json，含 job_id / 时间 / 剧本 / 版本 / 状态 / 退出码）
- [x] job_id 追踪（POST /deploy 返回 job_id，GET /jobs/{job_id} 查询单次部署）
- [x] 健康检查（GET /status）

## Roadmap
- [ ] SQLite 任务存储（替代 jobs.json，解决并发写竞态）
- [ ] JWT 认证
- [ ] WebSocket 实时日志（基于 ansible-runner 事件流）
- [ ] Celery + Redis 任务队列（任务持久化、失败重试、多 worker）

## 接口一览
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /deploy | 触发部署，返回 job_id，异步执行 Playbook |
| GET | /status | 健康检查（runner 目录状态、历史记录数） |
| GET | /jobs | 部署历史列表 |
| GET | /jobs/{job_id} | 单次部署详情 |

## 快速开始（远程 Linux 服务器）
```bash
# 1. 环境
sudo apt update && sudo apt install -y python3-venv python3-pip git sshpass
python3 -m venv ~/ops-venv && source ~/ops-venv/bin/activate
pip install "fastapi[standard]" ansible ansible-runner

# 2. 拉代码
git clone <你的Gitee仓库地址> ops-platform && cd ops-platform

# 3. 建 runner 数据目录 + 放 playbook/清单
sudo mkdir -p /opt/ops/runner/{project,inventory} /root/vars
sudo cp -r ansible-enterprise-practice/. /opt/ops/runner/project/
sudo cp playbooks/web/deploy-nginx.yml /opt/ops/runner/project/
sudo cp inventory/hosts.example /opt/ops/runner/inventory/hosts
# 注意：04-nginx-web.yml 等引用绝对路径 /root/vars/*.yml，需把变量文件放过去
sudo cp ansible-enterprise-practice/vars/*.yml /root/vars/

# 4. 先验证 ansible-runner（不经过 FastAPI）
cd app && python -c "from runner import run_playbook; print(run_playbook('deploy-nginx.yml'))"

# 5. 起 API
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 目录结构
```
app/         FastAPI 后端代码（runner.py 是 ansible-runner 封装）
playbooks/   部署剧本（web / k8s / monitor 按场景分）
ansible-enterprise-practice/   企业级 Ansible 实战（NFS+Nginx+Keepalived 高可用，存量资产）
inventory/   主机清单（只推 hosts.example 模板，真实清单本地保留）
scripts/     辅助运维脚本
docs/        学习笔记
```
