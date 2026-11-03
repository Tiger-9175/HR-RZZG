<template>
  <div class="home-page">
    <!-- Dynamic Background -->
    <div class="hero-bg">
      <div class="bg-mesh"></div>
      <div class="bg-grid"></div>
      <div class="bg-talent">
        <svg viewBox="0 0 900 500" preserveAspectRatio="xMidYMid slice" class="talent-svg">
          <defs>
            <linearGradient id="flowGrad1" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#1a73e8" stop-opacity="0"/>
              <stop offset="50%" stop-color="#4fc3f7" stop-opacity="0.4"/>
              <stop offset="100%" stop-color="#1a73e8" stop-opacity="0"/>
            </linearGradient>
            <linearGradient id="flowGrad2" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#a78bfa" stop-opacity="0"/>
              <stop offset="50%" stop-color="#8b5cf6" stop-opacity="0.35"/>
              <stop offset="100%" stop-color="#a78bfa" stop-opacity="0"/>
            </linearGradient>
            <radialGradient id="personGlow">
              <stop offset="0%" stop-color="#4fc3f7" stop-opacity="0.6"/>
              <stop offset="100%" stop-color="#4fc3f7" stop-opacity="0"/>
            </radialGradient>
          </defs>

          <!-- Career growth staircase (bottom-left area) -->
          <g opacity="0.35">
            <rect x="60" y="380" width="48" height="6" rx="2" fill="#4fc3f7"/>
            <rect x="90" y="340" width="56" height="6" rx="2" fill="#4fc3f7"/>
            <rect x="120" y="300" width="64" height="6" rx="2" fill="#1a73e8"/>
            <rect x="150" y="260" width="72" height="6" rx="2" fill="#1a73e8"/>
            <rect x="180" y="220" width="80" height="6" rx="2" fill="#8b5cf6"/>
            <line x1="156" y1="385" x2="186" y2="345" stroke="#4fc3f7" stroke-width="1" stroke-dasharray="4,3"/>
            <line x1="190" y1="345" x2="218" y2="305" stroke="#4fc3f7" stroke-width="1" stroke-dasharray="4,3"/>
            <line x1="224" y1="305" x2="248" y2="265" stroke="#1a73e8" stroke-width="1" stroke-dasharray="4,3"/>
            <line x1="258" y1="265" x2="284" y2="225" stroke="#8b5cf6" stroke-width="1" stroke-dasharray="4,3"/>
            <!-- Person on stair step -->
            <circle cx="130" cy="286" r="6" fill="none" stroke="#1a73e8" stroke-width="1.2"/>
            <line x1="130" y1="292" x2="130" y2="304" stroke="#1a73e8" stroke-width="1"/>
            <!-- Person at top -->
            <circle cx="248" cy="210" r="6" fill="none" stroke="#8b5cf6" stroke-width="1.5"/>
            <line x1="248" y1="216" x2="248" y2="226" stroke="#8b5cf6" stroke-width="1"/>
            <animateTransform attributeName="transform" type="translate" values="0,0;0,-3;0,0" dur="4s" repeatCount="indefinite"/>
          </g>

          <!-- Talent organization network (center-right) -->
          <g opacity="0.4">
            <!-- Top manager -->
            <circle cx="520" cy="60" r="10" fill="none" stroke="#4fc3f7" stroke-width="1.5">
              <animate attributeName="stroke-opacity" values="0.4;0.8;0.4" dur="3s" repeatCount="indefinite"/>
            </circle>
            <circle cx="520" cy="56" r="5" fill="#4fc3f7" opacity="0.5">
              <animate attributeName="opacity" values="0.3;0.7;0.3" dur="3s" repeatCount="indefinite"/>
            </circle>
            <line x1="520" y1="66" x2="520" y2="76" stroke="#4fc3f7" stroke-width="1.2"/>
            <!-- Branch lines -->
            <line x1="520" y1="76" x2="440" y2="110" stroke="#4fc3f7" stroke-width="0.8"/>
            <line x1="520" y1="76" x2="600" y2="110" stroke="#4fc3f7" stroke-width="0.8"/>
            <!-- Level 2 people -->
            <circle cx="440" cy="117" r="8" fill="none" stroke="#1a73e8" stroke-width="1.2"/>
            <circle cx="440" cy="113" r="4" fill="#1a73e8" opacity="0.5"/>
            <line x1="440" y1="125" x2="440" y2="134" stroke="#1a73e8" stroke-width="1"/>
            <line x1="440" y1="134" x2="400" y2="160" stroke="#1a73e8" stroke-width="0.7"/>
            <line x1="440" y1="134" x2="480" y2="160" stroke="#1a73e8" stroke-width="0.7"/>
            <circle cx="600" cy="117" r="8" fill="none" stroke="#1a73e8" stroke-width="1.2"/>
            <circle cx="600" cy="113" r="4" fill="#1a73e8" opacity="0.5"/>
            <line x1="600" y1="125" x2="600" y2="134" stroke="#1a73e8" stroke-width="1"/>
            <line x1="600" y1="134" x2="560" y2="160" stroke="#1a73e8" stroke-width="0.7"/>
            <line x1="600" y1="134" x2="640" y2="160" stroke="#1a73e8" stroke-width="0.7"/>
            <!-- Level 3 people -->
            <circle cx="400" cy="168" r="7" fill="none" stroke="#a78bfa" stroke-width="1"/>
            <circle cx="400" cy="164" r="3.5" fill="#a78bfa" opacity="0.5"/>
            <circle cx="480" cy="168" r="7" fill="none" stroke="#a78bfa" stroke-width="1"/>
            <circle cx="480" cy="164" r="3.5" fill="#a78bfa" opacity="0.5"/>
            <circle cx="560" cy="168" r="7" fill="none" stroke="#a78bfa" stroke-width="1"/>
            <circle cx="560" cy="164" r="3.5" fill="#a78bfa" opacity="0.5"/>
            <circle cx="640" cy="168" r="7" fill="none" stroke="#a78bfa" stroke-width="1"/>
            <circle cx="640" cy="164" r="3.5" fill="#a78bfa" opacity="0.5"/>
            <!-- Person row animation -->
            <animateTransform attributeName="transform" type="translate" values="0,0;0,-6;0,0" dur="5s" repeatCount="indefinite" begin="2s"/>
          </g>

          <!-- Talent evaluation radar rings (right-center area) -->
          <g transform="translate(760, 300)" opacity="0.3">
            <circle cx="0" cy="0" r="20" fill="none" stroke="#4fc3f7" stroke-width="1">
              <animate attributeName="r" values="16;20;16" dur="3s" repeatCount="indefinite"/>
              <animate attributeName="opacity" values="0.15;0.4;0.15" dur="3s" repeatCount="indefinite"/>
            </circle>
            <circle cx="0" cy="0" r="35" fill="none" stroke="#1a73e8" stroke-width="0.8">
              <animate attributeName="r" values="30;36;30" dur="4s" repeatCount="indefinite"/>
              <animate attributeName="opacity" values="0.1;0.3;0.1" dur="4s" repeatCount="indefinite"/>
            </circle>
            <circle cx="0" cy="0" r="50" fill="none" stroke="#8b5cf6" stroke-width="0.6">
              <animate attributeName="r" values="45;52;45" dur="5s" repeatCount="indefinite"/>
              <animate attributeName="opacity" values="0.08;0.22;0.08" dur="5s" repeatCount="indefinite"/>
            </circle>
            <!-- Radar axes -->
            <line x1="0" y1="-52" x2="0" y2="52" stroke="#4fc3f7" stroke-width="0.4" opacity="0.3"/>
            <line x1="-52" y1="0" x2="52" y2="0" stroke="#4fc3f7" stroke-width="0.4" opacity="0.3"/>
            <line x1="-37" y1="-37" x2="37" y2="37" stroke="#4fc3f7" stroke-width="0.4" opacity="0.2"/>
            <line x1="37" y1="-37" x2="-37" y2="37" stroke="#4fc3f7" stroke-width="0.4" opacity="0.2"/>
            <!-- Center star -->
            <polygon points="0,-8 2,-3 7,-3 3,1 5,6 0,3 -5,6 -3,1 -7,-3 -2,-3" fill="#4fc3f7" opacity="0.5">
              <animate attributeName="opacity" values="0.2;0.6;0.2" dur="2s" repeatCount="indefinite"/>
            </polygon>
          </g>

          <!-- Talent pipeline / flow tracks (subtle horizontal curves) -->
          <g opacity="0.2">
            <path d="M 0,80 Q 200,40 400,80 T 900,60" fill="none" stroke="url(#flowGrad1)" stroke-width="1.5" stroke-dasharray="6,100 40,60">
              <animate attributeName="stroke-dashoffset" from="0" to="-300" dur="8s" repeatCount="indefinite"/>
            </path>
            <path d="M 0,200 Q 250,170 500,200 T 900,180" fill="none" stroke="url(#flowGrad2)" stroke-width="1.2" stroke-dasharray="5,80 30,50">
              <animate attributeName="stroke-dashoffset" from="0" to="-300" dur="10s" repeatCount="indefinite"/>
            </path>
          </g>

          <!-- Achievement stars (scattered sparkles) -->
          <g opacity="0.35">
            <text x="320" y="95" font-size="12" fill="#4fc3f7" opacity="0.5">✦</text>
            <text x="700" y="240" font-size="10" fill="#1a73e8" opacity="0.4">✦</text>
            <text x="530" y="40" font-size="14" fill="#a78bfa" opacity="0.5">✦</text>
            <text x="380" y="360" font-size="8" fill="#4fc3f7" opacity="0.3">✦</text>
            <text x="820" y="160" font-size="11" fill="#1a73e8" opacity="0.4">✦</text>
            <text x="200" y="150" font-size="9" fill="#f97316" opacity="0.3">★</text>
            <text x="680" y="380" font-size="10" fill="#f97316" opacity="0.3">★</text>
            <text x="100" y="280" font-size="12" fill="#4fc3f7" opacity="0.3">✦</text>
          </g>

          <!-- Evaluation score indicator (bottom-right) -->
          <g transform="translate(800, 440)" opacity="0.25">
            <rect x="-24" y="-14" width="48" height="28" rx="6" fill="none" stroke="#1a73e8" stroke-width="1"/>
            <text x="0" y="4" text-anchor="middle" font-size="9" fill="#1a73e8" font-weight="600">A+</text>
            <animate attributeName="opacity" values="0.15;0.35;0.15" dur="2.5s" repeatCount="indefinite"/>
          </g>
        </svg>
      </div>
    </div>

    <!-- Hero Section -->
    <div class="hero-section">
      <div class="hero-content">
        <h1 class="hero-title">
          <el-icon :size="40" color="#4fc3f7"><TrendCharts /></el-icon>
          任职资格智能评价系统
        </h1>
        <p class="hero-subtitle">
          基于思维链（Chain-of-Thought）技术与大语言模型，<br/>
          对任职资格认证答辩材料进行智能、客观、全面的评估
        </p>
        <div class="hero-actions">
          <el-button type="primary" size="large" round @click="$router.push('/evaluate')">
            <el-icon><Upload /></el-icon>
            开始评价
          </el-button>
          <el-button size="large" round @click="$router.push('/demo')">
            <el-icon><FolderOpened /></el-icon>
            查看示例
          </el-button>
        </div>
      </div>
      <div class="hero-illustration">
        <div class="floating-cards">
          <div class="float-card card-1">
            <el-icon :size="24" color="#34a853"><Document /></el-icon>
            <span>上传PPT</span>
          </div>
          <div class="float-card card-2">
            <el-icon :size="24" color="#1a73e8"><Cpu /></el-icon>
            <span>AI推理</span>
          </div>
          <div class="float-card card-3">
            <el-icon :size="24" color="#f97316"><DataAnalysis /></el-icon>
            <span>生成报告</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Features -->
    <div class="features-section">
      <h2 class="section-title">核心功能</h2>
      <div class="features-grid">
        <div class="feature-card hover-card" v-for="f in features" :key="f.title">
          <div class="feature-icon" :style="{ background: f.bg }">
            <el-icon :size="24" color="#fff">
              <component :is="f.icon" />
            </el-icon>
          </div>
          <h3 class="feature-title">{{ f.title }}</h3>
          <p class="feature-desc">{{ f.desc }}</p>
        </div>
      </div>
    </div>

    <!-- Workflow -->
    <div class="workflow-section">
      <h2 class="section-title">评价流程</h2>
      <el-steps :active="5" align-center class="workflow-steps">
        <el-step title="上传材料" description="上传答辩PPT和任职资格标准" />
        <el-step title="信息提取" description="自动提取候选人信息和工作成果" />
        <el-step title="门槛核查" description="检查是否满足基本条件" />
        <el-step title="维度评分" description="逐项评估各维度表现并打分" />
        <el-step title="生成报告" description="输出综合评价报告和建议" />
      </el-steps>
    </div>
  </div>
</template>

<script setup>
const features = [
  {
    icon: 'Upload',
    title: '多格式支持',
    desc: '支持上传 PPT/PPTX、Excel 等多种格式的答辩材料和标准文件',
    bg: 'linear-gradient(135deg, #1a73e8, #4a90d9)',
  },
  {
    icon: 'Cpu',
    title: 'AI智能评价',
    desc: '基于思维链技术，结合大语言模型进行深度、客观的多维度评估',
    bg: 'linear-gradient(135deg, #34a853, #66bb6a)',
  },
  {
    icon: 'DataAnalysis',
    title: '全面分析',
    desc: '覆盖基本条件、责任贡献、规划能力、方案设计、问题解决等多个维度',
    bg: 'linear-gradient(135deg, #f97316, #fb923c)',
  },
  {
    icon: 'Document',
    title: '专业报告',
    desc: '生成详细的评价报告，包含评分、优劣势分析和发展建议',
    bg: 'linear-gradient(135deg, #8b5cf6, #a78bfa)',
  },
  {
    icon: 'Setting',
    title: '灵活配置',
    desc: '可配置LLM接口地址，支持接入内网部署的各种大语言模型',
    bg: 'linear-gradient(135deg, #ec4899, #f472b6)',
  },
  {
    icon: 'Connection',
    title: '离线部署',
    desc: '支持 Docker 容器化部署，适合企业内部离线环境使用',
    bg: 'linear-gradient(135deg, #14b8a6, #2dd4bf)',
  },
]
</script>

<style scoped>
.home-page {
  max-width: 1200px;
  margin: 0 auto;
  position: relative;
}

/* ============ Dynamic Background ============ */
.hero-bg {
  position: absolute;
  top: -80px;
  left: -200px;
  right: -200px;
  height: 600px;
  overflow: hidden;
  z-index: 0;
  pointer-events: none;
}

/* Animated mesh gradient */
.bg-mesh {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 60% 50% at 20% 30%, rgba(79, 195, 247, 0.12) 0%, transparent 60%),
    radial-gradient(ellipse 50% 60% at 75% 20%, rgba(26, 115, 232, 0.10) 0%, transparent 60%),
    radial-gradient(ellipse 50% 50% at 50% 70%, rgba(139, 92, 246, 0.08) 0%, transparent 50%),
    radial-gradient(ellipse 40% 40% at 85% 80%, rgba(79, 195, 247, 0.06) 0%, transparent 50%);
  animation: meshShift 12s ease-in-out infinite alternate;
}

/* Subtle grid pattern overlay */
.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(79, 195, 247, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(79, 195, 247, 0.04) 1px, transparent 1px);
  background-size: 60px 60px;
  opacity: 0.6;
}

@keyframes meshShift {
  0% {
    background:
      radial-gradient(ellipse 60% 50% at 20% 30%, rgba(79, 195, 247, 0.12) 0%, transparent 60%),
      radial-gradient(ellipse 50% 60% at 75% 20%, rgba(26, 115, 232, 0.10) 0%, transparent 60%),
      radial-gradient(ellipse 50% 50% at 50% 70%, rgba(139, 92, 246, 0.08) 0%, transparent 50%),
      radial-gradient(ellipse 40% 40% at 85% 80%, rgba(79, 195, 247, 0.06) 0%, transparent 50%);
  }
  100% {
    background:
      radial-gradient(ellipse 60% 50% at 30% 25%, rgba(26, 115, 232, 0.12) 0%, transparent 60%),
      radial-gradient(ellipse 50% 60% at 65% 30%, rgba(79, 195, 247, 0.10) 0%, transparent 60%),
      radial-gradient(ellipse 50% 50% at 40% 65%, rgba(20, 184, 166, 0.08) 0%, transparent 50%),
      radial-gradient(ellipse 40% 40% at 80% 75%, rgba(139, 92, 246, 0.06) 0%, transparent 50%);
  }
}

/* Talent-themed SVG background */
.bg-talent {
  position: absolute;
  inset: 0;
}

.talent-svg {
  width: 100%;
  height: 100%;
  opacity: 0.55;
}

/* ============ Hero Section ============ */
.hero-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 30px 0 20px;
  gap: 40px;
  position: relative;
  z-index: 1;
}

.hero-content {
  flex: 1;
}

.hero-title {
  font-size: 34px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.hero-subtitle {
  font-size: 17px;
  color: #6b7280;
  line-height: 1.7;
  margin-bottom: 24px;
}

.hero-actions {
  display: flex;
  gap: 16px;
}

.hero-illustration {
  flex: 0 0 300px;
  height: 300px;
  position: relative;
}

.floating-cards {
  position: relative;
  width: 100%;
  height: 100%;
}

.float-card {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  font-weight: 500;
  animation: float 3s ease-in-out infinite;
}

.card-1 { top: 20%; left: 10%; animation-delay: 0s; }
.card-2 { top: 50%; left: 30%; animation-delay: 0.5s; }
.card-3 { top: 30%; left: 50%; animation-delay: 1s; }

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.section-title {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  text-align: center;
  margin-bottom: 24px;
}

.features-section {
  padding: 24px 0 16px;
}

.workflow-section {
  padding: 24px 0 40px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.feature-card {
  background: #fff;
  border-radius: 16px;
  padding: 32px 24px;
  text-align: center;
  cursor: default;
}

.feature-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.feature-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #1f2937;
}

.feature-desc {
  font-size: 14px;
  color: #6b7280;
  line-height: 1.6;
}

.workflow-steps {
  margin-top: 20px;
}

@media (max-width: 768px) {
  .hero-section { flex-direction: column; padding: 30px 0; }
  .hero-illustration { display: none; }
  .features-grid { grid-template-columns: 1fr; }
}
</style>
