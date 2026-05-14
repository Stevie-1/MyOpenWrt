# 防火墙 Shell 脚本（Phase 3 占位）

> 本目录将在 Phase 3 实现 OpenWrt 24.10 `fw4`（nftables 后端）规则的增/删/查/清。当前 4 个 `.sh` 文件仅包含 shebang、参数校验与 `TODO` 占位输出，保证语法正确并能被后端 `subprocess.run([...])` 安全调用。

## 文件清单

| 文件 | 接口 | 参数 | 退出码 |
|---|---|---|---|
| `add_rule.sh` | 添加规则 | `<proto> <src> <dst> <port> <action>` | 0=成功，64=参数错，其它=失败 |
| `del_rule.sh` | 删除规则 | `<ruleId>` | 0=成功，1=未找到，64=参数错 |
| `list_rules.sh` | 列出规则 | 无 | 0=成功，输出 JSON 到 stdout |
| `clear_rules.sh` | 清空规则 | 无 | 0=成功 |

## 设计约束

1. **Shebang `#!/bin/sh`**：OpenWrt 默认是 ash 而非 bash，绝不使用 `[[ ]]`、数组等 bash 扩展。
2. **`set -eu`**：错误立即退出、未定义变量报错，避免静默失败。
3. **位置参数 `$1 $2 ...`**：禁止 `eval`，禁止字符串拼接命令，禁止 `bash -c "..."`。
4. **输入信任级别**：Flask 后端 `_validators.py` 已做强白名单 + 反注入，但本脚本仍需把每个参数视为不可信，只把它们作为 argv 透传给 `nft` / `uci` 命令。
5. **`list_rules.sh` 输出 JSON**：与 [docs/api.md](../docs/api.md) 中 firewall rule schema 完全一致，便于 Flask 后端用 `json.loads()` 直接解析。

## 在 OpenWrt 上部署

```sh
# 通过 Samba 把 firewall-scripts/ 整目录拷到 /mnt/p0/
cp /mnt/p0/firewall-scripts/*.sh /usr/local/bin/
chmod +x /usr/local/bin/*.sh
# 防 CRLF 兜底
sed -i 's/\r$//' /usr/local/bin/*.sh
```

部署后 Flask 在 `MOCK_MODE=false` 下会通过 `FIREWALL_SCRIPTS_DIR`（默认 `/usr/local/bin`）找到它们。

## 本地语法检查

```bash
for f in firewall-scripts/*.sh; do
    sh -n "$f" && echo "OK: $f"
done
```
