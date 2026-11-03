"""PPT file parser - handles the backslash path issue in some PPTX files."""
import zipfile
import shutil
import tempfile
import os
import logging
import xml.etree.ElementTree as ET
from pptx import Presentation
from pptx.util import Inches, Pt
from app.schemas.models import CandidateInfo

logger = logging.getLogger(__name__)


def fix_pptx_backslash(src_path: str) -> str:
    """Fix PPTX files that use backslash paths (Windows-generated)."""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.pptx')
    os.close(tmp_fd)
    try:
        with zipfile.ZipFile(src_path, 'r') as zin:
            with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)
                    fixed_name = item.filename.replace('\\', '/')
                    zout.writestr(fixed_name, data)
        return tmp_path
    except Exception as e:
        os.unlink(tmp_path)
        raise


def parse_pptx(file_path: str) -> tuple[list[dict], CandidateInfo]:
    """
    Parse a PPTX file and extract slide content and candidate info.
    Returns (slides_data, candidate_info).
    """
    candidate = CandidateInfo()
    slides_data = []
    tmp_path = None

    try:
        # Fix potential backslash path issues
        tmp_path = fix_pptx_backslash(file_path)
        prs = Presentation(tmp_path)

        for slide_idx, slide in enumerate(prs.slides):
            slide_content = {
                "index": slide_idx + 1,
                "texts": [],
                "tables": [],
                "shapes": [],
            }

            for shape in slide.shapes:
                shape_info = {"type": str(shape.shape_type), "name": shape.name}

                if shape.has_text_frame:
                    text = shape.text_frame.text.strip()
                    if text:
                        slide_content["texts"].append(text)
                        shape_info["text"] = text[:500]

                if shape.has_table:
                    table_data = []
                    table = shape.table
                    for row in table.rows:
                        cells = [cell.text.strip() for cell in row.cells]
                        table_data.append(cells)
                    slide_content["tables"].append(table_data)
                    shape_info["table"] = table_data

                slide_content["shapes"].append(shape_info)

            slides_data.append(slide_content)

        # Try to extract candidate info from the first few slides
        candidate = _extract_candidate_info(slides_data)

        return slides_data, candidate

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _extract_candidate_info(slides: list[dict]) -> CandidateInfo:
    """Extract candidate information from slide content."""
    info = CandidateInfo()

    # Get all text from first 5 slides
    all_text = []
    for slide in slides[:5]:
        all_text.extend(slide["texts"])
        for table in slide.get("tables", []):
            for row in table:
                all_text.extend(row)

    full_text = '\n'.join(all_text)

    # Extract name - look for "姓名：" pattern
    import re
    name_match = re.search(r'[姓]名[：:]\s*(\S+)', full_text)
    if name_match:
        info.name = name_match.group(1).strip()

    # Extract from filename patterns in PPT
    name_match2 = re.search(r'(?:申请人|姓名)[：:]\s*(\S+)', full_text)
    if not name_match and name_match2:
        info.name = name_match2.group(1).strip()

    # Extract department
    dept_match = re.search(r'(?:所在部门|部门|单位)[：:]\s*(\S+)', full_text)
    if dept_match:
        info.department = dept_match.group(1).strip()

    # Extract applied level
    level_match = re.search(r'(?:申请认证等级|申请等级|申请)[：:]\s*(\S+)', full_text)
    if level_match:
        info.applied_level = level_match.group(1).strip()

    # Extract performance
    perf_match = re.search(r'(?:近两年度考核结果|考核结果)[：:]\s*(\S+)', full_text)
    if perf_match:
        info.performance_last_two_years = perf_match.group(1).strip()

    # Try to find name from title slide
    if not info.name and slides:
        first_text = '\n'.join(slides[0]["texts"])
        # Look for common patterns
        lines = [l.strip() for l in first_text.split('\n') if l.strip()]
        for line in lines:
            if '答辩' in line or '申请' in line:
                # Try to find name embedded in title
                m = re.search(r'[—\-–]\s*(\S{2,4})\s*$', line)
                if m:
                    info.name = m.group(1)

    return info


def pptx_to_markdown(slides: list[dict]) -> str:
    """Convert parsed PPT content to markdown text for LLM processing."""
    md_parts = []

    for slide in slides:
        md_parts.append(f"\n## 幻灯片 {slide['index']}\n")

        for text in slide["texts"]:
            md_parts.append(text + "\n")

        for table in slide.get("tables", []):
            if table:
                md_parts.append("| " + " | ".join(table[0]) + " |")
                md_parts.append("| " + " | ".join(["---"] * len(table[0])) + " |")
                for row in table[1:]:
                    md_parts.append("| " + " | ".join(row) + " |")

    return '\n'.join(md_parts)
