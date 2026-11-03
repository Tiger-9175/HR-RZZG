"""Evaluation criteria prompt assembly.

The structural sections (standard / weights / rules) are generated from the
parsed qualification standard, while the editable wording lives in
``app.evaluation.prompts`` (persisted to ``data/prompt_templates.json``) so the
scoring口径 can be tuned without code changes.
"""
from app.evaluation import prompts


def build_threshold_prompt(standard) -> str:
    """Build the threshold (basic conditions) check section."""
    lines = []
    lines.append("## 门槛条件（基本条件 - 不占分值，不满足则直接否决）\n")
    for lv, conds in sorted(standard.basic_conditions.items()):
        lines.append(f"**{lv}级门槛要求：**")
        for field, req in conds.items():
            field_name = {
                "performance": "绩效",
                "certification": "职业资格",
                "work_years": "技术工作年限",
                "feedback": "组织回馈",
            }.get(field, field)
            lines.append(f"  - {field_name}: {req}")
        lines.append("")
    return "\n".join(lines)


def build_weights_prompt(standard, level: int) -> str:
    """Build the scoring weight section for a specific level."""
    lines = []
    weights = standard.weights.get(level, {})
    if not weights:
        # Fallback: use any level's weights
        for lv in sorted(standard.weights.keys()):
            if abs(lv - int(level)) <= 1:
                weights = standard.weights[lv]
                break

    lines.append(f"## {level}级评分权重分配（满分100分）\n")
    total = 0
    for dim, w in weights.items():
        lines.append(f"- **{dim}**: {w:.0f}分")
        total += w
    lines.append(f"- **满分合计**: {total:.0f}分")
    return "\n".join(lines)


def build_scoring_rules_prompt(standard, level: int) -> str:
    """Build detailed scoring rules for a specific level."""
    rules = standard.scoring_rules.get(level, [])
    if not rules:
        return ""

    lines = [f"\n## {level}级详细评分细则\n"]
    for r in rules:
        dim = r.get("dimension", "")
        sub = r.get("sub_dimension", "")
        header = f"{dim}/{sub}" if sub else dim
        lines.append(f"\n### {header}")
        if r.get("standard"):
            lines.append(f"**评价标准：** {r['standard'][:400]}")
        if r.get("criteria"):
            lines.append(f"**考察点：** {r['criteria'][:300]}")
        if r.get("evidence"):
            lines.append(f"**举证要求：** {r['evidence'][:300]}")
        if r.get("max_score"):
            lines.append(f"**满分：** {r['max_score']}分 | **达标值：** {r.get('threshold', 0)}分")
        if r.get("scoring_rules"):
            lines.append(f"**打分规则：** {r['scoring_rules'][:500]}")
    return "\n".join(lines)


def build_evaluation_prompt(standard, ppt_content: str, candidate_level: str,
                            responsibility_score: float = 0.0) -> str:
    """Build a complete evaluation prompt with profession-specific criteria."""
    level_num = _level_to_num(candidate_level)

    profession = standard.profession if standard else "未知专业"
    raw_standard = standard.raw_text if standard else "未加载标准"
    threshold_section = build_threshold_prompt(standard) if standard else ""
    weights_section = build_weights_prompt(standard, level_num) if standard else ""
    rules_section = build_scoring_rules_prompt(standard, level_num) if standard else ""

    # Get dimension names from the standard weights
    if standard and level_num in standard.weights:
        dims = list(standard.weights[level_num].keys())
    else:
        dims = ["责任贡献", "洞察规划能力", "工艺方案设计能力",
                "问题识别解决能力", "创新能力", "沟通协调能力"]

    templates = prompts.load_templates()

    # Per-dimension instructions (manual dimension handled separately)
    dim_instructions = ""
    for index, dim in enumerate(dims, start=1):
        if "责任贡献" in dim or "责任结果" in dim:
            block = prompts.render(templates["manual_dimension_instruction"], {
                "dim_index": index,
                "dim_name": dim,
                "responsibility_score": responsibility_score,
            })
        else:
            block = prompts.render(templates["dimension_instruction"], {
                "dim_index": index,
                "dim_name": dim,
            })
        dim_instructions += block.rstrip() + "\n"

    return prompts.render(templates["evaluation_template"], {
        "profession": profession,
        "raw_standard": raw_standard,
        "threshold_section": threshold_section,
        "weights_section": weights_section,
        "rules_section": rules_section,
        "ppt_content": ppt_content,
        "candidate_level": candidate_level,
        "dim_instructions": dim_instructions.rstrip(),
        "material_rules": templates["evidence_rules"],
        "output_schema": templates["output_schema"],
        "responsibility_score": responsibility_score,
    })


def get_system_prompt() -> str:
    """Current system prompt (re-read每次调用, so edits apply without restart)."""
    return prompts.system_prompt()


def _level_to_num(level_str: str) -> int:
    """Convert level string like '三级' or '三' to integer 3."""
    mapping = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}
    for ch, num in mapping.items():
        if ch in level_str:
            return num
    return 3  # default
