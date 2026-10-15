# ops-platform 运维自动化平台

基于 FastAPI + Ansible Runner 的运维自动化 API，把 playbook 封装成可调用的 Web 接口。

## 技术栈
- FastAPI（Web API）+ Pydantic（数据校验）
- ansible-runner（Ansible Python API）
- SQLite 持久化（部署历史 jobs.db，Python 自带，无需额外服务）

## 功能
- [x] 项目骨架 / 部署服务 API
- [x] Playbook 一键触发 API（ansible-runner 接入，返回结构化 status / rc / stats）
- [x] BackgroundTasks 异步执行（受理即返回 202 + job_id，Playbook 在线程池中执行，不阻塞事件循环）
- [x] 任务状态全程可查（queued → starting → running → successful / failed / timeout / error；hosts 一台都没匹配上记为 no_hosts；进程被强杀后重启标记为 lost）
- [x] 部署历史持久化（SQLite，含 job_id / 时间 / 剧本 / 版本 / 状态 / 退出码 / 按主机统计）
- [x] 输入白名单（版本号格式校验、剧本白名单），防止 extravars 被 Jinja 渲染导致命令注入
- [x] 同一目标互斥（同一剧本 + limit 已有任务在执行时返回 409）
- [x] 健康检查（GET /status 检查 project / inventory 目录与 ansible-playbook 命令）

## Roadmap
- [ ] JWT 认证
- [ ] WebSocket 实时日志（基于 ansible-runner 事件流）
- [ ] Celery + Redis 任务队列（任务持久化、失败重试、多 worker）

## 接口一览
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /deploy | 触发部署：202 返回 job_id；参数非法 422；同一目标有任务在执行 409 |
| GET | /status | 健康检查：ok / degraded，附各项检查结果 |
| GET | /jobs | 部署历史列表（按时间倒序，?limit=50） |
| GET | /jobs/{job_id} | 单次部署详情，不存在返回 404 |

请求示例：
```bash
curl -X POST http://127.0.0.1:8000/deploy -H 'Content-Type: application/json' \
     -d '{"app_version": "1.2.3"}'
# 可选 "limit": "web01"，只对部分主机执行（失败主机定向重试）
```

## 已知限制
- 未做认证：只在内网或本机使用，上线前必须加认证（见 Roadmap）
- 任务在 Web 进程的线程池里执行；SQLite 与进程内锁只适合单实例部署
- 平台清单示例只有 localhost；多主机部署需把真实清单放到 /opt/ops/runner/inventory/hosts

## 快速开始（远程 Linux 服务器）
```bash
# 1. 环境
sudo apt update && sudo apt install -y python3-venv python3-pip git sshpass
python3 -m venv ~/ops-venv && source ~/ops-venv/bin/activate
pip install "fastapi[standard]" ansible ansible-runner

# 2. 拉代码
git clone https://github.com/chenxiweng819-pixel/ops-platform.git && cd ops-platform

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
playbooks/   部署剧本（目前 web/deploy-nginx.yml 为跑通链路的演示剧本）
ansible-enterprise-practice/   企业级 Ansible 实战（NFS+Nginx+Keepalived 高可用，存量资产）
inventory/   主机清单（只推 hosts.example 模板，真实清单本地保留）
docs/        学习笔记
```
