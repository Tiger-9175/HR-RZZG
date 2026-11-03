# HR-RZZG 任职资格智能评价系统

基于思维链（Chain-of-Thought）技术与大语言模型，对任职资格认证答辩材料进行智能评估。

## 功能特点

- 📊 **多格式支持**：上传 PPT/PPTX、Excel 等多种格式
- 🧠 **AI 智能评价**：基于思维链 + 大模型的深度多维度评估
- 📋 **全面分析**：涵盖基本条件、责任贡献、洞察规划、方案设计、问题解决、创新能力、沟通协调等维度
- 📝 **专业报告**：生成详细的评价报告，含评分、优劣势分析和发展建议
- 📄 **PDF 报告**：一键生成并下载 A4 标准化 PDF 报告（自动归档、可重复下载）
- 🗂️ **评价台账**：所有评价记录入库（SQLite），支持按姓名/专业/等级/结论检索、回看与删除
- 📦 **批量评价**：一次上传多人 PPTX，后台串行排队评价，实时进度与逐人结果
- 🔗 **证据溯源**：每个维度标注「页码 + 原文摘录」，结果页点击直达 PPT 原文，PDF 报告同步呈现
- 🗜️ **报告打包**：整批 / 勾选多条记录一键导出 ZIP
- 📊 **横向对比**：多人维度雷达叠加 + 得分对照表，辅助评委会定档
- 🔁 **评审流转**：AI 已评 → 人工复核 → 终审通过/不通过，记录评审人与意见
- 🔧 **灵活配置**：支持接入内网部署的各种开源大模型
- 🐳 **Docker 部署**：容器化支持，适合企业内网离线环境

## 快速开始

### 1. 环境要求

- Python 3.10+
- Node.js 20+
- Docker & Docker Compose（可选）

### 2. 本地开发

```bash
# 安装后端依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend && npm install

# 启动后端（终端1）
python -m app.main

# 启动前端开发服务器（终端2）
cd frontend && npm run dev
```

访问 http://localhost:3000

### 3. Docker 部署

```bash
# 构建并启动
docker compose build
docker compose up -d

# 查看日志
docker compose logs -f
```

访问 http://localhost:8000

### 4. 配置大模型

系统需要连接一个 OpenAI 兼容的 LLM 服务（内网部署的模型）。
通过系统设置页面或环境变量配置：

- `LLM_BASE_URL`: API 地址，如 http://192.168.1.100:8000/v1
- `LLM_MODEL`: 模型名称，如 qwen2.5-72b-instruct
- `LLM_API_KEY`: API Key

## 评价流程

1. **上传材料**：上传答辩 PPT 和任职资格标准 Excel
2. **信息提取**：自动提取候选人信息和工作成果
3. **门槛核查**：检查是否满足基本条件
4. **维度评分**：逐项评估各维度表现并打分
5. **生成报告**：输出综合评价报告和建议
6. **归档留痕**：评价结果与 PDF 报告入库，可在「历史记录」随时回看和重新下载

## 主要接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 / LLM 配置状态 |
| POST | `/api/upload` | 上传并解析 PPTX / Excel（≤50MB） |
| POST | `/api/evaluate/precheck` | 门槛条件核查（结构化返回） |
| POST | `/api/evaluate` | 执行评价，结果自动入库并返回 `record_id` |
| GET | `/api/evaluations` | 评价记录列表（keyword/profession/candidate_level/passed/分页） |
| GET | `/api/evaluations/{id}` | 评价记录详情（含完整结果与原始材料） |
| DELETE | `/api/evaluations/{id}` | 删除记录及其归档报告 |
| GET | `/api/evaluations/{id}/report` | 下载归档 PDF（首次访问自动生成） |
| GET | `/api/reports/zip?ids=a,b` | 多条记录 PDF 打包下载（ZIP） |
| GET | `/api/batches/{id}/reports.zip` | 整批报告打包下载（ZIP） |
| POST | `/api/report/pdf` | 临时生成 PDF（未入库场景） |
| GET | `/api/stats/overview` | 统计概览（总数/通过率/平均分/报告数/评审状态分布） |
| PATCH | `/api/evaluations/{id}/review` | 评审流转（human_reviewed / final_passed / final_rejected） |
| GET | `/api/compare?ids=a,b` | 多条记录维度对齐对比 |
| POST | `/api/batches` | 批量上传并启动批量评价任务 |
| GET | `/api/batches` `GET /api/batches/{id}` | 批量任务列表 / 详情（含逐人进度） |
| POST | `/api/batches/{id}/cancel` | 取消批量任务 |
| DELETE | `/api/batches/{id}?with_records=true` | 删除批量任务（可选连带删除评价记录） |

数据文件：`data/evaluations.db`（记录与批量任务）、`data/reports/{id}.pdf`（报告归档）、`uploads/batches/{batch_id}/`（批量源文件）。

## 项目结构

```
.
├── app/                    # 后端 Python 代码
│   ├── main.py             # 应用入口
│   ├── api/                # API 路由
│   ├── core/               # 配置、LLM 客户端、SQLite 存储
│   ├── parsers/            # 文件解析器（PPT/Excel）
│   ├── evaluation/         # 评价引擎（思维链 + 标准 + 门槛核查）
│   ├── report/             # PDF 报告生成（reportlab）
│   └── schemas/            # 数据模型
├── frontend/               # 前端 Vue 3 应用
│   ├── src/
│   │   ├── views/          # 页面组件
│   │   ├── router/         # 路由
│   │   └── assets/         # 静态资源
│   └── dist/               # 构建产物
├── demo/                   # 示例数据
├── Dockerfile              # 多阶段构建
├── docker-compose.yml      # Docker 编排
└── requirements.txt        # Python 依赖
```

## 技术栈

- **后端**: FastAPI + Python 3.11
- **前端**: Vue 3 + Element Plus + ECharts
- **AI**: Chain-of-Thought + OpenAI SDK
- **部署**: Docker / Docker Compose
