<template>
  <div class="firewall-config">
    <h2>防火墙规则配置</h2>

    <el-card class="form-card">
      <el-form :model="ruleForm" label-width="100px">
        <el-form-item label="协议">
          <el-select v-model="ruleForm.proto" placeholder="选择协议">
            <el-option label="TCP" value="tcp" />
            <el-option label="UDP" value="udp" />
            <el-option label="ICMP" value="icmp" />
          </el-select>
        </el-form-item>

        <el-form-item label="源地址">
          <el-input v-model="ruleForm.src" placeholder="IPv4 / CIDR / any" />
        </el-form-item>

        <el-form-item label="目的地址">
          <el-input v-model="ruleForm.dst" placeholder="IPv4 / CIDR / any" />
        </el-form-item>

        <el-form-item label="端口">
          <el-input v-model="ruleForm.port" placeholder="1-65535（icmp 时忽略）" />
        </el-form-item>

        <el-form-item label="动作">
          <el-radio-group v-model="ruleForm.action">
            <el-radio label="accept">允许</el-radio>
            <el-radio label="reject">拒绝(reject)</el-radio>
            <el-radio label="drop">丢弃(drop)</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="addRule">添加规则</el-button>
          <el-button @click="clearRules">清空所有规则</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="rules-card">
      <h3>当前规则列表</h3>
      <el-table :data="rules" border stripe>
        <el-table-column prop="id" label="ID" width="100" />
        <el-table-column prop="proto" label="协议" width="80" />
        <el-table-column prop="src" label="源地址" width="180" />
        <el-table-column prop="dst" label="目的地址" width="180" />
        <el-table-column prop="port" label="端口" width="80" />
        <el-table-column prop="action" label="动作" width="120" />
        <el-table-column label="操作" width="100">
          <template #default="scope">
            <el-button size="small" type="danger" @click="deleteRule(scope.row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api'

const ruleForm = ref({
  proto: '',
  src: '',
  dst: '',
  port: '',
  action: 'accept',
})

const rules = ref([])

async function loadRules() {
  try {
    const { data } = await api.get('/firewall/rules')
    rules.value = data.rules ?? []
  } catch { /* 拦截器已提示 */ }
}

async function addRule() {
  try {
    await api.post('/firewall/rules', {
      proto: ruleForm.value.proto,
      src: ruleForm.value.src,
      dst: ruleForm.value.dst,
      port: Number(ruleForm.value.port),
      action: ruleForm.value.action,
    })
    await loadRules()
  } catch { /* 拦截器已提示 */ }
}

async function deleteRule(id) {
  try {
    await api.delete(`/firewall/rules/${id}`)
    await loadRules()
  } catch { /* 拦截器已提示 */ }
}

async function clearRules() {
  try {
    await api.post('/firewall/clear')
    await loadRules()
  } catch { /* 拦截器已提示 */ }
}

onMounted(() => loadRules())
</script>

<style scoped>
.firewall-config {
  padding: 20px;
}

.form-card, .rules-card {
  margin-bottom: 20px;
}
</style>
