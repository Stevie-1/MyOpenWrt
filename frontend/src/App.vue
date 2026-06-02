<template>
  <div id="app">
    <el-container>
      <el-header>
        <h1>OpenWrt 网络管理工具</h1>
      </el-header>
      <el-main>
        <el-tabs
          v-model="activeTab"
          class="main-tabs"
          @tab-change="onTabChange"
        >
          <el-tab-pane label="流量监控" name="traffic" />
          <el-tab-pane label="防火墙规则" name="firewall" />
        </el-tabs>
        <TrafficMonitor v-show="activeTab === 'traffic'" />
        <FirewallConfig v-show="activeTab === 'firewall'" />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TrafficMonitor from './views/TrafficMonitor.vue'
import FirewallConfig from './views/FirewallConfig.vue'

const route = useRoute()
const router = useRouter()

const activeTab = ref(route.path === '/firewall' ? 'firewall' : 'traffic')

function onTabChange(name) {
  router.push(name === 'firewall' ? '/firewall' : '/traffic')
}

watch(() => route.path, (path) => {
  activeTab.value = path === '/firewall' ? 'firewall' : 'traffic'
})
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
}

.el-header {
  background-color: #409eff;
  color: white;
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.el-header h1 {
  margin: 0;
  font-size: 24px;
}

.main-tabs {
  margin-bottom: 20px;
}
</style>
