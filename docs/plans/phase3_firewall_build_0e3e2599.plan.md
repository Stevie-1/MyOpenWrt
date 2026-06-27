---
name: phase3 firewall build
overview: 实现防火墙真实链路：4 个基于 uci+fw4 的 OpenWrt 脚本 + backend/api/firewall.py 非 mock 分支（subprocess argv 调用）+ ruleId 校验，并用桩脚本在 WSL2 上做端到端单测，真机生效由角色 C 按文档验证。
todos:
  - id: validators
    content: _validators.py 新增 validate_rule_id（^[A-Za-z0-9_-]{1,64}$）
    status: completed
  - id: config
    content: config.py 新增 firewall_timeout（env FIREWALL_TIMEOUT，默认 8s）
    status: completed
  - id: backend
    content: firewall.py 加 _run_script 并实现 add/list/delete/clear 的真实非 mock 分支，解析 ruleId= 与退出码映射(1→404)
    status: completed
  - id: scripts
    content: 用 uci+fw4 reload 实现 add_rule.sh / list_rules.sh / del_rule.sh / clear_rules.sh（ash 兼容、手写 JSON、webfw- 前缀）
    status: completed
  - id: scripts-readme
    content: 更新 firewall-scripts/README.md：uci 字段映射、ruleId= 契约、退出码、真机验证节
    status: completed
  - id: stub
    content: 新建 test/fixtures/firewall-stub/ 桩脚本（文件态模拟，不碰系统防火墙）
    status: completed
  - id: tests
    content: 新建 test/test_firewall_real.py：monkeypatch config 走桩，覆盖 happy path/404/500/缺失/非法 ruleId 不触发 subprocess
    status: completed
  - id: verify
    content: 本地验收：sh -n + 可选 shellcheck + pytest 全绿
    status: completed
  - id: commit
    content: squash commit + rebase + push origin main
    status: completed
isProject: false
---

# Phase 3：防火墙配置（可 build / 可测）

## 总体目标对齐

把 [backend/api/firewall.py](backend/api/firewall.py) 里 4 个接口的"非 mock"分支从 501 占位换成真实 `subprocess.run([...])` 调用 [firewall-scripts/](firewall-scripts/) 的脚本；脚本用 OpenWrt 24.10 的 `uci`+`fw4 reload` 落地规则。WSL2 上无 OpenWrt，所以"可 build"= 脚本过 `sh -n`/`shellcheck` + 后端真实分支用**桩脚本**跑通单测；真机生效由角色 C 验证（[docs/plans/role-C-vmware-openwrt.md](docs/plans/role-C-vmware-openwrt.md) 3.3 节）。

不破坏现有 44 个测试：`config` 默认 `MOCK_MODE=true`，现有 mock 用例保持绿；真实分支测试通过 monkeypatch `api.firewall.config` 注入 `mock_mode=False` + 桩脚本目录。

## 设计决策

- 规则后端：**uci + fw4 reload**（持久化、`fw4 print`/LuCI 可见、ID 稳定）。
- 规则标识：uci `name='webfw-<n>'`，对前端即 `id`。`<n>` 取现有 webfw 规则最大序号 +1。前缀 `webfw-` 用于只列/清本程序创建的规则，不动系统规则。
- ID 生成方：由 `add_rule.sh` 生成并在 stdout 打印 `ruleId=<id>`，后端解析回填 `ruleId`（保持 API 响应 shape 不变）。
- uci 字段映射：`target=ACCEPT|REJECT|DROP`、`family=ipv4`、`src='*'`、`proto`、`src_ip`(非 any 才设)、`dest_ip`(非 any 才设)、`dest_port`(仅 tcp/udp)。

## 一、后端真实分支（WSL2 可测）

### 1.1 [backend/api/_validators.py](backend/api/_validators.py)
新增 `validate_rule_id(rule_id)`：`^[A-Za-z0-9_-]{1,64}$`，否则 `ValidationError(field="ruleId")`。DELETE 的路径参数来自客户端，进 argv 前必须过此校验。

### 1.2 [backend/config.py](backend/config.py)
新增 `firewall_timeout`（env `FIREWALL_TIMEOUT`，默认 `8`，留足 `fw4 reload` 时间）。

### 1.3 [backend/api/firewall.py](backend/api/firewall.py)
新增 `_run_script(name, args) -> (code, stdout, stderr)`：
- 路径 `os.path.join(config.firewall_scripts_dir, name)`，`subprocess.run([path, *args], shell=False, capture_output=True, text=True, timeout=config.firewall_timeout)`。
- `FileNotFoundError`/`PermissionError` → 抛内部异常，路由层转 500；`TimeoutExpired` → 500（`message: firewall script timeout`）。

替换 4 处 `_not_implemented(...)`：
- `add_rule` 真实：`_run_script("add_rule.sh",[proto,src,dst,str(port),action])`；`code!=0` → 500（回传 stdout/stderr/code）；`code==0` → 解析 stdout 中 `ruleId=` 行得到 `ruleId`，返回 `ok/ruleId/stdout/stderr/code`。
- `list_rules` 真实（`_list_real_rules`）：`_run_script("list_rules.sh",[])`，`json.loads(stdout)["rules"]`；解析失败记 warning 并返回 `[]`。
- `delete_rule` 真实：先 `validate_rule_id(rule_id)`（失败 422），`_run_script("del_rule.sh",[rule_id])`；约定退出码 `1`→404，`0`→200，其它→500。
- `clear_rules` 真实：`_run_script("clear_rules.sh",[])`，`code!=0`→500。

保持响应字段与 [docs/api.md](docs/api.md) 一致（`ok/ts/ruleId?/stdout/stderr/code`）。

## 二、四个真实脚本（OpenWrt uci/fw4）

全部 `#!/bin/sh` + ash 兼容，禁 `eval`/字符串拼命令，参数仅作 argv 透传。注意 `set -e` 下用 `if/then` 而非 `a && b || c`。

- [firewall-scripts/add_rule.sh](firewall-scripts/add_rule.sh)：算 next id → `SEC=$(uci add firewall rule)` → `uci set` 各字段 → `uci commit firewall` → `fw4 reload` → 打印 `ruleId=webfw-<n>`。
- [firewall-scripts/list_rules.sh](firewall-scripts/list_rules.sh)：`uci -q show firewall` 用 `sed` 抽 `name='webfw-<n>'` 的 section，逐条读字段，**手写 JSON**（值已被后端校验，无需 jq 依赖），target 转小写、缺省 `src/dst=any`、`port` 缺省 `0`，输出 `{"rules":[...]}`。
- [firewall-scripts/del_rule.sh](firewall-scripts/del_rule.sh)：按 `name='<ruleId>'` 找 section，找不到 `exit 1`，否则 `uci delete`+`commit`+`fw4 reload`。
- [firewall-scripts/clear_rules.sh](firewall-scripts/clear_rules.sh)：循环删除所有 `webfw-*`（section 名会变，每次取 `head -n1`），计数后 `commit`+`reload`，打印 `Cleared <n> rules`。

更新 [firewall-scripts/README.md](firewall-scripts/README.md)：写明 uci 字段映射、`ruleId=` stdout 契约、退出码语义（0/1/64/其它）。

## 三、WSL2 可测：桩脚本 + 单测

- 新建 `test/fixtures/firewall-stub/`：与 4 个脚本同名、同契约的**桩**，用本地文件（如 `$STUB_STATE` 环境变量指向的临时 JSON）模拟增删查清，**不碰系统防火墙**；`add` 打印 `ruleId=`，`del` 不存在时 `exit 1`，注入态可被断言。
- 新建 `test/test_firewall_real.py`：fixture 用 `dataclasses.replace(config, mock_mode=False, firewall_scripts_dir=<stub dir>)` monkeypatch `api.firewall.config`，覆盖：
  - add→list→delete→clear happy path（真实 subprocess 走桩）；
  - `del` 未知 id → 404；脚本 `code!=0` → 500；脚本缺失 → 500；
  - 非法 ruleId（`../`、含空格）→ 422 且桩**未被调用**（断言状态文件无变化）；
  - 复用注入用例：确认非法输入在 subprocess 之前就被拒。
- 现有 [test/test_firewall_api.py](test/test_firewall_api.py) 不动，确保 mock 路径仍绿。

## 四、写进 plan 文档：角色 C 真机验证（含命令）

在 [firewall-scripts/README.md](firewall-scripts/README.md) 增"真机验证"节，沿用 [docs/plans/role-C-vmware-openwrt.md](docs/plans/role-C-vmware-openwrt.md) 3.3.3 证据链：部署 → 手测 4 脚本 → `add drop tcp 80` → Windows `curl` 被拒 → `del` 后恢复 → `fw4 print`/`nft list ruleset` 截图存 `docs/screenshots/firewall-verify/`。

## 五、本地验收

- `sh -n firewall-scripts/*.sh`；有 `shellcheck` 则一并跑（无则跳过并提示）。
- `pytest test/ -v` 全绿（现有 44 + 新增真实分支用例）。
- 不交叉编译、不连真实 OpenWrt；真机部分由角色 C 执行。

## 六、提交

squash 一个 commit：`feat(firewall): implement uci/fw4 scripts and real backend path with stub-based tests`，rebase 后 push `origin main`。