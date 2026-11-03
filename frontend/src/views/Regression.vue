<template>
  <div class="regression-page">
    <el-card shadow="never" class="card">
      <template #header>
        <span class="card-title"><el-icon><Odometer /></el-icon> 一致性回归测试</span>
      </template>

      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="回归测试会真实调用大模型（每个用例 × 重复次数），不写入评价台账，仅用于检查评分稳定性。"
        class="tip"
      />

      <el-form label-width="100px" class="form">
        <el-form-item label="测试用例">
          <el-select
            v-model="form.cases"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="选择 demo 中的答辩材料"
            style="width: 100%"
          >
            <el-option v-for="f in demoFiles" :key="f" :label="f" :value="f" />
          </el-select>
          <div class="hint-row">
            <el-button link type="primary" @click="form.cases = demoFiles.slice(0, 3)">取前3个</el-button>
            <el-button link type="primary" @click="form.cases = []">清空</el-button>
            <span class="hint">已在演示数据中加载 {{ demoFiles.length }} 份答辩 PPT</span>
          </div>
        </el-form-item>
        <el-form-item label="重复次数">
          <el-input-number v-model="form.repeats" :min="1" :max="5" />
          <span class="hint">同一材料重复评价次数，用于计算分数标准差（越大越耗时）</span>
        </el-form-item>
        <el-form-item label="责任贡献分">
          <el-input-number v-model="form.responsibility_score" :min="0" :max="30" />
          <span class="hint">统一套用到本批用例，便于横向比较</span>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :loading="starting"
            :disabled="!form.cases.length || job?.status === 'running'"
            @click="startRun"
          >
            开始回归测试（{{ form.cases.length }} 用例 × {{ form.repeats }} 次）
          </el-button>
          <el-button :disabled="!job || job.status === 'running'" @click="saveAsBaseline">保存为基线</el-button>
          <el-button :disabled="!baseline.cases || !Object.keys(baseline.cases).length" @click="clearBaseline">清除基线</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="job" shadow="never" class="card">
      <template #header>
        <div class="card-header">
          <span class="card-title"><el-icon><DataLine /></el-icon> 运行结果</span>
          <div class="header-actions">
            <el-tag :type="job.status === 'finished' ? 'success' : job.status === 'failed' ? 'danger' : 'warning'" size="small">
              {{ job.status === 'finished' ? '已完成' : job.status === 'failed' ? '失败' : '进行中' }}
            </el-tag>
            <span class="meta">模型 {{ job.model }} · 提示词指纹 {{ job.prompt_hash }}</span>
          </div>
        </div>
      </template>

      <el-progress :percentage="job.progress || 0" :stroke-width="8" :status="job.status === 'finished' ? 'success' : undefined" />
      <div class="progress-text">
        已完成 {{ job.finished }} / {{ job.total }}　<span v-if="job.error" class="error">{{ job.error }}</span>
      </div>

      <el-table :data="job.results" size="small" style="margin-top: 12px">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div v-if="row.stats?.dimensions" class="dim-wrap">
              <el-table :data="dimRows(row)" size="small" border>
                <el-table-column prop="name" label="维度" min-width="160" />
                <el-table-column prop="mean" label="均值" width="90" />
                <el-table-column prop="std" label="标准差" width="90" />
                <el-table-column prop="base" label="基线均值" width="100" />
                <el-table-column width="100" label="偏差">
                  <template #default="{ row: dim }">
                    <span :class="deltaClass(dim.delta, 0.5)">{{ formatDelta(dim.delta) }}</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <div v-else class="dim-wrap muted">{{ row.error || '暂无维度数据' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="filename" label="测试用例" min-width="260" show-overflow-tooltip />
        <el-table-column prop="candidate" label="候选人" width="90" />
        <el-table-column prop="level" label="等级" width="70" />
        <el-table-column label="平均得分率" width="110">
          <template #default="{ row }">
            <span v-if="row.stats?.mean_percentage !== undefined" class="score">{{ row.stats.mean_percentage }}%</span>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="标准差" width="90">
          <template #default="{ row }">
            <span v-if="row.stats?.std_percentage !== undefined" :class="deltaClass(row.stats.std_percentage, 2)">
              {{ row.stats.std_percentage }}
            </span>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="极差" width="90">
          <template #default="{ row }">
            <span v-if="row.stats?.min_percentage !== undefined">
              {{ (row.stats.max_percentage - row.stats.min_percentage).toFixed(1) }}
            </span>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="通过率" width="90">
          <template #default="{ row }">{{ row.stats?.pass_rate ?? '-' }}%</template>
        </el-table-column>
        <el-table-column label="与基线偏差" width="110">
          <template #default="{ row }">
            <span v-if="row.delta !== null && row.delta !== undefined" :class="deltaClass(row.delta, 2)">
              {{ formatDelta(row.delta) }}
            </span>
            <span v-else class="muted">无基线</span>
          </template>
        </el-table-column>
        <el-table-column prop="error" label="异常" min-width="160" show-overflow-tooltip />
      </el-table>
    </el-card>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="never" class="card">
          <template #header><span class="card-title">当前基线</span></template>
          <el-descriptions :column="1" size="small" border>
            <el-descriptions-item label="生成时间">{{ baseline.created_at || '未设置' }}</el-descriptions-item>
            <el-descriptions-item label="模型">{{ baseline.model || '-' }}</el-descriptions-item>
            <el-descriptions-item label="提示词指纹">
              {{ baseline.prompt_hash || '-' }}
              <el-tag v-if="baselineStale" type="warning" size="small" effect="plain" style="margin-left: 6px">
                提示词已变更
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="用例数">{{ Object.keys(baseline.cases || {}).length }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="card">
          <template #header><span class="card-title">历史任务（本次会话）</span></template>
          <el-empty v-if="!jobs.length" description="暂无任务" :image-size="60" />
          <el-table v-else :data="jobs" size="small">
            <el-table-column prop="created_at" label="时间" width="150">
              <template #default="{ row }">{{ (row.created_at || '').replace('T', ' ') }}</template>
            </el-table-column>
            <el-table-column prop="total" label="用例" width="70" />
            <el-table-column prop="repeats" label="次数" width="70" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === 'finished' ? 'success' : 'warning'">
                  {{ row.status === 'finished' ? '完成' : '进行中' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button link type="primary" @click="loadJob(row.id)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const demoFiles = ref([])
const form = ref({ cases: [], repeats: 1, responsibility_score: 0 })
const starting = ref(false)
const job = ref(null)
const jobs = ref([])
const baseline = ref({ cases: {} })
const currentHash = ref('')
let timer = null

const baselineStale = computed(() => {
  const base = baseline.value
  return Boolean(base?.prompt_hash && currentHash.value && base.prompt_hash !== currentHash.value)
})

function deltaClass(value, threshold = 2) {
  if (value === null || value === undefined) return 'muted'
  const abs = Math.abs(value)
  if (abs >= threshold * 2) return 'delta-bad'
  if (abs >= threshold) return 'delta-warn'
  return 'delta-ok'
}

function formatDelta(value) {
  if (value === null || value === undefined) return '-'
  return (value > 0 ? '+' : '') + Number(value).toFixed(1)
}

function dimRows(row) {
  const stats = row.stats?.dimensions || {}
  const baseDims = row.baseline?.dimensions || {}
  return Object.keys(stats).map(name => ({
    name,
    mean: stats[name].mean,
    std: stats[name].std,
    base: baseDims[name]?.mean ?? '-',
    delta: baseDims[name] ? Number((stats[name].mean - baseDims[name].mean).toFixed(1)) : null,
  }))
}

async function loadDemo() {
  try {
    const res = await axios.get('/api/demo/files')
    demoFiles.value = (res.data.files?.ppt || []).map(f => f.name)
    if (!form.value.cases.length && demoFiles.value.length) {
      form.value.cases = demoFiles.value.slice(0, 2)
    }
  } catch {
    // non-blocking
  }
}

async function loadBaseline() {
  try {
    const res = await axios.get('/api/regression/baseline')
    baseline.value = res.data || { cases: {} }
  } catch {
    baseline.value = { cases: {} }
  }
  try {
    const info = await axios.get('/api/prompts')
    currentHash.value = info.data?.prompt_hash || ''
  } catch {
    // ignore
  }
}

async function loadJobs() {
  try {
    const res = await axios.get('/api/regression/jobs')
    jobs.value = res.data.items || []
  } catch {
    // non-blocking
  }
}

async function startRun() {
  starting.value = true
  try {
    const res = await axios.post('/api/regression/run', form.value)
    job.value = res.data
    startPolling(res.data.id)
    ElMessage.success('回归任务已启动，正在逐个评价…')
  } catch (e) {
    ElMessage.error('启动失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    starting.value = false
  }
}

function startPolling(jobId) {
  stopPolling()
  timer = setInterval(async () => {
    const data = await loadJob(jobId, true)
    if (!data || data.status !== 'running') {
      stopPolling()
      loadJobs()
      loadBaseline()
      if (data?.status === 'finished') ElMessage.success('回归测试完成')
    }
  }, 4000)
}

function stopPolling() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

async function loadJob(jobId, silent = false) {
  try {
    const res = await axios.get(`/api/regression/jobs/${jobId}`)
    job.value = res.data
    return res.data
  } catch (e) {
    if (!silent) ElMessage.error('加载任务失败: ' + (e.response?.data?.detail || e.message))
    return null
  }
}

async function saveAsBaseline() {
  if (!job.value) return
  try {
    await ElMessageBox.confirm(
      '将本次结果的平均分保存为基线，后续回归将以它为参照计算偏差。继续？',
      '保存基线', { type: 'info', confirmButtonText: '保存', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    baseline.value = await (await axios.post('/api/regression/baseline', { job_id: job.value.id })).data
    ElMessage.success('基线已保存')
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function clearBaseline() {
  try {
    await ElMessageBox.confirm('清除后偏差列将不再显示，确定？', '清除基线',
      { type: 'warning', confirmButtonText: '清除', cancelButtonText: '取消' })
  } catch {
    return
  }
  try {
    await axios.delete('/api/regression/baseline')
    baseline.value = { cases: {} }
    ElMessage.success('基线已清除')
  } catch (e) {
    ElMessage.error('清除失败: ' + (e.response?.data?.detail || e.message))
  }
}

onMounted(() => {
  loadDemo()
  loadBaseline()
  loadJobs()
})

onBeforeUnmount(stopPolling)
</script>

<style scoped>
.regression-page {
  max-width: 1280px;
  margin: 0 auto;
}

.card {
  border-radius: 12px;
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.meta {
  font-size: 12px;
  color: #9ca3af;
}

.tip {
  margin-bottom: 12px;
}

.form {
  margin-top: 4px;
}

.hint {
  margin-left: 10px;
  font-size: 12px;
  color: #9ca3af;
}

.hint-row {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 2px;
}

.progress-text {
  margin-top: 6px;
  font-size: 13px;
  color: #6b7280;
}

.error {
  color: #ef4444;
}

.score {
  font-weight: 600;
  color: #1a73e8;
}

.muted {
  color: #9ca3af;
}

.delta-ok {
  color: #34a853;
}

.delta-warn {
  color: #f97316;
}

.delta-bad {
  color: #ef4444;
  font-weight: 600;
}

.dim-wrap {
  padding: 8px 16px 12px 48px;
}
</style>
