<template>
  <div class="result-page" v-if="result" v-loading="loadingRecord">
    <!-- Top Summary Banner -->
    <div :class="['result-banner', result.passed ? 'passed' : 'failed']">
      <div class="banner-left">
        <el-icon :size="48" v-if="result.passed"><CircleCheckFilled /></el-icon>
        <el-icon :size="48" v-else><CircleCloseFilled /></el-icon>
        <div class="banner-text">
          <h2>{{ result.passed ? '恭喜通过评价' : '未达到申报等级要求' }}</h2>
          <p>{{ result.candidate.name || '候选人' }} · 申请{{ result.candidate.applied_level }}</p>
        </div>
      </div>
      <div class="banner-right">
        <div class="big-score">
          <span class="score-num">{{ result.total_score?.toFixed(1) }}</span>
          <span class="score-divider">/</span>
          <span class="score-total">{{ result.total_full_score }}</span>
        </div>
        <div class="score-label">综合得分</div>
      </div>
    </div>

    <!-- Stats Row -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6" v-for="stat in stats" :key="stat.label">
        <div :class="['stat-card', stat.bg]">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- ===== 评审状态 ===== -->
    <div class="review-bar" v-if="recordId">
      <el-tag :type="reviewType(recordMeta?.review_status)" size="small" effect="plain">
        {{ reviewLabels[recordMeta?.review_status] || 'AI已评' }}
      </el-tag>
      <span v-if="recordMeta?.reviewer" class="review-meta">评审人：{{ recordMeta.reviewer }}</span>
      <span v-if="recordMeta?.reviewed_at" class="review-meta">
        {{ String(recordMeta.reviewed_at).replace('T', ' ') }}
      </span>
      <div class="spacer"></div>
      <el-button size="small" @click="openReview">评审处理</el-button>
    </div>

    <!-- ===== 门槛条件核查 ===== -->
    <div class="report-section" v-if="result.threshold_check?.items?.length">
      <div class="section-title-bar">
        <el-icon><Checked /></el-icon>
        <span>门槛条件核查</span>
        <el-tag
          :type="result.threshold_check.overall_pass ? 'success' : 'danger'"
          size="small"
          style="margin-left: auto"
        >
          {{ result.threshold_check.overall_pass ? '全部满足' : '存在不满足项' }}
        </el-tag>
      </div>
      <div class="threshold-list">
        <div v-for="item in result.threshold_check.items" :key="item.field" class="threshold-item">
          <div class="threshold-head">
            <el-tag
              :type="item.status?.startsWith('✅') ? 'success' : item.status?.startsWith('⚠️') ? 'warning' : 'danger'"
              size="small"
            >
              {{ item.status || '未核查' }}
            </el-tag>
            <span class="threshold-name">{{ item.label }}</span>
            <span class="threshold-required">要求：{{ item.required || '—' }}</span>
          </div>
          <div class="threshold-detail">{{ item.detail || '—' }}</div>
        </div>
      </div>
    </div>

    <!-- Charts & Dimensions -->
    <el-row :gutter="16" class="charts-row">
      <!-- Radar Chart -->
      <el-col :span="10" class="radar-col">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <span class="card-title"><el-icon><DataAnalysis /></el-icon> 能力维度雷达图</span>
          </template>
          <div ref="radarRef" class="radar-chart"></div>
        </el-card>
      </el-col>

      <!-- Score Distribution -->
      <el-col :span="14" class="scores-col">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <span class="card-title"><el-icon><Histogram /></el-icon> 各维度得分详情</span>
          </template>
          <div class="dimension-scores">
            <div v-for="dim in result.dimensions" :key="dim.name" class="dim-item">
              <div class="dim-header">
                <span class="dim-name">{{ dim.name }}</span>
                <span class="dim-score">
                  <span :class="scoreClass(dim)">{{ dim.score?.toFixed(1) || '-' }}</span>
                  / {{ dim.full_score }}
                  <el-tag :type="scoreTag(dim)" size="small" effect="plain" style="margin-left: 8px;">
                    {{ dim.score_percentage?.toFixed(0) || 0 }}%
                  </el-tag>
                </span>
              </div>
              <el-progress
                :percentage="dimPercentage(dim)"
                :stroke-width="10"
                :color="dim.score && dim.full_score && (dim.score / dim.full_score) >= 0.6 ? '#34a853' : (dim.score && dim.full_score && (dim.score / dim.full_score) >= 0.4 ? '#f97316' : '#ef4444')"
                striped
              />
              <div class="dim-threshold" v-if="dim.threshold">
                达标线：{{ dim.threshold }}分
                <el-icon v-if="dim.score && dim.score >= dim.threshold" color="#34a853"><CircleCheck /></el-icon>
                <el-icon v-else color="#ef4444"><CircleClose /></el-icon>
                <span v-if="dim.pages?.length" class="dim-pages" @click.stop="jumpToSlide(dim.pages[0])">
                  证据：P{{ dim.pages.join('、P') }}
                </span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ===== 综合评价 ===== -->
    <div class="report-section">
      <div class="section-title-bar">
        <el-icon><Document /></el-icon>
        <span>综合评价</span>
      </div>
      <div class="analysis-content">
        <h4>综合评价意见</h4>
        <p>{{ result.summary || '暂无' }}</p>

        <el-row :gutter="20" class="strength-row">
          <el-col :span="12">
            <h4 class="strength-title"><el-icon color="#34a853"><CircleCheck /></el-icon> 核心优势</h4>
            <ul class="strength-list">
              <li v-for="(s, i) in result.strengths" :key="i">{{ s }}</li>
            </ul>
          </el-col>
          <el-col :span="12">
            <h4 class="improve-title"><el-icon color="#f97316"><WarningFilled /></el-icon> 待改进方面</h4>
            <ul class="improve-list">
              <li v-for="(s, i) in result.improvements" :key="i">{{ s }}</li>
            </ul>
          </el-col>
        </el-row>

        <div v-if="result.suggestions" class="suggestions-block">
          <h4><el-icon color="#1a73e8"><Lightbulb /></el-icon> 发展建议</h4>
          <p class="suggestion-text">{{ result.suggestions }}</p>
        </div>
      </div>
    </div>

    <!-- ===== 各维度详细评价 ===== -->
    <div class="report-section" v-if="result.dimensions?.length">
      <div class="section-title-bar">
        <el-icon><List /></el-icon>
        <span>各维度详细评价</span>
      </div>
      <div class="dim-details-list">
        <div v-for="dim in result.dimensions" :key="dim.name" class="dim-detail-card">
          <div class="dim-detail-header">
            {{ dim.name }}（{{ dim.score?.toFixed(1) || '-' }}/{{ dim.full_score }}分）
          </div>
          <div v-if="dim.comments" class="dim-detail-body">
            <strong>评价意见：</strong>
            <p>{{ dim.comments }}</p>
          </div>
          <div v-if="dim.details" class="dim-detail-body">
            <strong>详细分析：</strong>
            <p>{{ dim.details }}</p>
          </div>
          <div v-if="dim.evidence?.length" class="dim-detail-body">
            <strong>举证溯源（点击页码跳转到原文）：</strong>
            <div
              v-for="(ev, i) in dim.evidence"
              :key="i"
              class="evidence-item"
              @click="jumpToSlide(ev.page)"
            >
              <el-tag v-if="ev.page" size="small" effect="plain" class="page-tag">P{{ ev.page }}</el-tag>
              <span class="evidence-quote">“{{ ev.quote }}”</span>
              <span v-if="ev.note" class="evidence-note">{{ ev.note }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 思维链推理过程 ===== -->
    <div class="report-section" v-if="result.chain_of_thought">
      <div class="section-title-bar">
        <el-icon><Cpu /></el-icon>
        <span>思维链推理过程</span>
      </div>
      <pre class="cot-content">{{ result.chain_of_thought }}</pre>
    </div>

    <!-- ===== 原始材料 ===== -->
    <div class="report-section">
      <div class="section-title-bar">
        <el-icon><Reading /></el-icon>
        <span>原始材料</span>
      </div>
      <div class="raw-content">
        <div v-if="slides.length" class="slide-list">
          <div
            v-for="slide in slides"
            :id="`slide-${slide.no}`"
            :key="slide.no"
            class="slide-block"
          >
            <div class="slide-title">幻灯片 {{ slide.no }}</div>
            <pre class="slide-text">{{ slide.text }}</pre>
          </div>
        </div>
        <pre v-else class="raw-text">{{ pptContentDisplay }}</pre>
      </div>
    </div>

    <el-dialog v-model="reviewVisible" title="评审处理" width="520px" class="no-print">
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
      <template #footer>
        <el-button @click="reviewVisible = false">取消</el-button>
        <el-button type="primary" :loading="reviewSaving" @click="submitReview">保存</el-button>
      </template>
    </el-dialog>

    <!-- Actions (hidden in print) -->
    <div class="result-actions no-print">
      <el-button type="primary" size="large" :loading="pdfLoading" @click="downloadPdf">
        <el-icon><Download /></el-icon>
        生成PDF报告
      </el-button>
      <el-button size="large" @click="printResult">
        <el-icon><Printer /></el-icon>
        打印报告
      </el-button>
      <el-button size="large" plain @click="$router.push('/history')">
        <el-icon><Clock /></el-icon>
        历史记录
      </el-button>
      <el-button size="large" plain @click="$router.push('/evaluate')">
        <el-icon><Back /></el-icon>
        返回重新评价
      </el-button>
    </div>
  </div>

  <!-- No result state -->
  <div v-else class="empty-state">
    <el-empty description="请先进行评价">
      <el-button type="primary" @click="$router.push('/evaluate')">
        <el-icon><Upload /></el-icon>
        去上传材料
      </el-button>
    </el-empty>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const radarRef = ref(null)
const result = ref(null)
const pptContentDisplay = ref('')
const pdfLoading = ref(false)
const loadingRecord = ref(false)
const recordId = ref('')
const recordMeta = ref(null)
const reviewVisible = ref(false)
const reviewSaving = ref(false)
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

function openReview() {
  reviewForm.value = {
    status: recordMeta.value?.review_status && recordMeta.value.review_status !== 'ai_reviewed'
      ? recordMeta.value.review_status
      : 'human_reviewed',
    reviewer: recordMeta.value?.reviewer || '',
    comment: '',
  }
  reviewVisible.value = true
}

async function submitReview() {
  if (!recordId.value) return
  reviewSaving.value = true
  try {
    const res = await axios.patch(`/api/evaluations/${recordId.value}/review`,
      reviewForm.value)
    recordMeta.value = res.data
    reviewVisible.value = false
    ElMessage.success('评审状态已更新')
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    reviewSaving.value = false
  }
}

const stats = computed(() => {
  if (!result.value) return []
  const dims = result.value.dimensions || []
  return [
    { value: result.value.total_score?.toFixed(1) || '0', label: '综合得分', bg: 'gradient-bg-blue' },
    { value: dims.length, label: '评价维度', bg: 'gradient-bg-green' },
    { value: result.value.strengths?.length || 0, label: '核心优势', bg: 'gradient-bg-orange' },
    { value: result.value.passed ? '通过' : '未通过', label: '评价结论', bg: result.value.passed ? 'gradient-bg-green' : 'gradient-bg-red' },
  ]
})

const slides = computed(() => splitSlides(pptContentDisplay.value))

function splitSlides(markdown) {
  if (!markdown) return []
  const pattern = /^##\s*幻灯片\s*(\d+)\s*$/gm
  const marks = []
  let match
  while ((match = pattern.exec(markdown)) !== null) {
    marks.push({ no: Number(match[1]), headingStart: match.index, bodyStart: pattern.lastIndex })
  }
  return marks.map((mark, index) => ({
    no: mark.no,
    text: markdown
      .slice(mark.bodyStart, index + 1 < marks.length ? marks[index + 1].headingStart : markdown.length)
      .trim(),
  }))
}

function jumpToSlide(page) {
  if (!page) return
  const target = document.getElementById(`slide-${page}`)
  if (!target) {
    ElMessage.warning(`原始材料中没有找到第 ${page} 页`)
    return
  }
  target.scrollIntoView({ behavior: 'smooth', block: 'center' })
  target.classList.add('flash')
  setTimeout(() => target.classList.remove('flash'), 2000)
}

function dimPercentage(dim) {
  if (!dim?.full_score || dim.score === null || dim.score === undefined) return 0
  return Math.round((dim.score / dim.full_score) * 100)
}

function scoreTag(dim) {
  if (!dim.score || !dim.full_score) return 'info'
  const pct = dim.score / dim.full_score
  if (pct >= 0.8) return 'success'
  if (pct >= 0.6) return 'warning'
  return 'danger'
}

function scoreClass(dim) {
  if (!dim.score || !dim.full_score) return ''
  const pct = dim.score / dim.full_score
  if (pct >= 0.8) return 'score-high'
  if (pct >= 0.6) return 'score-mid'
  return 'score-low'
}

let chartInstance = null

function initRadar() {
  if (!radarRef.value || !result.value?.dimensions?.length) return

  const dims = result.value.dimensions

  if (chartInstance) {
    chartInstance.dispose()
  }
  chartInstance = echarts.init(radarRef.value)

  const maxLabelLen = 5
  const shortNames = dims.map(d =>
    d.name.length > maxLabelLen ? d.name.substring(0, maxLabelLen) + '…' : d.name
  )

  const option = {
    radar: {
      center: ['50%', '50%'],
      radius: '55%',
      indicator: dims.map((d, i) => ({
        name: shortNames[i],
        max: d.full_score || 30,
      })),
      shape: 'polygon',
      splitNumber: 4,
      axisName: {
        color: '#374151',
        fontSize: 12,
        fontWeight: 500,
        overflow: 'truncate',
        width: 60,
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(26,115,232,0.02)', 'rgba(26,115,232,0.05)'],
        },
      },
    },
    series: [{
      type: 'radar',
      data: [{
        value: dims.map(d => d.score || 0),
        name: '评估得分',
        areaStyle: { color: 'rgba(26,115,232,0.2)' },
        lineStyle: { color: '#1a73e8', width: 2 },
        itemStyle: { color: '#1a73e8' },
      }],
      symbol: 'circle',
      symbolSize: 8,
    }],
    tooltip: {
      trigger: 'item',
      formatter: function (params) {
        const vals = params.value || []
        return dims.map((d, i) =>
          `<div style="margin:2px 0;"><b>${d.name}</b>: ${vals[i]?.toFixed(1) || 0}/${d.full_score}</div>`
        ).join('')
      },
    },
  }

  chartInstance.setOption(option)

  const observer = new ResizeObserver(() => {
    if (chartInstance) chartInstance.resize()
  })
  observer.observe(radarRef.value)
  window.addEventListener('resize', () => {
    if (chartInstance) chartInstance.resize()
  })
}

function printResult() {
  // Resize chart for print layout first
  if (chartInstance) {
    chartInstance.resize()
  }
  // Small delay to let resize apply, then print
  setTimeout(() => window.print(), 150)
}

function parseFilename(disposition) {
  if (!disposition) return ''
  const star = /filename\*=UTF-8''([^;]+)/i.exec(disposition)
  if (star) {
    try {
      return decodeURIComponent(star[1].trim())
    } catch {
      return ''
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(disposition)
  return plain ? plain[1].trim() : ''
}

async function downloadPdf() {
  if (!result.value) return
  pdfLoading.value = true
  try {
    let res
    if (recordId.value) {
      // Archived records are served (and cached on disk) by the backend
      res = await axios.get(`/api/evaluations/${recordId.value}/report`, {
        responseType: 'blob',
        timeout: 120000,
      })
    } else {
      res = await axios.post('/api/report/pdf', {
        result: result.value,
        ppt_content: pptContentDisplay.value || '',
        reviewer: '',
        organization: '',
        include_cot: true,
      }, { responseType: 'blob', timeout: 120000 })
    }

    const fallbackName = `任职资格评价报告_${result.value.candidate?.name || '候选人'}.pdf`
    const filename = parseFilename(res.headers['content-disposition']) || fallbackName
    const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    ElMessage.success('PDF报告已生成并开始下载')
  } catch (e) {
    let msg = e.message
    if (e.response?.data instanceof Blob) {
      try {
        const text = await e.response.data.text()
        msg = JSON.parse(text).detail || text.slice(0, 200)
      } catch {
        // keep original message
      }
    }
    ElMessage.error('报告生成失败: ' + msg)
  } finally {
    pdfLoading.value = false
  }
}

onMounted(async () => {
  // 1) Opened from the history list: load the archived record by id
  const id = route.params.id
  if (id) {
    loadingRecord.value = true
    try {
      const res = await axios.get(`/api/evaluations/${id}`)
      result.value = res.data.result
      recordId.value = res.data.id
      recordMeta.value = res.data
      pptContentDisplay.value = res.data.ppt_content || ''
      return
    } catch (e) {
      ElMessage.error('评价记录加载失败: ' + (e.response?.data?.detail || e.message))
    } finally {
      loadingRecord.value = false
    }
  }

  // 2) Fresh evaluation: read from session storage
  const stored = sessionStorage.getItem('evalResult')
  if (stored) {
    try {
      const parsed = JSON.parse(stored)
      result.value = parsed
      recordId.value = parsed.record_id || ''
      recordMeta.value = { review_status: 'ai_reviewed' }
      pptContentDisplay.value = sessionStorage.getItem('pptContent') || ''
      // Keep the URL in sync so the page can be refreshed / shared
      if (recordId.value && !route.params.id) {
        router.replace(`/result/${recordId.value}`)
      }
    } catch (e) {
      console.error('Failed to load result:', e)
    }
  }
})

watch(result, () => {
  nextTick(() => initRadar())
})
</script>

<style scoped>
.result-page {
  max-width: 1100px;
  margin: 0 auto;
}

/* ---------- Banner ---------- */
.result-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 32px;
  border-radius: 16px;
  color: white;
}

.result-banner.passed {
  background: linear-gradient(135deg, #34a853, #66bb6a);
}

.result-banner.failed {
  background: linear-gradient(135deg, #ef4444, #f87171);
}

.banner-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.banner-text h2 {
  font-size: 22px;
  margin-bottom: 4px;
}

.banner-text p {
  opacity: 0.9;
  font-size: 14px;
}

.banner-right {
  text-align: center;
}

.big-score .score-num {
  font-size: 48px;
  font-weight: 700;
}

.big-score .score-divider {
  font-size: 36px;
  opacity: 0.6;
  margin: 0 4px;
}

.big-score .score-total {
  font-size: 24px;
  opacity: 0.8;
}

.score-label {
  font-size: 13px;
  opacity: 0.9;
  margin-top: 4px;
}

/* ---------- Stats ---------- */
.stats-row {
  margin-top: 16px;
}

.stat-card {
  padding: 20px 16px;
  border-radius: 12px;
  color: #fff;
  text-align: center;
}

.stat-value {
  font-size: 28px;
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

.gradient-bg-red {
  background: linear-gradient(135deg, #ef4444, #f87171);
}

/* ---------- Review bar ---------- */
.review-bar {
  margin-top: 16px;
  padding: 10px 16px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.review-meta {
  font-size: 12px;
  color: #9ca3af;
}

.spacer {
  flex: 1;
}

/* ---------- Threshold check ---------- */
.threshold-list {
  padding: 6px 20px 14px;
}

.threshold-item {
  padding: 10px 0;
  border-bottom: 1px dashed #eef1f5;
}

.threshold-item:last-child {
  border-bottom: none;
}

.threshold-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.threshold-name {
  font-weight: 600;
  color: #374151;
}

.threshold-required {
  font-size: 12px;
  color: #6b7280;
}

.threshold-detail {
  margin-top: 6px;
  font-size: 13px;
  color: #4b5563;
  line-height: 1.6;
}

/* ---------- Charts ---------- */
.charts-row {
  margin-top: 16px;
}

.chart-card {
  border-radius: 12px;
}

.radar-chart {
  height: 380px;
  width: 100%;
  min-width: 300px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.dimension-scores {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dim-item {
  padding: 8px 0;
}

.dim-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.dim-name {
  font-weight: 500;
  color: #374151;
}

.dim-score {
  font-size: 14px;
  color: #6b7280;
}

.dim-score .score-high {
  color: #34a853;
  font-weight: 600;
}

.dim-score .score-mid {
  color: #f97316;
  font-weight: 600;
}

.dim-score .score-low {
  color: #ef4444;
  font-weight: 600;
}

.dim-threshold {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* ---------- Report Sections ---------- */
.report-section {
  margin-top: 20px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

.section-title-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
  font-weight: 600;
  font-size: 15px;
  color: #374151;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.analysis-content {
  padding: 20px;
}

.analysis-content h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  color: #374151;
}

.strength-row {
  margin-top: 20px;
}

.strength-title {
  color: #34a853;
}

.improve-title {
  color: #f97316;
}

.strength-list,
.improve-list {
  padding-left: 20px;
}

.strength-list li,
.improve-list li {
  margin-bottom: 6px;
  line-height: 1.6;
}

.strength-list li {
  color: #059669;
}

.improve-list li {
  color: #d97706;
}

.suggestions-block {
  margin-top: 20px;
}

.suggestion-text {
  color: #1a73e8;
  line-height: 1.8;
  background: #e8f0fe;
  padding: 12px 16px;
  border-radius: 8px;
}

/* ---------- Dimension details ---------- */
.dim-details-list {
  padding: 16px 20px;
}

.dim-detail-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 12px;
}

.dim-detail-header {
  font-weight: 600;
  color: #1a73e8;
  font-size: 15px;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f3f4f6;
}

.dim-detail-body {
  margin-top: 6px;
}

.dim-detail-body strong {
  color: #374151;
}

.dim-detail-body p {
  margin-top: 4px;
  color: #4b5563;
  line-height: 1.6;
}

/* ---------- CoT + Raw ---------- */
.cot-content {
  padding: 16px 20px;
  margin: 0;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.7;
  color: #374151;
  background: #fafbfc;
}

.raw-content {
  padding: 12px 20px;
}

.raw-text {
  margin: 0;
  white-space: pre-wrap;
  font-size: 12px;
  line-height: 1.5;
  color: #6b7280;
  max-height: 400px;
  overflow-y: auto;
}

/* ---------- Evidence ---------- */
.dim-pages {
  margin-left: 10px;
  color: #1a73e8;
  cursor: pointer;
  text-decoration: underline dotted;
}

.evidence-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  flex-wrap: wrap;
  padding: 8px 10px;
  margin-top: 6px;
  background: #f7f9fc;
  border-left: 3px solid #1a73e8;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.evidence-item:hover {
  background: #e8f0fe;
}

.page-tag {
  flex-shrink: 0;
}

.evidence-quote {
  color: #374151;
  font-size: 13px;
  line-height: 1.6;
}

.evidence-note {
  color: #9ca3af;
  font-size: 12px;
}

/* ---------- Raw material slides ---------- */
.slide-list {
  max-height: 520px;
  overflow-y: auto;
  padding-right: 4px;
}

.slide-block {
  padding: 10px 12px;
  margin-bottom: 8px;
  border: 1px solid #eef1f5;
  border-radius: 8px;
  transition: background 0.3s, border-color 0.3s;
}

.slide-block.flash {
  background: #fff7e6;
  border-color: #f97316;
}

.slide-title {
  font-size: 12px;
  font-weight: 600;
  color: #1a73e8;
  margin-bottom: 6px;
}

.slide-text {
  margin: 0;
  white-space: pre-wrap;
  font-size: 12px;
  line-height: 1.6;
  color: #4b5563;
}

/* ---------- Actions ---------- */
.result-actions {
  margin-top: 20px;
  text-align: center;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

/* Blocks with bg */
.no-print {
  /* shown on screen, hidden in print */
}
</style>

<!-- Global print styles (NOT scoped) -->
<style>
@media print {
  /* ===== TOP-LEVEL RESET: kill all layout constraints ===== */
  html, body, #app {
    height: auto !important;
    overflow: visible !important;
  }

  .app-container {
    height: auto !important;
    overflow: visible !important;
    display: block !important;
  }

  .main-container {
    display: block !important;
    overflow: visible !important;
    height: auto !important;
  }

  /* Hide sidebar, header */
  .app-sidebar, .app-header, .el-menu, .el-aside {
    display: none !important;
  }

  /* Main area: remove flex constraints, allow full scroll */
  .app-main {
    margin-left: 0 !important;
    padding: 0 !important;
    background: #fff !important;
    flex: none !important;
    height: auto !important;
    overflow: visible !important;
  }

  .el-main {
    padding: 0 !important;
    overflow: visible !important;
    height: auto !important;
  }

  /* Result page full width */
  .result-page {
    max-width: 100% !important;
    margin: 0 !important;
    padding: 8px !important;
  }

  /* ===== CHARTS ROW: stack vertically ===== */
  .charts-row,
  .charts-row .el-col,
  .radar-col,
  .scores-col {
    display: block !important;
    width: 100% !important;
    max-width: 100% !important;
    flex: none !important;
  }

  .radar-chart {
    height: 480px !important;
    width: 100% !important;
  }

  .chart-card {
    margin-bottom: 16px;
    page-break-inside: avoid;
  }

  /* ===== REPORT SECTIONS: all visible ===== */
  .report-section {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    height: auto !important;
    overflow: visible !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    margin-bottom: 12px;
    page-break-inside: avoid;
  }

  /* ===== BANNER & STATS ===== */
  .result-banner {
    border-radius: 0 !important;
    box-shadow: none !important;
    page-break-inside: avoid;
  }

  .stat-card {
    border-radius: 4px !important;
    box-shadow: none !important;
  }

  .stats-row {
    page-break-inside: avoid;
  }

  /* ===== EXPAND all text ===== */
  .cot-content,
  .raw-text,
  .raw-content,
  .slide-list,
  .slide-text {
    max-height: none !important;
    overflow: visible !important;
    display: block !important;
    visibility: visible !important;
  }

  /* ===== DIMENSION DETAILS ===== */
  .dim-details-list,
  .dim-detail-card,
  .dim-detail-body {
    display: block !important;
    visibility: visible !important;
    page-break-inside: avoid;
  }

  /* ===== ACTION BUTTONS ===== */
  .result-actions, .no-print {
    display: none !important;
  }

  /* ===== FORCE COLORS ===== */
  * {
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }

  .section-title-bar {
    background: #f3f4f6 !important;
    border-bottom: 2px solid #1a73e8 !important;
  }

  @page {
    size: A4;
    margin: 10mm 12mm;
  }
}
</style>
