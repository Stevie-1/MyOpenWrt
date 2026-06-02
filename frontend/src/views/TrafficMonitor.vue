<template>
  <div class="traffic-monitor">
    <h2>实时流量监控</h2>

    <el-card class="chart-card">
      <v-chart :option="chartOption" autoresize style="height: 400px" />
    </el-card>

    <el-card class="table-card">
      <el-table :data="trafficData" border stripe>
        <el-table-column prop="proto" label="协议" width="100" />
        <el-table-column prop="srcIp" label="源IP" width="180" />
        <el-table-column prop="dstIp" label="目标IP" width="180" />
        <el-table-column prop="srcPort" label="源端口" width="100" />
        <el-table-column prop="dstPort" label="目标端口" width="100" />
        <el-table-column prop="rxBytes" label="接收字节" width="120" />
        <el-table-column prop="txBytes" label="发送字节" width="120" />
        <el-table-column prop="avg2s" label="实时速率(byte/s)" width="150" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import api from '@/api'

use([CanvasRenderer, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

const trafficData = ref([])

const chartOption = ref({
  title: { text: '实时速率 (avg2s byte/s)' },
  tooltip: { trigger: 'axis' },
  legend: { data: ['速率'] },
  xAxis: { type: 'category', data: [] },
  yAxis: { type: 'value' },
  series: [
    { name: '速率', type: 'line', data: [], smooth: true },
  ],
})

let timer = null

async function pollTraffic() {
  try {
    const { data } = await api.get('/traffic')
    trafficData.value = data.items ?? []

    const now = new Date().toLocaleTimeString()
    const totalAvg = trafficData.value.reduce((sum, item) => sum + (item.avg2s ?? 0), 0)

    const xData = chartOption.value.xAxis.data
    const yData = chartOption.value.series[0].data
    xData.push(now)
    yData.push(totalAvg)
    if (xData.length > 30) { xData.shift(); yData.shift() }
  } catch {
    // 错误已由拦截器统一提示
  }
}

onMounted(() => {
  pollTraffic()
  timer = setInterval(pollTraffic, 1500)
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
</style>
