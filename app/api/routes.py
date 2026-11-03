"""API routes for the evaluation system."""
import datetime
import io
import json
import os
import logging
import shutil
import re
import uuid
import zipfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional
from urllib.parse import quote

from app.core.config import settings
from app.core import db
from app.core.llm import llm_client
from app.parsers.ppt_parser import parse_pptx, pptx_to_markdown
from app.parsers.excel_parser import parse_qualification_standard, standard_to_text
from app.evaluation import batch as batch_runner
from app.evaluation import prompts as prompt_store
from app.evaluation import regression
from app.evaluation.criteria import build_evaluation_prompt
from app.evaluation.engine import (
    evaluate_candidate, stream_evaluate, precheck_candidate,
    find_standard_for_candidate, get_loaded_standards,
)
from app.report.pdf_report import build_report_pdf, report_filename
from app.schemas.models import (
    LLMConfig, ReportRequest, ReviewUpdate, PromptTemplatesUpdate,
    PromptPreviewRequest, RegressionRunRequest, BaselineRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Ensure upload directory exists
os.makedirs(settings.upload_dir, exist_ok=True)

MAX_UPLOAD_MB = 50
ALLOWED_EXTENSIONS = {".pptx", ".xlsx", ".xls"}


def _safe_filename(filename: str) -> str:
    """Strip path components and unsafe characters from an upload name."""
    name = os.path.basename(filename.replace("\\", "/"))
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    if not name:
        name = "upload"
    stem, ext = os.path.splitext(name)
    return f"{stem[:80]}{ext}"


def _content_disposition(filename: str, fallback: str = "download") -> str:
    ext = os.path.splitext(filename)[1] or ""
    return (f"attachment; filename=\"{fallback}{ext}\"; "
            f"filename*=UTF-8''{quote(filename)}")


def _pdf_response(pdf_bytes: bytes, filename: str) -> Response:
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition":
                             _content_disposition(filename, "report")})


def _report_bytes(record: dict, regenerate: bool = False) -> bytes:
    """Return the archived PDF for a record, generating it when missing."""
    path = record.get("report_path")
    if not regenerate and path and os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()

    pdf_bytes = build_report_pdf(record["result"],
                                 ppt_content=record.get("ppt_content") or "")
    path = db.report_file_path(record["id"])
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    db.set_report(record["id"], path)
    return pdf_bytes


def _zip_bytes(files: list) -> bytes:
    """Pack ``[(name, bytes), ...]`` into an in-memory zip archive."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files:
            archive.writestr(name, data)
    return buffer.getvalue()


@router.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "llm_configured": llm_client.is_configured,
        "llm_base_url": settings.llm_base_url,
        "llm_model": settings.llm_model,
    }


@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a PPT or Excel file and parse its content."""
    if not file.filename:
        raise HTTPException(400, "未选择文件")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext == ".ppt":
        raise HTTPException(
            400,
            "暂不支持 .ppt 旧格式，请用 PowerPoint/WPS 另存为 .pptx 后重新上传",
        )
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件类型：{ext}，请上传 PPTX 或 Excel 文件")

    content = await file.read()
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(400, f"文件过大，请控制在 {MAX_UPLOAD_MB}MB 以内")
    if not content:
        raise HTTPException(400, "文件内容为空")

    safe_name = _safe_filename(file.filename)
    file_path = os.path.join(settings.upload_dir, safe_name)
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        if ext == ".pptx":
            slides, candidate = parse_pptx(file_path)
            markdown_content = pptx_to_markdown(slides)
            return {
                "filename": safe_name,
                "file_type": "ppt",
                "candidate": candidate.model_dump(),
                "content": markdown_content,
                "message": "PPT解析成功",
            }
        # For Excel - treat as qualification standard
        standard = parse_qualification_standard(file_path)
        text = standard_to_text(standard)
        return {
            "filename": safe_name,
            "file_type": "standard",
            "content": text,
            "message": "任职资格标准解析成功",
        }
    except Exception as e:
        logger.error(f"Parse error: {e}", exc_info=True)
        raise HTTPException(500, f"文件解析失败: {str(e)}")


@router.post("/api/evaluate")
async def evaluate(
    ppt_content: str = Form(...),
    qualification_standard: str = Form(""),
    candidate_level: str = Form("三级"),
    candidate_position: str = Form(""),
    responsibility_score: str = Form("0"),
    ppt_filename: str = Form(""),
    api_key: Optional[str] = Form(None),
    base_url: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
):
    """Run a full evaluation with Chain-of-Thought and persist the record."""
    # Update LLM config if provided
    if api_key and base_url and model:
        llm_client.update_config(api_key, base_url, model)
    elif not llm_client.client:
        raise HTTPException(400, "LLM not configured. Please provide API configuration.")

    # Parse manual responsibility score
    resp_score = 0.0
    try:
        resp_score = float(responsibility_score)
    except (ValueError, TypeError):
        pass

    # Match standard by candidate position/industry
    standard = find_standard_for_candidate(
        ppt_content=ppt_content,
        candidate_position=candidate_position,
    )

    try:
        result = await evaluate_candidate(
            ppt_content=ppt_content,
            standard=standard,
            candidate_level=candidate_level,
            responsibility_score=resp_score,
        )
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        raise HTTPException(500, f"评价失败: {str(e)}")

    payload = result.model_dump()
    try:
        record_id = db.save_evaluation(
            payload,
            ppt_filename=ppt_filename or "",
            ppt_content=ppt_content,
            standard_filename=standard.filename if standard else "",
            responsibility_score=resp_score,
            llm_model=settings.llm_model,
            profession=standard.profession if standard else "",
        )
        payload["record_id"] = record_id
    except Exception as e:  # persistence must not break the evaluation result
        logger.error(f"Failed to persist evaluation: {e}", exc_info=True)

    return payload


@router.post("/api/evaluate/precheck")
async def evaluate_precheck(
    ppt_content: str = Form(""),
    candidate_level: str = Form("三级"),
    candidate_position: str = Form(""),
    ppt_filename: str = Form(""),
):
    """Check the basic conditions (门槛) before scoring."""
    standard = find_standard_for_candidate(
        ppt_content=ppt_content,
        candidate_position=candidate_position,
    )
    if standard is None:
        return {"has_conditions": False, "overall_pass": True, "items": [],
                "message": "未匹配到任职资格标准，跳过门槛核查"}

    if not llm_client.client or not llm_client.is_configured:
        # No usable model: still show the requirements so the reviewer
        # can verify them manually.
        from app.evaluation.criteria import _level_to_num
        from app.evaluation.engine import THRESHOLD_LABELS
        conditions = standard.basic_conditions.get(_level_to_num(candidate_level), {})
        items = [{"field": f, "label": THRESHOLD_LABELS.get(f, f),
                  "required": str(r)[:300], "status": "⚠️",
                  "detail": "大模型未配置，请人工核查"} for f, r in conditions.items()]
        return {"has_conditions": bool(items), "overall_pass": False,
                "items": items, "message": "大模型未配置，已列出门槛要求供人工核查"}

    try:
        data = await precheck_candidate(ppt_content, standard, candidate_level)
        data["standard"] = standard.filename
        data["profession"] = standard.profession
        return data
    except Exception as e:
        logger.error(f"Precheck failed: {e}", exc_info=True)
        raise HTTPException(500, f"门槛核查失败: {str(e)}")


@router.post("/api/evaluate/stream")
async def evaluate_stream(
    ppt_content: str = Form(...),
    qualification_standard: str = Form(""),
    candidate_level: str = Form("三级"),
    candidate_position: str = Form(""),
    api_key: Optional[str] = Form(None),
    base_url: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
):
    """Stream evaluation process for real-time updates."""
    if api_key and base_url and model:
        llm_client.update_config(api_key, base_url, model)
    elif not llm_client.client:
        raise HTTPException(400, "LLM not configured")

    standard = find_standard_for_candidate(
        ppt_content=ppt_content,
        candidate_position=candidate_position,
    )

    return StreamingResponse(
        stream_evaluate(ppt_content, standard, candidate_level),
        media_type="text/event-stream",
    )


@router.post("/api/report/pdf")
async def generate_report(payload: ReportRequest):
    """Generate an A4 PDF evaluation report and return it as a download."""
    result = payload.result.model_dump()
    try:
        pdf_bytes = build_report_pdf(
            result,
            ppt_content=payload.ppt_content,
            reviewer=payload.reviewer,
            organization=payload.organization,
            include_cot=payload.include_cot,
        )
    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        raise HTTPException(500, f"报告生成失败: {str(e)}")

    return _pdf_response(pdf_bytes, report_filename(result))


# ------------------------------------------------------------ records ----
@router.get("/api/evaluations")
async def list_evaluations(
    keyword: str = "",
    profession: str = "",
    candidate_level: str = "",
    passed: str = "",
    review_status: str = "",
    page: int = 1,
    page_size: int = 20,
):
    """List archived evaluation records (newest first)."""
    passed_flag: Optional[bool] = None
    if passed in ("true", "1"):
        passed_flag = True
    elif passed in ("false", "0"):
        passed_flag = False
    return db.list_evaluations(
        keyword=keyword, profession=profession, applied_level=candidate_level,
        passed=passed_flag, review_status=review_status,
        page=page, page_size=page_size,
    )


@router.get("/api/evaluations/{record_id}")
async def get_evaluation(record_id: str):
    """Load one archived evaluation record (full result + material)."""
    record = db.get_evaluation(record_id)
    if not record:
        raise HTTPException(404, "评价记录不存在")
    return record


@router.delete("/api/evaluations/{record_id}")
async def delete_evaluation(record_id: str):
    """Delete a record and its archived PDF report."""
    if not db.delete_evaluation(record_id):
        raise HTTPException(404, "评价记录不存在")
    return {"message": "评价记录已删除", "id": record_id}


@router.get("/api/evaluations/{record_id}/report")
async def download_record_report(record_id: str, regenerate: bool = False):
    """Download the archived PDF report, generating it on first request."""
    record = db.get_evaluation(record_id)
    if not record:
        raise HTTPException(404, "评价记录不存在")
    try:
        pdf_bytes = _report_bytes(record, regenerate=regenerate)
    except Exception as e:
        logger.error(f"Report generation failed for {record_id}: {e}", exc_info=True)
        raise HTTPException(500, f"报告生成失败: {str(e)}")
    return _pdf_response(pdf_bytes, report_filename(record["result"]))


@router.get("/api/reports/zip")
async def download_reports_zip(ids: str = ""):
    """Download several records' PDF reports packed in one zip archive."""
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list:
        raise HTTPException(400, "请至少选择一条评价记录")

    files, missing = [], []
    for index, record_id in enumerate(id_list, start=1):
        record = db.get_evaluation(record_id, with_content=True)
        if not record:
            missing.append(record_id)
            continue
        try:
            pdf_bytes = _report_bytes(record)
        except Exception as e:
            logger.error(f"Zip report failed for {record_id}: {e}", exc_info=True)
            missing.append(record_id)
            continue
        files.append((f"{index:02d}_{report_filename(record['result'])}", pdf_bytes))

    if not files:
        raise HTTPException(404, "没有可导出的报告")

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    zip_name = f"任职资格评价报告_{len(files)}份_{stamp}.zip"
    return Response(content=_zip_bytes(files), media_type="application/zip",
                    headers={"Content-Disposition":
                             _content_disposition(zip_name, "reports")})


@router.get("/api/stats/overview")
async def stats_overview():
    """Aggregated statistics for the dashboard."""
    return db.stats_overview()


@router.patch("/api/evaluations/{record_id}/review")
async def update_review(record_id: str, payload: ReviewUpdate):
    """Advance the review workflow (AI → 人工复核 → 终审通过/不通过)."""
    if payload.status not in db.REVIEW_STATUSES:
        raise HTTPException(400, f"未知评审状态: {payload.status}")
    if not db.update_review(record_id, payload.status, payload.reviewer,
                            payload.comment):
        raise HTTPException(404, "评价记录不存在")
    return db.get_evaluation(record_id, with_content=False)


@router.get("/api/compare")
async def compare_records(ids: str = ""):
    """Compare several archived records dimension by dimension."""
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if len(id_list) < 2:
        raise HTTPException(400, "请至少选择两条评价记录进行对比")
    return db.compare_records(id_list)


# --------------------------------------------------------------- batches ----
@router.post("/api/batches")
async def create_batch(
    files: list[UploadFile] = File(...),
    name: str = Form(""),
    candidate_level: str = Form("三级"),
    responsibility_score: str = Form("0"),
):
    """Upload several candidate PPTs and start a batch evaluation."""
    if not files:
        raise HTTPException(400, "请至少上传一个 PPTX 文件")

    # 1) validate everything first so a bad file does not create a half batch
    payloads: list[tuple[str, bytes]] = []
    for upload in files:
        if not upload.filename:
            continue
        ext = os.path.splitext(upload.filename)[1].lower()
        if ext != ".pptx":
            raise HTTPException(
                400, f"批量评价仅支持 .pptx 文件，{upload.filename} 格式不支持")
        content = await upload.read()
        if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(400, f"{upload.filename} 超过 {MAX_UPLOAD_MB}MB 限制")
        if not content:
            raise HTTPException(400, f"{upload.filename} 内容为空")
        payloads.append((_safe_filename(upload.filename), content))

    if not payloads:
        raise HTTPException(400, "没有可用的文件")

    try:
        score = float(responsibility_score or 0)
    except (TypeError, ValueError):
        score = 0.0

    # 2) create the job, then store its files under uploads/batches/{id}
    batch = db.create_batch(
        name=name or f"批量评价 {len(payloads)} 人",
        candidate_level=candidate_level,
        responsibility_score=score,
        filenames=[f[0] for f in payloads],
    )
    target_dir = batch_runner.batch_dir(batch["id"])
    os.makedirs(target_dir, exist_ok=True)
    for filename, content in payloads:
        with open(os.path.join(target_dir, filename), "wb") as f:
            f.write(content)

    batch_runner.schedule(batch["id"])
    return batch


@router.get("/api/batches")
async def list_batches(limit: int = 30):
    """List batch jobs (newest first)."""
    return db.list_batches(limit=limit)


@router.get("/api/batches/{batch_id}")
async def get_batch(batch_id: str):
    """Batch job detail with per-candidate progress."""
    batch = db.get_batch(batch_id)
    if not batch:
        raise HTTPException(404, "批量任务不存在")
    return batch


@router.get("/api/batches/{batch_id}/reports.zip")
async def download_batch_reports(batch_id: str):
    """Download every finished candidate report of a batch as one zip."""
    batch = db.get_batch(batch_id)
    if not batch:
        raise HTTPException(404, "批量任务不存在")

    files, skipped = [], []
    for index, item in enumerate(batch["items"], start=1):
        record_id = item.get("record_id")
        if not record_id:
            skipped.append(item.get("filename", ""))
            continue
        record = db.get_evaluation(record_id)
        if not record:
            skipped.append(item.get("filename", ""))
            continue
        try:
            pdf_bytes = _report_bytes(record)
        except Exception as e:
            logger.error(f"Batch zip report failed for {record_id}: {e}", exc_info=True)
            skipped.append(item.get("filename", ""))
            continue
        files.append((f"{index:02d}_{report_filename(record['result'])}", pdf_bytes))

    if not files:
        raise HTTPException(404, "该批次还没有可导出的报告（可能仍在评价中）")

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    base = (batch.get("name") or "批量评价").strip() or "批量评价"
    zip_name = f"{base}_报告_{len(files)}份_{stamp}.zip"
    return Response(content=_zip_bytes(files), media_type="application/zip",
                    headers={"Content-Disposition":
                             _content_disposition(zip_name, "batch_reports")})


@router.post("/api/batches/{batch_id}/cancel")
async def cancel_batch(batch_id: str):
    """Cancel a running batch (in-flight candidate finishes first)."""
    if not db.cancel_batch(batch_id):
        raise HTTPException(400, "任务不存在或已结束")
    return {"message": "已取消", "id": batch_id}


@router.delete("/api/batches/{batch_id}")
async def delete_batch(batch_id: str, with_records: bool = False):
    """Delete a batch job; optionally delete its evaluation records too."""
    batch = db.get_batch(batch_id)
    if not batch:
        raise HTTPException(404, "批量任务不存在")
    if with_records:
        for item in batch["items"]:
            if item.get("record_id"):
                db.delete_evaluation(item["record_id"])
    db.delete_batch(batch_id)
    # drop the uploaded source files as well
    shutil.rmtree(batch_runner.batch_dir(batch_id), ignore_errors=True)
    return {"message": "批量任务已删除", "id": batch_id}


@router.post("/api/config/llm")
async def update_llm_config(config: LLMConfig):
    """Update LLM configuration."""
    try:
        llm_client.update_config(config.api_key, config.base_url, config.model)
        return {"message": "LLM配置更新成功", "config": config.model_dump()}
    except Exception as e:
        raise HTTPException(500, f"配置失败: {str(e)}")


@router.post("/api/config/llm/test")
async def test_llm_connection(config: LLMConfig):
    """Test LLM connection by sending a real API request."""
    try:
        # First update config
        llm_client.update_config(config.api_key, config.base_url, config.model)
        # Then actually test the connection
        result = await llm_client.test_connection()
        if result["ok"]:
            return result
        else:
            raise HTTPException(400, result["message"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"测试连接失败: {str(e)}")


@router.get("/api/config/llm")
async def get_llm_config():
    """Get current LLM configuration."""
    return {
        "base_url": settings.llm_base_url,
        "model": settings.llm_model,
        "has_api_key": bool(settings.llm_api_key and settings.llm_api_key != "sk-placeholder"),
        "configured": llm_client.is_configured,
    }


@router.get("/api/demo/files")
async def list_demo_files():
    """List available demo files."""
    demo_dir = Path(settings.demo_dir)
    if not demo_dir.exists():
        return {"files": []}

    grouped = {"ppt": [], "standard": [], "job_desc": []}

    for f in sorted(demo_dir.iterdir()):
        ext = f.suffix.lower()
        if ext not in ['.pptx', '.ppt', '.xlsx', '.xls']:
            continue
        size = f.stat().st_size
        name = f.name
        entry = {"name": name, "size": size}

        if ext in ['.pptx', '.ppt']:
            entry["type"] = "ppt"
            grouped["ppt"].append(entry)
        else:
            # All Excel files are treated as qualification standards,
            # except the job description file (职位说明书) - try both
            # possible encodings of the keyword
            if "职位说明书" in name or "鑱屼綅璇存槑涔" in name:
                entry["type"] = "job_desc"
                grouped["job_desc"].append(entry)
            else:
                entry["type"] = "standard"
                grouped["standard"].append(entry)

    return {"files": grouped}


@router.get("/api/demo/standards")
async def list_standards():
    """List loaded qualification standards with profession info."""
    standards = get_loaded_standards()
    return {
        "standards": [
            {
                "profession": s.profession,
                "industry": s.industry,
                "title": s.title,
                "filename": s.filename,
                "levels": sorted(s.weights.keys()),
                "dimensions": list(s.weights.get(3, s.weights.get(sorted(s.weights.keys())[0], {})).keys()) if s.weights else [],
            }
            for s in standards
        ],
        "count": len(standards),
    }


@router.get("/api/demo/load")
async def load_demo_file(filename: str):
    """Load and parse a demo file."""
    file_path = os.path.join(settings.demo_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(404, f"Demo file not found: {filename}")

    ext = os.path.splitext(filename)[1].lower()
    try:
        if ext in ['.pptx', '.ppt']:
            slides, candidate = parse_pptx(file_path)
            markdown_content = pptx_to_markdown(slides)
            return {
                "filename": filename,
                "file_type": "ppt",
                "candidate": candidate.model_dump(),
                "content": markdown_content,
            }
        else:
            standard = parse_qualification_standard(file_path)
            text = standard_to_text(standard)
            return {
                "filename": filename,
                "file_type": "standard",
                "content": text,
            }
    except Exception as e:
        raise HTTPException(500, f"解析失败: {str(e)}")


@router.get("/api/demo/load-paired")
async def load_paired_demo(candidate_name: str = ""):
    """Load a candidate's PPT and matching qualification standard."""
    demo_dir = Path(settings.demo_dir)
    if not demo_dir.exists():
        raise HTTPException(404, "Demo directory not found")

    # Find matching PPT
    ppt_file = None
    standard_file = None

    for f in demo_dir.iterdir():
        if candidate_name and candidate_name in f.name and f.suffix.lower() in ['.pptx', '.ppt']:
            ppt_file = f.name
        if "任职资格标准" in f.name and f.suffix.lower() in ['.xlsx', '.xls']:
            # Try to match industry
            if candidate_name:
                # Extract industry from PPT filename
                ppt_parts = candidate_name.split('_', 1)
                if len(ppt_parts) > 1:
                    industry = ppt_parts[0].replace('公开 ', '').replace('公开', '')
                    if industry in f.name:
                        standard_file = f.name

    # Fallback: just take any standard
    if not standard_file:
        for f in demo_dir.iterdir():
            if "任职资格标准" in f.name and f.suffix.lower() in ['.xlsx', '.xls']:
                standard_file = f.name
                break

    result = {"ppt": None, "standard": None}

    if ppt_file:
        ppt_path = os.path.join(settings.demo_dir, ppt_file)
        slides, candidate = parse_pptx(ppt_path)
        result["ppt"] = {
            "filename": ppt_file,
            "candidate": candidate.model_dump(),
            "content": pptx_to_markdown(slides),
        }

    if standard_file:
        std_path = os.path.join(settings.demo_dir, standard_file)
        standard = parse_qualification_standard(std_path)
        result["standard"] = {
            "filename": standard_file,
            "content": standard_to_text(standard),
        }

    return result


# ---------------------------------------------------------------- prompts ----
@router.get("/api/prompts")
async def get_prompts():
    """Current prompt templates, defaults and editable metadata."""
    return prompt_store.template_info()


@router.put("/api/prompts")
async def update_prompts(payload: PromptTemplatesUpdate):
    """Persist template overrides (takes effect on the next evaluation)."""
    if not payload.templates:
        raise HTTPException(400, "没有需要保存的模板内容")
    prompt_store.save_templates(payload.templates)
    info = prompt_store.template_info()
    info["message"] = "提示词模板已保存，下次评价生效"
    return info


@router.post("/api/prompts/reset")
async def reset_prompts():
    """Restore the built-in prompt templates."""
    prompt_store.reset_templates()
    info = prompt_store.template_info()
    info["message"] = "已恢复默认提示词"
    return info


@router.post("/api/prompts/preview")
async def preview_prompt(payload: PromptPreviewRequest):
    """Render the final evaluation prompt for inspection (no LLM call)."""
    standards = get_loaded_standards()
    if not standards:
        raise HTTPException(400, "尚未加载任职资格标准")

    standard = standards[0]
    if payload.standard_filename:
        standard = next((s for s in standards
                         if s.filename == payload.standard_filename), standards[0])

    prompt = build_evaluation_prompt(
        standard,
        "（预览模式：此处为候选人答辩材料，实际评价时会替换为完整内容）",
        payload.candidate_level,
        payload.responsibility_score,
    )
    return {
        "standard": standard.filename,
        "profession": standard.profession,
        "length": len(prompt),
        "prompt": prompt,
    }


# ------------------------------------------------------------- regression ----
@router.post("/api/regression/run")
async def run_regression(payload: RegressionRunRequest):
    """Start a consistency regression run over demo materials."""
    cases = [c for c in payload.cases if c]
    if not cases:
        raise HTTPException(400, "请至少选择一个用例")
    if not regression.prompts_can_run():
        raise HTTPException(400, "大模型未配置，无法执行回归测试")
    job = regression.create_job(cases, payload.repeats,
                                payload.responsibility_score)
    return job


@router.get("/api/regression/jobs")
async def list_regression_jobs():
    """Recent regression jobs (in-memory, per server session)."""
    return {"items": regression.list_jobs()}


@router.get("/api/regression/jobs/{job_id}")
async def get_regression_job(job_id: str):
    """Regression job detail with per-case scores and drift."""
    job = regression.get_job(job_id)
    if not job:
        raise HTTPException(404, "回归任务不存在")
    return job


@router.get("/api/regression/baseline")
async def get_regression_baseline():
    """Current regression baseline (stored on disk)."""
    return regression.load_baseline()


@router.post("/api/regression/baseline")
async def save_regression_baseline(payload: BaselineRequest):
    """Promote a finished job to the baseline."""
    try:
        return regression.baseline_from_job(payload.job_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.delete("/api/regression/baseline")
async def delete_regression_baseline():
    """Remove the stored baseline."""
    regression.delete_baseline()
    return {"message": "回归基线已清除"}
