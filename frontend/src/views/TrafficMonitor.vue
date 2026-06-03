<template>
  <div class="traffic-monitor">
    <h2>实时流量监控</h2>

    <el-card class="chart-card">
      <v-chart :option="chartOption" autoresize style="height: 400px" />
    </el-card>

    <el-card class="table-card">
      <el-table :data="tableData" border stripe max-height="350">
        <el-table-column prop="proto" label="协议" width="80" />
        <el-table-column prop="srcIp" label="源IP" width="160" />
        <el-table-column prop="dstIp" label="目标IP" width="160" />
        <el-table-column prop="srcPort" label="源端口" width="90" />
        <el-table-column prop="dstPort" label="目标端口" width="90" />
        <el-table-column prop="rxBytes" label="接收字节" width="110" sortable />
        <el-table-column prop="txBytes" label="发送字节" width="110" sortable />
        <el-table-column prop="avg2s" label="avg2s" width="90" sortable />
        <el-table-column prop="avg10s" label="avg10s" width="90" sortable />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import api from '@/api'

use([CanvasRenderer, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

const INTERVAL_MS = 1500
const MAX_POINTS = 40   // 1 分钟
const MAX_LINES = 6
const IDLE_KEEP = 3

const trafficData = ref([])
const xData = ref([])
const flowHistory = new Map()

const chartOption = ref({
  title: { text: '活跃流实时速率 (avg2s byte/s)' },
  tooltip: { trigger: 'axis' },
  legend: { type: 'scroll', bottom: 0 },
  xAxis: { type: 'category', data: [] },
  yAxis: { type: 'value' },
  series: [],
})

const tableData = computed(() => {
  const items = [...trafficData.value]
  items.sort((a, b) => {
    const aActive = (a.avg2s ?? 0) + (a.avg10s ?? 0)
    const bActive = (b.avg2s ?? 0) + (b.avg10s ?? 0)
    if (aActive > 0 && bActive === 0) return -1
    if (bActive > 0 && aActive === 0) return 1
    return (b.rxBytes ?? 0) - (a.rxBytes ?? 0)
  })
  return items
})

let timer = null

function flowKey(item) {
  return `${item.srcIp}:${item.srcPort}→${item.dstIp}:${item.dstPort} ${item.proto}`
}

function buildChartOption() {
  const entries = []
  for (const [key, h] of flowHistory) {
    if (h.data.length > 0) {
      entries.push({ key, latest: h.data[h.data.length - 1], data: h.data })
    }
  }
  entries.sort((a, b) => b.latest - a.latest)
  const top = entries.slice(0, MAX_LINES)

  const keep = new Set(top.map(e => e.key))
  for (const key of flowHistory.keys()) {
    if (!keep.has(key)) flowHistory.delete(key)
  }

  const series = top.map(e => {
    const pad = xData.value.length - e.data.length
    const padded = pad > 0
      ? [...new Array(pad).fill(0), ...e.data]
      : e.data.slice(-xData.value.length)
    return {
      name: e.key,
      type: 'line',
      data: padded,
      smooth: true,
      showSymbol: false,
    }
  })

  chartOption.value = {
    title: { text: '活跃流实时速率 (avg2s byte/s)' },
    tooltip: { trigger: 'axis' },
    legend: { type: 'scroll', bottom: 0 },
    xAxis: { type: 'category', data: xData.value },
    yAxis: { type: 'value' },
    series,
  }
}

async function pollTraffic() {
  try {
    const { data } = await api.get('/traffic')
    trafficData.value = data.items ?? []

    xData.value.push(new Date().toLocaleTimeString())
    if (xData.value.length > MAX_POINTS) xData.value.shift()

    const seen = new Set()
    for (const item of trafficData.value) {
      const key = flowKey(item)
      seen.add(key)
      const val = item.avg2s ?? 0
      let h = flowHistory.get(key)
      if (!h) {
        h = { data: [], idle: 0 }
        flowHistory.set(key, h)
      }
      h.data.push(val)
      if (h.data.length > MAX_POINTS) h.data.shift()
      h.idle = val > 0 ? 0 : h.idle + 1
    }

    for (const [key, h] of flowHistory) {
      if (!seen.has(key) || h.idle >= IDLE_KEEP) {
        flowHistory.delete(key)
      }
    }

    buildChartOption()
  } catch {
    // 错误已由拦截器统一提示
  }
}

onMounted(() => {
  pollTraffic()
  timer = setInterval(pollTraffic, INTERVAL_MS)
})

onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.traffic-monitor {
  padding: 20px;
}

.chart-card, .table-card {
  margin-bottom: 20px;
}

.chart-toolbar {
  margin-bottom: 8px;
}
.chart-toolbar .label {
  margin-right: 8px;
  font-size: 13px;
  color: #606266;
}
</style>
