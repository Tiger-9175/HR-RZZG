"""Consistency / drift regression runs.

Runs the same demo materials through the pipeline ``repeats`` times and reports
score stability plus the delta against a stored baseline. Regression runs never
persist evaluation records — they are a QA tool, not business data.

Jobs live in memory (a QA session), the baseline is stored on disk.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import statistics
import uuid
from datetime import datetime
from typing import Optional

from app.core.config import settings
from app.evaluation import prompts
from app.evaluation.engine import evaluate_candidate, find_standard_for_candidate
from app.parsers.ppt_parser import parse_pptx, pptx_to_markdown

logger = logging.getLogger(__name__)

BASELINE_FILE = "regression_baseline.json"
_jobs: dict[str, dict] = {}
_tasks: dict[str, asyncio.Task] = {}


# ------------------------------------------------------------------ baseline ----
def baseline_path() -> str:
    return os.path.join(settings.data_dir, BASELINE_FILE)


def load_baseline() -> dict:
    path = baseline_path()
    if not os.path.exists(path):
        return {"created_at": None, "model": "", "prompt_hash": "", "cases": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("cases", {})
        return data
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to load regression baseline: %s", exc)
        return {"created_at": None, "model": "", "prompt_hash": "", "cases": {}}


def save_baseline(cases: dict) -> dict:
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "model": settings.llm_model,
        "prompt_hash": prompts.template_hash(),
        "cases": cases,
    }
    os.makedirs(settings.data_dir, exist_ok=True)
    with open(baseline_path(), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info("Regression baseline saved: %d case(s)", len(cases))
    return payload


def delete_baseline() -> None:
    path = baseline_path()
    if os.path.exists(path):
        os.remove(path)


# ----------------------------------------------------------------------- jobs ----
def list_jobs(limit: int = 20) -> list[dict]:
    jobs = sorted(_jobs.values(), key=lambda j: j["created_at"], reverse=True)
    return [_job_view(j, with_results=False) for j in jobs[:limit]]


def get_job(job_id: str) -> Optional[dict]:
    job = _jobs.get(job_id)
    return _job_view(job, with_results=True) if job else None


def _job_view(job: dict, with_results: bool = True) -> dict:
    data = {k: v for k, v in job.items() if k != "results"}
    data["progress"] = round(job["finished"] / job["total"] * 100, 1) if job["total"] else 0
    if with_results:
        data["results"] = job["results"]
    return data


def create_job(cases: list[str], repeats: int = 1,
               responsibility_score: float = 0.0) -> dict:
    job_id = uuid.uuid4().hex[:12]
    job = {
        "id": job_id,
        "status": "running",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "model": settings.llm_model,
        "prompt_hash": prompts.template_hash(),
        "repeats": max(1, min(5, int(repeats or 1))),
        "responsibility_score": float(responsibility_score or 0),
        "total": len(cases),
        "finished": 0,
        "error": "",
        "results": [],
    }
    _jobs[job_id] = job
    task = asyncio.create_task(_run(job_id, cases, job["repeats"],
                                    job["responsibility_score"]))
    _tasks[job_id] = task
    task.add_done_callback(lambda _t: _tasks.pop(job_id, None))
    logger.info("Regression job %s started (%d cases x %d)", job_id, len(cases),
                job["repeats"])
    return _job_view(job)


async def _run(job_id: str, cases: list[str], repeats: int,
               responsibility_score: float) -> None:
    job = _jobs[job_id]
    baseline = load_baseline()
    if not prompts_can_run():
        job["status"] = "failed"
        job["error"] = "大模型未配置，无法执行回归测试"
        return

    for filename in cases:
        entry = {
            "filename": filename,
            "candidate": "",
            "runs": [],
            "stats": {},
            "baseline": baseline.get("cases", {}).get(filename),
            "delta": None,
            "error": "",
        }
        try:
            path = os.path.join(settings.demo_dir, filename)
            slides, candidate = parse_pptx(path)
            content = pptx_to_markdown(slides)
            level = candidate.applied_level or "三级"
            standard = find_standard_for_candidate(
                ppt_content=content, candidate_position=candidate.position or "")
            entry["candidate"] = candidate.name
            entry["level"] = level
            entry["profession"] = standard.profession if standard else ""

            for _ in range(repeats):
                result = await evaluate_candidate(
                    ppt_content=content,
                    standard=standard,
                    candidate_level=level,
                    responsibility_score=responsibility_score,
                )
                entry["runs"].append({
                    "total_score": result.total_score,
                    "total_percentage": result.total_percentage,
                    "passed": result.passed,
                    "dimensions": {d.name: d.score for d in result.dimensions},
                })

            entry["stats"] = _stats(entry["runs"])
            base = entry["baseline"]
            if base and base.get("mean_percentage") is not None:
                entry["delta"] = round(
                    entry["stats"]["mean_percentage"] - base["mean_percentage"], 1)
                base_dims = base.get("dimensions") or {}
                entry["dimension_delta"] = {
                    name: round(value["mean"] - base_dims[name]["mean"], 1)
                    for name, value in entry["stats"]["dimensions"].items()
                    if name in base_dims
                }
        except Exception as exc:
            logger.error("Regression case failed %s: %s", filename, exc, exc_info=True)
            entry["error"] = str(exc)[:300]

        job["results"].append(entry)
        job["finished"] += 1

    job["status"] = "finished"
    logger.info("Regression job %s finished", job_id)


def prompts_can_run() -> bool:
    from app.core.llm import llm_client

    return bool(llm_client.client)


def _stats(runs: list[dict]) -> dict:
    """Mean/std over repeated runs, including per dimension."""
    if not runs:
        return {}
    pcts = [float(r["total_percentage"] or 0) for r in runs]
    totals = [float(r["total_score"] or 0) for r in runs]

    dim_values: dict[str, list[float]] = {}
    for run in runs:
        for name, score in (run.get("dimensions") or {}).items():
            if score is None:
                continue
            dim_values.setdefault(name, []).append(float(score))

    dimensions = {
        name: {"mean": round(statistics.mean(values), 1),
               "std": round(statistics.pstdev(values), 2) if len(values) > 1 else 0.0}
        for name, values in dim_values.items()
    }
    return {
        "runs": len(runs),
        "mean_percentage": round(statistics.mean(pcts), 1),
        "std_percentage": round(statistics.pstdev(pcts), 2) if len(pcts) > 1 else 0.0,
        "min_percentage": round(min(pcts), 1),
        "max_percentage": round(max(pcts), 1),
        "mean_total": round(statistics.mean(totals), 1),
        "pass_rate": round(sum(1 for r in runs if r.get("passed")) / len(runs) * 100, 1),
        "dimensions": dimensions,
    }


def baseline_from_job(job_id: str, only_successful: bool = True) -> dict:
    """Store a finished job's mean scores as the new baseline."""
    job = _jobs.get(job_id)
    if not job:
        raise KeyError("回归任务不存在")
    if job["status"] == "running":
        raise ValueError("任务尚未完成")

    cases = {}
    for entry in job["results"]:
        if only_successful and (entry.get("error") or not entry.get("stats")):
            continue
        cases[entry["filename"]] = {
            "candidate": entry.get("candidate"),
            "level": entry.get("level"),
            "profession": entry.get("profession"),
            "mean_percentage": entry["stats"]["mean_percentage"],
            "std_percentage": entry["stats"]["std_percentage"],
            "runs": entry["stats"]["runs"],
            "dimensions": entry["stats"]["dimensions"],
        }
    if not cases:
        raise ValueError("没有可写入基线的成功用例")
    return save_baseline(cases)
