"""Excel file parser for qualification standards and job descriptions."""
import zipfile
import os
import logging
import xml.etree.ElementTree as ET
from typing import Any

logger = logging.getLogger(__name__)

# XML namespace for spreadsheetml
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
RELS_NS = {'r': 'http://schemas.openxmlformats.org/package/2006/relationships'}
WB_NS = {
    's': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
}


def _fix_path(p: str) -> str:
    """Normalize backslash to forward slash."""
    return p.replace('\\', '/')


class ExcelReader:
    """Reader for .xlsx files with backslash path support."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.shared_strings: dict[int, str] = {}
        self.sheets: dict[str, list[dict[str, Any]]] = {}
        self._parse()

    def _parse(self):
        """Parse the xlsx file."""
        with zipfile.ZipFile(self.file_path, 'r') as z:
            names = [_fix_path(n) for n in z.namelist()]
            raw_map = {_fix_path(k): v for k, v in
                       [(n, z.read(n)) for n in z.namelist()]}

            # Read shared strings
            ss_key = [k for k in raw_map if k.endswith('sharedStrings.xml')]
            if ss_key:
                self._parse_shared_strings(raw_map[ss_key[0]])

            # Get sheet names and file mapping
            wb_key = [k for k in raw_map if k.endswith('workbook.xml')]
            if not wb_key:
                raise ValueError("No workbook.xml found")

            sheet_names = self._get_sheet_names(raw_map[wb_key[0]])

            # Read each sheet
            for sheet_name, sheet_file in sheet_names:
                if sheet_file in raw_map:
                    rows = self._parse_sheet(raw_map[sheet_file])
                    self.sheets[sheet_name] = rows

    def _parse_shared_strings(self, xml_data: bytes):
        """Parse shared strings table."""
        root = ET.fromstring(xml_data)
        for i, si in enumerate(root.findall('.//s:si', NS)):
            texts = []
            for t in si.findall('.//s:t', NS):
                if t.text:
                    texts.append(t.text)
            self.shared_strings[i] = ''.join(texts)

    def _get_sheet_names(self, xml_data: bytes) -> list[tuple[str, str]]:
        """Get mapping of sheet names to file paths."""
        root = ET.fromstring(xml_data)
        # Get relationships
        sheets = []
        for sheet in root.findall('.//s:sheet', WB_NS):
            name = sheet.get('name')
            sheet_id = int(sheet.get('sheetId', 0))
            # sheet files are named sheet{id}.xml
            sheet_file = f"xl/worksheets/sheet{sheet_id}.xml"
            sheets.append((name, sheet_file))
        return sheets

    def _parse_sheet(self, xml_data: bytes) -> list[dict[str, Any]]:
        """Parse a worksheet."""
        root = ET.fromstring(xml_data)
        rows = []

        for row_el in root.findall('.//s:sheetData/s:row', NS):
            row_num = int(row_el.get('r', 0))
            row_data = {"_row": row_num}

            for c in row_el.findall('s:c', NS):
                ref = c.get('r', '')
                col = ref[0] if ref else ''
                cell_type = c.get('t', '')
                val_el = c.find('s:v', NS)
                raw_val = val_el.text if val_el is not None else ''

                if cell_type == 's' and raw_val:
                    try:
                        val = self.shared_strings.get(int(raw_val), raw_val)
                    except (ValueError, IndexError):
                        val = raw_val
                else:
                    val = raw_val

                row_data[col] = val

            rows.append(row_data)

        return rows

    def get_sheet(self, name: str) -> list[dict[str, Any]]:
        """Get rows for a specific sheet."""
        return self.sheets.get(name, [])

    def get_sheet_names(self) -> list[str]:
        return list(self.sheets.keys())


def parse_qualification_standard(file_path: str) -> dict:
    """
    Parse a qualification standard Excel file.
    Returns structured data organized by level and dimension.
    """
    reader = ExcelReader(file_path)

    result = {
        "industry": "",
        "description": "",
        "levels": {},
        "weight_distribution": {},
        "difficulty_guide": [],
    }

    # Get basic info
    basic_info = reader.get_sheet("基本信息")
    if basic_info:
        for row in basic_info:
            a = row.get('A', '')
            b = row.get('B', '')
            if '专业技术序列' in str(a):
                result["description"] = str(b or a)

    # Get weight distribution
    weights = reader.get_sheet("分值权重分配")
    if weights:
        for row in weights:
            dim = row.get('A', '') or row.get('C', '') or ''
            if dim and dim != '维度':
                levels_data = {}
                for level_col, level_name in [
                    ('E', '一级'), ('F', '二级'), ('G', '三级'),
                    ('H', '四级'), ('I', '五级'), ('J', '六级')
                ]:
                    val = row.get(level_col, '')
                    if val:
                        levels_data[level_name] = val
                result["weight_distribution"][str(dim).strip()] = levels_data

    # Parse level-specific scoring rules
    level_sheets = {
        '一级细则': '一级', '二级细则': '二级', '三级细则': '三级',
        '四级细则': '四级', '五级细则': '五级', '六级细则': '六级'
    }

    for sheet_name, level_name in level_sheets.items():
        sheet_data = reader.get_sheet(sheet_name)
        if sheet_data:
            level_info = {"dimensions": [], "full_score": 100}
            current_dim = ""
            for row in sheet_data:
                dim = row.get('A', '') or row.get('C', '') or ''
                if dim and dim != '维度' and str(dim).strip():
                    current_dim = str(dim).strip()
                score = row.get('H', '')
                threshold = row.get('I', '')
                standard = row.get('E', '')
                inspection = row.get('F', '')
                scoring_rules = row.get('J', '')

                if current_dim and score:
                    level_info["dimensions"].append({
                        "name": current_dim,
                        "full_score": str(score),
                        "threshold": str(threshold),
                        "standard": str(standard)[:300],
                        "inspection_points": str(inspection)[:200],
                        "scoring_rules": str(scoring_rules)[:500],
                    })

            result["levels"][level_name] = level_info

    # Parse difficulty guide
    difficulty = reader.get_sheet("★项目难度层级指引★")
    if not difficulty:
        # Try alternative names
        for name in reader.get_sheet_names():
            if '难度' in name:
                difficulty = reader.get_sheet(name)
                break

    if difficulty:
        for row in difficulty:
            level = row.get('A', '')
            level_name = row.get('B', '')
            desc = row.get('C', '')
            if level:
                result["difficulty_guide"].append({
                    "level": str(level),
                    "name": str(level_name),
                    "description": str(desc),
                })

    return result


def parse_job_description(file_path: str) -> dict:
    """Parse a job description Excel file."""
    reader = ExcelReader(file_path)
    result = {"sheets": {}}
    for name in reader.get_sheet_names():
        rows = reader.get_sheet(name)
        result["sheets"][name] = rows
    return result


def standard_to_text(standard: dict) -> str:
    """Convert qualification standard to text for LLM context."""
    lines = []
    lines.append(f"# 任职资格标准\n")
    lines.append(f"概述：{standard.get('description', '')}\n")

    lines.append("## 分值权重分配\n")
    for dim, weights in standard.get("weight_distribution", {}).items():
        weight_str = " | ".join([f"{k}:{v}" for k, v in weights.items()])
        lines.append(f"- {dim}: {weight_str}")

    if standard.get("difficulty_guide"):
        lines.append("\n## 项目难度层级指引\n")
        for g in standard["difficulty_guide"]:
            lines.append(f"- Level {g['level']} ({g['name']}): {g['description']}")

    lines.append("\n## 各等级评分细则\n")
    for level_name, level_data in standard.get("levels", {}).items():
        lines.append(f"\n### {level_name}\n")
        lines.append(f"总分：{level_data.get('full_score', 100)}分\n")
        for dim in level_data.get("dimensions", []):
            lines.append(f"**{dim['name']}**")
            lines.append(f"- 标准：{dim.get('standard', '')}")
            lines.append(f"- 考察点：{dim.get('inspection_points', '')}")
            lines.append(f"- 分值：{dim.get('full_score', '')} | 达标值：{dim.get('threshold', '')}")
            lines.append(f"- 打分规则：{dim.get('scoring_rules', '')}")
            lines.append("")

    return '\n'.join(lines)
