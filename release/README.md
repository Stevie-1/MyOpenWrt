# release/ — OpenWrt 部署产物

本目录存放 **可直接 push 给 Role C** 的二进制和部署辅助文件，由 Role A
在 WSL2 上交叉编译产生。

## 当前版本

| 项 | 值 |
|---|---|
| 文件 | `traffic_monitor` |
| 版本 | `0.1.0` |
| 目标 | OpenWrt 24.10 x86_64 (musl) |
| 大小 | ~270 KB（已 strip） |
| 依赖 | 仅 `libc.so`（musl，OpenWrt 自带）；`libpcap` 静态链接进入二进制 |
| SHA256 | 见同目录下 `traffic_monitor.sha256` |

## 部署给 OpenWrt（给 Role C 的步骤）

下面以 `\\OpenWrt-IP\p0\`（Samba 共享）为投递通道。如改用 SCP，方法类似。

```bash
# 在 Windows 资源管理器：把 release/traffic_monitor 拖入 \\OpenWrt-IP\p0\

# 在 OpenWrt SSH：
cp /mnt/p0/traffic_monitor /usr/bin/traffic_monitor
chmod +x /usr/bin/traffic_monitor

# 烟测：
/usr/bin/traffic_monitor --version            # 期望: 0.1.0
/usr/bin/traffic_monitor --self-test -o /tmp/traffic.json
cat /tmp/traffic.json | head -20                    # 期望: 合法 JSON, items 3 条

# 正式运行：抓 br-lan，写 /tmp/traffic.json，每秒一次
/usr/bin/traffic_monitor -i eth0 -t 1000 -o /tmp/traffic.json &
```

## 校验 SHA256

```bash
# WSL2 上重算：
sha256sum release/traffic_monitor

# OpenWrt 上对账：
sha256sum /usr/bin/traffic_monitor
```

两边必须一致；不一致说明传输过程中文件被改了（编码、换行被改写等）。

## 校验 ELF 类型

```bash
file release/traffic_monitor
# 应包含：ELF 64-bit LSB executable, x86-64, ...
#         interpreter /lib/ld-musl-x86_64.so.1
#         stripped
```

如果看到 `interpreter /lib64/ld-linux-x86-64.so.2`（glibc）说明用错 Makefile，
重新跑 `make -f Makefile.openwrt`。

## 重新构建

如果改了 `traffic-monitor/src/*.c` 或 `include/*.h`，按以下流程产出新版：

```bash
cd traffic-monitor
make -f Makefile.openwrt clean
make -f Makefile.openwrt
~/openwrt-sdk/staging_dir/toolchain-x86_64_gcc-13.3.0_musl/bin/x86_64-openwrt-linux-musl-strip bin/traffic_monitor.openwrt
cp bin/traffic_monitor.openwrt ../release/traffic_monitor
sha256sum ../release/traffic_monitor | tee ../release/traffic_monitor.sha256
```

## CLI 参数（运行时）

```
traffic_monitor 0.1.0 — per-flow traffic stats via libpcap
  -i, --iface IFACE     network interface (default: any)
  -f, --filter EXPR     BPF filter expression (default: "ip")
  -o, --output PATH     JSON output path (default: /tmp/traffic.json)
  -s, --snaplen N       pcap snaplen bytes (default: 96)
  -t, --interval MS     write/tick interval (default: 1000)
      --self-test       写一份固定样本 JSON 后退出（无需 root，CI/对接用）
  -h, --help            打印帮助
      --version         打印版本
```

输出 JSON 的字段定义见 `docs/api.md` 第 2 节"流量监控"。
