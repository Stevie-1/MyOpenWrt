# 流量监控 C 程序（Phase 2 占位）

> 该目录将在 Phase 2 实现完整的 libpcap 抓包、五元组统计、滑动窗口与 JSON 输出。当前仅放骨架与 Makefile。

## 设计目标

- 在指定网卡上抓 IP 数据包，按 (srcIp, dstIp, srcPort, dstPort, proto) 五元组聚合
- 维护每条连接的：
  - 累计 `rxBytes` / `txBytes`
  - 历史 `peak` 速率（B/s）
  - 过去 2s / 10s / 40s 滑动窗口平均速率
- 每 1 秒将统计结果写入 `--out` 指定的 JSON 文件，写入采用 "tmp + rename" 原子替换避免后端读到半截
- 用 pthread 把抓包线程与统计上报线程解耦

## CLI 接口

```text
traffic_monitor -i <iface> -o <jsonPath> [-f <bpf_filter>] [-s <snaplen>]

  -i  网卡名（如 br-lan, eth0），必填
  -o  输出 JSON 文件路径，必填
  -f  BPF 过滤表达式，默认 "ip"
  -s  pcap snaplen，默认 96（够看到完整 IP+TCP/UDP 头）
```

## 输出 JSON 结构

与 `docs/api.md` 中 `/api/traffic` 完全一致，可直接被 Flask 后端在 `MOCK_MODE=false` 时读取。

## 构建

### 本地（WSL2 / Ubuntu）

```bash
sudo apt install -y build-essential libpcap-dev
make
./bin/traffic_monitor -i eth0 -o /tmp/traffic.json
```

### 交叉编译到 OpenWrt（24.10 x86_64 musl）

```bash
# 下载并解压 OpenWrt SDK 到 ~/openwrt-sdk/
export SDK_DIR=~/openwrt-sdk
make -f Makefile.openwrt
# 产物：bin/traffic_monitor.openwrt
```

详细 SDK 准备步骤见 [docs/plans/role-A-wsl2-backend.md](../docs/plans/role-A-wsl2-backend.md) 的 Phase 1.2 节。

## 目录结构

```text
traffic-monitor/
├── src/
│   ├── main.c          # CLI 解析 + 启动
│   ├── capture.c       # libpcap 抓包线程
│   ├── stats.c         # 五元组哈希 + 滑动窗口
│   └── output.c        # JSON 序列化与原子写
├── include/
│   ├── capture.h
│   ├── stats.h
│   └── output.h
├── bin/                # 编译产物（被 .gitignore 忽略）
├── Makefile            # 本地编译
└── Makefile.openwrt    # 交叉编译
```
