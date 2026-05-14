<template>
  <div class="traffic-monitor">
    <h2>实时流量监控</h2>
    
    <el-card class="chart-card">
      <v-chart :option="chartOption" autoresize style="height: 400px" />
    </el-card>

    <el-card class="table-card">
      <el-table :data="trafficData" border stripe>
        <el-table-column prop="protocol" label="协议" width="100" />
        <el-table-column prop="src_ip" label="源IP" width="150" />
        <el-table-column prop="dst_ip" label="目标IP" width="150" />
        <el-table-column prop="src_port" label="源端口" width="100" />
        <el-table-column prop="dst_port" label="目标端口" width="100" />
        <el-table-column prop="bytes" label="流量(字节)" width="120" />
        <el-table-column prop="packets" label="数据包数" width="120" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'

use([CanvasRenderer, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

const trafficData = ref([])
const chartOption = ref({
  title: { text: '网络流量趋势' },
  tooltip: { trigger: 'axis' },
  legend: { data: ['上行流量', '下行流量'] },
  xAxis: { type: 'category', data: [] },
  yAxis: { type: 'value' },
  series: [
    { name: '上行流量', type: 'line', data: [] },
    { name: '下行流量', type: 'line', data: [] },
  ],
})
</script>

<style scoped>
.traffic-monitor {
  padding: 20px;
}

.chart-card, .table-card {
  margin-bottom: 20px;
}
</style>