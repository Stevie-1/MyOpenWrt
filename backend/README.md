# Flask 后端

提供 `/api/health`、`/api/traffic`、`/api/firewall/*` 共 5 个 REST 接口。详见仓库根目录 [`docs/api.md`](../docs/api.md)。

## 本地启动

```bash
# 在仓库根目录执行
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cd backend
python app.py
# 监听 0.0.0.0:5000，MOCK_MODE 默认 true
```

冒烟测试：

```bash
curl http://localhost:5000/api/health
curl http://localhost:5000/api/traffic
curl http://localhost:5000/api/firewall/rules
curl -X POST -H "Content-Type: application/json" \
     -d '{"proto":"tcp","src":"any","dst":"192.168.1.1","port":80,"action":"drop"}' \
     http://localhost:5000/api/firewall/rules
```

## Mock 模式与真实模式

通过环境变量 `MOCK_MODE` 切换：

```bash
MOCK_MODE=true  python app.py    # 默认：返 backend/mock/*.json
MOCK_MODE=false python app.py    # 部署：读 /tmp/traffic.json + 调 shell 脚本
```

`MOCK_MODE=true` 时：

- `GET /api/traffic` 返 `backend/mock/traffic.json`
- `GET /api/firewall/rules` 返内存 store（启动时从 `mock/firewall_rules.json` 初始化）
- `POST/DELETE /api/firewall/*` 都对内存 store 生效，**Flask 重启后清零**

`MOCK_MODE=false` 时：

- `GET /api/traffic` 读 `TRAFFIC_JSON_PATH`（默认 `/tmp/traffic.json`），由 C 程序写入
- `GET/POST/DELETE /api/firewall/*` 调用 `FIREWALL_SCRIPTS_DIR/*.sh`（默认 `/usr/local/bin/`）—— 这部分由 Phase 3 完成

## 完整环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `MOCK_MODE` | `true` | Mock 与真实切换 |
| `TRAFFIC_JSON_PATH` | `/tmp/traffic.json` | C 程序输出文件 |
| `FIREWALL_SCRIPTS_DIR` | `/usr/local/bin` | shell 脚本目录 |
| `FLASK_HOST` | `0.0.0.0` | 监听地址 |
| `FLASK_PORT` | `5000` | 监听端口 |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 逗号分隔 |

## 目录结构

```text
backend/
├── app.py                # Flask app 创建与启动入口
├── config.py             # Config dataclass，集中读环境变量
├── requirements.txt
├── api/
│   ├── __init__.py
│   ├── traffic.py        # GET /api/traffic
│   ├── firewall.py       # /api/firewall/* 增删查清
│   └── _validators.py    # 白名单 + 防注入（5 字段全覆盖）
└── mock/
    ├── traffic.json
    └── firewall_rules.json
```

## 测试

```bash
# 在仓库根目录执行
pytest test/ -v
```

测试包含：

- `test_health.py`：健康检查
- `test_traffic_api.py`：流量接口字段完整性 + Mock 数据一致性
- `test_firewall_api.py`：增删查清 + **5 种安全场景**（非法 proto / action / IP / port + 命令注入字符）
