"""Pydantic data models for the evaluation system."""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class EvalLevel(str, Enum):
    LEVEL_1 = "一级"
    LEVEL_2 = "二级"
    LEVEL_3 = "三级"
    LEVEL_4 = "四级"
    LEVEL_5 = "五级"
    LEVEL_6 = "六级"


class CandidateInfo(BaseModel):
    """Basic candidate information from PPT."""
    name: str = ""
    department: str = ""
    position: str = ""
    current_level: str = ""
    applied_level: str = ""
    years_of_experience: str = ""
    performance_last_two_years: str = ""
    professional_title: str = ""


class EvidenceItem(BaseModel):
    """A piece of evidence linking a score back to the source material."""
    page: int = 0          # 幻灯片页码（PPT 中的“幻灯片 N”）
    quote: str = ""        # 原文摘录
    note: str = ""         # 该证据支撑了什么


class EvaluationDimension(BaseModel):
    """A single dimension in the evaluation."""
    name: str
    full_score: float
    threshold: float
    score: Optional[float] = None
    score_percentage: Optional[float] = None
    comments: str = ""
    details: str = ""
    sub_dimensions: list = []
    evidence: list[EvidenceItem] = []   # 证据溯源
    pages: list[int] = []               # 证据涉及的页码（去重排序）


class ThresholdItem(BaseModel):
    """One basic-condition (threshold) check result."""
    field: str = ""
    label: str = ""
    required: str = ""
    status: str = ""
    detail: str = ""


class ThresholdCheck(BaseModel):
    """Structured threshold check outcome (kept out of chain_of_thought)."""
    overall_pass: bool = True
    items: list[ThresholdItem] = []


class EvaluationResult(BaseModel):
    """Complete evaluation result for one candidate."""
    candidate: CandidateInfo
    total_score: float
    total_full_score: float
    total_percentage: float
    passed: bool
    dimensions: list[EvaluationDimension]
    chain_of_thought: str = ""
    summary: str = ""
    strengths: list[str] = []
    improvements: list[str] = []
    suggestions: str = ""
    threshold_check: Optional[ThresholdCheck] = None
    record_id: Optional[str] = None


class LLMConfig(BaseModel):
    api_key: str
    base_url: str
    model: str


class ReportRequest(BaseModel):
    """Payload for PDF report generation."""
    result: EvaluationResult
    ppt_content: str = ""
    reviewer: str = ""
    organization: str = ""
    include_cot: bool = True


class ReviewUpdate(BaseModel):
    """Review workflow transition for an archived record."""
    status: str = "human_reviewed"
    reviewer: str = ""
    comment: str = ""


class PromptTemplatesUpdate(BaseModel):
    """Editable prompt templates (only provided keys are overridden)."""
    templates: dict[str, str] = {}


class PromptPreviewRequest(BaseModel):
    """Render the evaluation prompt for a standard without calling the LLM."""
    standard_filename: str = ""
    candidate_level: str = "三级"
    responsibility_score: float = 0.0


class RegressionRunRequest(BaseModel):
    """Consistency test: run the same demo material several times."""
    cases: list[str] = []
    repeats: int = 1
    responsibility_score: float = 0.0


class BaselineRequest(BaseModel):
    """Promote a finished regression job to the new baseline."""
    job_id: str


class UploadResponse(BaseModel):
    filename: str
    file_type: str
    candidate: CandidateInfo
    content: str
    message: str


class EvalRequest(BaseModel):
    candidate_level: str
    qualification_standard: str = ""
    ppt_content: str = ""
    llm_config: Optional[LLMConfig] = None


class EvalProgress(BaseModel):
    stage: str
    progress: int
    message: str
