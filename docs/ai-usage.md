# AI 使用说明

> 本节记录团队三人在项目开发过程中使用 AI 工具的情况，包括使用的工具/模型、关键提示词、对生成代码的评价与修改、以及踩坑经验。
> **评分提醒：漏写本项 = 0 分（指导书硬性要求）。**

---

## 角色 A：WSL2 主开发（C/Flask/Shell/Git）

### 使用的工具与模型

- **工具**：Claude Code（Anthropic 官方 CLI），部署在 WSL2 Ubuntu 22.04
- **模型**：Claude Opus 4.7

### 使用场景

| 任务 | 使用方式 | 关键提示词要点 |
|---|---|---|
| C 流量监控程序 (`traffic-monitor/`) | 由 Claude Code 生成初始框架，人工审查并调整 | "implement a libpcap-based traffic monitor with 5-tuple hash table, ring buffer sliding window (2s/10s/40s), and 1-second JSON output using atomic rename" |
| Flask 后端骨架 (`backend/`) | Claude Code 生成 app.py、blueprint 划分、Mock 数据 | "create Flask app with traffic and firewall blueprints, CORS enabled, mock mode toggle via env var" |
| 防火墙 shell 脚本 (`firewall-scripts/`) | Claude Code 生成脚本模板，人工验证 fw4 命令 | "write OpenWrt fw4/nftables shell scripts for add/del/list/clear with positional args, no eval, subprocess-safe" |
| API 契约 (`docs/api.md`) | Claude Code 协助起草，人工与角色 B 对齐 | "draft API contract for traffic monitoring and firewall management" |
| 联调文档 (`docs/integration-handoff.md`) | Claude Code 生成 | "write integration handoff guide for roles B and C" |
| 测试用例 (`test/`) | Claude Code 生成 pytest 用例 | "generate pytest for traffic and firewall APIs with edge cases" |
| README 与仓库基建 | Claude Code 生成 | "create comprehensive README with directory structure and quickstart" |

### 对生成代码的评价与修改

1. **C 程序 stats.c（滑动窗口）**：Claude Code 生成的环形缓冲区逻辑正确，五元组哈希表实现简洁。但初始版本未处理 `cursor` 在 `stats_snapshot` 中的快照一致性——已在人工审查时修复，在 snapshot 入口处读取 cursor 快照避免并发读写竞争。
2. **防火墙脚本**：初始版本使用了 bash 的 `[[ ]]` 语法，OpenWrt 的 ash 不支持。人工替换为 POSIX sh 兼容写法。`list_rules.sh` 的 JSON 输出格式经过三次迭代才与后端解析对齐。
3. **后端验证器**：Claude Code 生成的 `_validators.py` 严格白名单校验（协议、IP、端口、动作）质量很高，命令注入测试用例覆盖了 `; rm -rf /` 等常见攻击向量。
4. **跨域 CORS**：初始配置仅允许 `localhost:5173`，部署到 OpenWrt 后需扩展为 `0.0.0.0:5000` 以便外部访问。

### 踩坑记录

- **OpenWrt SDK 交叉编译**：Claude Code 建议的 `-static` 全静态编译导致 musl 与 glibc 符号冲突，最终改为 `-static-libgcc` + 静态链接 libpcap。
- **musl libc**：`fts.h`、`execinfo.h` 等 GNU 扩展在 musl 中不可用，需在代码中条件编译排除。
- **shell 行尾符**：Windows 团队成员编辑 `.sh` 文件后产生 CRLF，在 OpenWrt 上 `bad interpreter`。解决方案是 `.gitattributes` + 部署时 `sed -i 's/\r$//'`。

---

## 角色 B：Vue 前端开发

### 使用的工具与模型

- **工具**：Claude Code（Anthropic 官方 CLI），部署在 Windows 宿主机
- **模型**：Claude Opus 4.7

### 使用场景

| 任务 | 使用方式 | 关键提示词要点 |
|---|---|---|
| Vue 3 工程初始化 | Claude Code 协助 `pnpm create vite` 并安装 Element Plus + ECharts + Axios | "init Vue 3 + Vite + TS project with element-plus, echarts, axios, vue-router" |
| 流量监控页 (`TrafficMonitor.vue`) | Claude Code 生成完整组件，包括折线图 + 表格 | "create traffic monitor page with real-time ECharts line chart and el-table" |
| 防火墙配置页 (`FirewallConfig.vue`) | Claude Code 生成表单 + 规则表格 + 执行回显 | "create firewall config page with el-form validation, rule table, and exec result panel" |
| API 封装 (`api.js`) | Claude Code 生成 axios 封装 | "create axios instance with base URL, interceptors for error handling" |
| 折线图展示优化 | Claude Code 将总速率折线改为每条流独立分线，添加活跃流过滤 | "change chart from aggregate sum to per-flow line chart, only show active flows" |
| Vite 代理配置 | Claude Code 协助配置开发期 proxy 指向 VM 后端 | "configure vite proxy /api to OpenWrt VM backend" |

### 对生成代码的评价与修改

1. **TrafficMonitor.vue 初版**：Claude Code 生成的图表初始使用"所有流 avg2s 求和"作为单一折线，导致图表呈现"一次函数稳步上升"的假象（因为流数量单调递增）。经讨论后改为活跃流独立分线——仅展示 `avg2s > 0` 的流，闲置 3 次轮询后自动移除。修改后能直观区分不同连接的实时速率。
2. **FirewallConfig.vue**：Claude Code 生成的表单校验（Element Plus rules）覆盖了协议三选一、端口范围 1-65535、IP 正则初校，质量较好。人工补充了 `el-popconfirm` 防误触清空按钮。
3. **axios 拦截器**：生成的错误拦截器使用 `ElMessage.error` 统一提示，开发体验良好。
4. **表格过长问题**：初始版本未限制表格高度，50+ 条流导致页面无限拉长。Claude Code 添加 `max-height="350"` 表内滚动解决。
5. **字段对齐**：前端字段名需与 `docs/api.md` 完全一致（`srcIp`/`dstIp`/`srcPort`/`dstPort`/`rxBytes`/`txBytes`/`avg2s` 等），Claude Code 做了校对。

### 踩坑记录

- **Vite proxy 目标**：开发期 proxy 指向 `localhost:5000`，后端部署到 VM 后需改为 `192.168.135.100:5000`。此文件（`vite.config.js`）不应入库，属于本地环境配置。
- **ECharts 按需引入**：Claude Code 生成的代码使用 `echarts/core` 按需引入 LineChart 等组件，初始遗漏了 `TitleComponent` 导致标题不显示，人工补充。
- **Vite 端口冲突**：5173 和 5174 端口被旧进程占用，Vite 自动切换到 5175，需在浏览器中注意端口号。

---

## 角色 C：VMware / OpenWrt 部署（Stevie-1）

### 使用的工具与模型

- **工具**：Claude Code（Anthropic 官方 CLI），通过 SSH 从 Windows 远程操作 OpenWrt VM
- **模型**：Claude Opus 4.7

### 使用场景

| 任务 | 使用方式 | 关键提示词要点 |
|---|---|---|
| OpenWrt VM 网络配置 | Claude Code 诊断 VMnet8 网卡缺失，指导恢复默认网络 | "check VMware network adapter, fix VMnet8 connectivity" |
| SSH 免密登录配置 | Claude Code 生成 ed25519 密钥对，通过 HTTP 临时服务传输公钥 | "setup SSH key auth from Windows to OpenWrt VM" |
| 软件包安装 | Claude Code 通过 SSH 执行 `opkg install` 安装 python3、flask、libpcap 等 | "install python3-light flask libpcap1 curl on OpenWrt" |
| 项目文件部署 | Claude Code 通过 SCP 传输 backend/、firewall-scripts/、traffic_monitor 到 VM | "deploy project files to OpenWrt VM via scp" |
| 后端启动与联调 | Claude Code 启动 `traffic_monitor` 和 Flask（MOCK_MODE=false），验证 API | "start traffic monitor and flask backend in real mode" |
| DNS 修复 | Claude Code 诊断 DNS 解析失败，配置 nameserver | "fix DNS resolution on OpenWrt" |
| 流量验证 | Claude Code 通过 ping/curl 造流量，验证 C 程序实时采集 | "generate test traffic and verify live capture" |

### 对生成代码的评价与修改

1. **网络诊断**：Claude Code 准确识别了 VMnet8 虚拟网卡缺失的问题，指导在 VMware Virtual Network Editor 中恢复默认设置。OpenWrt 的静态 IP 从 `192.168.1.1` 修改为 `192.168.135.100` 以对齐 NAT 网段。
2. **SSH 免密登录**：由于 VMware 控制台粘贴困难，Claude Code 提出在 Windows 起 HTTP 服务器，VM 通过 `wget -O -` 拉取公钥的方案，实际解决了无法粘贴的问题。
3. **软件包安装**：Claude Code 准确选择了 `python3-flask`（opkg 包）而非通过 pip 安装 Flask（节省空间）。`flask-cors` 在 opkg 中不可用，通过 pip 安装。剩余磁盘空间从 71MB 降至 21MB，在可接受范围内。
4. **环境变量**：MOCK_MODE=false 切换正常，TRAFFIC_JSON_PATH 和 FIREWALL_SCRIPTS_DIR 路径与 C 程序输出和脚本部署位置一致。

### 踩坑记录

- **VMware 虚拟网卡缺失**：初始 `ipconfig` 无 VMnet1/VMnet8，需在 Virtual Network Editor 中点击"Restore Defaults"恢复。
- **OpenWrt ash 限制**：`nohup`、`file`、`stat` 命令不存在，后台进程需使用 `bash -c "cmd &"` 包装。
- **DNS 配置**：`uci set network.lan.dns` 后需重启网络才能持久生效。
- **流量短连接问题**：HTTP API 请求使用临时端口，每个连接数秒内完成，导致 C 程序 `avg2s` 大部分时间为 0。这不是 bug，是正常行为——只有持续流量（如 ping、大文件下载）才会在窗口中留下非零值。
- **SCP 路径**：`/usr/local/bin/` 在 OpenWrt 上默认不存在，需 `mkdir -p` 创建。

---

## 总结

本项目全程使用 **Claude Code（Claude Opus 4.7）** 辅助开发。AI 在以下方面提供了显著帮助：

1. **代码生成**：C 程序的 libpcap 抓包 + 滑动统计算法、Flask 蓝图 + Mock 双模式、Vue 组件（ECharts + Element Plus）、Shell 脚本模板——均由 AI 生成初始版本，人工审查修改。
2. **环境配置**：VMware 网络诊断、OpenWrt 软件包安装、SSH 免密配置——AI 提供了准确的命令和排错路径。
3. **联调诊断**：流量数据验证、活跃流过滤、图表展示优化——AI 帮助识别了"所有流 avg2s 求和"的展示误区。

AI 生成的代码整体质量较高，但需要人工把关的场景包括：POSIX 兼容性（ash vs bash）、musl libc 差异、前后端字段对齐、环境特定配置不入库等。**AI 是高效的工具，但最终代码的正确性和适用性由人负责。**
