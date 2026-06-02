# 团队环境信息

> 本文件记录团队三人各自的开发环境与运行环境，供联调时查阅。**敏感信息（密码、Token）不在此入库**，走团队即时通讯私传。

## 角色 A：WSL2 主开发

- 操作系统：Windows 11 + WSL2 Ubuntu 22.04
- IP：`<请跑 ip addr show eth0 后填写>`
- 端口：
  - Flask 后端：`5000`
  - pytest：本地跑
- 工具链：
  - gcc：`<gcc --version 后填写>`
  - libpcap-dev：`<dpkg -l libpcap-dev 后填写>`
  - Python：`<python3 --version 后填写>`
  - OpenWrt SDK：`~/openwrt-sdk/`（手动下载到此目录）

## 角色 B：Vue 前端

- 操作系统：Windows
- Node.js：`<待填>`，建议 LTS 20.x
- 包管理器：pnpm `<待填>`
- 端口：Vite Dev Server `5173`
- Vite proxy 配置中的 `target`：指向角色 A 的 WSL2 IP 或部署后的 OpenWrt VM IP（5000 端口）

## 角色 C：VMware / OpenWrt VM

> 由角色 C（Stevie-1）填写。所有 IP 都用 NAT 模式下与 VMnet8 同网段的静态 IP。

- VMware Workstation 版本：`17.5.0`
- OpenWrt 版本：`24.10.0 x86_64`
- VM 内存：`<待填，建议 512MB-1GB>`
- VM CPU：`<待填，1-2 核足够>`

### 网络配置

| 项 | 值 |
|---|---|
| 网卡模式 | NAT（对应 VMnet8） |
| VMnet8 网段 | `192.168.122.0/24` |
| OpenWrt 静态 IP | `192.168.122.100` |
| 子网掩码 | `255.255.255.0` |
| 网关 | `192.168.122.2` |
| DNS | `<待填，例如 8.8.8.8 / 114.114.114.114>` |
| 主网卡名 | `br-lan` |
| LAN 网卡（抓包用） | `eth0` |

### 访问方式

| 项 | 值 |
|---|---|
| SSH | `ssh root@192.168.122.100` |
| LuCI 管理界面 | `http://192.168.122.100` |
| Samba 共享 | `\\192.168.122.100\p0` → `/mnt/p0` |

### 已装软件包

- `luci-app-samba4`（Samba 服务）
- `libpcap1`（流量监控运行时依赖）
- `python3-light` + `pip flask flask-cors`（Flask 后端运行时）
- `opkg install bash openssh-sftp-server libpcap iperf3 curl tcpdump-mini`

## 端口与路径约定

| 项 | 值 |
|---|---|
| Flask 后端端口 | `5000` |
| Vite Dev Server 端口 | `5173` |
| 流量统计 JSON 输出路径 | `/tmp/traffic.json`（开发期 WSL2 与 OpenWrt 都用同一路径） |
| 防火墙脚本目录 | `/usr/local/bin/`（OpenWrt 上） |
| 前端 dist 部署位置 | `/www/app/`（OpenWrt 上由 uhttpd 托管）或 `backend/static/`（由 Flask 托管） |

## 环境变量

后端运行时支持以下环境变量：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `MOCK_MODE` | `true` | `true` 时所有接口返 mock 数据；部署期设为 `false` |
| `TRAFFIC_JSON_PATH` | `/tmp/traffic.json` | C 程序输出的 JSON 路径 |
| `FIREWALL_SCRIPTS_DIR` | `/usr/local/bin` | shell 脚本所在目录 |
| `FLASK_HOST` | `0.0.0.0` | 监听地址 |
| `FLASK_PORT` | `5000` | 监听端口 |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 逗号分隔的 CORS 白名单 |

## 联调通道

- Git 仓库：`git@github.com:Stevie-1/MyOpenWrt.git`
- 云盘（OpenWrt 镜像 / pcap / 视频）：`<填群里约定的网盘链接>`
- 即时通讯群：`<填群名>`
- 远程联调会议：腾讯会议 / VSCode Live Share 临时建
