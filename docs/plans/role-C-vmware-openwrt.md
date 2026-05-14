# 角色 C 工作计划：VMware / OpenWrt 操作同伴

> 负责 OpenWrt 虚拟机部署、网络配置、文件传输、真实环境联调、规则生效验证、演示视频录制。**你是整个项目唯一能跑真实 OpenWrt 的人，是验证一切的最终把关者。**

## 一、角色定位

- 工作环境：Windows + VMware Workstation 17 + OpenWrt 24.10.0 VM
- 核心交付物：
  - 一台可正常运行、网络通畅、已装 Samba 的 OpenWrt VM
  - `docs/env.md`：OpenWrt IP、网卡名、登录方式、Samba 共享路径
  - 在 OpenWrt 上部署并运行流量监控 C 程序、Flask 后端、前端 `dist/`、防火墙脚本
  - 防火墙规则生效前/后的访问验证证据
  - 实验报告中的"部署与运行"章节、所有运行截图
  - **演示视频 ≤ 5 分钟**
- 不负责：写 C 代码、写 Vue、写 Flask 后端（但你需要看懂如何启动它们）

## 二、前置准备（Day 0-1）

### 2.1 VMware Workstation 17 安装

- 官网下载，安装时确认与 Windows 上现有 Hyper-V 共存（VMware 16.2+ 支持）
- 如果你 Windows 上同时跑了角色 A 的 WSL2 视为正常，二者可共存

### 2.2 下载 OpenWrt 镜像

- 地址：`https://downloads.openwrt.org/releases/24.10.0/targets/x86/64/`
- 下载文件：`openwrt-24.10.0-x86-64-generic-ext4-combined.img.gz`（或 squashfs 版）
- 解压得到 `.img` 文件

### 2.3 镜像转 vmdk

- 工具：StarWind V2V Image Converter（免费，需邮箱注册）
- 选 `Local file` → `.img` → `VMware ESX server image (Growable)` → 输出 `.vmdk`
- 也可用 `qemu-img convert -f raw -O vmdk ow.img ow.vmdk`（如装了 QEMU）

### 2.4 上传到云盘

- 把 `.img` 原始镜像和转换后的 `.vmdk` 都传一份云盘，便于团队复用与排错

## 三、阶段任务

### Phase 0（Day 1）：仓库准备 + VMware 安装

- [ ] `git clone` 仓库到 Windows（例如 `D:\projects\ComputerNetworkExp`），通读 `README.md`
- [ ] 装 VMware 17
- [ ] 下载 OpenWrt 24.10.0 `img`、转 `vmdk`、传云盘
- [ ] 装 Git for Windows，配置：
  ```powershell
  git config --global core.autocrlf input
  ```
  > **这一条很关键**：避免你在 Windows 上看代码时把 `.sh` 改成 CRLF，导致 OpenWrt 跑脚本报 `bad interpreter: No such file or directory`

### Phase 1（Day 2-3）：OpenWrt VM 启动与配置

#### 3.1.1 新建虚拟机

- VMware：`File → New Virtual Machine → Custom`
- 客户机操作系统：`Other Linux 5.x kernel 64-bit`
- 处理器：1 核足够；内存：512 MB-1 GB
- 网络：**NAT 模式**（重要，便于 Windows 主机访问）
- 磁盘：**移除默认创建的磁盘**，挂载你前面转换好的 `.vmdk`
- 完成后启动

#### 3.1.2 网络配置

- OpenWrt 启动后按回车进入命令行
- 第一次先改 root 密码：`passwd`
- 查看本机网卡：`ip addr`，通常是 `br-lan` 或 `eth0`
- 编辑网络配置：
  ```sh
  vi /etc/config/network
  ```
  确保 lan 配置类似：
  ```text
  config interface 'lan'
      option device 'br-lan'
      option proto 'static'
      option ipaddr '192.168.x.1'        # 改成与 VMnet8 同网段
      option netmask '255.255.255.0'
      option gateway '192.168.x.2'       # VMnet8 的网关，通常 .2
      list dns '192.168.x.2'
      list dns '8.8.8.8'
  ```
- 查询 VMnet8 网段：Windows `cmd` 执行 `ipconfig`，看 `VMware Network Adapter VMnet8` 的 IPv4 地址
- 重启网络：
  ```sh
  /etc/init.d/network restart
  ```
- 验证联网：
  ```sh
  ping -c 3 8.8.8.8
  ping -c 3 www.baidu.com
  opkg update    # 能成功就说明网通了
  ```

#### 3.1.3 安装 Samba（文件传输）

```sh
opkg update
opkg install luci-app-samba4
opkg install luci-i18n-samba4-zh-cn   # 可选汉化
```

- Windows 浏览器输入 OpenWrt 的 IP 进 LuCI 管理界面（默认 user `root` + 你刚设的密码）
- `服务 → 网络共享`：
  - 勾选"启用扩展调整"、"强制同步 I/O"
  - 编辑模板，注释 `invalid users = root`
  - 添加共享：名称随意，路径 `/mnt/p0`，勾选"可浏览"、"允许匿名用户"，创建权限掩码 `0777`，目录权限掩码 `0777`
- 回到 SSH 终端：
  ```sh
  mkdir -p /mnt/p0
  chmod -R 777 /mnt/p0
  /etc/init.d/samba4 restart
  ```
- Windows 主机 `Win + R` 输入 `\\<OpenWrt-IP>`，应能看到 `p0` 共享目录

#### 3.1.4 装常用工具（便于后续）

```sh
opkg install bash openssh-sftp-server libpcap iperf3 curl tcpdump-mini
# 防火墙在 24.10 已是 fw4，无需额外装
```

#### 3.1.5 填写 `docs/env.md`

新建 `docs/env.md`（如果角色 A 还没建则你建），填：

```markdown
# OpenWrt VM 运行环境

- VM 软件：VMware Workstation 17
- OpenWrt 版本：24.10.0 x86_64
- 静态 IP：192.168.x.1
- 网关：192.168.x.2
- 主网卡：br-lan
- LAN 网卡（抓包用）：br-lan 或 eth0（运行 `ip addr` 查准确名）
- SSH：`ssh root@192.168.x.1`
- Samba 共享：`\\192.168.x.1\p0` → `/mnt/p0`
- root 密码：（团队内部沟通，不入库）
```

提交 PR：`docs: env info for openwrt vm`

### Phase 2（Day 4-7）：流量监控部署与联调

#### 3.2.1 拿到角色 A 的交叉编译产物

- 角色 A 会把 `traffic-monitor/bin/traffic_monitor`（OpenWrt 版二进制）通过云盘或共享 push
- 把它放进 `\\OpenWrt-IP\p0\`，在 OpenWrt 上 `cp /mnt/p0/traffic_monitor /usr/local/bin/`，`chmod +x`

#### 3.2.2 跑 C 程序

```sh
# 确认网卡名
ip addr | grep -E 'br-lan|eth0'

# 启动（前台跑，便于看输出）
/usr/local/bin/traffic_monitor -i br-lan -o /tmp/traffic.json -f "ip"

# 或后台：
/usr/local/bin/traffic_monitor -i br-lan -o /tmp/traffic.json -f "ip" &
```

- 如果报"动态库找不到"（例如 `libpcap.so.x`），`opkg install libpcap1`；仍不行回复角色 A，让他改静态编译
- 验证 JSON 文件正在更新：
  ```sh
  watch -n 1 cat /tmp/traffic.json
  ```

#### 3.2.3 造测试流量

- 在 OpenWrt 上：
  ```sh
  iperf3 -c iperf.he.net -t 30        # 跑公共 iperf 服务器
  wget -O /dev/null http://speedtest.tele2.net/100MB.zip
  ```
- 同时在 Windows Chrome 看角色 B 的前端页面（开发期通过 Vite proxy 访问），曲线应有实时变化

#### 3.2.4 部署 Flask 后端到 OpenWrt（或暂跑在角色 A 的 WSL2 上）

两种方案选其一：

**方案 A（联调期推荐）**：Flask 跑在角色 A 的 WSL2 上，OpenWrt 仅跑 C 程序 + 把 `/tmp/traffic.json` 通过 NFS / SMB 共享给 WSL2 读
- 实现简单但联调期能用

**方案 B（最终演示用）**：Flask 真正跑在 OpenWrt 上
- 安装：
  ```sh
  opkg install python3-light python3-pip
  pip install flask flask-cors
  ```
- 把 `backend/` 目录拷到 OpenWrt（Samba 推 `/root/backend/`）
- 启动：
  ```sh
  cd /root/backend && python3 app.py
  ```
- 注意：OpenWrt 资源紧张，Python 启动慢、占内存。如果 overlay 不够大，可以挂载额外存储或走静态编译方案
- 演示视频里走方案 B

#### 3.2.5 联调反馈

- 反馈给角色 A：
  - 网卡名实际是什么？
  - 有没有动态库报错？
  - JSON 字段是否齐？速率单位对吗？
- 反馈给角色 B：
  - 真实数据下页面是否抖动？刷新频率合适吗？
  - 字段渲染有没有溢出？

### Phase 3（Day 8-10）：防火墙脚本部署与生效验证

#### 3.3.1 拿到角色 A 的脚本

- 从 Git 拉 `firewall-scripts/*.sh` 到 OpenWrt：
  ```sh
  cp /mnt/p0/firewall-scripts/*.sh /usr/local/bin/
  chmod +x /usr/local/bin/*.sh
  # 防 CRLF
  dos2unix /usr/local/bin/*.sh 2>/dev/null || sed -i 's/\r$//' /usr/local/bin/*.sh
  ```

#### 3.3.2 验证脚本在 OpenWrt 上能跑

- 手动测试每个脚本：
  ```sh
  /usr/local/bin/list_rules.sh
  /usr/local/bin/add_rule.sh tcp 192.168.x.100 0.0.0.0/0 80 drop
  /usr/local/bin/list_rules.sh
  /usr/local/bin/del_rule.sh <ruleId>
  /usr/local/bin/clear_rules.sh
  ```
- 如果脚本里用了 `bash` 特性 → 反馈角色 A 改成 `sh`
- 如果脚本调 `iptables` 而不是 `fw4` → 反馈改

#### 3.3.3 规则生效验证（指导书 3.3 节硬要求）

这一步极其重要，必须有完整证据链：

**示例：禁止访问端口 80**

```sh
# 添加规则前：从 Windows 主机能访问 OpenWrt 的 HTTP 端口
# 在 Windows cmd: 
#   curl http://192.168.x.1
#   返回：HTML 内容

# OpenWrt 上加规则
/usr/local/bin/add_rule.sh tcp 0.0.0.0/0 192.168.x.1 80 drop

# 添加规则后：从 Windows 主机访问被拒
#   curl http://192.168.x.1 --max-time 3
#   返回：Connection timed out

# 删除规则后：恢复访问
/usr/local/bin/del_rule.sh <ruleId>
#   curl http://192.168.x.1
#   返回：HTML 内容
```

- 全程截图 / 录屏（Windows 端 curl 输出 + OpenWrt 端 `fw4 print` / `nft list ruleset` 输出）
- 存到 `docs/screenshots/firewall-verify/`

#### 3.3.4 防火墙 Web 联调

- 启动 Flask 后端（方案 B），同伴 B 的前端 dev server 通过 proxy 访问
- 在浏览器上完整跑一遍：增 → 列表 → 删 → 列表 → 清 → 列表
- 截图存档

### Phase 4（Day 11-12）：部署、演示视频、报告

#### 3.4.1 把前端 dist 部署到 OpenWrt

- 角色 B 给你 `frontend/dist/`
- Samba 推到 OpenWrt：`\\OpenWrt-IP\p0\dist\`
- 在 OpenWrt 上：
  ```sh
  cp -r /mnt/p0/dist /www/app
  ```
- 验证：浏览器访问 `http://<OpenWrt-IP>/app/`，应看到 Vue 页面
- 如果 Flask 静态托管方案：把 `dist/` 放到 `backend/static/`，由 Flask 提供

#### 3.4.2 最终演示视频（≤ 5 分钟）

**录制脚本（建议提前写在 `docs/demo-script.md`）：**

1. (0:00-0:20) OpenWrt VM 启动画面，简介环境
2. (0:20-0:40) 打开浏览器访问 Web 应用首页
3. (0:40-1:40) 流量监控：
   - 介绍页面布局
   - 启动 `iperf3` 或 wget 造流量
   - 观察折线图实时上升、表格更新
   - 说明字段含义（峰值、2s/10s/40s 均值）
4. (1:40-3:30) 防火墙配置：
   - 切到防火墙页
   - 演示当前规则列表为空
   - 添加规则（如 drop tcp port 80）
   - 切回浏览器另一个标签或 cmd 演示 `curl` 被拒
   - 删除规则
   - 演示访问恢复
   - 演示参数非法时的错误提示
5. (3:30-4:30) 后台架构简介：
   - 终端展示 C 程序在跑、`/tmp/traffic.json` 在更新
   - 展示 Flask 后端日志
   - 展示 `nft list ruleset` 看真实规则
6. (4:30-5:00) 总结
   
**工具**：OBS Studio（免费）、Bandicam、ScreenToGif（短片）
**导出**：mp4，1080p，码率适中（≤ 200MB），命名 `张三+李四+王五_演示.mp4`

#### 3.4.3 报告"部署与运行"章节

- 你主笔以下内容，提交 PR：
  - VMware + OpenWrt 安装过程（含截图）
  - 网络配置过程（截图）
  - Samba 配置过程
  - 部署架构图（哪个进程跑在哪儿）
  - 联调中遇到的问题与解决（动态库、CRLF、网卡名、fw4 命令等）
- 运行截图汇总到 `docs/screenshots/`

#### 3.4.4 AI 使用说明你的部分

- 在 `docs/ai-usage.md` 加你的二级标题：
  - 你用 AI 做了什么（例如：让 AI 解释 fw4 命令、生成排错指令、写部署脚本）
  - 提示词截图或文字
  - 评价（哪些有用、哪些是错的、你怎么改）
- **漏写本项 = 0 分**

## 四、关键操作速查

### 4.1 OpenWrt 常用命令

| 操作 | 命令 |
|---|---|
| 看网卡 | `ip addr` |
| 看路由 | `ip route` |
| 看防火墙 | `fw4 print` 或 `nft list ruleset` |
| 重启网络 | `/etc/init.d/network restart` |
| 装包 | `opkg update && opkg install <pkg>` |
| 看 overlay 容量 | `df -h /overlay` |
| 抓包 | `tcpdump -i br-lan -nn` |

### 4.2 文件传输优先级

1. **Samba**：最方便，Windows 直接 `\\OpenWrt-IP\p0` 拖拽
2. **scp**：`scp file root@OpenWrt-IP:/path`，需要 `opkg install openssh-sftp-server`
3. **wget**：`wget http://<角色 A 起的简单 HTTP 服务>/file`，临时用
4. **粘贴**：极短文本可直接 `cat > file <<EOF` 粘贴

### 4.3 常见错误对照表

| 现象 | 原因 | 解决 |
|---|---|---|
| `bad interpreter: No such file...` | 脚本是 CRLF | `dos2unix file.sh` 或 `sed -i 's/\r$//' file.sh` |
| `Permission denied` | 没 +x | `chmod +x file` |
| `library not found` | 动态库缺失 | `opkg install libpcap1` 或让 A 静态编译 |
| `/overlay: no space` | overlay 满 | 卸载不必要包，或扩磁盘 |
| `Operation not permitted` | 防火墙脚本权限 | 用 root 跑 |
| Windows 主机访问 VM IP 不通 | 不在同一网段 | 重新对照 VMnet8 网段改 IP |

## 五、与队友的同步接触点

| 时机 | 找谁 | 同步什么 |
|---|---|---|
| Phase 1 末 | 角色 A | 提供 OpenWrt IP、网卡名（写入 `docs/env.md`） |
| Phase 2 中 | 角色 A | 反馈交叉编译产物运行结果（成功/动态库缺失/字段问题） |
| Phase 2 末 | 角色 B | 给他确认前端 proxy 该指向哪里 |
| Phase 3 中 | 角色 A | 反馈 shell 脚本在 OpenWrt 上的兼容性问题 |
| Phase 3 末 | 全员 | 防火墙规则生效验证证据汇总 |
| Phase 4 中 | 角色 B | 拿 `dist/` 部署 |
| Phase 4 末 | 全员 | 演示视频与报告截图 |

## 六、自检清单

- [ ] VMware 17 已装
- [ ] OpenWrt VM 启动成功，能 SSH、能上网、`opkg update` 通过
- [ ] Samba 配好，Windows 能访问 `\\OpenWrt-IP\p0`
- [ ] `docs/env.md` 已填且角色 A 已确认
- [ ] 流量监控 C 程序在 OpenWrt 上能跑、`/tmp/traffic.json` 持续更新
- [ ] 造流量时前端折线图有实时反应
- [ ] 防火墙 4 个脚本在 OpenWrt 上手动测试均通过
- [ ] 规则生效"前/后/恢复"三段访问验证有完整证据截图
- [ ] Flask 后端在 OpenWrt 上能跑（最终演示阶段）
- [ ] 前端 `dist/` 部署后浏览器可访问且功能可用
- [ ] 演示视频 ≤ 5 分钟，覆盖流量监控 + 防火墙生效验证
- [ ] 报告"部署与运行"章节完成
- [ ] AI 使用说明你那部分已写
