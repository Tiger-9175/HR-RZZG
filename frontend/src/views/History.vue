<template>
  <div class="history-page">
    <!-- Stats -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6" v-for="card in statCards" :key="card.label">
        <div :class="['stat-card', card.bg]">
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- Filters -->
    <el-card shadow="never" class="filter-card">
      <div class="filters">
        <el-input
          v-model="filters.keyword"
          placeholder="搜索姓名 / 部门"
          clearable
          style="width: 200px"
          @keyup.enter="reload(1)"
        />
        <el-select v-model="filters.profession" placeholder="专业" clearable style="width: 140px">
          <el-option v-for="p in professions" :key="p" :label="p" :value="p" />
        </el-select>
        <el-select v-model="filters.candidate_level" placeholder="申报等级" clearable style="width: 120px">
          <el-option v-for="l in levels" :key="l" :label="l" :value="l" />
        </el-select>
        <el-select v-model="filters.passed" placeholder="评价结论" clearable style="width: 120px">
          <el-option label="通过" value="true" />
          <el-option label="未通过" value="false" />
        </el-select>
        <el-select v-model="filters.review_status" placeholder="评审状态" clearable style="width: 130px">
          <el-option v-for="(label, key) in reviewLabels" :key="key" :label="label" :value="key" />
        </el-select>
        <el-button type="primary" @click="reload(1)">
          <el-icon><Search /></el-icon> 查询
        </el-button>
        <el-button @click="reset">重置</el-button>
        <div class="spacer"></div>
        <el-button
          plain
          :disabled="!selection.length"
          :loading="zipLoading"
          @click="downloadSelectedZip"
        >
          <el-icon><Download /></el-icon> 批量下载PDF（{{ selection.length }}）
        </el-button>
        <el-button type="primary" plain :disabled="selection.length < 2" @click="compareSelected">
          <el-icon><DataAnalysis /></el-icon> 对比选中（{{ selection.length }}）
        </el-button>
      </div>
    </el-card>

    <!-- Table -->
    <el-card shadow="never" class="table-card">
      <el-table
        :data="records"
        v-loading="loading"
        stripe
        style="width: 100%"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column prop="created_at" label="评价时间" width="160">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="candidate_name" label="候选人" width="95" />
        <el-table-column prop="department" label="部门" width="105" show-overflow-tooltip />
        <el-table-column prop="profession" label="专业" width="105" />
        <el-table-column prop="applied_level" label="申报等级" width="85" />
        <el-table-column label="综合得分" width="120">
          <template #default="{ row }">
            <span class="score">{{ row.total_score?.toFixed(1) }}</span>
            <span class="score-total"> / {{ row.total_full_score?.toFixed(0) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="结论" width="90">
          <template #default="{ row }">
            <el-tag :type="row.passed ? 'success' : 'danger'" size="small">
              {{ row.passed ? '通过' : '未通过' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="报告" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.has_report" type="info" size="small" effect="plain">已生成</el-tag>
            <span v-else class="muted">未生成</span>
          </template>
        </el-table-column>
        <el-table-column label="评审状态" width="115">
          <template #default="{ row }">
            <el-tag :type="reviewType(row.review_status)" size="small" effect="plain">
              {{ reviewLabels[row.review_status] || 'AI已评' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="openRecord(row)">查看</el-button>
            <el-button link type="primary" @click.stop="openReview(row)">评审</el-button>
            <el-button link type="primary" :loading="downloading === row.id" @click.stop="downloadReport(row)">
              下载PDF
            </el-button>
            <el-button link type="danger" @click.stop="removeRecord(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next"
          :total="total"
          :current-page="page"
          :page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          @current-change="onPageChange"
          @size-change="onSizeChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="reviewVisible" title="评审处理" width="520px">
      <div v-if="reviewTarget">
        <p class="review-name">
          {{ reviewTarget.candidate_name }} ·
          {{ reviewTarget.applied_level }} ·
          综合得分 {{ reviewTarget.total_score?.toFixed(1) }}
        </p>
        <el-form label-width="90px">
          <el-form-item label="评审结论">
            <el-radio-group v-model="reviewForm.status">
              <el-radio-button label="human_reviewed">人工已复核</el-radio-button>
              <el-radio-button label="final_passed">终审通过</el-radio-button>
              <el-radio-button label="final_rejected">终审不通过</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="评审人">
            <el-input v-model="reviewForm.reviewer" placeholder="姓名" />
          </el-form-item>
          <el-form-item label="评审意见">
            <el-input v-model="reviewForm.comment" type="textarea" :rows="3" placeholder="复核意见、调整说明等" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="reviewVisible = false">取消</el-button>
        <el-button type="primary" :loading="reviewSaving" @click="submitReview">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const router = useRouter()

const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const downloading = ref('')
const zipLoading = ref(false)
const professions = ref([])
const levels = ['一级', '二级', '三级', '四级', '五级', '六级']
const stats = ref({ total: 0, passed: 0, pass_rate: 0, avg_percentage: 0, reports: 0 })

const filters = ref({ keyword: '', profession: '', candidate_level: '', passed: '', review_status: '' })

const selection = ref([])
const reviewVisible = ref(false)
const reviewSaving = ref(false)
const reviewTarget = ref(null)
const reviewForm = ref({ status: 'human_reviewed', reviewer: '', comment: '' })

const reviewLabels = {
  ai_reviewed: 'AI已评',
  human_reviewed: '人工已复核',
  final_passed: '终审通过',
  final_rejected: '终审不通过',
}

function reviewType(status) {
  return {
    ai_reviewed: 'info',
    human_reviewed: 'warning',
    final_passed: 'success',
    final_rejected: 'danger',
  }[status] || 'info'
}

const statCards = computed(() => [
  { value: stats.value.total, label: '评价记录总数', bg: 'gradient-bg-blue' },
  { value: `${stats.value.pass_rate}%`, label: '通过率', bg: 'gradient-bg-green' },
  { value: stats.value.avg_percentage, label: '平均得分率', bg: 'gradient-bg-orange' },
  { value: stats.value.reports, label: '已归档报告', bg: 'gradient-bg-purple' },
])

function formatTime(value) {
  if (!value) return '-'
  return value.replace('T', ' ')
}

async function reload(targetPage) {
  if (targetPage) page.value = targetPage
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    Object.entries(filters.value).forEach(([k, v]) => {
      if (v !== '' && v !== null && v !== undefined) params[k] = v
    })
    const res = await axios.get('/api/evaluations', { params })
    records.value = res.data.items || []
    total.value = res.data.total || 0
  } catch (e) {
    ElMessage.error('加载评价记录失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const res = await axios.get('/api/stats/overview')
    stats.value = res.data
  } catch {
    // non-blocking
  }
}

async function loadProfessions() {
  try {
    const res = await axios.get('/api/demo/standards')
    professions.value = (res.data.standards || []).map(s => s.profession)
  } catch {
    // non-blocking
  }
}

function reset() {
  filters.value = { keyword: '', profession: '', candidate_level: '', passed: '', review_status: '' }
  reload(1)
}

function onSelectionChange(rows) {
  selection.value = rows
}

function compareSelected() {
  if (selection.value.length < 2) return
  const ids = selection.value.map(r => r.id).join(',')
  router.push({ path: '/compare', query: { ids } })
}

async function downloadSelectedZip() {
  if (!selection.value.length) return
  zipLoading.value = true
  try {
    const ids = selection.value.map(r => r.id).join(',')
    const res = await axios.get('/api/reports/zip', {
      params: { ids },
      responseType: 'blob',
      timeout: 300000,
    })
    saveBlob(res, '任职资格评价报告.zip')
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
    zipLoading.value = false
  }
}

function openReview(row) {
  reviewTarget.value = row
  reviewForm.value = {
    status: row.review_status && row.review_status !== 'ai_reviewed'
      ? row.review_status
      : 'human_reviewed',
    reviewer: row.reviewer || '',
    comment: '',
  }
  reviewVisible.value = true
}

async function submitReview() {
  if (!reviewTarget.value) return
  reviewSaving.value = true
  try {
    await axios.patch(`/api/evaluations/${reviewTarget.value.id}/review`, reviewForm.value)
    ElMessage.success('评审状态已更新')
    reviewVisible.value = false
    reload()
    loadStats()
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    reviewSaving.value = false
  }
}

function onPageChange(value) {
  page.value = value
  reload()
}

function onSizeChange(value) {
  pageSize.value = value
  reload(1)
}

function openRecord(row) {
  router.push(`/result/${row.id}`)
}

async function downloadReport(row) {
  downloading.value = row.id
  try {
    const res = await axios.get(`/api/evaluations/${row.id}/report`, {
      responseType: 'blob',
      timeout: 120000,
    })
    saveBlob(res, `任职资格评价报告_${row.candidate_name || '候选人'}.pdf`)
    ElMessage.success('报告已开始下载')
    reload()
  } catch (e) {
    ElMessage.error('报告下载失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    downloading.value = ''
  }
}

function saveBlob(res, fallbackName) {
  const disposition = res.headers['content-disposition'] || ''
  const match = /filename\*=UTF-8''([^;]+)/i.exec(disposition)
  const filename = match ? decodeURIComponent(match[1].trim()) : fallbackName
  const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

async function removeRecord(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除 ${row.candidate_name || '该候选人'} 的评价记录及其PDF报告吗？删除后不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await axios.delete(`/api/evaluations/${row.id}`)
    ElMessage.success('已删除')
    if (records.value.length === 1 && page.value > 1) page.value -= 1
    reload()
    loadStats()
  } catch (e) {
    ElMessage.error('删除失败: ' + (e.response?.data?.detail || e.message))
  }
}

onMounted(() => {
  reload(1)
  loadStats()
  loadProfessions()
})
</script>

<style scoped>
.history-page {
  max-width: 1200px;
  margin: 0 auto;
}

.stats-row {
  margin-bottom: 16px;
}

.stat-card {
  padding: 18px 16px;
  border-radius: 12px;
  color: #fff;
  text-align: center;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
}

.stat-label {
  font-size: 13px;
  opacity: 0.85;
  margin-top: 4px;
}

.gradient-bg-blue {
  background: linear-gradient(135deg, #1a73e8, #4a90d9);
}

.gradient-bg-green {
  background: linear-gradient(135deg, #34a853, #66bb6a);
}

.gradient-bg-orange {
  background: linear-gradient(135deg, #f97316, #fb923c);
}

.gradient-bg-purple {
  background: linear-gradient(135deg, #7c4dff, #9c7bff);
}

.filter-card {
  border-radius: 12px;
  margin-bottom: 16px;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.spacer {
  flex: 1;
}

.review-name {
  margin-bottom: 12px;
  color: #374151;
  font-weight: 600;
}

.table-card {
  border-radius: 12px;
}

.score {
  font-weight: 600;
  color: #1a73e8;
}

.score-total {
  color: #9ca3af;
  font-size: 12px;
}

.muted {
  color: #9ca3af;
  font-size: 13px;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

:deep(.clickable-row) {
  cursor: pointer;
}
</style>
