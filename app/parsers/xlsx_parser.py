"""WPS-compatible .xlsx parser.

WPS Office generates .xlsx files without xl/sharedStrings.xml,
storing string values inline in each cell: <c r="A1" t="str"><is><t>text</t></is></c>.
Standard openpyxl can't read these files - this module fills that gap.
"""
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, List

NS = {
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


class XlsxReader:
    """Read WPS-generated .xlsx files into a dict of sheet_name -> 2D list.

    Handles both backslash-separated paths (WPS Windows bug) and
    both inline strings (WPS style) and shared string tables.
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.sheets: Dict[str, List[List[str]]] = {}
        self._shared_strings: List[str] = []

    @staticmethod
    def _zread(z: zipfile.ZipFile, path: str) -> bytes:
        """Read from zip, trying forward-slash first then backslash (WPS bug)."""
        try:
            return z.read(path)
        except KeyError:
            bs_path = path.replace("/", "\\")
            return z.read(bs_path)

    def _try_read(self, z: zipfile.ZipFile, path: str) -> bytes:
        """Try to read a file from zip, return empty bytes if not found."""
        try:
            return self._zread(z, path)
        except KeyError:
            return b""

    def parse(self) -> Dict[str, List[List[str]]]:
        """Parse all sheets and return {sheet_name: [[cell_value, ...], ...]}."""
        with zipfile.ZipFile(self.filepath, "r") as z:
            # Load shared strings if available
            self._load_shared_strings(z)
            sheet_map = self._get_sheet_map(z)
            for sheet_name, rel_id in sheet_map.items():
                self.sheets[sheet_name] = self._parse_sheet(z, rel_id)
        return self.sheets

    def _load_shared_strings(self, z: zipfile.ZipFile):
        """Load shared string table if it exists."""
        xml = self._try_read(z, "xl/sharedStrings.xml")
        if not xml:
            return
        root = ET.fromstring(xml)
        for si in root.findall(".//s:si", NS):
            # Collect all text within <si> (can be multiple <r><t> runs or plain <t>)
            parts = []
            for t in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"):
                if t.text:
                    parts.append(t.text)
            self._shared_strings.append("".join(parts))

    def _get_sheet_map(self, z: zipfile.ZipFile) -> Dict[str, str]:
        """Read workbook.xml to map sheet names to rId values."""
        wb_xml = self._zread(z, "xl/workbook.xml")
        root = ET.fromstring(wb_xml)
        sheet_map = {}
        for sheet_el in root.findall(".//s:sheet", NS):
            name = sheet_el.get("name", "")
            r_id = sheet_el.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id",
                "",
            )
            if name and r_id:
                sheet_map[name] = r_id
        return sheet_map

    def _parse_sheet(self, z: zipfile.ZipFile, r_id: str) -> List[List[str]]:
        """Parse a single sheet XML by relationship ID."""
        rels_xml = self._zread(z, "xl/_rels/workbook.xml.rels")
        rels_root = ET.fromstring(rels_xml)
        target = None
        for rel in rels_root.findall(".//s:Relationship",
            {"s": "http://schemas.openxmlformats.org/package/2006/relationships"}):
            if rel.get("Id") == r_id:
                target = rel.get("Target", "")
                break
        if not target:
            return []

        sheet_path = f"xl/{target}"
        sheet_xml = self._zread(z, sheet_path)
        return self._parse_sheet_xml(sheet_xml)

    def _get_cell_value(self, cell_el: ET.Element) -> str:
        """Extract cell value, handling inline strings and shared strings."""
        cell_type = cell_el.get("t", "")

        # Case 1: Inline string (WPS style) — <is><t>text</t></is>
        is_el = cell_el.find("s:is", NS)
        if is_el is not None:
            parts = []
            for t in is_el.findall(".//s:t", NS):
                if t.text:
                    parts.append(t.text)
            return "".join(parts)

        # Case 2: Shared string reference (t="s") — <v>index</v>
        v_el = cell_el.find("s:v", NS)
        if v_el is None or not v_el.text:
            return ""

        if cell_type == "s":
            try:
                idx = int(v_el.text)
                if idx < len(self._shared_strings):
                    return self._shared_strings[idx]
            except (ValueError, IndexError):
                pass

        # Case 3: Plain value (number, boolean, etc.)
        return v_el.text

    def _parse_sheet_xml(self, xml_bytes: bytes) -> List[List[str]]:
        """Parse sheet XML bytes into a 2D list of string values."""
        root = ET.fromstring(xml_bytes)
        rows = {}

        for row_el in root.findall(".//s:row", NS):
            row_num = int(row_el.get("r", "0"))
            row_data = {}

            for cell_el in row_el.findall("s:c", NS):
                cell_ref = cell_el.get("r", "")
                col = "".join(c for c in cell_ref if c.isalpha())
                value = self._get_cell_value(cell_el)
                if value:
                    row_data[col] = value

            if row_data:
                rows[row_num] = row_data

        if not rows:
            return []

        max_row = max(rows.keys())
        all_cols = set()
        for rdata in rows.values():
            all_cols.update(rdata.keys())

        max_col_idx = max(self._col_index(c) for c in all_cols) if all_cols else 0

        result = []
        for r in range(1, max_row + 1):
            row_data = rows.get(r, {})
            row_list = [row_data.get(self._col_str(i), "") for i in range(max_col_idx + 1)]
            result.append(row_list)

        return result

    @staticmethod
    def _col_index(c: str) -> int:
        result = 0
        for ch in c:
            result = result * 26 + (ord(ch.upper()) - ord("A") + 1)
        return result - 1

    @staticmethod
    def _col_str(idx: int) -> str:
        result = ""
        n = idx
        while n >= 0:
            result = chr(n % 26 + ord("A")) + result
            n = n // 26 - 1
        return result


def parse_xlsx_file(filepath: str) -> Dict[str, List[List[str]]]:
    """Parse a WPS-generated xlsx file. Returns {sheet_name: [[cell, ...], ...]}."""
    reader = XlsxReader(filepath)
    return reader.parse()
