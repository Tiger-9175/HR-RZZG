<template>
  <div class="batch-page">
    <!-- Upload -->
    <el-card shadow="never" class="card">
      <template #header>
        <span class="card-title"><el-icon><UploadFilled /></el-icon> 批量评价</span>
      </template>

      <el-upload
        drag
        multiple
        :auto-upload="false"
        accept=".pptx"
        :file-list="fileList"
        :on-change="onFileChange"
        :on-remove="onFileRemove"
        class="uploader"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">把多个候选人 PPTX 拖到这里，或 <em>点击选择</em></div>
        <template #tip>
          <div class="el-upload__tip">
            仅支持 .pptx，单个文件 ≤ 50MB；任务会逐个串行评价，避免把大模型服务打满。
          </div>
        </template>
      </el-upload>

      <el-form inline class="batch-form">
        <el-form-item label="任务名称">
          <el-input v-model="form.name" placeholder="如：2026年冶金专业三级认证" style="width: 260px" />
        </el-form-item>
        <el-form-item label="申报等级">
          <el-select v-model="form.candidate_level" style="width: 120px">
            <el-option v-for="l in levels" :key="l" :label="l" :value="l" />
          </el-select>
        </el-form-item>
        <el-form-item label="责任贡献分">
          <el-input-number v-model="form.responsibility_score" :min="0" :max="30" :step="1" />
          <span class="hint">人工评分项，统一套用到本批全部候选人</span>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="creating"
            :disabled="!fileList.length || running"
            @click="startBatch"
          >
            开始批量评价（{{ fileList.length }} 人）
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Current job -->
    <el-card v-if="current" shadow="never" class="card">
      <template #header>
        <div class="card-header">
          <span class="card-title"><el-icon><Loading /></el-icon> {{ current.name || '当前任务' }}</span>
          <div class="header-actions">
            <el-tag :type="statusType(current.status)" size="small">{{ statusText(current.status) }}</el-tag>
            <el-button
              size="small"
              type="primary"
              plain
              :disabled="!current.finished"
              :loading="zipping"
              @click="downloadZip(current)"
            >
              下载全部报告(ZIP)
            </el-button>
            <el-button size="small" :disabled="current.status !== 'running'" @click="cancelJob">取消</el-button>
            <el-button size="small" @click="() => loadBatch(current.id)">刷新</el-button>
          </div>
        </div>
      </template>

      <el-progress
        :percentage="current.progress || 0"
        :status="current.status === 'finished' ? 'success' : undefined"
        :stroke-width="10"
        striped
        :striped-flow="current.status === 'running'"
      />
      <div class="progress-text">
        已完成 {{ current.finished }} / {{ current.total }}，失败 {{ current.failed }}
      </div>

      <el-table :data="current.items" size="small" style="margin-top: 12px">
        <el-table-column prop="filename" label="文件" show-overflow-tooltip />
        <el-table-column prop="candidate_name" label="候选人" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="综合得分" width="150">
          <template #default="{ row }">
            <span v-if="row.total_score !== null && row.total_score !== undefined">
              {{ row.total_score?.toFixed(1) }} / {{ row.total_percentage?.toFixed(0) }}%
            </span>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="结论" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.passed === true" type="success" size="small">通过</el-tag>
            <el-tag v-else-if="row.passed === false" type="danger" size="small">未通过</el-tag>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="说明" show-overflow-tooltip />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :disabled="!row.record_id" @click="openRecord(row)">查看</el-button>
            <el-button link type="primary" :disabled="!row.record_id" @click="downloadReport(row)">PDF</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- History -->
    <el-card shadow="never" class="card">
      <template #header>
        <span class="card-title"><el-icon><Tickets /></el-icon> 批量任务历史</span>
      </template>
      <el-table :data="batches" size="small" v-loading="loadingBatches">
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ (row.created_at || '').replace('T', ' ') }}</template>
        </el-table-column>
        <el-table-column prop="name" label="任务名称" show-overflow-tooltip />
        <el-table-column prop="candidate_level" label="等级" width="80" />
        <el-table-column label="进度" width="140">
          <template #default="{ row }">
            {{ row.finished + row.failed }} / {{ row.total }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="190">
          <template #default="{ row }">
            <el-button link type="primary" @click="loadBatch(row.id)">查看</el-button>
            <el-button link type="primary" :disabled="!row.finished" @click="downloadZip(row)">报告ZIP</el-button>
            <el-button link type="danger" @click="removeBatch(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const levels = ['一级', '二级', '三级', '四级', '五级', '六级']

const fileList = ref([])
const form = ref({ name: '', candidate_level: '三级', responsibility_score: 0 })
const creating = ref(false)
const zipping = ref(false)
const current = ref(null)
const batches = ref([])
const loadingBatches = ref(false)
let timer = null

const running = computed(() => current.value?.status === 'running')

function statusText(status) {
  return {
    running: '进行中', finished: '已完成', cancelled: '已取消',
    pending: '排队中', success: '成功', failed: '失败',
  }[status] || status
}

function statusType(status) {
  return {
    running: 'warning', finished: 'success', cancelled: 'info',
    pending: 'info', success: 'success', failed: 'danger',
  }[status] || 'info'
}

function onFileChange(file, files) {
  fileList.value = files
}

function onFileRemove(file, files) {
  fileList.value = files
}

async function startBatch() {
  if (!fileList.value.length) return
  creating.value = true
  try {
    const data = new FormData()
    fileList.value.forEach(f => {
      if (f.raw) data.append('files', f.raw)
    })
    data.append('name', form.value.name || '')
    data.append('candidate_level', form.value.candidate_level)
    data.append('responsibility_score', String(form.value.responsibility_score))

    const res = await axios.post('/api/batches', data, { timeout: 180000 })
    ElMessage.success(`批量任务已创建，共 ${res.data.total} 人`)
    current.value = res.data
    fileList.value = []
    startPolling(res.data.id)
    loadBatches()
  } catch (e) {
    ElMessage.error('创建批量任务失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    creating.value = false
  }
}

function startPolling(batchId) {
  stopPolling()
  timer = setInterval(async () => {
    const batch = await loadBatch(batchId, true)
    if (!batch || batch.status !== 'running') {
      stopPolling()
      loadBatches()
      if (batch && batch.status === 'finished') {
        ElMessage.success(`批量评价完成：成功 ${batch.finished}，失败 ${batch.failed}`)
      }
    }
  }, 4000)
}

function stopPolling() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

async function loadBatch(batchId, silent = false) {
  try {
    const res = await axios.get(`/api/batches/${batchId}`)
    current.value = res.data
    return res.data
  } catch (e) {
    if (!silent) ElMessage.error('加载任务失败: ' + (e.response?.data?.detail || e.message))
    return null
  }
}

async function loadBatches() {
  loadingBatches.value = true
  try {
    const res = await axios.get('/api/batches')
    batches.value = res.data.items || []
  } catch {
    // non-blocking
  } finally {
    loadingBatches.value = false
  }
}

async function cancelJob() {
  try {
    await axios.post(`/api/batches/${current.value.id}/cancel`)
    ElMessage.info('已请求取消，当前候选人完成后停止')
    loadBatch(current.value.id)
  } catch (e) {
    ElMessage.error('取消失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function removeBatch(row) {
  try {
    await ElMessageBox.confirm(
      '删除批量任务？（不会删除已生成的评价记录）', '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await axios.delete(`/api/batches/${row.id}`)
    if (current.value?.id === row.id) current.value = null
    ElMessage.success('已删除')
    loadBatches()
  } catch (e) {
    ElMessage.error('删除失败: ' + (e.response?.data?.detail || e.message))
  }
}

function openRecord(row) {
  if (row.record_id) router.push(`/result/${row.record_id}`)
}

function saveBlob(res, fallbackName) {
  const disposition = res.headers['content-disposition'] || ''
  const match = /filename\*=UTF-8''([^;]+)/i.exec(disposition)
  const filename = match ? decodeURIComponent(match[1].trim()) : fallbackName
  const url = URL.createObjectURL(res.data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

async function downloadZip(batch) {
  if (!batch?.id) return
  zipping.value = true
  try {
    const res = await axios.get(`/api/batches/${batch.id}/reports.zip`, {
      responseType: 'blob',
      timeout: 300000,
    })
    saveBlob(res, `${batch.name || '批量评价'}_报告.zip`)
    ElMessage.success('报告压缩包已开始下载')
  } catch (e) {
    let msg = e.message
    if (e.response?.data instanceof Blob) {
      try {
        msg = JSON.parse(await e.response.data.text()).detail || msg
      } catch {
        // keep original
      }
    }
    ElMessage.error('打包下载失败: ' + msg)
  } finally {
    zipping.value = false
  }
}

async function downloadReport(row) {
  if (!row.record_id) return
  try {
    const res = await axios.get(`/api/evaluations/${row.record_id}/report`, {
      responseType: 'blob',
      timeout: 120000,
    })
    const disposition = res.headers['content-disposition'] || ''
    const match = /filename\*=UTF-8''([^;]+)/i.exec(disposition)
    const filename = match
      ? decodeURIComponent(match[1].trim())
      : `任职资格评价报告_${row.candidate_name || '候选人'}.pdf`
    const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (e) {
    ElMessage.error('报告下载失败: ' + (e.response?.data?.detail || e.message))
  }
}

onMounted(() => {
  loadBatches()
})

onBeforeUnmount(stopPolling)
</script>

<style scoped>
.batch-page {
  max-width: 1200px;
  margin: 0 auto;
}

.card {
  border-radius: 12px;
  margin-bottom: 16px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.uploader {
  margin-bottom: 16px;
}

.batch-form {
  margin-top: 8px;
}

.hint {
  margin-left: 8px;
  font-size: 12px;
  color: #9ca3af;
}

.progress-text {
  margin-top: 6px;
  font-size: 13px;
  color: #6b7280;
}

.muted {
  color: #9ca3af;
}
</style>
