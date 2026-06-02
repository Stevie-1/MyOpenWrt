# 基于 OpenWrt 的网络应用程序开发

> 电子科技大学《计算机网络系统》课程实验二
> 团队 Git 仓库：https://github.com/Stevie-1/MyOpenWrt

本仓库实现两个 Web 化的网络管理工具，部署在 OpenWrt 24.10.0 上：

1. **流量监控**：基于 libpcap 的 C 程序抓包、统计五元组流量（累计/峰值/2s/10s/40s 滑动均值），通过 Flask REST 提供数据，Vue 前端以 ECharts 折线图与表格实时展示。
2. **防火墙配置**：Web 表单录入 fw4/nftables 规则，后端严格白名单校验后调用 shell 脚本执行 OpenWrt 防火墙增/删/查/清操作，前端展示执行结果与生效验证。

## 目录结构

```text
ComputerNetworkExp/
├── README.md                 # 本文件
├── .gitignore
├── .gitattributes
├── docs/
│   ├── api.md                # API 契约（团队三人合作的合同）
│   ├── env.md                # OpenWrt VM 环境信息（角色 C 填）
│   └── plans/                # 三份角色执行计划
│       ├── role-A-wsl2-backend.md
│       ├── role-B-vue-frontend.md
│       └── role-C-vmware-openwrt.md
├── traffic-monitor/          # 任务 2：C + libpcap 流量监控（Phase 2）
│   ├── src/
│   ├── include/
│   ├── Makefile
│   └── Makefile.openwrt
├── firewall-scripts/         # 任务 3：fw4 防火墙 shell 脚本（Phase 3）
│   ├── add_rule.sh
│   ├── del_rule.sh
│   ├── list_rules.sh
│   └── clear_rules.sh
├── backend/                  # Flask 后端 + Mock
│   ├── app.py
│   ├── config.py
│   ├── api/
│   │   ├── traffic.py
│   │   └── firewall.py
│   ├── mock/
│   └── requirements.txt
├── frontend/                 # Vue 3 + Vite（由角色 B 在 Windows 上初始化）
├── scripts/
│   ├── deploy_to_openwrt.sh
│   └── package_submission.sh
├── release/                  # OpenWrt 交叉编译产物（给角色 C 部署用）
│   ├── traffic_monitor       # x86_64 musl ELF，已 strip
│   ├── traffic_monitor.sha256
│   └── README.md
└── test/
    ├── test_health.py
    ├── test_traffic_api.py
    ├── test_firewall_api.py
    ├── test_traffic_json_schema.py
    └── traffic_generator.py
```

## 快速开始

### 后端（任意 Linux/WSL2）

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend && python app.py
# 默认监听 0.0.0.0:5000，MOCK_MODE=true
```

验证：

```bash
curl http://localhost:5000/api/health
curl http://localhost:5000/api/traffic
curl http://localhost:5000/api/firewall/rules
```

### 前端（Windows 宿主机或 WSL2）

```bash
cd frontend
pnpm install
pnpm dev
# Vite 默认监听 0.0.0.0:5173，/api/* 经 vite proxy 转发到后端
```

### 测试

```bash
pytest test/ -v
```

### 部署 traffic_monitor 到 OpenWrt

`release/traffic_monitor` 已是 OpenWrt 24.10 x86_64 musl 的可执行文件（依赖
仅 `libc.so`，libpcap 已静态打包），由 Role C 拷入 VM 即用。详细步骤见
[release/README.md](release/README.md)。重新构建：

```bash
cd traffic-monitor
make -f Makefile.openwrt clean && make -f Makefile.openwrt
```

## 团队分工与协作

三份分角色的详细执行计划位于 `docs/plans/`：

- [角色 A：WSL2 主开发（C/Flask/脚本/Git）](docs/plans/role-A-wsl2-backend.md)
- [角色 B：Vue 前端同伴](docs/plans/role-B-vue-frontend.md)
- [角色 C：VMware/OpenWrt 操作同伴](docs/plans/role-C-vmware-openwrt.md)

API 契约见 [docs/api.md](docs/api.md)，OpenWrt VM 环境信息见 [docs/env.md](docs/env.md)。

**联调与上线**：A 的后端/C 程序/防火墙脚本交付给 B/C 的对接说明（含上线步骤、各自自测清单、字段对照、联调顺序）见 [docs/integration-handoff.md](docs/integration-handoff.md)。

## 贡献规范

- **分支策略**：保护 `main`，所有改动走 `feat/*`、`fix/*`、`docs/*`、`chore/*` 分支 + PR
- **Commit 消息**：[Conventional Commits](https://www.conventionalcommits.org/zh-hans/v1.0.0/)
  - `feat(backend): add traffic api with sliding window`
  - `fix(firewall): reject negative port`
  - `docs: update api contract for firewall response`
- **行尾符**：所有 `.sh`、源码统一 LF，由 `.gitattributes` 强制（避免 Windows CRLF 让 OpenWrt 报 `bad interpreter`）
- **大文件**：OpenWrt 镜像、抓包样本、演示视频走云盘共享，不入 Git
- **凭证**：私钥、`.env`、token 一律不入库

## 提交物（截至 Phase 4）

按命名规范打包：
- `张三+李四+王五_代码.zip`
- `张三+李四+王五_演示.mp4`
- `张三+李四+王五_报告.docx`

`scripts/package_submission.sh` 会自动排除 `node_modules/`、`__pycache__/`、`build/`、`.venv/`、`.git/` 后打包。

## 评分构成提醒

- 实验报告 40%（**必须包含 AI 使用说明，漏写本项为 0 分**）
- 实验源码 30%
- 演示视频 20%
- 真实路由器部署 +10%（选做）

AI 使用记录维护在 `docs/ai-usage.md`，三人各自维护对应章节。
