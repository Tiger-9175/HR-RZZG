<template>
  <el-container class="app-container">
    <!-- Sidebar -->
    <el-aside :width="isCollapse ? '64px' : '240px'" class="app-sidebar">
      <div class="sidebar-header">
        <div class="logo">
          <el-icon :size="28" color="#fff">
            <TrendCharts />
          </el-icon>
          <span v-show="!isCollapse" class="logo-text">昌飞任职资格智能评价系统</span>
        </div>
      </div>

      <el-menu
        :default-active="route.path"
        :collapse="isCollapse"
        :router="true"
        background-color="#1a1a2e"
        text-color="#a0aec0"
        active-text-color="#4fc3f7"
        class="sidebar-menu"
      >
        <el-menu-item index="/">
          <el-icon><HomeFilled /></el-icon>
          <template #title>首页</template>
        </el-menu-item>
        <el-menu-item index="/evaluate">
          <el-icon><Document /></el-icon>
          <template #title>开始评价</template>
        </el-menu-item>
        <el-menu-item index="/batch">
          <el-icon><Files /></el-icon>
          <template #title>批量评价</template>
        </el-menu-item>
        <el-menu-item index="/history">
          <el-icon><Clock /></el-icon>
          <template #title>历史记录</template>
        </el-menu-item>
        <el-menu-item index="/demo">
          <el-icon><FolderOpened /></el-icon>
          <template #title>示例数据</template>
        </el-menu-item>
        <el-menu-item index="/prompts">
          <el-icon><EditPen /></el-icon>
          <template #title>提示词模板</template>
        </el-menu-item>
        <el-menu-item index="/regression">
          <el-icon><Odometer /></el-icon>
          <template #title>质量回归</template>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <template #title>系统设置</template>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-footer">
        <el-button
          :icon="isCollapse ? 'Expand' : 'Fold'"
          text
          bg
          size="small"
          @click="isCollapse = !isCollapse"
          class="collapse-btn"
        >
          <template v-if="!isCollapse">收起</template>
        </el-button>
      </div>
    </el-aside>

    <!-- Main content -->
    <el-container class="main-container">
      <!-- Header -->
      <el-header class="app-header">
        <div class="header-left">
          <h2 class="page-title">{{ pageTitle }}</h2>
        </div>
        <div class="header-right">
          <el-tag v-if="llmStatus" :type="llmStatus.connected ? 'success' : 'danger'" size="small" effect="dark">
            <el-icon style="vertical-align: middle; margin-right: 4px;">
              <Connection />
            </el-icon>
            {{ llmStatus.connected ? 'LLM已连接' : 'LLM未连接' }}
          </el-tag>
          <el-tag type="info" size="small" effect="plain" style="margin-left: 8px;">
            v1.0.0
          </el-tag>
        </div>
      </el-header>

      <!-- Content -->
      <el-main class="app-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const router = useRouter()
const isCollapse = ref(false)
const llmStatus = ref(null)

const pageTitles = {
  '/': '首页',
  '/evaluate': '开始评价',
  '/result': '评价结果',
  '/history': '历史记录',
  '/batch': '批量评价',
  '/compare': '横向对比',
  '/prompts': '提示词模板',
  '/regression': '质量回归',
  '/settings': '系统设置',
  '/demo': '示例数据',
}

const pageTitle = computed(() => {
  return pageTitles[route.path] || '昌飞任职资格智能评价系统'
})

async function checkLLMStatus() {
  try {
    const res = await axios.get('/api/health')
    llmStatus.value = {
      connected: res.data.llm_configured,
      model: res.data.llm_model,
      url: res.data.llm_base_url,
    }
  } catch {
    llmStatus.value = { connected: false, model: '-', url: '-' }
  }
}

onMounted(() => {
  checkLLMStatus()
})

// Re-check LLM status on every route change so it stays in sync
// after user configures in Settings page
router.afterEach(() => {
  checkLLMStatus()
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
}

.app-sidebar {
  background: #1a1a2e;
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  overflow: hidden;
  position: sticky;
  top: 0;
  height: 100vh;
  z-index: 10;
}

.sidebar-header {
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-text {
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
}

.sidebar-menu {
  flex: 1;
  border-right: none !important;
}

.sidebar-menu .el-menu-item {
  margin: 4px 8px;
  border-radius: 8px;
}

.sidebar-menu .el-menu-item.is-active {
  background: rgba(79, 195, 247, 0.15) !important;
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.collapse-btn {
  width: 100%;
  color: #a0aec0;
}

.main-container {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 60px;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.app-main {
  flex: 1;
  padding: 24px;
  background: #f0f2f5;
}
</style>
