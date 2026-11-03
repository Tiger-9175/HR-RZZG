"""Qualification standard parser — parses all 6 professional standard files.

Extracts for each profession:
  - Profession name and industry
  - Level-specific criteria (basic conditions, key capabilities)
  - Scoring weight allocations per level
  - Detailed scoring rules per level
"""
import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import xlrd
from app.parsers.xlsx_parser import parse_xlsx_file

logger = logging.getLogger(__name__)

# Map industry keywords from PPT paths to standard file keywords
INDUSTRY_MAP = {
    "冶金": "冶金",
    "机加": "机加",
    "系统集成": "系统集成",
    "结构装配": "结构装配",
    "钣金": "钣金",
    "非金属": "非金属",
    "铸造": "钣金",    # 铸造/塑形加工 → 钣金
    "部装": "结构装配",
    "总装": "系统集成",
    "非金属": "非金属",
    "非金属": "非金属",
}


def _read_sheet_rows(filepath: str) -> Dict[str, List[List[str]]]:
    """Read all sheets from an Excel file (xls or xlsx). Returns {sheet: [[cells]]}."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".xls":
        wb = xlrd.open_workbook(filepath)
        result = {}
        for sn in wb.sheet_names():
            ws = wb.sheet_by_name(sn)
            rows = []
            for r in range(ws.nrows):
                row = []
                for c in range(ws.ncols):
                    v = ws.cell_value(r, c)
                    if isinstance(v, float):
                        if v == int(v):
                            row.append(str(int(v)))
                        else:
                            row.append(str(v))
                    elif v:
                        row.append(str(v).strip())
                    else:
                        row.append("")
                rows.append(row)
            result[sn] = rows
        wb.release_resources()
        return result
    else:
        return parse_xlsx_file(filepath)


def _find_sheet(sheets: Dict[str, List[str]], *patterns: str) -> Optional[str]:
    """Find a sheet name matching any of the given patterns (flexible match)."""
    for sn in sheets:
        for pat in patterns:
            if pat in sn:
                return sn
    return None


def _get_profession_info(sheets: Dict[str, List[List[str]]]) -> Tuple[str, str]:
    """Extract profession name and industry from the standard."""
    std_sheet = _find_sheet(sheets, "任职资格标准")
    if not std_sheet:
        return ("未知", "未知")
    rows = sheets[std_sheet]
    if len(rows) < 2:
        return ("未知", "未知")
    title = rows[1][0] if rows[1] else ""

    # "专业技术序列-系统集成专业-任职资格标准" → profession="系统集成"
    # "专业技术序列-冶金-任职资格标准" → profession="冶金"
    profession = "未知"
    match = re.search(r"专业技术序列[—\-](.+?)(?:专业|加工)?[—\-]任职资格标准", title)
    if match:
        profession = match.group(1).strip()
    if profession == "未知" or not profession:
        match = re.search(r"(.+?)(?:专业|加工)[—\-]", title)
        if match:
            profession = match.group(1).strip()

    # Map profession to industry keyword
    industry = profession
    for kw, std in INDUSTRY_MAP.items():
        if kw == profession or kw in profession:
            industry = std
            break

    return (profession, industry)


class QualificationStandard:
    """Parsed qualification standard for one profession."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.profession = ""
        self.industry = ""
        self.title = ""

        # Basic conditions per level {level (1-6): {field: requirement}}
        self.basic_conditions: Dict[int, Dict[str, str]] = {}

        # Scoring weights per level {level: {dimension: max_score}}
        self.weights: Dict[int, Dict[str, float]] = {}

        # Detailed criteria per level {level: [{dim, standard, criteria, score, threshold, rules}]}
        self.scoring_rules: Dict[int, List[dict]] = {}

        # Raw text of all sheets for LLM context
        self.raw_text: str = ""

        self._parse()

    def _parse(self):
        """Parse the Excel file into structured data."""
        sheets = _read_sheet_rows(self.filepath)
        self.profession, self.industry = _get_profession_info(sheets)
        self.title = f"{self.profession}专业"

        # Parse weights
        weight_sheet = _find_sheet(sheets, "分值权重分配")
        if weight_sheet:
            self._parse_weights(sheets[weight_sheet])

        # Parse basic conditions (from 任职资格标准 sheet)
        std_sheet = _find_sheet(sheets, "任职资格标准")
        if std_sheet:
            self._parse_basic_conditions(sheets[std_sheet])

        # Parse per-level scoring rules
        for level in range(1, 7):
            level_cn = ["", "一", "二", "三", "四", "五", "六"][level]
            level_sheet = _find_sheet(sheets, f"{level_cn}级")
            if level_sheet:
                self._parse_level_rules(sheets[level_sheet], level)

        # Build raw text for LLM
        self._build_raw_text(sheets)

    def _parse_basic_conditions(self, rows: List[List[str]]):
        """Parse basic conditions from 任职资格标准 sheet."""
        # Find header row with levels
        header_row = -1
        for r, row in enumerate(rows):
            if any("一级" in c or "二级" in c for c in row):
                header_row = r
                break
        if header_row < 0:
            return

        # Map column to level
        col_level = {}
        for c, val in enumerate(rows[header_row]):
            for lv in range(1, 7):
                level_str = ["", "一", "二", "三", "四", "五", "六"][lv]
                if f"{level_str}级" in val:
                    col_level[c] = lv

        # Extract basic conditions rows
        fields = {"绩效": "performance", "职业资格": "certification",
                   "技术工作年限": "work_years", "组织回馈": "feedback"}
        for row in rows[header_row + 1:]:
            if len(row) < 3:
                continue
            dim = row[0] if row[0] else ""
            sub = row[2] if len(row) > 2 else ""
            field = ""
            for kw, key in fields.items():
                if kw in sub and sub.index(kw) < 5:
                    field = key
                    break
            if not field:
                if "基本条件" not in dim and field:
                    continue
            if field:
                for col, lv in col_level.items():
                    if col < len(row):
                        req = row[col].strip()
                        if req and req not in ("—", "/", "无"):
                            self.basic_conditions.setdefault(lv, {})[field] = req

    def _parse_weights(self, rows: List[List[str]]):
        """Parse scoring weights from 分值权重分配 sheet."""
        # Find header row
        header_row = -1
        for r, row in enumerate(rows):
            if any("一级" in c or "二级" in c for c in row):
                header_row = r
                break
        if header_row < 0:
            return

        col_level = {}
        for c, val in enumerate(rows[header_row]):
            for lv in range(1, 7):
                level_str = ["", "一", "二", "三", "四", "五", "六"][lv]
                if f"{level_str}级" in val:
                    col_level[c] = lv

        for row in rows[header_row + 1:]:
            if len(row) < 3:
                continue
            # Find dimension name
            dim_name = ""
            for c, v in enumerate(row):
                if v and v not in ("", "—", "无", "核心条件", "门槛条件") and not v.startswith("考试"):
                    if any(w in v for w in ["能力", "贡献", "结果"]):
                        dim_name = v
                        break
            if not dim_name:
                continue

            # Normalize dimension name
            dim_name = re.sub(r'\s+', '', dim_name)

            for col, lv in col_level.items():
                if col < len(row):
                    val = row[col].strip()
                    weight = self._parse_number(val)
                    if weight is not None and weight > 0:
                        self.weights.setdefault(lv, {})[dim_name] = weight

    @staticmethod
    def _parse_number(val: str) -> Optional[float]:
        """Try to parse a numeric value from a cell string."""
        if not val:
            return None
        val = val.replace("—", "").replace(" ", "")
        try:
            return float(val)
        except ValueError:
            return None

    def _parse_level_rules(self, rows: List[List[str]], level: int):
        """Parse detailed scoring rules for a specific level."""
        rules = []
        # Find header row
        header_row = -1
        for r, row in enumerate(rows):
            if any("标准" in (c or "") or "考察点" in (c or "") for c in row):
                header_row = r
                break
        if header_row < 0:
            return

        # Identify columns from header
        cols = {}
        for c, v in enumerate(rows[header_row]):
            if not v:
                continue
            if "标准" in v and "考察" not in v:
                cols["standard"] = c
            if "考察点" in v:
                cols["criteria"] = c
            if "举证" in v:
                cols["evidence"] = c
            if "分值" in v:
                cols["score"] = c
            if "达标" in v:
                cols["threshold"] = c
            if "打分" in v:
                cols["rules"] = c

        # Find dimension column — check header row itself
        dim_col = None
        for c, v in enumerate(rows[header_row]):
            if v and "维度" in str(v):
                dim_col = c
                break

        if dim_col is None:
            # Check rows before header too
            for r in range(header_row):
                for c, v in enumerate(rows[r]):
                    if v and "维度" in str(v):
                        dim_col = c
                        break
                if dim_col is not None:
                    break

        # Parse each row
        current_dim = ""
        for row in rows[header_row + 1:]:
            if not any(v for v in row):
                continue

            # Track dimension from dim_col
            if dim_col is not None and dim_col < len(row) and row[dim_col]:
                val = row[dim_col].strip()
                if val and val not in ("", "基本条件", "责任贡献", "关键能力"):
                    # This is a sub-dimension change
                    pass
                if val in ("基本条件", "责任贡献", "关键能力"):
                    current_dim = val

            # Get sub-dimension from dim_col+1 or dim_col+2
            sub = ""
            for offset in [1, 2]:
                idx = (dim_col or 0) + offset
                if dim_col is not None and idx < len(row) and row[idx]:
                    candidate = row[idx].strip()
                    if candidate and candidate not in current_dim:
                        sub = candidate
                        break

            standard = _cell_safe(row, cols, "standard")
            criteria = _cell_safe(row, cols, "criteria")
            score_str = _cell_safe(row, cols, "score").replace("\n", " ")
            threshold_str = _cell_safe(row, cols, "threshold").replace("\n", " ")
            rules_str = _cell_safe(row, cols, "rules")

            entry = {
                "dimension": current_dim,
                "sub_dimension": sub,
                "standard": standard,
                "criteria": criteria,
                "evidence": _cell_safe(row, cols, "evidence"),
                "max_score": self._parse_number(score_str) or 0,
                "threshold": self._parse_number(threshold_str) or 0,
                "scoring_rules": rules_str,
            }
            if entry["standard"] or entry["criteria"]:
                rules.append(entry)

        if rules:
            self.scoring_rules[level] = rules

    def _build_raw_text(self, sheets: Dict[str, List[List[str]]]):
        """Build a human-readable text representation for LLM context."""
        parts = []
        parts.append(f"专业: {self.profession}")
        parts.append(f"标题: {self.title}")

        # Basic conditions
        if self.basic_conditions:
            parts.append("\n## 基本条件（门槛）")
            for lv in sorted(self.basic_conditions):
                cond = self.basic_conditions[lv]
                parts.append(f"  {lv}级: " + " | ".join(f"{k}: {v}" for k, v in cond.items()))

        # Weights
        if self.weights:
            parts.append("\n## 分值权重分配（满分100分）")
            dims = set()
            for lv in self.weights:
                dims.update(self.weights[lv].keys())
            dims = sorted(dims, key=lambda d: sum(self.weights.get(lv, {}).get(d, 0) for lv in self.weights), reverse=True)
            header = "维度\\等级 | " + " | ".join(f"{lv}级" for lv in sorted(self.weights))
            parts.append(header)
            for dim in dims:
                row = dim
                for lv in sorted(self.weights):
                    w = self.weights[lv].get(dim, 0)
                    row += f" | {w:.0f}" if w else " | /"
                parts.append(row)

        # Per-level scoring rules
        for lv in sorted(self.scoring_rules):
            rules = self.scoring_rules[lv]
            parts.append(f"\n## {lv}级评分细则")
            for r in rules:
                parts.append(f"- [{r['dimension']}/{r['sub_dimension']}] 满分{r['max_score']}分, 达标{r['threshold']}分")
                if r['standard']:
                    parts.append(f"  标准: {r['standard'][:300]}")
                if r['criteria']:
                    parts.append(f"  考察点: {r['criteria'][:200]}")
                if r['scoring_rules']:
                    parts.append(f"  评分规则: {r['scoring_rules'][:300]}")

        self.raw_text = "\n".join(parts)


def _cell_safe(rows: List[str], cols: Dict[str, int], key: str) -> str:
    """Safely get cell value from column map."""
    if key not in cols:
        return ""
    c = cols[key]
    return rows[c] if c < len(rows) else ""


def load_all_standards(demo_dir: str) -> List[QualificationStandard]:
    """Load all qualification standard files from demo directory."""
    standards = []
    if not os.path.isdir(demo_dir):
        logger.warning(f"Demo directory not found: {demo_dir}")
        return standards

    for fname in sorted(os.listdir(demo_dir)):
        if "任职资格标准" not in fname:
            continue
        fpath = os.path.join(demo_dir, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            std = QualificationStandard(fpath)
            standards.append(std)
            logger.info(f"Loaded standard: {std.profession} ({fname})")
        except Exception as e:
            logger.error(f"Failed to parse standard {fname}: {e}", exc_info=True)

    return standards


def match_standard(standards: List[QualificationStandard],
                   candidate_industry: str = "",
                   candidate_position: str = "") -> Optional[QualificationStandard]:
    """Find the best-matching standard for a candidate."""
    if not standards:
        return None

    search_terms = [candidate_industry, candidate_position]

    for term in search_terms:
        if not term:
            continue
        for std in standards:
            if term in std.profession or term in std.industry or term in std.title:
                return std
        # Try INDUSTRY_MAP
        for kw, target in INDUSTRY_MAP.items():
            if kw in term:
                for std in standards:
                    if target in std.industry or target in std.profession:
                        return std

    return standards[0]  # fallback to first
