"""Evaluation engine — profession-aware Chain-of-Thought assessment."""
import json
import logging
import re
from typing import Optional

from app.core.llm import llm_client
from app.evaluation import prompts
from app.evaluation.criteria import build_evaluation_prompt, get_system_prompt
from app.schemas.models import (
    EvaluationResult, EvaluationDimension, CandidateInfo,
    ThresholdCheck, ThresholdItem, EvidenceItem,
)
from app.parsers.standard_parser import (
    QualificationStandard, match_standard, load_all_standards,
)

logger = logging.getLogger(__name__)

_standards_cache: list[QualificationStandard] = []

# Display labels for the four basic conditions defined by the standards
THRESHOLD_LABELS = {
    "performance": "近两年绩效",
    "professional_title": "职称/职业资格",
    "certification": "职业资格",
    "work_years": "技术工作年限",
    "organization_contribution": "组织回馈",
    "feedback": "组织回馈",
}


def _sse(payload: dict) -> str:
    """Format a dict as one Server-Sent-Events message."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def get_loaded_standards() -> list:
    return _standards_cache


def init_standards(demo_dir: str = "demo"):
    """Load all qualification standards on startup."""
    global _standards_cache
    _standards_cache = load_all_standards(demo_dir)
    logger.info(f"Loaded {len(_standards_cache)} qualification standards")
    for s in _standards_cache:
        logger.info(f"  - {s.profession} ({len(s.weights)} levels, "
                     f"{sum(len(r) for r in s.scoring_rules.values())} rules)")


def find_standard_for_candidate(
    ppt_content: str = "",
    candidate_industry: str = "",
    candidate_position: str = "",
) -> Optional[QualificationStandard]:
    """Find the best-matching standard for a candidate."""
    if not _standards_cache:
        return None
    return match_standard(_standards_cache, candidate_industry or "", candidate_position or "")


async def precheck_candidate(
    ppt_content: str,
    standard: Optional[QualificationStandard] = None,
    candidate_level: str = "三级",
) -> dict:
    """Check the basic conditions (门槛条件) of the applied level.

    Returns ``{"has_conditions": bool, "overall_pass": bool, "items": [...]}``
    where every item carries ``field/label/required/status/detail``.
    """
    from app.evaluation.criteria import _level_to_num

    level_num = _level_to_num(candidate_level)
    conditions = standard.basic_conditions.get(level_num, {}) if standard else {}
    if not conditions:
        return {"has_conditions": False, "overall_pass": True, "items": []}

    items = [
        {
            "field": field,
            "label": THRESHOLD_LABELS.get(field, field),
            "required": str(requirement)[:300],
            "status": "⚠️",
            "detail": "待核查",
        }
        for field, requirement in conditions.items()
    ]

    if not ppt_content.strip():
        return {"has_conditions": True, "overall_pass": False, "items": items}

    requirements = "\n".join(
        f"- {THRESHOLD_LABELS.get(f, f)}（field={f}）：{str(r)[:300]}"
        for f, r in conditions.items()
    )
    prompt = prompts.render(prompts.get("precheck_prompt"), {
        "profession": standard.profession,
        "candidate_level": candidate_level,
        "requirements": requirements,
        "ppt_content": ppt_content[:8000],
    })

    try:
        response = await llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1500,
        )
    except Exception as exc:
        logger.warning("Precheck LLM call failed: %s", exc)
        for item in items:
            item["detail"] = "自动核查失败，请人工确认"
        return {"has_conditions": True, "overall_pass": False, "items": items}

    parsed = _extract_json(response)
    if isinstance(parsed, dict):
        parsed = parsed.get("items") or parsed.get("threshold_check") or []
    if not isinstance(parsed, list) or not parsed:
        for item in items:
            item["detail"] = "未能从材料中确认，请人工复核"
        return {"has_conditions": True, "overall_pass": False, "items": items}

    by_field = {str(entry.get("field", "")): entry for entry in parsed
                if isinstance(entry, dict)}
    overall = True
    for item in items:
        entry = by_field.get(item["field"])
        if not entry:
            continue
        item["status"] = str(entry.get("status") or "⚠️")[:8]
        item["detail"] = str(entry.get("detail") or "")
        if entry.get("required"):
            item["required"] = str(entry["required"])[:300]
        if "不满足" in item["status"] or item["status"].startswith("❌"):
            overall = False
        if item["status"].startswith("⚠️"):
            overall = False

    return {"has_conditions": True, "overall_pass": overall, "items": items}


def _extract_json(text: str):
    """Best-effort JSON extraction from an LLM reply."""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    candidate = fenced.group(1) if fenced else text
    for pattern in (r"\[[\s\S]*\]", r"\{[\s\S]*\}"):
        match = re.search(pattern, candidate)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


async def evaluate_candidate(
    ppt_content: str,
    standard: Optional[QualificationStandard] = None,
    candidate_level: str = "三级",
    responsibility_score: float = 0.0,
    on_progress=None,
) -> EvaluationResult:
    """Evaluate a candidate using profession-specific criteria."""
    if on_progress:
        await on_progress(10, "正在加载专业评价标准...")

    prompt = build_evaluation_prompt(standard, ppt_content, candidate_level,
                                     responsibility_score)

    if on_progress:
        await on_progress(20, "正在发送给大模型进行思维链推理...")

    try:
        response = await llm_client.chat(
            messages=[
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=8192,
        )

        if on_progress:
            await on_progress(80, "正在解析评价结果...")

        result = _sanitize_evidence(
            _parse_evaluation_response(response, responsibility_score), ppt_content)

        if on_progress:
            await on_progress(100, "评价完成！")

        return result

    except Exception as e:
        logger.error(f"Evaluation error: {e}")
        if on_progress:
            await on_progress(100, f"评价出错: {str(e)}")
        raise


def _parse_evaluation_response(response: str,
                               responsibility_score: float = 0.0) -> EvaluationResult:
    """Parse LLM response. Injects manual responsibility score and recalculates totals."""
    json_match = re.search(r'```json\n(.+?)\n```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_match = re.search(r'\{[\s\S]*"candidate"[\s\S]*"suggestions"[\s\S]*\}', response)
        if json_match:
            json_str = json_match.group()
        else:
            json_str = response

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        logger.warning("Failed to parse JSON from LLM response, using fallback")
        return _create_fallback_result(response)

    candidate_data = data.get("candidate", {})
    if isinstance(candidate_data, str):
        candidate_data = {}

    candidate = CandidateInfo(
        name=candidate_data.get("name", ""),
        department=candidate_data.get("department", ""),
        applied_level=candidate_data.get("applied_level", ""),
        years_of_experience=candidate_data.get("years_of_experience", ""),
        performance_last_two_years=candidate_data.get("performance_last_two_years", ""),
        professional_title=candidate_data.get("professional_title", ""),
    )

    dimensions = []
    for dim_data in data.get("dimensions", []):
        if isinstance(dim_data, dict):
            evidence, pages = _parse_evidence(dim_data.get("evidence"))
            dim = EvaluationDimension(
                name=dim_data.get("name", ""),
                full_score=float(dim_data.get("full_score", 0) or 0),
                threshold=float(dim_data.get("threshold", 0) or 0),
                score=float(dim_data.get("score", 0)) if dim_data.get("score") is not None else None,
                score_percentage=float(dim_data.get("score_percentage", 0)) if dim_data.get("score_percentage") else None,
                comments=dim_data.get("comments", ""),
                details=dim_data.get("details", ""),
                sub_dimensions=dim_data.get("sub_dimensions", []),
                evidence=evidence,
                pages=pages,
            )
            dimensions.append(dim)

    # Inject manual responsibility score
    if responsibility_score > 0:
        _inject_manual_score(dimensions, responsibility_score)

    threshold_raw = data.get("threshold_check", {})
    threshold_check = _parse_threshold_check(threshold_raw)
    threshold_pass = threshold_check.overall_pass

    result = EvaluationResult(
        candidate=candidate,
        total_score=float(data.get("total_score", 0)),
        total_full_score=float(data.get("total_full_score", 100)),
        total_percentage=float(data.get("total_percentage", 0)),
        passed=bool(data.get("passed", False) and threshold_pass),
        dimensions=dimensions,
        chain_of_thought=data.get("chain_of_thought", ""),
        summary=data.get("summary", ""),
        strengths=data.get("strengths", []),
        improvements=data.get("improvements", []),
        suggestions=data.get("suggestions", ""),
        threshold_check=threshold_check,
    )

    # Recalculate totals with manual score included
    return _recalc_totals(result)


def _parse_threshold_check(raw) -> ThresholdCheck:
    """Normalise the LLM's threshold_check object into structured items."""
    if not isinstance(raw, dict):
        return ThresholdCheck(overall_pass=True, items=[])

    items: list[ThresholdItem] = []
    for key, value in raw.items():
        if key == "overall_pass":
            continue
        if isinstance(value, dict):
            status = str(value.get("status", "") or "")
            detail = str(value.get("detail", "") or "")
            required = str(value.get("required", "") or "")
        else:
            status, detail, required = str(value or ""), "", ""
        items.append(ThresholdItem(
            field=key,
            label=THRESHOLD_LABELS.get(key, key),
            status=status,
            detail=detail,
            required=required,
        ))
    return ThresholdCheck(overall_pass=bool(raw.get("overall_pass", True)),
                          items=items)


def _parse_evidence(raw) -> tuple[list, list]:
    """Normalise the LLM's ``evidence`` field into items + page list."""
    items: list[EvidenceItem] = []
    if isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, dict):
                try:
                    page = int(entry.get("page") or 0)
                except (TypeError, ValueError):
                    page = 0
                quote = str(entry.get("quote") or "").strip()
                note = str(entry.get("note") or "").strip()
                if quote or note:
                    items.append(EvidenceItem(page=max(0, page), quote=quote, note=note))
            elif isinstance(entry, str) and entry.strip():
                items.append(EvidenceItem(quote=entry.strip()))
    elif isinstance(raw, str) and raw.strip():
        items.append(EvidenceItem(quote=raw.strip()))

    pages = sorted({item.page for item in items if item.page > 0})
    return items, pages


def _sanitize_evidence(result: EvaluationResult, ppt_content: str) -> EvaluationResult:
    """Drop evidence pointing at slide numbers that do not exist."""
    slide_numbers = {int(m) for m in re.findall(r"##\s*幻灯片\s*(\d+)", ppt_content)}
    if not slide_numbers:
        return result
    dropped = 0
    for dim in result.dimensions:
        kept = [e for e in dim.evidence if e.page == 0 or e.page in slide_numbers]
        dropped += len(dim.evidence) - len(kept)
        dim.evidence = kept
        dim.pages = sorted({e.page for e in kept if e.page})
    if dropped:
        logger.warning("Dropped %d evidence item(s) with invalid page numbers", dropped)
    return result


def _inject_manual_score(dimensions: list, score: float):
    """Replace or insert the 责任贡献 dimension with the manual score."""
    for dim in dimensions:
        if "责任贡献" in dim.name or "责任结果" in dim.name:
            dim.score = score
            if dim.full_score > 0:
                dim.score_percentage = round(score / dim.full_score * 100, 1)
            dim.comments = "此项由人工评委打分（手动评分）"
            dim.details = (dim.details or "") + "\n[人工评分]"
            return
    # If LLM didn't include it, add it
    dim = EvaluationDimension(
        name="责任贡献",
        full_score=30,
        threshold=18,
        score=score,
        score_percentage=round(score / 30 * 100, 1) if score > 0 else 0,
        comments="此项由人工评委打分（手动评分）",
        details="[人工评分]",
    )
    dimensions.insert(0, dim)


def _recalc_totals(result: EvaluationResult) -> EvaluationResult:
    """Recalculate total_score and total_percentage from dimensions after manual injection."""
    total_full = sum(d.full_score for d in result.dimensions)
    total_score = sum((d.score or 0) for d in result.dimensions)
    result.total_full_score = total_full
    result.total_score = round(total_score, 1)
    result.total_percentage = round(total_score / total_full * 100, 1) if total_full > 0 else 0
    # Check all thresholds
    all_ok = all(
        (d.score or 0) >= (d.threshold or 0) for d in result.dimensions if d.threshold
    )
    result.passed = result.passed and all_ok
    return result


def _create_fallback_result(raw_response: str) -> EvaluationResult:
    return EvaluationResult(
        candidate=CandidateInfo(name="解析失败"),
        total_score=0,
        total_full_score=100,
        total_percentage=0,
        passed=False,
        dimensions=[],
        chain_of_thought=raw_response[:2000],
        summary="系统解析大模型返回结果时遇到问题，请查看原始输出",
        strengths=[],
        improvements=[],
        suggestions="请检查LLM返回的格式是否正确",
    )


async def stream_evaluate(
    ppt_content: str,
    standard: Optional[QualificationStandard] = None,
    candidate_level: str = "三级",
):
    """Stream the evaluation as Server-Sent Events (``data: {json}`` lines)."""
    prompt = build_evaluation_prompt(standard, ppt_content, candidate_level)

    yield _sse({"type": "progress", "stage": "推理中", "progress": 30,
                "message": "正在调用大模型进行思维链推理..."})

    full_response = ""
    try:
        async for chunk in llm_client.chat_stream(
            messages=[
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        ):
            full_response += chunk
            yield _sse({"type": "chunk", "content": chunk})
    except Exception as e:
        yield _sse({"type": "error", "message": str(e)})
        return

    yield _sse({"type": "progress", "stage": "解析中", "progress": 80,
                "message": "正在解析评价结果..."})

    try:
        result = _sanitize_evidence(_parse_evaluation_response(full_response), ppt_content)
        yield _sse({"type": "result", "data": result.model_dump()})
    except Exception as e:
        yield _sse({"type": "error", "message": f"解析失败: {str(e)}"})
