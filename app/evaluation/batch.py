"""Sequential batch evaluation runner.

Each batch evaluates candidate PPTs one by one (LLM services usually cannot
serve many concurrent long-context requests), persisting every result into the
same evaluation table so batch output and single evaluations look identical.
"""
from __future__ import annotations

import asyncio
import logging
import os

from app.core import db
from app.core.config import settings
from app.evaluation.engine import evaluate_candidate, find_standard_for_candidate
from app.parsers.ppt_parser import parse_pptx, pptx_to_markdown

logger = logging.getLogger(__name__)

_tasks: dict[str, asyncio.Task] = {}


def batch_dir(batch_id: str) -> str:
    return os.path.join(settings.upload_dir, "batches", batch_id)


def schedule(batch_id: str) -> None:
    """Start a batch job in the background (non-blocking)."""
    task = asyncio.create_task(run_batch(batch_id))
    _tasks[batch_id] = task
    task.add_done_callback(lambda _t: _tasks.pop(batch_id, None))
    logger.info("Batch %s scheduled", batch_id)


async def run_batch(batch_id: str) -> None:
    batch = db.get_batch(batch_id)
    if not batch:
        logger.warning("Batch %s not found", batch_id)
        return

    logger.info("Batch %s started (%d items)", batch_id, len(batch["items"]))
    for item in db.pending_batch_items(batch_id):
        if db.batch_status(batch_id) != "running":
            break

        db.set_batch_item(item["id"], "running")
        path = os.path.join(batch_dir(batch_id), item["filename"])
        try:
            slides, candidate = parse_pptx(path)
            content = pptx_to_markdown(slides)
            level = batch.get("candidate_level") or candidate.applied_level or "三级"
            standard = find_standard_for_candidate(
                ppt_content=content, candidate_position=candidate.position or "")
            result = await evaluate_candidate(
                ppt_content=content,
                standard=standard,
                candidate_level=level,
                responsibility_score=float(batch.get("responsibility_score") or 0),
            )
            payload = result.model_dump()
            record_id = db.save_evaluation(
                payload,
                ppt_filename=item["filename"],
                ppt_content=content,
                standard_filename=standard.filename if standard else "",
                responsibility_score=float(batch.get("responsibility_score") or 0),
                llm_model=settings.llm_model,
                profession=standard.profession if standard else "",
            )
            db.set_batch_item(item["id"], "success", record_id=record_id,
                              candidate_name=candidate.name or "")
            logger.info("Batch %s: %s done -> %s", batch_id, item["filename"], record_id)
        except Exception as exc:  # keep going with the next candidate
            logger.error("Batch %s: %s failed: %s", batch_id, item["filename"], exc,
                         exc_info=True)
            db.set_batch_item(item["id"], "failed", message=str(exc))
        finally:
            db.refresh_batch(batch_id)

    if db.batch_status(batch_id) == "running":
        db.refresh_batch(batch_id, status="finished")
    logger.info("Batch %s finished", batch_id)
