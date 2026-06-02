# 防火墙 Shell 脚本（Phase 3）

> 在 OpenWrt 24.10 上用 `uci` 写入 `/etc/config/firewall` 再 `fw4 reload` 落地规则（fw4 = nftables 后端）。规则持久化、可在 LuCI / `fw4 print` 看到、重启不丢。由 Flask 后端 [backend/api/firewall.py](../backend/api/firewall.py) 在 `MOCK_MODE=false` 下通过 `subprocess.run([脚本, ...argv])` 调用。

## 文件清单

| 文件 | 接口 | 参数 | 退出码 |
|---|---|---|---|
| `add_rule.sh` | 添加规则 | `<proto> <src> <dst> <port> <action>` | 0=成功；64=参数错；其它=uci/fw4 失败 |
| `del_rule.sh` | 删除规则 | `<ruleId>` | 0=成功；1=未找到；64=参数错；其它=失败 |
| `list_rules.sh` | 列出规则 | 无 | 0=成功，JSON 输出到 stdout |
| `clear_rules.sh` | 清空规则 | 无 | 0=成功；其它=失败 |

## 规则标识与 stdout 契约

- 每条规则在 uci 里以 `name='webfw-<n>'` 标记，`<n>` 单调递增（取现有 `webfw-*` 最大序号 +1）。对前端而言这个 `webfw-<n>` 就是规则 `id`。
- **`webfw-` 前缀是本程序的私有命名空间**：`list_rules.sh` / `clear_rules.sh` 只列举/清除带此前缀的规则，绝不动系统默认规则。
- `add_rule.sh` 成功时在 stdout 打印一行 `ruleId=webfw-<n>`，后端用它回填响应里的 `ruleId` 字段。

## uci 字段映射

| API 字段 | uci 选项 | 说明 |
|---|---|---|
| （规则名） | `name='webfw-<n>'` | 标识本程序创建的规则 |
| `proto` | `proto` | `tcp` / `udp` / `icmp` |
| `action` | `target` | 转大写：`ACCEPT` / `REJECT` / `DROP` |
| `src` | `src_ip` | 非 `any` 才设；`src` 区域固定 `'*'`（任意 zone），`family='ipv4'` |
| `dst` | `dest_ip` | 非 `any` 才设 |
| `port` | `dest_port` | 仅 `tcp`/`udp` 设置；`icmp` 不设 |

## 设计约束

1. **Shebang `#!/bin/sh`**：OpenWrt 默认 ash 而非 bash，绝不使用 `[[ ]]`、数组等 bash 扩展。
2. **`set -eu`**：错误立即退出、未定义变量报错；`set -e` 下用 `if/then` 而非 `a && b || c`（后者会吞掉退出码）。
3. **位置参数 `$1 $2 ...`**：禁止 `eval`、禁止字符串拼接命令、禁止 `sh -c "..."`；所有用户值只作为 `uci set ...=<value>` 的值或 `sed` 精确匹配。
4. **输入信任级别**：后端 `_validators.py` 已做强白名单 + 反注入 + `ruleId` 形状校验，但脚本仍把每个参数视为不可信。
5. **`list_rules.sh` 输出 JSON**：与 [docs/api.md](../docs/api.md) firewall rule schema 完全一致，手写拼接（不依赖 `jq`），便于后端 `json.loads()` 解析。

## 在 OpenWrt 上部署

```sh
# 通过 Samba 把 firewall-scripts/ 拷到 /mnt/p0/，再：
cp /mnt/p0/firewall-scripts/*.sh /usr/local/bin/
chmod +x /usr/local/bin/*.sh
# 防 CRLF 兜底（Windows 上改过的话）
dos2unix /usr/local/bin/*.sh 2>/dev/null || sed -i 's/\r$//' /usr/local/bin/*.sh
```

部署后 Flask 在 `MOCK_MODE=false` 下通过 `FIREWALL_SCRIPTS_DIR`（默认 `/usr/local/bin`）找到它们；单条脚本超时预算由 `FIREWALL_TIMEOUT`（默认 8s）控制。

## 本地语法检查（WSL2）

```bash
for f in firewall-scripts/*.sh; do sh -n "$f" && echo "OK: $f"; done
# 有 shellcheck 的话：
command -v shellcheck >/dev/null && shellcheck firewall-scripts/*.sh
```

> WSL2 上没有 `uci`/`fw4`，无法真正执行这些脚本。后端真实分支的可测性通过 `test/fixtures/firewall-stub/` 桩脚本 + [test/test_firewall_real.py](../test/test_firewall_real.py) 保证；真机生效由角色 C 验证。

## 真机验证（角色 C，指导书 3.3 节硬要求）

需要一条完整的"前 / 后 / 恢复"证据链，全程截图或录屏，存到 `docs/screenshots/firewall-verify/`：

```sh
# 0) 部署后先手测 4 个脚本本身能跑
/usr/local/bin/list_rules.sh                                  # {"rules":[]}
/usr/local/bin/add_rule.sh tcp any 192.168.122.100 80 drop    # ruleId=webfw-1
/usr/local/bin/list_rules.sh                                  # 含 webfw-1
/usr/local/bin/del_rule.sh webfw-1                            # Rule webfw-1 deleted
/usr/local/bin/clear_rules.sh                                 # Cleared N rules

# 1) 加规则前：Windows 主机能访问 OpenWrt 的 80 端口（LuCI）
#    Windows: curl http://192.168.122.100 --max-time 3   → 返回 HTML

# 2) 加规则：丢弃到本机 80 的 tcp
/usr/local/bin/add_rule.sh tcp any 192.168.122.100 80 drop

# 3) 加规则后：同样的请求被拒/超时
#    Windows: curl http://192.168.122.100 --max-time 3   → 超时/拒绝

# 4) 看真实生效的规则
fw4 print | grep -A3 webfw     # 或 nft list ruleset

# 5) 删规则后恢复：访问再次成功
/usr/local/bin/del_rule.sh webfw-1
#    Windows: curl http://192.168.122.100 --max-time 3   → 返回 HTML
```

随后用浏览器经前端走一遍 增 → 列表 → 删 → 列表 → 清，确认 Web 全链路（前端 → Flask → 脚本 → fw4）通畅。
