<template>
  <div class="demo-page">
    <el-card shadow="never" class="demo-card">
      <template #header>
        <div class="card-header">
          <el-icon><FolderOpened /></el-icon>
          <span>示例数据</span>
          <el-tag type="warning" size="small" effect="plain">演示用数据</el-tag>
        </div>
      </template>

      <el-alert
        title="选择一组示例数据快速体验评价功能"
        type="info"
        show-icon
        :closable="false"
        style="margin-bottom: 20px;"
      />

      <el-tabs v-model="activeTab">
        <el-tab-pane label="答辩PPT" name="ppt">
          <el-table :data="pptFiles" stripe style="width: 100%" @row-click="selectPPT">
            <el-table-column prop="name" label="文件名" min-width="300">
              <template #default="{ row }">
                <div class="file-name">
                  <el-icon><Document /></el-icon>
                  {{ row.name }}
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="size" label="大小" width="120">
              <template #default="{ row }">
                {{ (row.size / 1024).toFixed(1) }} KB
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  size="small"
                  :disabled="selectedPPT === row.name"
                  @click.stop="selectPPT(row)"
                >
                  {{ selectedPPT === row.name ? '已选' : '选择' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="任职资格标准" name="standard">
          <el-table :data="standardFiles" stripe @row-click="selectStandard">
            <el-table-column prop="name" label="文件名" min-width="300">
              <template #default="{ row }">
                <div class="file-name">
                  <el-icon><Reading /></el-icon>
                  {{ row.name }}
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="size" label="大小" width="120">
              <template #default="{ row }">
                {{ (row.size / 1024).toFixed(1) }} KB
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  size="small"
                  :disabled="selectedStandard === row.name"
                  @click.stop="selectStandard(row)"
                >
                  {{ selectedStandard === row.name ? '已选' : '选择' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="职位说明书" name="job_desc">
          <el-table :data="jobDescFiles" stripe @row-click="selectJobDesc">
            <el-table-column prop="name" label="文件名" min-width="300">
              <template #default="{ row }">
                <div class="file-name">
                  <el-icon><Collection /></el-icon>
                  {{ row.name }}
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="size" label="大小" width="120">
              <template #default="{ row }">
                {{ (row.size / 1024).toFixed(1) }} KB
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  size="small"
                  :disabled="selectedJobDesc === row.name"
                  @click.stop="selectJobDesc(row)"
                >
                  {{ selectedJobDesc === row.name ? '已选' : '选择' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>

      <div style="margin-top: 20px; padding: 16px; background: #f0fdf4; border-radius: 8px;" v-if="selectedPPT">
        <h4 style="margin-bottom: 8px; color: #059669;">
          <el-icon><CircleCheck /></el-icon>
          已选择
        </h4>
        <p>PPT: {{ selectedPPT }}</p>
        <p v-if="selectedStandard">标准: {{ selectedStandard }}</p>
      </div>

      <div class="demo-actions" style="margin-top: 20px;">
        <el-button
          type="primary"
          size="large"
          :disabled="!selectedPPT"
          @click="loadDemo"
        >
          <el-icon><Cpu /></el-icon>
          加载并开始评价
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const activeTab = ref('ppt')

const pptFiles = ref([])
const standardFiles = ref([])
const jobDescFiles = ref([])
const selectedPPT = ref('')
const selectedStandard = ref('')
const selectedJobDesc = ref('')

onMounted(async () => {
  try {
    const res = await axios.get('/api/demo/files')
    const files = res.data.files || {}
    pptFiles.value = files.ppt || []
    standardFiles.value = files.standard || []
    jobDescFiles.value = files.job_desc || []
  } catch (e) {
    ElMessage.warning('无法加载示例文件列表')
  }
})

function selectPPT(file) {
  selectedPPT.value = file.name
  // Try to auto-select matching standard
  const prefix = file.name.split('_')[0].replace('公开 ', '').replace('公开', '')
  const match = standardFiles.value.find(s => s.name.includes(prefix))
  if (match) {
    selectedStandard.value = match.name
  }
}

function selectStandard(file) {
  selectedStandard.value = file.name === selectedStandard.value ? '' : file.name
}

function selectJobDesc(file) {
  selectedJobDesc.value = file.name === selectedJobDesc.value ? '' : file.name
}

async function loadDemo() {
  if (!selectedPPT.value) return

  try {
    ElMessage.info('正在加载示例数据...')

    // Load PPT
    const pptRes = await axios.get('/api/demo/load', {
      params: { filename: selectedPPT.value },
    })
    sessionStorage.setItem('pptContent', pptRes.data.content)
    sessionStorage.setItem('candidateInfo', JSON.stringify(pptRes.data.candidate))

    // Load standard if selected
    if (selectedStandard.value) {
      const stdRes = await axios.get('/api/demo/load', {
        params: { filename: selectedStandard.value },
      })
      sessionStorage.setItem('standardContent', stdRes.data.content)
    }

    ElMessage.success('示例数据加载完成，正在跳转...')
    router.push('/evaluate')
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  }
}
</script>

<style scoped>
.demo-page {
  max-width: 1000px;
  margin: 0 auto;
}

.demo-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 16px;
}

.file-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.demo-actions {
  text-align: center;
}
</style>
