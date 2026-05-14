<template>
  <div class="firewall-config">
    <h2>防火墙规则配置</h2>

    <el-card class="form-card">
      <el-form :model="ruleForm" label-width="100px">
        <el-form-item label="协议">
          <el-select v-model="ruleForm.protocol" placeholder="选择协议">
            <el-option label="TCP" value="tcp" />
            <el-option label="UDP" value="udp" />
            <el-option label="ICMP" value="icmp" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="源IP">
          <el-input v-model="ruleForm.src_ip" placeholder="例如: 192.168.1.100" />
        </el-form-item>
        
        <el-form-item label="目标IP">
          <el-input v-model="ruleForm.dst_ip" placeholder="例如: 10.0.0.1" />
        </el-form-item>
        
        <el-form-item label="源端口">
          <el-input v-model="ruleForm.src_port" placeholder="可选" />
        </el-form-item>
        
        <el-form-item label="目标端口">
          <el-input v-model="ruleForm.dst_port" placeholder="例如: 80" />
        </el-form-item>
        
        <el-form-item label="动作">
          <el-radio-group v-model="ruleForm.action">
            <el-radio label="accept">允许</el-radio>
            <el-radio label="drop">拒绝</el-radio>
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
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="protocol" label="协议" width="100" />
        <el-table-column prop="src_ip" label="源IP" width="150" />
        <el-table-column prop="dst_ip" label="目标IP" width="150" />
        <el-table-column prop="src_port" label="源端口" width="100" />
        <el-table-column prop="dst_port" label="目标端口" width="100" />
        <el-table-column prop="action" label="动作" width="100" />
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button size="small" type="danger" @click="deleteRule(scope.row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const ruleForm = ref({
  protocol: '',
  src_ip: '',
  dst_ip: '',
  src_port: '',
  dst_port: '',
  action: 'accept',
})

const rules = ref([])

const addRule = () => {
  console.log('添加规则:', ruleForm.value)
}

const deleteRule = (id) => {
  console.log('删除规则:', id)
}

const clearRules = () => {
  console.log('清空所有规则')
}
</script>

<style scoped>
.firewall-config {
  padding: 20px;
}

.form-card, .rules-card {
  margin-bottom: 20px;
}
</style>