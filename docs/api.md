# API 契约 v1

本文件是团队三人合作的"合同"。任何字段变更先发 PR 改本文件，三人 review 通过后再改代码。

- **版本**：v1.0.0
- **基础路径**：`/api`
- **后端地址**：开发期 `http://<WSL2 IP>:5000`，生产期 `http://<OpenWrt VM IP>:5000`
- **前端开发期通过 Vite proxy 转发 `/api/*`**，前端代码统一写相对路径 `/api/xxx`
- **响应格式**：JSON，UTF-8
- **时间戳**：毫秒 Unix 时间戳（`Date.now()`），整数

## 通用约定

### 成功响应

业务接口的响应顶层都有以下结构（具体数据在不同接口里有不同字段）：

```json
{
  "ok": true,
  "ts": 1736838400123,
  "...": "业务字段"
}
```

### 错误响应

校验失败、命令执行失败时，返回 4xx 状态码 + JSON：

```json
{
  "ok": false,
  "message": "human-readable error message",
  "field": "可选：哪个字段错了",
  "code": "可选：业务错误码"
}
```

| HTTP | 含义 |
|---|---|
| 400 | 参数缺失/类型错误/格式不符 |
| 422 | 参数语义错误（如端口超范围、IP 非法、协议不在白名单） |
| 404 | 资源不存在（如删除一个不存在的规则 ID） |
| 500 | 服务端异常（subprocess 抛错、JSON 读取失败等） |

前端约定用 axios 拦截器统一处理：

```ts
axios.interceptors.response.use(
  r => r,
  err => { ElMessage.error(err.response?.data?.message ?? '请求失败'); return Promise.reject(err) }
)
```

## 1. 健康检查

### `GET /api/health`

**响应 200**：

```json
{
  "ok": true,
  "ts": 1736838400123,
  "mockMode": true,
  "version": "1.0.0"
}
```

字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `ok` | boolean | 永远为 true（异常时 Flask 会返 500） |
| `ts` | int | 毫秒时间戳 |
| `mockMode` | boolean | 当前后端是否处于 Mock 模式（部署期排查用） |
| `version` | string | 后端版本 |

## 2. 流量监控

### `GET /api/traffic`

返回当前所有活动连接的统计。

**响应 200**：

```json
{
  "ok": true,
  "ts": 1736838400123,
  "items": [
    {
      "srcIp": "192.168.1.10",
      "dstIp": "8.8.8.8",
      "srcPort": 54321,
      "dstPort": 443,
      "proto": "tcp",
      "rxBytes": 12345,
      "txBytes": 678,
      "peak": 102400,
      "avg2s": 8192,
      "avg10s": 4096,
      "avg40s": 1024
    }
  ]
}
```

### Traffic Item 字段对照表

| 字段 | 类型 | 单位 | 范围 | 说明 |
|---|---|---|---|---|
| `srcIp` | string | - | IPv4 点分十进制 | 源 IP（C 程序按"本机/对端"区分时填本机） |
| `dstIp` | string | - | IPv4 点分十进制 | 目的 IP |
| `srcPort` | int | - | 0-65535 | 源端口；ICMP 为 0 |
| `dstPort` | int | - | 0-65535 | 目的端口；ICMP 为 0 |
| `proto` | string | - | `"tcp"` \| `"udp"` \| `"icmp"` \| `"other"` | 协议类型 |
| `rxBytes` | int | 字节 | ≥ 0 | 累计接收字节数 |
| `txBytes` | int | 字节 | ≥ 0 | 累计发送字节数 |
| `peak` | int | 字节/秒 | ≥ 0 | 该连接历史峰值速率 |
| `avg2s` | int | 字节/秒 | ≥ 0 | 过去 2 秒平均速率 |
| `avg10s` | int | 字节/秒 | ≥ 0 | 过去 10 秒平均速率 |
| `avg40s` | int | 字节/秒 | ≥ 0 | 过去 40 秒平均速率 |

### 数据源切换

- `MOCK_MODE=true`：返回 `backend/mock/traffic.json` 内容
- `MOCK_MODE=false`：读取 `TRAFFIC_JSON_PATH`（默认 `/tmp/traffic.json`，由 C 程序周期性写入）；文件不存在时降级为空 items 并日志告警

### 轮询频率

前端建议每 1500 ms 拉一次。C 程序每 1000 ms 更新 JSON 文件。

## 3. 防火墙配置

### 3.1 `GET /api/firewall/rules`

返回当前所有自定义规则。

**响应 200**：

```json
{
  "ok": true,
  "ts": 1736838400123,
  "rules": [
    {
      "id": "rule-1",
      "proto": "tcp",
      "src": "0.0.0.0/0",
      "dst": "192.168.1.1",
      "port": 80,
      "action": "drop"
    }
  ]
}
```

### Firewall Rule 字段对照表

| 字段 | 类型 | 取值 | 说明 |
|---|---|---|---|
| `id` | string | 后端生成 | 规则唯一 ID；本实验用 `rule-<n>` 简单递增 |
| `proto` | string | `"tcp"` \| `"udp"` \| `"icmp"` | 协议 |
| `src` | string | IPv4 / CIDR / `"any"` | 源地址 |
| `dst` | string | IPv4 / CIDR / `"any"` | 目的地址 |
| `port` | int | 1-65535 | 端口（ICMP 时忽略，前端可填 0 或任意值） |
| `action` | string | `"accept"` \| `"reject"` \| `"drop"` | 处理动作 |

### 3.2 `POST /api/firewall/rules`

**请求体**：

```json
{
  "proto": "tcp",
  "src": "0.0.0.0/0",
  "dst": "192.168.1.1",
  "port": 80,
  "action": "drop"
}
```

**校验规则**（后端 `_validators.py` 严格执行）：

- `proto` ∈ `{tcp, udp, icmp}`，否则 422
- `action` ∈ `{accept, reject, drop}`，否则 422
- `src`、`dst` 必须是合法 IPv4 / CIDR / 字面量 `"any"`，否则 422
- `port` 必须是整数且 `1 ≤ port ≤ 65535`，否则 422
- 任何字段缺失返 400
- **拒绝命令注入字符**：`;`、`|`、`&`、`` ` ``、`$`、`\n`、`\r` 出现在任意字符串字段都返 422

**响应 200（成功）**：

```json
{
  "ok": true,
  "ts": 1736838400123,
  "ruleId": "rule-3",
  "stdout": "Rule added successfully\n",
  "stderr": "",
  "code": 0
}
```

**响应 422（校验失败）**：

```json
{
  "ok": false,
  "message": "invalid proto: 'sctp' not in {tcp, udp, icmp}",
  "field": "proto"
}
```

**响应 500（脚本执行失败）**：

```json
{
  "ok": false,
  "message": "firewall script failed",
  "stdout": "",
  "stderr": "nft: command not found\n",
  "code": 127
}
```

### 3.3 `DELETE /api/firewall/rules/<ruleId>`

**路径参数**：`ruleId` 是 `GET /api/firewall/rules` 返回的某条规则的 `id`。

**响应 200**：

```json
{
  "ok": true,
  "ts": 1736838400123,
  "stdout": "Rule rule-2 deleted\n",
  "stderr": "",
  "code": 0
}
```

**响应 404**：规则不存在。

### 3.4 `POST /api/firewall/clear`

清空所有自定义规则。无请求体。

**响应 200**：

```json
{
  "ok": true,
  "ts": 1736838400123,
  "stdout": "All custom rules cleared\n",
  "stderr": "",
  "code": 0
}
```

## 4. CORS

后端默认放行：

- `http://localhost:5173`
- `http://127.0.0.1:5173`

部署到 OpenWrt 后建议前端与后端**同源**部署（Flask 静态托管 `dist/`），生产期无需 CORS。

## 5. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-05-14 | 初稿，定义 health、traffic、firewall 全部接口 |
