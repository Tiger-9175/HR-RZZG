<template>
  <div class="settings-page">
    <el-card shadow="never" class="settings-card">
      <template #header>
        <div class="card-header">
          <el-icon><Setting /></el-icon>
          <span>大模型配置</span>
        </div>
      </template>

      <el-form :model="form" label-width="140px" size="large">
        <el-form-item label="API 地址">
          <el-input v-model="form.base_url" placeholder="http://192.168.x.x:8000/v1">
            <template #prepend>Base URL</template>
          </el-input>
          <div class="form-tip">
            支持 OpenAI 兼容接口格式，如：http://localhost:8000/v1
          </div>
        </el-form-item>

        <el-form-item label="模型名称">
          <el-input v-model="form.model" placeholder="qwen2.5-72b-instruct">
            <template #prepend>Model</template>
          </el-input>
          <div class="form-tip">
            填写您内部部署的模型名称，如 qwen2.5-72b-instruct、deepseek-v3 等
          </div>
        </el-form-item>

        <el-form-item label="API Key">
          <el-input v-model="form.api_key" type="password" show-password placeholder="sk-...">
            <template #prepend>API Key</template>
          </el-input>
          <div class="form-tip">
            如果您的 LLM 服务不需要 API Key，可填写任意占位符
          </div>
        </el-form-item>

        <el-form-item label="其他参数">
          <el-row :gutter="16">
            <el-col :span="8">
              <el-input-number v-model="form.temperature" :min="0" :max="2" :step="0.1" />
              <div class="form-tip">温度 (Temperature)，默认 0.3</div>
            </el-col>
            <el-col :span="8">
              <el-input-number v-model="form.max_tokens" :min="1024" :max="32768" :step="1024" />
              <div class="form-tip">最大 Token 数，默认 8192</div>
            </el-col>
          </el-row>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="saveConfig" :loading="saving">
            <el-icon><Check /></el-icon>
            保存配置
          </el-button>
          <el-button @click="testConnection" :loading="testing">
            <el-icon><Connection /></el-icon>
            测试连接
          </el-button>
        </el-form-item>

        <el-form-item v-if="testResult">
          <el-alert
            :title="testResult.ok ? '连接成功' : '连接失败'"
            :type="testResult.ok ? 'success' : 'error'"
            :description="testResult.msg"
            show-icon
            :closable="false"
          />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- System Info -->
    <el-card shadow="never" class="settings-card" style="margin-top: 16px;">
      <template #header>
        <div class="card-header">
          <el-icon><InfoFilled /></el-icon>
          <span>系统信息</span>
        </div>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="系统名称">任职资格智能评价系统</el-descriptions-item>
        <el-descriptions-item label="版本号">v1.0.0</el-descriptions-item>
        <el-descriptions-item label="技术架构">FastAPI + Vue 3 + Element Plus</el-descriptions-item>
        <el-descriptions-item label="评价引擎">Chain-of-Thought + LLM</el-descriptions-item>
        <el-descriptions-item label="部署方式">Docker 容器化部署</el-descriptions-item>
        <el-descriptions-item label="支持格式">PPT/PPTX, XLSX/XLS</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const LOCAL_KEY = 'llm_settings_cache'

// Load cached values from localStorage to survive page refresh
function loadFromCache() {
  try {
    const cached = localStorage.getItem(LOCAL_KEY)
    if (cached) return JSON.parse(cached)
  } catch (e) { /* ignore */ }
  return {}
}

function saveToCache(data) {
  try {
    localStorage.setItem(LOCAL_KEY, JSON.stringify(data))
  } catch (e) { /* ignore */ }
}

const cache = loadFromCache()

const form = ref({
  base_url: cache.base_url || 'http://localhost:8000/v1',
  model: cache.model || 'qwen2.5-72b-instruct',
  api_key: cache.api_key || '',
  temperature: 0.3,
  max_tokens: 8192,
})

const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)

onMounted(async () => {
  try {
    const res = await axios.get('/api/config/llm')
    // Backend has the authoritative values (survives container restart)
    form.value.base_url = res.data.base_url || form.value.base_url
    form.value.model = res.data.model || form.value.model
    // If backend says key is already set, keep the locally cached one
    // (backend won't return the actual key for security)
    if (!res.data.has_api_key && !form.value.api_key) {
      // Neither backend nor local cache has a key — still fine, user can fill in
    }
  } catch (e) {
    // Use cached defaults
  }
})

// Auto-save form fields to localStorage on change
watch(form, (val) => {
  saveToCache({
    base_url: val.base_url,
    model: val.model,
    api_key: val.api_key,
  })
}, { deep: true })

async function saveConfig() {
  saving.value = true
  try {
    await axios.post('/api/config/llm', {
      api_key: form.value.api_key,
      base_url: form.value.base_url,
      model: form.value.model,
    })
    saveToCache({ base_url: form.value.base_url, model: form.value.model, api_key: form.value.api_key })
    ElMessage.success('配置保存成功')
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

async function testConnection() {
  testing.value = true
  testResult.value = null
  try {
    const res = await axios.post('/api/config/llm/test', {
      api_key: form.value.api_key,
      base_url: form.value.base_url,
      model: form.value.model,
    })
    testResult.value = {
      ok: res.data.ok === true,
      msg: res.data.message || (res.data.ok ? '连接成功' : '连接失败'),
    }
  } catch (e) {
    testResult.value = { ok: false, msg: '网络请求异常: ' + (e.message || '未知') }
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.settings-page {
  max-width: 800px;
  margin: 0 auto;
}

.settings-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 16px;
}

.form-tip {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
}
</style>
