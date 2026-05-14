# 角色 B 工作计划：Vue 前端开发同伴

> 在 Windows 宿主机上做前端工程，开发 Vue 3 单页应用，与角色 A 的 Flask 后端联调。

## 一、角色定位

- 开发环境：Windows + Node.js 20 LTS + pnpm（**不在 OpenWrt 里、不在 VMware 里**）
- 核心交付物：
  - `frontend/`：Vue 3 + Vite + TypeScript 工程
  - `views/TrafficView.vue`：流量监控页（ECharts 折线 + 表格）
  - `views/FirewallView.vue`：防火墙配置页（表单 + 规则表格 + 执行回显）
  - `frontend/dist/`：生产构建产物（最终交付时附带）
  - 实验报告中的"前端实现"章节、Web 界面截图
- 不负责：C/libpcap、Flask 后端、shell 脚本、OpenWrt VM 操作

## 二、前置准备（Day 0-1）

### 2.1 装 Node.js 20 LTS

- 下载：`https://nodejs.org/zh-cn/download/` 选 LTS 安装包
- 验证：
  ```powershell
  node -v   # 应输出 v20.x.x
  npm -v
  ```

### 2.2 装 pnpm（速度比 npm 快很多，磁盘占用小）

```powershell
npm i -g pnpm
pnpm -v
```

### 2.3 装 Git for Windows

- 下载：`https://git-scm.com/download/win`
- 安装时选 `Checkout as-is, commit Unix-style line endings`（避免 .sh 文件被改成 CRLF 把 OpenWrt 跑炸）
- 配置：
  ```powershell
  git config --global core.autocrlf input
  git config --global user.name "你的名字"
  git config --global user.email "你的邮箱"
  ```

### 2.4 推荐 IDE

- VSCode + 插件：
  - Vue - Official（Volar 的新名字）
  - ESLint
  - Prettier
  - TypeScript Vue Plugin
- 或 WebStorm

## 三、阶段任务

### Phase 0（Day 1）：等角色 A 建好仓库

- [ ] `git clone` 仓库到本地，例如 `D:\projects\ComputerNetworkExp`
- [ ] 通读 `README.md` 与 `docs/api.md` 草稿
- [ ] **重要**：和角色 A 一起 review API 契约，你从前端角度提需求：
  - 时间戳格式（毫秒还是秒？建议毫秒 `Date.now()`）
  - 分页/排序？流量列表如果上百条要不要分页？
  - 错误响应是 4xx + JSON 还是 200 + `{ok:false}`？（建议前者，更标准）
  - 防火墙 `port` 支持范围（如 `80-100`）吗？支持多端口逗号分隔吗？
- [ ] 把对齐结果 commit 到 `docs/api.md`

### Phase 1（Day 2-3）：初始化 Vue 工程

- [ ] 在 `frontend/` 目录执行：
  ```powershell
  cd ComputerNetworkExp
  pnpm create vite frontend --template vue-ts
  cd frontend
  pnpm install
  ```
- [ ] 装核心依赖：
  ```powershell
  pnpm add vue-router pinia axios
  pnpm add element-plus @element-plus/icons-vue
  pnpm add echarts vue-echarts
  pnpm add -D @types/node
  ```
- [ ] 配 `vite.config.ts` 代理：
  ```ts
  import { defineConfig } from 'vite'
  import vue from '@vitejs/plugin-vue'
  import path from 'path'
  
  export default defineConfig({
    plugins: [vue()],
    resolve: {
      alias: { '@': path.resolve(__dirname, 'src') }
    },
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://<角色 A 的 WSL2 IP 或 OpenWrt VM IP>:5000',
          changeOrigin: true
        }
      }
    }
  })
  ```
  > 角色 A 的 WSL2 IP 通过 `ip addr show eth0` 查；或者用 OpenWrt VM 的 IP 让后端跑那里。
- [ ] 配 Vue Router（`src/router/index.ts`）：
  ```ts
  import { createRouter, createWebHashHistory } from 'vue-router'
  export default createRouter({
    history: createWebHashHistory(),
    routes: [
      { path: '/', redirect: '/traffic' },
      { path: '/traffic',  component: () => import('@/views/TrafficView.vue') },
      { path: '/firewall', component: () => import('@/views/FirewallView.vue') }
    ]
  })
  ```
  > 用 hash 模式（`#/traffic`），OpenWrt 上静态托管最省心。
- [ ] `src/App.vue` 用 `<el-menu mode="horizontal">` 或 `<el-tabs>` 切换两个路由
- [ ] `src/main.ts` 注册 Element Plus 与 ECharts：
  ```ts
  import ElementPlus from 'element-plus'
  import 'element-plus/dist/index.css'
  import { use } from 'echarts/core'
  import { CanvasRenderer } from 'echarts/renderers'
  import { LineChart } from 'echarts/charts'
  import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
  use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])
  ```
- [ ] 跑 `pnpm dev`，打开 `http://localhost:5173`，能看到默认页且 `/api/health` 通过代理能返 200
- [ ] 推个 PR：`feat/frontend-bootstrap`

### Phase 2（Day 4-7）：流量监控页

- [ ] `src/types/traffic.ts` 按 `docs/api.md` 定义 TS 类型：
  ```ts
  export interface TrafficItem {
    srcIp: string; dstIp: string;
    srcPort: number; dstPort: number;
    proto: 'tcp' | 'udp' | 'icmp';
    rxBytes: number; txBytes: number;
    peak: number; avg2s: number; avg10s: number; avg40s: number;
  }
  export interface TrafficResponse { ts: number; items: TrafficItem[] }
  ```
- [ ] `src/api/traffic.ts`：
  ```ts
  import axios from 'axios'
  export const fetchTraffic = () => axios.get<TrafficResponse>('/api/traffic').then(r => r.data)
  ```
- [ ] `src/components/TrafficChart.vue`：
  - 用 `vue-echarts` 画**实时折线图**（横轴时间，纵轴速率 KB/s）
  - 维护一个 `ref<{ts: number, value: number}[]>` 滚动窗口，最多保留 60 个点
- [ ] `src/components/TrafficTable.vue`：
  - 用 `<el-table>` 展示当前所有连接的：源 IP、目的 IP、协议、累计、峰值、2s/10s/40s 均值
  - 列支持排序
- [ ] `src/views/TrafficView.vue`：
  - 上半部分图、下半部分表
  - `onMounted` 启动 `setInterval(fetchTraffic, 1500)`，`onBeforeUnmount` 清除
  - 用 `el-empty` 占位"暂无数据"
- [ ] **联调步骤**：
  1. 先用角色 A 的 Mock 接口跑通，前端独立可用
  2. 再切真实接口（角色 A 写完 C 程序后，base URL 不变，数据从真）
  3. 截图存到 `docs/screenshots/`

### Phase 3（Day 8-10）：防火墙配置页

- [ ] `src/types/firewall.ts`：
  ```ts
  export type Proto  = 'tcp' | 'udp' | 'icmp'
  export type Action = 'accept' | 'reject' | 'drop'
  export interface FirewallRule {
    id: string; proto: Proto; src: string; dst: string; port: number; action: Action;
  }
  export interface FirewallExecResult { ok: boolean; stdout: string; stderr: string; code: number }
  ```
- [ ] `src/api/firewall.ts`：增删查清四个方法
- [ ] `src/components/FirewallForm.vue`：
  - `<el-form>` 配 Element Plus 的 `rules` 做前端校验：
    - 协议 `<el-select>` 三选一
    - 源/目 IP `<el-input>`，前端用正则初校（后端会再校）
    - 端口 `<el-input-number :min="1" :max="65535">`
    - 动作 `<el-radio-group>`
  - 提交后调用 POST，loading 状态
- [ ] `src/components/RuleTable.vue`：
  - `<el-table>` 展示规则列表，每行有"删除"按钮
  - 顶部一个"清空全部"按钮（加 `<el-popconfirm>` 防误点）
- [ ] `src/components/ExecResultPanel.vue`：
  - `<el-card>` 折叠展示 `stdout`、`stderr`、`code`
  - **这是指导书 3.3 节硬要求**，必须可见
  - 失败时用 `<el-alert type="error">` 高亮
- [ ] `src/views/FirewallView.vue` 组装上述三个组件
- [ ] **联调**：
  - 让角色 C 在 OpenWrt 上跑后端，你用 Vite Dev Server 通过 proxy 访问
  - 截图：添加前后访问验证对比（角色 C 提供 `curl` 输出，你截图整合到页面或单独贴报告）

### Phase 4（Day 11-12）：生产构建 + 交付

- [ ] 跑 `pnpm build`，产出 `frontend/dist/`
- [ ] 把 `dist/` 交给角色 C，他通过 Samba 推到 OpenWrt
  - 部署位置二选一：
    - **方案 1**：Flask 静态托管 `dist/`（推荐，简单）
    - **方案 2**：OpenWrt 自带 uhttpd 托管 `/www/app/`
- [ ] 验证 OpenWrt 上的页面在 Windows Chrome 中能正常访问，所有功能可用
- [ ] 截运行图，存 `docs/screenshots/`
- [ ] 在实验报告中写"前端实现"章节：
  - 技术选型（Vue 3 + Vite + ECharts + Element Plus）
  - 组件结构图
  - 关键代码片段（路由、API 封装、ECharts option）
  - 与后端联调过程中遇到的问题
- [ ] **`docs/ai-usage.md`** 里也要写你的 AI 使用情况（提示词、生成代码片段、你的评价）
  - 三人合并到同一个文件，每人一个二级标题

## 四、关键技术注意点

### 4.1 ECharts 实时折线参考

```ts
import * as echarts from 'echarts/core'
const option = {
  xAxis: { type: 'time' },
  yAxis: { type: 'value', name: 'KB/s' },
  series: [{
    type: 'line',
    showSymbol: false,
    data: dataRef.value  // [{value:[ts, kbps]}, ...]
  }]
}
```

### 4.2 Element Plus 按需引入（减包体）

可选用 `unplugin-vue-components` 自动按需引入，体积能小一半。

### 4.3 路由模式选 hash 还是 history

- **hash（`#/traffic`）**：静态服务器零配置，刷新不 404 → **推荐**
- **history（`/traffic`）**：需要后端做 fallback 到 `index.html`，OpenWrt uhttpd 配麻烦

### 4.4 跨域 / 代理

- 开发期：Vite proxy（你已配），绝对路径写 `/api/xxx`，自动转发，**前端代码里不要写 `http://localhost:5000`**
- 生产期：和后端同源部署（OpenWrt 上 Flask 既托管 `dist/` 又提供 `/api/*`），同样写 `/api/xxx` 即可

### 4.5 错误处理

```ts
axios.interceptors.response.use(
  r => r,
  err => {
    ElMessage.error(err.response?.data?.message ?? '请求失败')
    return Promise.reject(err)
  }
)
```

## 五、与队友的同步接触点

| 时机 | 找谁 | 同步什么 |
|---|---|---|
| Phase 0 | 角色 A | API 契约 review，从前端使用角度提需求 |
| Phase 1 末 | 角色 A | Mock 数据是否符合你的页面预期 |
| Phase 2 中 | 角色 A | 真实接口替换 Mock 的时间点 |
| Phase 3 末 | 角色 C | 后端部署到 OpenWrt 后，前端 proxy target 切换 |
| Phase 4 | 角色 C | `dist/` 交付与部署位置确认 |
| Phase 4 | 全员 | 报告与截图汇集 |

## 六、自检清单

- [ ] `pnpm dev` 在 Windows 上正常启动
- [ ] Vite proxy 把 `/api/*` 转发到 Flask
- [ ] 流量监控页：实时折线 + 表格，正常显示 Mock 数据
- [ ] 流量监控页：切换到真实接口后数据正确
- [ ] 防火墙页：表单前端校验（协议、IP、端口、动作）
- [ ] 防火墙页：增删查清四操作都可调通
- [ ] 防火墙页：stdout/stderr/code 完整展示
- [ ] 路由切换流畅，刷新不 404
- [ ] `pnpm build` 产出 `dist/` 无错误
- [ ] `dist/` 在 OpenWrt 托管后浏览器访问正常
- [ ] 截图入 `docs/screenshots/`
- [ ] AI 使用说明你那部分已写

## 七、`frontend/.gitignore`（Vite 模板自带，但确认下）

```text
node_modules
dist
dist-ssr
*.local
.vite
.cache
.DS_Store
```

注意：**`node_modules` 一定别 commit**，几百 MB；`dist/` 平时也不 commit，只在交付 zip 前 build 一份。
