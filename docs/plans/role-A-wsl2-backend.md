# 角色 A 工作计划：WSL2 主开发（你）

> 负责后端、C/libpcap、Shell 脚本、Git 维护、文档与 AI 使用说明。

## 一、角色定位

- 开发环境：WSL2 Ubuntu 22.04
- 核心交付物：
  - `traffic-monitor/`：C + libpcap 流量监控程序
  - `backend/`：Python Flask REST API
  - `firewall-scripts/`：OpenWrt `fw4`/nft 防火墙脚本
  - `docs/`：实验报告（你主笔）+ AI 使用说明 + API 契约
  - `.gitignore`、`.gitattributes`、`README.md` 等仓库基建
- 不负责：Vue 前端（角色 B）、OpenWrt VM 部署与录制（角色 C）

## 二、前置准备（Day 0）

### 2.1 WSL2 环境配置

```bash
sudo apt update
sudo apt install -y build-essential gcc make pkg-config \
    libpcap-dev \
    python3 python3-pip python3-venv \
    git curl jq tcpdump iperf3 \
    dos2unix
python3 -m venv ~/.venvs/cnet && source ~/.venvs/cnet/bin/activate
pip install flask flask-cors pytest
```

### 2.2 下载 OpenWrt SDK（用于交叉编译）

- 地址：`https://downloads.openwrt.org/releases/24.10.0/targets/x86/64/`
- 找形如 `openwrt-sdk-24.10.0-x86-64_gcc-*_musl.Linux-x86_64.tar.zst` 的包
- 解压到 `~/openwrt-sdk/`，按 SDK README 跑通 hello world 编译验证

### 2.3 Git 仓库初始化

- 仓库远端已建好。你要补：
  - `.gitignore`：见下方第六章
  - `.gitattributes`：`*.sh text eol=lf`，`*.vue text eol=lf`，`*.ts text eol=lf`
  - `README.md`：项目总览、目录结构、构建步骤、贡献规范
  - 分支保护：`main` 不允许直推，必走 PR

## 三、阶段任务

### Phase 0（Day 1）：仓库骨架

- [ ] 创建目录结构（见总计划第四章）
- [ ] 写 `README.md`、`.gitignore`、`.gitattributes`
- [ ] 写 `docs/api.md` 第一稿（API 契约草稿）—— **这份文档是团队三人合作的合同**
- [ ] 写 `docs/env.md` 模板，等角色 C 填 OpenWrt 网卡名/IP
- [ ] 创建占位目录：`traffic-monitor/`、`backend/`、`firewall-scripts/`、`scripts/`、`test/`
- [ ] 推第一个 commit 到 `main`，开 PR review 流程

### Phase 1（Day 2-3）：环境就绪 + API 契约定稿

- [ ] SDK 交叉编译 hello world，把产物 `scp` 给角色 C 验证能在 OpenWrt 上跑
- [ ] Flask 骨架 `backend/app.py`：
  - 启用 `flask-cors`，放行 `http://localhost:5173`（Vite Dev Server）
  - `/api/health` 路由
  - 蓝图划分：`backend/api/traffic.py`、`backend/api/firewall.py`
- [ ] 写 Mock 数据：`backend/mock/traffic.json`、`backend/mock/firewall_rules.json`
  - 让 Mock 接口先能跑，方便角色 B 独立开发前端
- [ ] **与角色 B 一起敲定 `docs/api.md`**，至少覆盖：
  ```text
  GET    /api/traffic              -> { ts, items: [...] }
  GET    /api/firewall/rules       -> { rules: [...] }
  POST   /api/firewall/rules       body {proto,src,dst,port,action}
                                   -> { ok, stdout, stderr, code, ruleId? }
  DELETE /api/firewall/rules/:id   -> { ok, stdout, stderr, code }
  POST   /api/firewall/clear       -> { ok, stdout, stderr, code }
  ```
- [ ] 把 `traffic.json` 单条字段示例固化在 `docs/api.md`，例如：
  ```json
  {
    "srcIp": "192.168.1.10", "dstIp": "8.8.8.8",
    "srcPort": 54321, "dstPort": 443, "proto": "tcp",
    "rxBytes": 12345, "txBytes": 678,
    "peak": 102400, "avg2s": 8192, "avg10s": 4096, "avg40s": 1024
  }
  ```

### Phase 2（Day 4-7）：流量监控

- [ ] `traffic-monitor/src/`：
  - `main.c`：解析参数 `-i <iface> -f <bpf>  -o <jsonPath>`
  - `capture.c`：`pcap_open_live` + `pcap_compile` + `pcap_setfilter` + `pcap_loop`
  - `stats.c`：五元组哈希（srcIp,dstIp,srcPort,dstPort,proto）累加 `rxBytes/txBytes`，环形缓冲实现 2s/10s/40s 滑动窗口
  - `output.c`：每 1 秒 dump 到 JSON（先 `tmp_path` 再 `rename` 避免读到半截）
  - `pthread` 把"抓包线程"和"统计上报线程"解耦
- [ ] `Makefile`：本地 host 编译
- [ ] `Makefile.openwrt`：调用 SDK 工具链交叉编译
  - 编译参数加 `-static-libgcc`，必要时全静态：`-static`，避免 OpenWrt 上动态库版本不匹配
- [ ] CLI 输出版先跑通，把样本输出贴到 `docs/api.md` 让角色 B 对齐
- [ ] `backend/api/traffic.py`：
  - `GET /api/traffic` 读 JSON 文件返回；文件不存在/读半返 Mock 数据并加日志
- [ ] 单测 `test/test_traffic_api.py`
- [ ] 与角色 C 同步：把交叉编译产物 push 到 Git（建议放 `release/` 目录，加 `.gitkeep` 但二进制本身用 `git-lfs` 或不入库改走 Samba/scp）

### Phase 3（Day 8-10）：防火墙

- [ ] `firewall-scripts/`：用 OpenWrt 的 `fw4`（底层 nftables）
  - `add_rule.sh <proto> <src> <dst> <port> <action>`
  - `del_rule.sh <ruleId>`
  - `list_rules.sh`（输出可被 Flask 解析的格式，建议 JSON）
  - `clear_rules.sh`
  - **所有脚本严格使用位置参数 `$1 $2 ...`，禁止 `eval`、禁止用变量拼接命令**
  - Shebang 用 `#!/bin/sh`（OpenWrt 默认是 ash，不是 bash）
- [ ] `backend/api/firewall.py`：
  ```python
  ALLOWED_PROTO = {"tcp", "udp", "icmp"}
  ALLOWED_ACTION = {"accept", "reject", "drop"}
  
  def validate(payload):
      assert payload["proto"] in ALLOWED_PROTO
      assert payload["action"] in ALLOWED_ACTION
      ipaddress.ip_address(payload["src"])  # 也允许 'any'，自己白名单
      ipaddress.ip_address(payload["dst"])
      port = int(payload["port"]); assert 1 <= port <= 65535
  
  result = subprocess.run(
      ["/usr/local/bin/add_rule.sh", proto, src, dst, str(port), action],
      shell=False, check=False, capture_output=True, text=True, timeout=5
  )
  return {"ok": result.returncode == 0,
          "stdout": result.stdout, "stderr": result.stderr,
          "code": result.returncode}
  ```
- [ ] 单测 `test/test_firewall_api.py`：覆盖非法 `proto`、非法 IP、非法端口、非法 action、命令注入尝试（`; rm -rf /` 等）必须被拒
- [ ] 把 stdout/stderr/code 全部回传 —— **指导书 3.3 节硬要求展示**

### Phase 4（Day 11-12）：交付

- [ ] 整理代码、补注释、每个目录单独 README
- [ ] 写实验报告（你主笔，角色 B/C 提供前端截图与运行截图）
  - 包含理论部分（指导书 2.x）、实现部分、运行结果、问题与解决
- [ ] **`docs/ai-usage.md`** 完整记录 AI 使用：
  - 哪些任务使用了 AI、用了哪个工具/模型
  - 关键提示词（脱敏即可）截图或文字记录
  - 你对生成代码的评价、修改、踩坑
  - **漏写本项 = 0 分**
- [ ] `scripts/package_submission.sh`：
  - 打包 `源码.zip`：包含 `traffic-monitor/`、`backend/`、`firewall-scripts/`、`frontend/src/`、`frontend/dist/`、`docs/`、`README.md`
  - 排除 `node_modules/`、`__pycache__/`、`.venv/`、`build/`、`*.pcap`、`.git/`

## 四、关键技术注意点

### 4.1 libpcap 数据流
```mermaid
flowchart LR
    NIC[Network Interface] -->|raw frames| LoopT[capture thread<br/>pcap_loop]
    LoopT -->|parsed pkt| Stats[stats thread<br/>5-tuple hash + window]
    Stats -->|every 1s| Json[/tmp/traffic.json]
    Json --> Flask[Flask /api/traffic]
```

### 4.2 OpenWrt 兼容性踩坑

- **shell**：`#!/bin/sh`，避免用 `bash` 特性（`[[ ]]`、数组等）
- **musl libc**：交叉编译的二进制不能链接 glibc，SDK 工具链已是 musl
- **动态库**：`libpcap.so` 需要在 OpenWrt 上 `opkg install libpcap`；或者改全静态
- **行尾符**：Windows 上同事改过的 `.sh` 拷到 OpenWrt 会报 `bad interpreter`，加 `.gitattributes` + 部署时 `dos2unix`
- **fw4 vs fw3**：OpenWrt 24.10 是 fw4（基于 nftables），不是 fw3（iptables）。脚本要写 `fw4` 或直接 `nft`

### 4.3 防注入

```python
import shlex, subprocess
result = subprocess.run([script_path, *args], shell=False, ...)
```
绝对不要：`subprocess.run(f"./add_rule.sh {ip}", shell=True)`

## 五、与队友的同步接触点

| 时机 | 找谁 | 同步什么 |
|---|---|---|
| Phase 0 末 | 角色 B | API 契约 `docs/api.md` 共同 review 拍板 |
| Phase 1 中 | 角色 B | 给他 Mock 数据，验证他前端能拉数据 |
| Phase 1 末 | 角色 C | 拿到 OpenWrt 的 IP、网卡名、Samba 路径，写入 `docs/env.md` |
| Phase 2 中 | 角色 C | 交叉编译 binary 给他，验证能在 OpenWrt 上跑 |
| Phase 2 末 | 角色 B | 真实接口替换 Mock，前端切换 base URL |
| Phase 3 中 | 角色 C | 给他 shell 脚本，他验证 fw4 规则真实生效 |
| Phase 4 中 | 全员 | 报告草稿互审，运行截图汇集 |

## 六、`.gitignore` 模板

```text
# C 构建
build/
*.o
*.a
*.so
traffic-monitor/bin/

# Python
__pycache__/
*.pyc
.venv/
.pytest_cache/

# 前端
node_modules/
frontend/dist/
frontend/.vite/

# IDE / OS
.vscode/
.idea/
.DS_Store
*.swp

# 实验大文件（走云盘）
*.pcap
*.iso
*.img
*.vmdk
*.mp4
*.log

# 临时
*.tmp
*.bak
```

## 七、自检清单

- [ ] WSL2 工具链装完，`gcc`、`libpcap-dev`、Python venv 就绪
- [ ] OpenWrt SDK hello world 跑通且在 VM 上能执行
- [ ] Flask Mock 接口对外可访问，CORS 配置正确
- [ ] `docs/api.md` 与角色 B 拍板版本一致
- [ ] C 程序本地（WSL2 `eth0`）能正确统计流量
- [ ] C 程序交叉编译产物在 OpenWrt 上跑通
- [ ] 防火墙 4 个脚本在 OpenWrt 上真实生效（由角色 C 验证）
- [ ] 后端单测覆盖非法输入与命令注入尝试
- [ ] 实验报告完成
- [ ] `docs/ai-usage.md` 完整
- [ ] 源码 zip 打包符合命名规范
