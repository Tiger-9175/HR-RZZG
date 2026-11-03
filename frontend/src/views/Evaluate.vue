<template>
  <div class="evaluate-page">
    <!-- LLM Status Bar -->
    <div class="llm-status-bar">
      <el-space>
        <el-tag :type="systemLlmConfigured ? 'success' : 'warning'" size="small" effect="light">
          <el-icon style="margin-right: 4px;"><Connection /></el-icon>
          {{ systemLlmConfigured ? `大模型已就绪 (${llmModel})` : '大模型未配置' }}
        </el-tag>
        <span v-if="!systemLlmConfigured" style="font-size:13px; color:#9ca3af;">
          请前往
          <router-link to="/settings">系统设置</router-link>
          配置大模型连接
        </span>
      </el-space>
    </div>

    <!-- Step 1: Upload Files -->
    <el-card class="step-card" shadow="never" style="margin-top: 16px;">
      <template #header>
        <div class="step-header">
          <el-tag type="primary" round>步骤 1</el-tag>
          <span class="step-title">上传评价材料</span>
        </div>
      </template>

      <el-row :gutter="20">
        <el-col :span="12">
          <div class="upload-area">
            <div class="upload-label">
              <el-icon><Document /></el-icon>
              答辩PPT（候选人材料）
            </div>
            <el-upload
              ref="pptUpload"
              drag
              :action="uploadUrl"
              :auto-upload="false"
              :on-change="handlePptChange"
              accept=".pptx,.ppt"
              :show-file-list="false"
              class="upload-box"
            >
              <el-icon class="upload-icon" :size="40"><UploadFilled /></el-icon>
              <div class="upload-text">
                <span v-if="!pptFile">将 PPT 文件拖到此处，或 <em>点击选择</em></span>
                <span v-else class="upload-success">
                  <el-icon color="#34a853"><CircleCheck /></el-icon>
                  {{ pptFile.name }}
                </span>
              </div>
              <template #tip>
                <div class="upload-tip">支持 .pptx / .ppt 格式</div>
              </template>
            </el-upload>
          </div>
        </el-col>

        <el-col :span="12">
          <div class="upload-area">
            <div class="upload-label">
              <el-icon><Reading /></el-icon>
              任职资格标准（Excel）
            </div>
            <el-upload
              ref="standardUpload"
              drag
              :action="uploadUrl"
              :auto-upload="false"
              :on-change="handleStandardChange"
              accept=".xlsx,.xls"
              :show-file-list="false"
              class="upload-box"
            >
              <el-icon class="upload-icon" :size="40"><UploadFilled /></el-icon>
              <div class="upload-text">
                <span v-if="!standardFile">将 Excel 文件拖到此处，或 <em>点击选择</em></span>
                <span v-else class="upload-success">
                  <el-icon color="#34a853"><CircleCheck /></el-icon>
                  {{ standardFile.name }}
                </span>
              </div>
              <template #tip>
                <div class="upload-tip">支持 .xlsx / .xls 格式</div>
              </template>
            </el-upload>
          </div>
        </el-col>
      </el-row>

      <!-- Preview -->
      <el-row :gutter="20" style="margin-top: 16px;">
        <el-col :span="12">
          <div v-if="candidateInfo" class="candidate-preview">
            <h4><el-icon><User /></el-icon> 候选人信息</h4>
            <el-descriptions :column="2" size="small" border>
              <el-descriptions-item label="姓名">{{ candidateInfo.name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="部门">{{ candidateInfo.department || '-' }}</el-descriptions-item>
              <el-descriptions-item label="申请等级">{{ candidateInfo.applied_level || '-' }}</el-descriptions-item>
              <el-descriptions-item label="近两年绩效">{{ candidateInfo.performance_last_two_years || '-' }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-col>
        <el-col :span="12">
          <div v-if="standardLoaded" class="standard-preview">
            <h4><el-icon><Reading /></el-icon> 标准已加载</h4>
            <el-progress :percentage="100" status="success" :stroke-width="6" />
            <el-text type="success">任职资格标准文件已解析完成</el-text>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- Step 3: Start Evaluation -->
    <el-card class="step-card" shadow="never" style="margin-top: 16px;">
      <template #header>
        <div class="step-header">
          <el-tag type="primary" round>步骤 2</el-tag>
          <span class="step-title">执行评价</span>
        </div>
      </template>

      <!-- Manual score: 责任贡献 -->
      <div class="manual-score-area">
        <div class="manual-score-header">
          <el-icon color="#f97316"><StarFilled /></el-icon>
          <span>责任贡献/责任结果 — 手动评分（0-30分）</span>
          <el-tag type="warning" size="small">不参与AI评价</el-tag>
        </div>
        <div class="manual-score-input">
          <el-slider
            v-model="responsibilityScore"
            :min="0"
            :max="30"
            :step="0.5"
            :marks="{ 0: '0', 10: '10', 18: '达标18', 20: '20', 30: '30' }"
            show-input
            :disabled="evaluating"
            style="max-width: 520px;"
          />
        </div>
      </div>

      <div class="eval-actions">
        <el-button
          type="primary"
          size="large"
          :disabled="!canEvaluate"
          :loading="evaluating"
          @click="startEvaluation"
        >
          <el-icon><Cpu /></el-icon>
          {{ evaluating ? '评价进行中...' : '开始智能评价' }}
        </el-button>

        <el-button
          size="large"
          @click="$router.push('/demo')"
          :disabled="evaluating"
        >
          <el-icon><FolderOpened /></el-icon>
          使用示例数据
        </el-button>
      </div>

      <!-- Progress Timeline -->
      <div v-if="evaluating" class="eval-progress">
        <el-steps :active="activeStep" direction="vertical" process-status="process" finish-status="success">
          <el-step
            v-for="s in steps"
            :key="s.id"
            :title="s.title"
            :description="s.desc"
            :status="s.status"
          />
        </el-steps>
        <div v-if="thresholdItems.length" class="threshold-preview">
          <el-divider>基本条件核查结果</el-divider>
          <div v-for="item in thresholdItems" :key="item.field" class="threshold-row">
            <el-tag :type="item.status === '✅' ? 'success' : item.status === '⚠️' ? 'warning' : 'danger'" size="small">
              {{ item.status }}
            </el-tag>
            <span class="threshold-label">{{ item.label }}：{{ item.required }}</span>
            <span class="threshold-detail">{{ item.detail }}</span>
          </div>
        </div>
        <el-progress
          :percentage="progress"
          :stroke-width="8"
          :status="progress >= 100 ? 'success' : undefined"
          striped
          striped-flow
          :duration="6"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()

// System LLM status (from backend /api/health)
const systemLlmConfigured = ref(false)
const llmModel = ref('')

async function fetchLlmStatus() {
  try {
    const res = await axios.get('/api/health')
    systemLlmConfigured.value = res.data.llm_configured
    llmModel.value = res.data.llm_model || ''
  } catch (e) {
    systemLlmConfigured.value = false
  }
}

onMounted(() => {
  fetchLlmStatus()
  restoreSessionData()
})

// Restore pre-loaded data from Demo page (stored in sessionStorage)
function restoreSessionData() {
  const ppt = sessionStorage.getItem('pptContent')
  const std = sessionStorage.getItem('standardContent')
  const info = sessionStorage.getItem('candidateInfo')

  if (ppt) {
    pptContent.value = ppt
    // Set a dummy file entry so the upload area shows it as loaded
    pptFile.value = { name: '示例PPT（已加载）' }
    try {
      candidateInfo.value = JSON.parse(info || '{}')
    } catch { /* ignore */ }
  }
  if (std) {
    standardContent.value = std
    standardFile.value = { name: '示例标准（已加载）' }
    standardLoaded.value = true
  }
}

// Files
const pptFile = ref(null)
const standardFile = ref(null)
const pptContent = ref('')
const standardContent = ref('')
const candidateInfo = ref(null)
const standardLoaded = ref(false)

// Evaluation state
const evaluating = ref(false)
const progress = ref(0)
const activeStep = ref(0)
const responsibilityScore = ref(0)
const thresholdItems = ref([])

const steps = ref([
  { id: 1, title: '匹配专业标准', desc: '根据候选人专业匹配对应的任职资格标准', status: 'wait' },
  { id: 2, title: '基本条件核查', desc: '核查绩效、职业资格、工作年限等门槛条件', status: 'wait' },
  { id: 3, title: '构建评价提示词', desc: '组织评价维度和评分细则', status: 'wait' },
  { id: 4, title: '大模型思维链推理', desc: '调用大模型进行多维度深度评估打分', status: 'wait' },
  { id: 5, title: '解析评价结果', desc: '解析模型输出，计算总分与判定', status: 'wait' },
  { id: 6, title: '评价完成', desc: '生成评价报告', status: 'wait' },
])

const uploadUrl = '/api/upload'

const canEvaluate = computed(() => {
  return (
    (pptContent.value || standardContent.value) &&
    systemLlmConfigured.value
  )
})

async function handlePptChange(file) {
  pptFile.value = file.raw
  const formData = new FormData()
  formData.append('file', file.raw)

  try {
    const res = await axios.post('/api/upload', formData)
    pptContent.value = res.data.content
    candidateInfo.value = res.data.candidate
    ElMessage.success('PPT解析成功')
  } catch (e) {
    ElMessage.error('PPT解析失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function handleStandardChange(file) {
  standardFile.value = file.raw
  const formData = new FormData()
  formData.append('file', file.raw)

  try {
    const res = await axios.post('/api/upload', formData)
    standardContent.value = res.data.content
    standardLoaded.value = true
    ElMessage.success('任职资格标准解析成功')
  } catch (e) {
    ElMessage.error('标准解析失败: ' + (e.response?.data?.detail || e.message))
  }
}

function updateStep(id, status, desc) {
  const s = steps.value.find(s => s.id === id)
  if (s) { s.status = status; if (desc) s.desc = desc }
  if (status === 'finish' || status === 'process') activeStep.value = id
}

function stepProgress(id) {
  const map = { 1: 5, 2: 18, 3: 30, 4: 40, 5: 85, 6: 100 }
  progress.value = map[id] || 0
}

async function startEvaluation() {
  if (!systemLlmConfigured.value) {
    ElMessage.warning('请先前往系统设置配置大模型连接')
    return
  }

  evaluating.value = true
  progress.value = 0
  thresholdItems.value = []
  activeStep.value = 0
  steps.value.forEach(s => { s.status = 'wait'; s.desc = s.id <= 1 ? s.desc : s.desc.split ? s.desc : '' })

  const level = candidateInfo.value?.applied_level || '三级'
  const position = candidateInfo.value?.position || ''
  const ppt = pptContent.value || ''

  try {
    // Step 1: Match standard
    updateStep(1, 'process', '根据候选人专业匹配对应的任职资格标准')
    stepProgress(1)

    // Step 2: Precheck basic conditions
    updateStep(1, 'finish')
    updateStep(2, 'process', '正在核查绩效、职业资格、工作年限等门槛条件')
    stepProgress(2)

    let precheckRes = null
    try {
      const params = new URLSearchParams()
      params.append('ppt_content', ppt)
      params.append('candidate_level', level)
      params.append('candidate_position', position)
      if (pptFile.value) params.append('ppt_filename', pptFile.value.name || '')
      precheckRes = await axios.post('/api/evaluate/precheck', params, { timeout: 60000 })
    } catch (e) {
      // Precheck failed, continue anyway
      updateStep(2, 'error', '基本条件核查暂时跳过')
    }

    if (precheckRes?.data?.items?.length) {
      updateStep(2, 'finish', '基本条件核查完成')
      thresholdItems.value = precheckRes.data.items
    } else if (precheckRes?.data?.has_conditions === false) {
      updateStep(2, 'finish', '该专业未定义基本条件，跳过核查')
    } else {
      updateStep(2, 'finish', '基本条件核查完成')
    }

    // Step 3: Build prompt
    updateStep(3, 'process', '正在构建评价提示词，组织维度权重与评分标准…')
    stepProgress(3)
    await sleep(300)

    // Step 4: LLM reasoning
    const formData = new FormData()
    formData.append('ppt_content', ppt)
    formData.append('qualification_standard', standardContent.value || '')
    formData.append('candidate_level', level)
    formData.append('candidate_position', position)
    formData.append('responsibility_score', String(responsibilityScore.value))
  if (pptFile.value) formData.append('ppt_filename', pptFile.value.name || '')

    updateStep(3, 'finish')
    updateStep(4, 'process', '大模型正在逐维度进行思维链推理与打分…')
    stepProgress(4)

    const res = await axios.post('/api/evaluate', formData, { timeout: 300000 })

    // Step 5: Parse result
    updateStep(4, 'finish')
    updateStep(5, 'process', '正在解析大模型评价结果，计算总分…')
    stepProgress(5)
    await sleep(300)

    // Step 6: Done
    updateStep(5, 'finish')
    updateStep(6, 'process', '评价完成，正在跳转到结果页…')
    stepProgress(6)

    sessionStorage.setItem('evalResult', JSON.stringify(res.data))
    sessionStorage.setItem('pptContent', ppt)
    sessionStorage.setItem('standardContent', standardContent.value || '')

    await sleep(800)
    updateStep(6, 'finish', '评价报告已生成')
    stepProgress(6)

    setTimeout(() => {
      evaluating.value = false
      // Navigate with the record id so the result page can be refreshed
      router.push(res.data?.record_id ? `/result/${res.data.record_id}` : '/result')
    }, 600)
  } catch (e) {
    evaluating.value = false
    progress.value = 0
    ElMessage.error('评价失败: ' + (e.response?.data?.detail || e.message))
  }
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}
</script>

<style scoped>
.evaluate-page {
  max-width: 1100px;
  margin: 0 auto;
}

.llm-status-bar {
  margin-bottom: 16px;
  padding: 10px 16px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.step-card {
  border-radius: 12px;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.step-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.help-icon {
  color: #9ca3af;
  cursor: help;
}

.upload-area {
  min-height: 200px;
}

.upload-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #374151;
}

.upload-box {
  width: 100%;
}

.upload-icon {
  margin-bottom: 8px;
}

.upload-text {
  font-size: 14px;
  color: #6b7280;
}

.upload-text em {
  color: #1a73e8;
  font-style: normal;
}

.upload-success {
  color: #34a853;
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
}

.upload-tip {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
}

.candidate-preview,
.standard-preview {
  background: #f9fafb;
  border-radius: 8px;
  padding: 16px;
}

.candidate-preview h4,
.standard-preview h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  color: #374151;
}

.eval-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.manual-score-area {
  background: #fffbeb;
  border: 1px solid #fcd34d;
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 16px;
}

.manual-score-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
  color: #92400e;
  margin-bottom: 12px;
}

.manual-score-input {
  padding: 0 8px;
}

.eval-progress {
  margin-top: 20px;
}

.threshold-preview {
  margin: 12px 0;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.threshold-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 13px;
}

.threshold-label {
  font-weight: 500;
  color: #374151;
  min-width: 120px;
}

.threshold-detail {
  color: #6b7280;
  flex: 1;
}

.progress-text {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  color: #6b7280;
  font-size: 14px;
}

.loading-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
