# 01 - ansible-runner API（CLI → Python 映射）

## 目的
把你会用的 ansible-playbook 命令翻译成 Python 调用，封装成函数（见 app/runner.py）。

## 核心映射表
| CLI 参数 | Python 参数 | 说明 |
|---|---|---|
| ansible-playbook <文件> | playbook="xxx.yml" | 相对 private_data_dir/project/ |
| -i inventory/hosts | inventory="inventory/hosts" | 相对 private_data_dir/inventory/ |
| -e '{"k":"v"}' | extravars={"k": "v"} | 运行时变量 |
| -l web_servers | limit="web_servers" | 限定主机 |
| （playbook 内 connection: local） | 同上 | 本机执行不走 SSH |

## 关键概念
- private_data_dir：runner 根目录，固定含 project/（playbook）和 inventory/（清单）
- run() 是同步阻塞的：跑完才返回 → 必须放后台线程/Celery，不能直接在 async 路由里 await
- 返回对象 r：r.status（successful/failed/canceled/timeout）、r.rc（退出码）、
  r.stats（每台主机统计）、r.events（事件流，第 4 周 WebSocket 用它）

## 验收标准
- [ ] python -c 调 run_playbook 能对 localhost 跑通 deploy-nginx.yml
- [ ] 通过 POST /deploy 触发后，服务器终端能看到 [successful] rc=0 stats={'ok': 2, 'changed': 2}
