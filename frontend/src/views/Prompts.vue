<template>
  <div class="prompts-page">
    <el-card shadow="never" class="card">
      <template #header>
        <div class="card-header">
          <span class="card-title"><el-icon><EditPen /></el-icon> 提示词模板</span>
          <div class="header-actions">
            <span v-if="updatedAt" class="updated">上次保存：{{ updatedAt.replace('T', ' ') }}</span>
            <el-button size="small" @click="previewVisible = true">
              <el-icon><View /></el-icon> 预览最终提示词
            </el-button>
            <el-button size="small" type="danger" plain @click="resetAll">恢复默认</el-button>
          </div>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="模板修改后立即生效，无需重启服务；仅覆盖你保存的字段，未修改的字段继续使用内置默认值。"
        class="tip"
      />

      <div class="layout">
        <div class="side">
          <el-menu :default-active="current" class="tpl-menu" @select="selectTemplate">
            <el-menu-item v-for="(meta, key) in meta" :key="key" :index="key">
              <span class="menu-label">{{ meta.label }}</span>
              <el-tag v-if="isOverridden(key)" size="small" type="warning" effect="plain">已改</el-tag>
            </el-menu-item>
          </el-menu>
        </div>

        <div class="editor" v-if="meta[current]">
          <div class="editor-head">
            <div>
              <div class="editor-title">{{ meta[current].label }}</div>
              <div class="editor-desc">{{ meta[current].desc }}</div>
            </div>
            <div class="editor-actions">
              <el-button size="small" :disabled="!isDirty" type="primary" :loading="saving" @click="saveCurrent">
                保存当前模板
              </el-button>
              <el-button size="small" :disabled="!isOverridden(current)" @click="restoreCurrent">
                还原为默认
              </el-button>
            </div>
          </div>

          <div v-if="variables[current]?.length" class="vars">
            <span class="vars-label">可用变量：</span>
            <el-tag
              v-for="v in variables[current]"
              :key="v"
              size="small"
              effect="plain"
              class="var-tag"
              @click="insertVariable(v)"
            >{{ varLabel(v) }}</el-tag>
            <span class="vars-hint">（点击插入到光标处）</span>
          </div>

          <el-input
            ref="editorRef"
            v-model="draft"
            type="textarea"
            :rows="20"
            resize="vertical"
            class="textarea"
            placeholder="在此编辑模板内容…"
          />
          <div class="counter">
            字符数：{{ draft.length }} <span v-if="isDirty" class="dirty">· 有未保存修改</span>
          </div>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="previewVisible" title="最终提示词预览" width="900px" top="4vh">
      <el-form inline>
        <el-form-item label="标准">
          <el-select v-model="previewForm.standard_filename" style="width: 260px">
            <el-option v-for="s in standards" :key="s.filename" :label="s.filename" :value="s.filename" />
          </el-select>
        </el-form-item>
        <el-form-item label="等级">
          <el-select v-model="previewForm.candidate_level" style="width: 110px">
            <el-option v-for="l in levels" :key="l" :label="l" :value="l" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="previewing" @click="doPreview">生成预览</el-button>
        </el-form-item>
      </el-form>
      <div v-if="previewText" class="preview-meta">共 {{ previewText.length }} 字符</div>
      <pre class="preview-box">{{ previewText || '点击“生成预览”查看渲染后的完整提示词' }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const levels = ['一级', '二级', '三级', '四级', '五级', '六级']

const templates = ref({})
const defaults = ref({})
const meta = ref({})
const variables = ref({})
const overridden = ref([])
const updatedAt = ref('')
const current = ref('system_prompt')
const draft = ref('')
const saving = ref(false)
const editorRef = ref(null)

const previewVisible = ref(false)
const previewing = ref(false)
const previewText = ref('')
const previewForm = ref({ standard_filename: '', candidate_level: '三级' })
const standards = ref([])

const isDirty = computed(() => draft.value !== (templates.value[current.value] || ''))

function isOverridden(key) {
  return overridden.value.includes(key)
}

// Built character by character: a literal "{{...}}" inside a Vue template
// expression would terminate the interpolation.
function varLabel(name) {
  return '{' + '{' + name + '}' + '}'
}

function selectTemplate(key) {
  if (isDirty.value) {
    // keep it simple: discard unsaved edits on switch, but warn
    ElMessage.warning('切换模板，未保存的修改已丢弃')
  }
  current.value = key
  draft.value = templates.value[key] || ''
}

async function load() {
  try {
    const res = await axios.get('/api/prompts')
    applyInfo(res.data)
  } catch (e) {
    ElMessage.error('加载提示词模板失败: ' + (e.response?.data?.detail || e.message))
  }
}

function applyInfo(data) {
  templates.value = data.templates || {}
  defaults.value = data.defaults || {}
  meta.value = data.meta || {}
  variables.value = data.variables || {}
  overridden.value = data.overridden || []
  updatedAt.value = data.updated_at || ''
  if (!templates.value[current.value]) {
    current.value = Object.keys(meta.value)[0] || 'system_prompt'
  }
  draft.value = templates.value[current.value] || ''
}

async function saveCurrent() {
  saving.value = true
  try {
    const res = await axios.put('/api/prompts', {
      templates: { [current.value]: draft.value },
    })
    applyInfo(res.data)
    ElMessage.success('模板已保存，下次评价生效')
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

async function restoreCurrent() {
  draft.value = defaults.value[current.value] || ''
  try {
    const res = await axios.put('/api/prompts', { templates: { [current.value]: draft.value } })
    applyInfo(res.data)
    draft.value = templates.value[current.value] || ''
    ElMessage.success('已还原为默认内容')
  } catch (e) {
    ElMessage.error('还原失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function resetAll() {
  try {
    await ElMessageBox.confirm('恢复默认将清除所有自定义模板，确定继续？', '恢复默认',
      { type: 'warning', confirmButtonText: '恢复', cancelButtonText: '取消' })
  } catch {
    return
  }
  try {
    const res = await axios.post('/api/prompts/reset')
    applyInfo(res.data)
    ElMessage.success('已恢复默认提示词')
  } catch (e) {
    ElMessage.error('恢复失败: ' + (e.response?.data?.detail || e.message))
  }
}

function insertVariable(name) {
  const textarea = editorRef.value?.textarea
  const token = `{{${name}}}`
  if (!textarea) {
    draft.value += token
    return
  }
  const start = textarea.selectionStart ?? draft.value.length
  const end = textarea.selectionEnd ?? draft.value.length
  draft.value = draft.value.slice(0, start) + token + draft.value.slice(end)
  nextTick(() => {
    textarea.focus()
    textarea.setSelectionRange(start + token.length, start + token.length)
  })
}

async function doPreview() {
  previewing.value = true
  try {
    const res = await axios.post('/api/prompts/preview', previewForm.value)
    previewText.value = res.data.prompt
  } catch (e) {
    ElMessage.error('预览失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    previewing.value = false
  }
}

async function loadStandards() {
  try {
    const res = await axios.get('/api/demo/standards')
    standards.value = res.data.standards || []
    if (standards.value.length) previewForm.value.standard_filename = standards.value[0].filename
  } catch {
    // non-blocking
  }
}

onMounted(() => {
  load()
  loadStandards()
})
</script>

<style scoped>
.prompts-page {
  max-width: 1280px;
  margin: 0 auto;
}

.card {
  border-radius: 12px;
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
  gap: 8px;
}

.updated {
  font-size: 12px;
  color: #9ca3af;
}

.tip {
  margin-bottom: 12px;
}

.layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.side {
  width: 240px;
  flex-shrink: 0;
  border-right: 1px solid #eef1f5;
}

.tpl-menu {
  border-right: none;
}

.menu-label {
  flex: 1;
  font-size: 13px;
  white-space: normal;
  line-height: 1.4;
}

.editor {
  flex: 1;
  min-width: 0;
}

.editor-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
}

.editor-title {
  font-weight: 600;
  color: #1f2937;
}

.editor-desc {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 2px;
  line-height: 1.5;
}

.editor-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.vars {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.vars-label {
  font-size: 12px;
  color: #6b7280;
}

.var-tag {
  cursor: pointer;
  font-family: Consolas, Monaco, monospace;
}

.vars-hint {
  font-size: 12px;
  color: #c0c4cc;
}

.textarea :deep(textarea) {
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 12.5px;
  line-height: 1.7;
}

.counter {
  margin-top: 6px;
  font-size: 12px;
  color: #9ca3af;
}

.dirty {
  color: #f97316;
}

.preview-meta {
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 6px;
}

.preview-box {
  max-height: 62vh;
  overflow: auto;
  background: #fafbfc;
  border: 1px solid #eef1f5;
  border-radius: 8px;
  padding: 12px;
  font-size: 12px;
  line-height: 1.7;
  white-space: pre-wrap;
  color: #374151;
}
</style>
