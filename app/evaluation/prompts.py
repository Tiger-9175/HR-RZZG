"""Configurable prompt templates.

Templates live in ``data/prompt_templates.json`` so scoring口径 can be tuned
without touching code. Missing keys fall back to the built-in defaults, which
reproduce the original hard-coded prompts.

Placeholders use ``{{name}}`` syntax (rendered with a regex, not ``str.format``)
so JSON braces inside templates stay untouched.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

FILENAME = "prompt_templates.json"

# ------------------------------------------------------------------ default ----
DEFAULT_SYSTEM_PROMPT = """# 角色定位

你是"任职资格智能评价专家"，服务于国内大型制造企业的任职资格认证工作。

## 专业背景

1. 精通人力资源管理中的任职资格管理体系，熟悉能力模型构建、评价标准制定和认证流程
2. 掌握制造业/工程技术领域的专业能力评价方法，能够准确评估候选人的技术水平和贡献
3. 熟悉从一级到六级的任职资格等级体系，理解各级别的核心能力要求差异：
  - 一级（入门）：在指导下完成基础技术工作
  - 二级（独立）：能够独立完成专业技术工作
  - 三级（骨干）：能够独立承担单位级技术工作
  - 四级（专家）：能够主导专业级技术工作
  - 五级（高级专家）：能够主导公司级重大技术工作
  - 六级（首席专家）：能够解决战略级核心技术问题

## 评价原则

1. **客观公正**：基于事实和证据进行评价，不主观臆断
2. **标准对齐**：严格对照提供的任职资格标准进行评分
3. **举证为本**：评分必须有候选人的举证材料支撑，无举证不评分
4. **全面覆盖**：覆盖所有评价维度，不遗漏
5. **发展导向**：评价目的不仅是判定是否通过，更要帮助候选人成长

## 评价方法

采用思维链（Chain-of-Thought）技术，按以下步骤系统化评估：
1. 信息提取 → 全面获取候选人工作和成果信息
2. 门槛核查 → 确认是否满足基本条件（不满足则直接否决）
3. 维度评分 → 对照标准逐一评估各维度并打分
4. 综合判定 → 加权汇总后判定是否通过
5. 生成报告 → 输出详细评价意见和建议

请严格按照标准执行评价，确保评价结果准确、可信、有建设性。"""

DEFAULT_EVIDENCE_RULES = """## ⚠️ 证据溯源要求（强制执行）

候选人的答辩材料以 `## 幻灯片 N` 分段，**N 就是页码**。每个维度（责任贡献除外）必须输出 `evidence` 数组：

1. `page`：整数页码，必须真实存在于材料中（就是对应 `## 幻灯片 N` 的 N）
2. `quote`：从该页原文**逐字摘录**的关键句，不超过 120 字，不得改写、不得编造
3. `note`：这条证据支撑了该维度的哪一项能力要求

规则：
- 每个维度至少 1 条证据；能力越强的结论需要越多证据支撑
- 若材料中没有有效举证，`evidence` 输出空数组，并在 `comments` 中写明"材料未提供有效举证"，该维度不得给达标以上分数
- 严禁编造原文；无法确定页码时宁可少给一条，也不要虚构"""

DEFAULT_OUTPUT_SCHEMA = """请严格按照以下JSON格式输出评价结果：

```json
{
  "candidate": {
    "name": "姓名",
    "department": "部门",
    "applied_level": "申报等级",
    "current_level": "当前等级",
    "years_of_experience": "工作年限",
    "performance_last_two_years": "近两年绩效",
    "professional_title": "职称"
  },
  "threshold_check": {
    "performance": {"status": "✅满足/❌不满足/⚠️部分满足", "detail": "说明"},
    "professional_title": {"status": "✅满足/❌不满足/⚠️部分满足", "detail": "说明"},
    "work_years": {"status": "✅满足/❌不满足/⚠️部分满足", "detail": "说明"},
    "organization_contribution": {"status": "✅满足/❌不满足/⚠️部分满足", "detail": "说明"},
    "overall_pass": true
  },
  "dimensions": [
    {
      "name": "维度名称",
      "full_score": 满分值,
      "threshold": 达标值,
      "score": 得分,
      "score_percentage": 得分百分比,
      "comments": "评价意见",
      "details": "详细评分依据和理由",
      "evidence": [
        {"page": 5, "quote": "该页原文摘录（逐字）", "note": "支撑了哪项能力要求"}
      ]
    }
  ],
  "total_score": 总分,
  "total_full_score": 满分合计,
  "total_percentage": 总百分比,
  "passed": true,
  "chain_of_thought": "完整的推理过程",
  "summary": "综合评价总结",
  "strengths": ["优势1", "优势2"],
  "improvements": ["待改进1", "待改进2"],
  "suggestions": "发展建议"
}
```

注意：维度名称必须与上述权重分配中的维度名完全一致，满分和达标值严格按标准填写。"""

DEFAULT_DIMENSION_INSTRUCTION = """{{dim_index}}. **{{dim_name}}**
   - 对照标准中的具体要求逐条评价
   - 基于候选人的举证材料判断达成程度
   - 严格按评分规则给出分数（满分和达标值参考权重和评分细则）
   - 给出详细的评分依据
   - ⚠️ 必须给出 `evidence` 证据引用（页码 + 原文摘录），至少 1 条"""

DEFAULT_MANUAL_DIMENSION_INSTRUCTION = """{{dim_index}}. **{{dim_name}}**（⚠️ 手动评分，不需要AI评价）
   - 此维度已由人工评委手动打分，得分为 **{{responsibility_score}}分（满分30分）**
   - 请在输出的JSON中直接使用这个分数，不需要AI重新评分
   - 评价意见字段填写："此项由人工评委打分，得分{{responsibility_score}}分" """

DEFAULT_EVALUATION_TEMPLATE = """你是一位专业的任职资格评价专家。请基于以下{{profession}}专业的任职资格标准，对候选人的答辩PPT材料进行严谨、客观的评价。

## ⚠️ 重要：手动评分项

本系统不涉及责任贡献/责任结果的AI评价，此项已由人工评委手动打分：

**手动打分：{{responsibility_score}} / 30 分**

请在输出JSON中直接使用此分数作为责任贡献维度的score，评价意见填写"此项由人工评委打分"。你只需对除责任贡献外的其他维度进行AI评价打分。

## 专业标准（{{profession}}）

{{raw_standard}}

{{threshold_section}}

{{weights_section}}

{{rules_section}}

## 候选人答辩材料

{{ppt_content}}

## 评价要求

申报等级：{{candidate_level}}级

请按照以下思维链步骤进行评价：

### 步骤1：信息提取
从材料中提取候选人的以下信息：
- 姓名、部门、申报等级、当前等级
- 工作经历和年限
- 近两年绩效结果
- 职称和职业资格
- 所有举证的工作成果和项目经历（这是评分的关键依据）

### 步骤2：门槛条件核查
逐一检查候选人是否满足申报等级的门槛条件（绩效、职业资格、工作年限、组织回馈）。
对于每个条件：✅满足 / ❌不满足 / ⚠️部分满足，并说明具体依据。

### 步骤3：分维度深度评估
{{dim_instructions}}

### 步骤4：综合评分与等级判定
1. 汇总各维度得分，计算总分
2. 对比申报等级的达标值
3. 综合判断是否通过评价（门槛条件全部满足 + 总分达标）

### 步骤5：评价总结
- 综合评价意见
- 核心优势（3-5点）
- 待改进方面（2-4点）
- 发展建议

{{material_rules}}

## 输出格式要求

{{output_schema}}"""

DEFAULT_PRECHECK_PROMPT = """你是任职资格评审专家。请依据候选人的答辩材料，逐条判断其是否满足
{{profession}}专业 {{candidate_level}}级的门槛（基本）条件。

## 门槛条件
{{requirements}}

## 候选人答辩材料
{{ppt_content}}

## 输出要求
只输出 JSON 数组，不要任何解释，格式：
[{"field": "performance", "required": "标准要求（简短）", "status": "✅满足/⚠️部分满足/❌不满足", "detail": "判断依据，引用材料中的事实"}]
必须覆盖上面列出的每一个 field。"""

DEFAULTS: dict[str, str] = {
    "system_prompt": DEFAULT_SYSTEM_PROMPT,
    "evaluation_template": DEFAULT_EVALUATION_TEMPLATE,
    "dimension_instruction": DEFAULT_DIMENSION_INSTRUCTION,
    "manual_dimension_instruction": DEFAULT_MANUAL_DIMENSION_INSTRUCTION,
    "evidence_rules": DEFAULT_EVIDENCE_RULES,
    "output_schema": DEFAULT_OUTPUT_SCHEMA,
    "precheck_prompt": DEFAULT_PRECHECK_PROMPT,
}

# Human readable metadata for the editor UI
TEMPLATE_META = {
    "system_prompt": {"label": "系统提示词", "desc": "设定模型角色、评价原则与评价方法，每次评价都会作为 system 消息发送"},
    "evaluation_template": {
        "label": "评价主模板",
        "desc": "整份评价请求的主体，可用变量见下方说明；留空的关键区块会导致评价结果缺项",
    },
    "dimension_instruction": {"label": "维度评价要求（AI 评分维度）", "desc": "逐维度重复渲染，可用 {{dim_index}} {{dim_name}}"},
    "manual_dimension_instruction": {"label": "人工评分维度要求", "desc": "责任贡献等人工项，可用 {{dim_index}} {{dim_name}} {{responsibility_score}}"},
    "evidence_rules": {"label": "证据溯源要求", "desc": "约束模型输出页码+原文证据的规则段落"},
    "output_schema": {"label": "输出格式（JSON Schema）", "desc": "必须与后端解析字段保持一致，谨慎修改字段名"},
    "precheck_prompt": {"label": "门槛核查提示词", "desc": "可用 {{profession}} {{candidate_level}} {{requirements}} {{ppt_content}}"},
}

VARIABLES = {
    "evaluation_template": [
        "profession", "raw_standard", "threshold_section", "weights_section",
        "rules_section", "ppt_content", "candidate_level", "dim_instructions",
        "material_rules", "output_schema", "responsibility_score",
    ],
    "dimension_instruction": ["dim_index", "dim_name"],
    "manual_dimension_instruction": ["dim_index", "dim_name", "responsibility_score"],
    "precheck_prompt": ["profession", "candidate_level", "requirements", "ppt_content"],
}

_PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def render(template: str, values: dict[str, Any]) -> str:
    """Replace ``{{name}}`` placeholders; unknown ones are left untouched."""
    def _sub(match: re.Match) -> str:
        key = match.group(1)
        if key in values and values[key] is not None:
            return str(values[key])
        return match.group(0)

    return _PLACEHOLDER.sub(_sub, template or "")


# --------------------------------------------------------------- persistence ----
def config_path() -> str:
    return os.path.join(settings.data_dir, FILENAME)


def load_templates() -> dict[str, str]:
    """Merged view of defaults + user overrides."""
    templates = dict(DEFAULTS)
    path = config_path()
    if not os.path.exists(path):
        return templates
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, value in (data.get("templates") or {}).items():
            if key in DEFAULTS and isinstance(value, str) and value.strip():
                templates[key] = value
    except Exception as exc:  # pragma: no cover - corrupted file
        logger.warning("Failed to load prompt templates: %s", exc)
    return templates


def save_templates(templates: dict[str, str]) -> dict:
    """Persist overrides (unknown keys are ignored)."""
    cleaned = {k: v for k, v in (templates or {}).items()
               if k in DEFAULTS and isinstance(v, str) and v.strip()}
    payload = {
        "updated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "templates": cleaned,
    }
    os.makedirs(settings.data_dir, exist_ok=True)
    with open(config_path(), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info("Saved %d prompt template override(s)", len(cleaned))
    return payload


def reset_templates() -> None:
    path = config_path()
    if os.path.exists(path):
        os.remove(path)
    logger.info("Prompt templates reset to defaults")


def template_info() -> dict:
    """Templates + defaults + metadata for the editor."""
    current = load_templates()
    path = config_path()
    updated_at = None
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                updated_at = json.load(f).get("updated_at")
        except Exception:  # pragma: no cover
            updated_at = None
    return {
        "templates": current,
        "defaults": DEFAULTS,
        "meta": TEMPLATE_META,
        "variables": VARIABLES,
        "overridden": sorted(k for k in DEFAULTS if current.get(k) != DEFAULTS[k]),
        "updated_at": updated_at,
        "prompt_hash": template_hash(),
    }


def get(key: str) -> str:
    return load_templates().get(key, DEFAULTS.get(key, ""))


def system_prompt() -> str:
    return get("system_prompt")


def template_hash() -> str:
    """Short fingerprint used to detect prompt drift between regression runs."""
    import hashlib

    merged = load_templates()
    blob = "\n".join(f"{k}:{merged[k]}" for k in sorted(merged))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]
