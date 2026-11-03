<template>
  <div class="compare-page">
    <el-card v-if="!records.length" shadow="never" class="card">
      <el-empty description="请先在历史记录中选择 2 条及以上记录进行对比">
        <el-button type="primary" @click="$router.push('/history')">去历史记录</el-button>
      </el-empty>
    </el-card>

    <template v-else>
      <el-card shadow="never" class="card">
        <template #header>
          <div class="card-header">
            <span class="card-title"><el-icon><DataAnalysis /></el-icon> 候选人横向对比</span>
            <div class="header-actions">
              <el-tag size="small" type="info">{{ records.length }} 人</el-tag>
              <el-button size="small" @click="$router.push('/history')">返回历史记录</el-button>
            </div>
          </div>
        </template>

        <el-row :gutter="16">
          <el-col :span="11">
            <div ref="radarRef" class="radar"></div>
          </el-col>
          <el-col :span="13">
            <el-table :data="records" size="small">
              <el-table-column prop="name" label="候选人" width="90" />
              <el-table-column prop="applied_level" label="等级" width="70" />
              <el-table-column prop="profession" label="专业" show-overflow-tooltip />
              <el-table-column label="总分" width="90">
                <template #default="{ row }">
                  <span class="score">{{ row.total_score?.toFixed(1) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="得分率" width="90">
                <template #default="{ row }">{{ row.total_percentage?.toFixed(1) }}%</template>
              </el-table-column>
              <el-table-column label="结论" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.passed ? 'success' : 'danger'" size="small">
                    {{ row.passed ? '通过' : '未通过' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-col>
        </el-row>
      </el-card>

      <el-card shadow="never" class="card">
        <template #header>
          <span class="card-title"><el-icon><Grid /></el-icon> 维度得分对照</span>
        </template>
        <el-table :data="matrixRows" size="small" border>
          <el-table-column prop="dimension" label="评价维度" min-width="150" fixed />
          <el-table-column
            v-for="record in records"
            :key="record.id"
            :label="`${record.name}${record.applied_level ? '（' + record.applied_level + '）' : ''}`"
            width="150"
          >
            <template #default="{ row }">
              <span class="cell-score">{{ formatCell(row.byRecord[record.id], row.full_score) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import axios from 'axios'

const route = useRoute()
const records = ref([])
const dimensions = ref([])
const radarRef = ref(null)
let chart = null

const matrixRows = computed(() => {
  const rows = dimensions.value.map(dim => {
    const byRecord = {}
    records.value.forEach(record => {
      const hit = (record.dimensions || []).find(d => d.name === dim.name)
      byRecord[record.id] = hit ? hit.score : null
    })
    return { dimension: dim.name, full_score: dim.full_score, byRecord }
  })

  const totalRow = { dimension: '综合得分', full_score: 100, byRecord: {} }
  records.value.forEach(record => {
    totalRow.byRecord[record.id] = record.total_score
  })
  rows.push(totalRow)
  return rows
})

function formatCell(score, full) {
  if (score === null || score === undefined) return '-'
  return full ? `${score.toFixed(1)} / ${full.toFixed(0)}` : score.toFixed(1)
}

const palette = ['#1a73e8', '#34a853', '#f97316', '#7c4dff', '#e91e63', '#00897b', '#8d6e63', '#ffb300']

function initChart() {
  if (!radarRef.value) return
  if (chart) chart.dispose()
  chart = echarts.init(radarRef.value)

  const indicator = dimensions.value.map(dim => ({
    name: dim.name.length > 6 ? dim.name.slice(0, 6) + '…' : dim.name,
    max: dim.full_score || 30,
  }))

  chart.setOption({
    color: palette,
    legend: { bottom: 0, type: 'scroll' },
    tooltip: { trigger: 'item' },
    radar: {
      indicator,
      radius: '62%',
      center: ['50%', '48%'],
      splitNumber: 4,
      axisName: { color: '#374151', fontSize: 12 },
      splitArea: { areaStyle: { color: ['rgba(26,115,232,0.02)', 'rgba(26,115,232,0.05)'] } },
    },
    series: [{
      type: 'radar',
      data: records.value.map(record => ({
        name: record.name || record.id,
        value: dimensions.value.map(dim => {
          const hit = (record.dimensions || []).find(d => d.name === dim.name)
          return hit?.score || 0
        }),
        areaStyle: { opacity: 0.12 },
        lineStyle: { width: 2 },
      })),
    }],
  })

  window.addEventListener('resize', resize)
}

function resize() {
  chart?.resize()
}

async function load() {
  const ids = (route.query.ids || '').split(',').filter(Boolean)
  if (ids.length < 2) return
  try {
    const res = await axios.get('/api/compare', { params: { ids: ids.join(',') } })
    records.value = res.data.records || []
    dimensions.value = res.data.dimensions || []
    await nextTick()
    initChart()
  } catch (e) {
    ElMessage.error('对比数据加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

onMounted(load)
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
})
</script>

<style scoped>
.compare-page {
  max-width: 1200px;
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
  gap: 8px;
}

.radar {
  height: 360px;
  width: 100%;
}

.score {
  font-weight: 600;
  color: #1a73e8;
}

.cell-score {
  font-size: 13px;
  color: #374151;
}
</style>
