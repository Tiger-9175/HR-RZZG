"""PDF report generation based on reportlab.

Produces a formal A4 evaluation report from an ``EvaluationResult`` dict.
Chinese fonts are resolved from the host system with a CJK CID-font fallback,
so the same code works on Windows dev machines and Linux containers.
"""
from __future__ import annotations

import datetime
import io
import logging
import os
from typing import Any, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)
from xml.sax.saxutils import escape

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- fonts ----
FONT_REG = "ReportCJK"
FONT_BOLD = "ReportCJK-Bold"

_REGULAR_FONTS = [
    ("C:/Windows/Fonts/msyh.ttc", 0),          # 微软雅黑
    ("C:/Windows/Fonts/simhei.ttf", None),     # 黑体
    ("C:/Windows/Fonts/simsun.ttc", 0),        # 宋体
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 0),
    ("/usr/share/fonts/truetype/arphic/uming.ttc", 0),
    ("/System/Library/Fonts/PingFang.ttc", 0),
]

_BOLD_FONTS = [
    ("C:/Windows/Fonts/msyhbd.ttc", 0),
    ("C:/Windows/Fonts/simhei.ttf", None),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 0),
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 0),
]

_fonts_ready = False


def _try_register(name: str, candidates) -> bool:
    for path, index in candidates:
        if not os.path.exists(path):
            continue
        try:
            if index is None:
                pdfmetrics.registerFont(TTFont(name, path))
            else:
                pdfmetrics.registerFont(TTFont(name, path, subfontIndex=index))
            return True
        except Exception as exc:  # pragma: no cover - font specific
            logger.warning("Register font failed %s: %s", path, exc)
    return False


def ensure_fonts() -> None:
    """Register a Chinese font family (idempotent)."""
    global _fonts_ready
    if _fonts_ready:
        return

    ok = _try_register(FONT_REG, _REGULAR_FONTS)
    if not ok:
        # Built-in CID font: supports Chinese without shipping a TTF file.
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        globals()["FONT_REG"] = "STSong-Light"
        logger.info("PDF report font: STSong-Light (CID fallback)")
        _fonts_ready = True
        return

    if not _try_register(FONT_BOLD, _BOLD_FONTS):
        pdfmetrics.registerFont(TTFont(FONT_BOLD, _REGULAR_FONTS[0][0]))
    pdfmetrics.registerFontFamily(FONT_REG, normal=FONT_REG, bold=FONT_BOLD,
                                  italic=FONT_REG, boldItalic=FONT_BOLD)
    logger.info("PDF report font registered: %s", FONT_REG)
    _fonts_ready = True


def _reg() -> str:
    ensure_fonts()
    return globals().get("FONT_REG", FONT_REG)


def _bold() -> str:
    ensure_fonts()
    if _reg() == "STSong-Light":
        return "STSong-Light"
    return globals().get("FONT_BOLD", FONT_BOLD)


# --------------------------------------------------------------- colors ----
BLUE = colors.HexColor("#1a73e8")
DARK = colors.HexColor("#1f2937")
GRAY = colors.HexColor("#6b7280")
LIGHT_GRAY = colors.HexColor("#e5e7eb")
BG_GRAY = colors.HexColor("#f9fafb")
GREEN = colors.HexColor("#34a853")
ORANGE = colors.HexColor("#f97316")
RED = colors.HexColor("#ef4444")


def _fmt(value: Any, digits: int = 1, dash: str = "-") -> str:
    if value is None or value == "":
        return dash
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:.{digits}f}"


def _ratio_color(ratio: Optional[float]):
    if ratio is None:
        return GRAY
    if ratio >= 0.8:
        return GREEN
    if ratio >= 0.6:
        return BLUE
    if ratio >= 0.4:
        return ORANGE
    return RED


_HEX = {GREEN: "#34a853", BLUE: "#1a73e8", ORANGE: "#f97316", RED: "#ef4444",
        GRAY: "#6b7280", DARK: "#1f2937"}


def _ratio_hex(ratio: Optional[float]) -> str:
    """CSS hex color for a score ratio (for use inside Paragraph markup)."""
    return _HEX.get(_ratio_color(ratio), "#1f2937")


# --------------------------------------------------------------- styles ----
def _styles() -> dict:
    reg, bold = _reg(), _bold()
    return {
        "title": ParagraphStyle("title", fontName=bold, fontSize=20, leading=28,
                                alignment=TA_CENTER, textColor=DARK, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", fontName=reg, fontSize=9, leading=14,
                                   alignment=TA_CENTER, textColor=GRAY,
                                   spaceAfter=10, wordWrap="CJK"),
        "h2": ParagraphStyle("h2", fontName=bold, fontSize=12.5, leading=18,
                             textColor=BLUE, spaceBefore=12, spaceAfter=8,
                             wordWrap="CJK"),
        "body": ParagraphStyle("body", fontName=reg, fontSize=10, leading=16.5,
                               textColor=DARK, alignment=TA_LEFT, wordWrap="CJK",
                               spaceAfter=4),
        "label": ParagraphStyle("label", fontName=reg, fontSize=9.5, leading=15,
                                textColor=GRAY, wordWrap="CJK"),
        "cell": ParagraphStyle("cell", fontName=reg, fontSize=9, leading=13.5,
                               textColor=DARK, wordWrap="CJK", alignment=TA_LEFT),
        "cell_center": ParagraphStyle("cell_center", fontName=reg, fontSize=9,
                                      leading=13.5, textColor=DARK, wordWrap="CJK",
                                      alignment=TA_CENTER),
        "head": ParagraphStyle("head", fontName=bold, fontSize=9.5, leading=14,
                               textColor=colors.white, alignment=TA_CENTER,
                               wordWrap="CJK"),
        "small": ParagraphStyle("small", fontName=reg, fontSize=8.5, leading=13,
                                textColor=GRAY, wordWrap="CJK"),
        "cot": ParagraphStyle("cot", fontName=reg, fontSize=8.5, leading=13,
                              textColor=colors.HexColor("#374151"), wordWrap="CJK",
                              backColor=colors.HexColor("#fafbfc"),
                              borderPadding=6, spaceAfter=4),
    }


def _para(text: Any, style, default: str = "暂无") -> Paragraph:
    raw = "" if text is None else str(text).strip()
    if not raw:
        raw = default
    html = escape(raw).replace("\r\n", "\n").replace("\n", "<br/>")
    return Paragraph(html, style)


# ------------------------------------------------------------- flowables ----
class ScoreBar(Flowable):
    """Horizontal bar: score against full score, with threshold marker."""

    def __init__(self, score, full, threshold=0, width=165 * mm, height=9 * mm,
                 label=""):
        super().__init__()
        self.score = float(score or 0)
        self.full = float(full or 0)
        self.threshold = float(threshold or 0)
        self.width = width
        self.height = height
        self.label = label

    def wrap(self, availWidth, availHeight):
        self.width = min(self.width, availWidth)
        return self.width, self.height

    def draw(self):
        c = self.canv
        label_w = 46 * mm
        bar_x = label_w
        bar_w = self.width - label_w - 26 * mm
        bar_y = self.height / 2 - 3 * mm
        bar_h = 6 * mm

        c.setFont(_reg(), 9)
        c.setFillColor(DARK)
        c.drawString(0, self.height / 2 - 3 * mm, self.label[:16])

        # track
        c.setFillColor(colors.HexColor("#eef1f5"))
        c.roundRect(bar_x, bar_y, bar_w, bar_h, 3 * mm, stroke=0, fill=1)

        ratio = (self.score / self.full) if self.full else 0
        ratio = max(0.0, min(1.0, ratio))
        if ratio > 0:
            c.setFillColor(_ratio_color(ratio))
            c.roundRect(bar_x, bar_y, max(bar_w * ratio, 2 * mm), bar_h, 3 * mm,
                        stroke=0, fill=1)

        # threshold marker
        if self.full and self.threshold:
            tx = bar_x + bar_w * min(1.0, self.threshold / self.full)
            c.setStrokeColor(colors.HexColor("#9ca3af"))
            c.setLineWidth(0.8)
            c.setDash(2, 2)
            c.line(tx, bar_y - 1.2 * mm, tx, bar_y + bar_h + 1.2 * mm)
            c.setDash()

        c.setFont(_bold(), 9)
        c.setFillColor(DARK)
        c.drawRightString(self.width, self.height / 2 - 3 * mm,
                          f"{self.score:.1f}/{self.full:.0f}")


class NumberedCanvas(rl_canvas.Canvas):
    """Canvas that prints '第 X 页 / 共 Y 页' after the total is known."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_pages = []

    def showPage(self):
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_pages)
        for state in self._saved_pages:
            self.__dict__.update(state)
            self._draw_footer(total)
            super().showPage()
        super().save()

    def _draw_footer(self, total: int):
        self.saveState()
        self.setStrokeColor(LIGHT_GRAY)
        self.setLineWidth(0.5)
        self.line(16 * mm, 15 * mm, A4[0] - 16 * mm, 15 * mm)
        self.setFont(_reg(), 8)
        self.setFillColor(GRAY)
        self.drawString(16 * mm, 10.5 * mm,
                        "本报告由人工智能辅助生成，仅供任职资格评价参考，最终结论以评审委员会意见为准。")
        self.drawRightString(A4[0] - 16 * mm, 10.5 * mm,
                             f"第 {self._pageNumber} 页 / 共 {total} 页")
        self.restoreState()


# ------------------------------------------------------------------ build ----
def _candidate_rows(candidate: dict, st: dict) -> Table:
    fields = [
        ("姓名", candidate.get("name")),
        ("所在部门", candidate.get("department")),
        ("申报等级", candidate.get("applied_level")),
        ("当前等级", candidate.get("current_level")),
        ("技术工作年限", candidate.get("years_of_experience")),
        ("近两年绩效", candidate.get("performance_last_two_years")),
        ("职称/职业资格", candidate.get("professional_title")),
        ("报告生成时间", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")),
    ]
    data = []
    for i in range(0, len(fields), 2):
        row = []
        for label, value in fields[i:i + 2]:
            row.append(Paragraph(f"<font color='#6b7280'>{label}</font>", st["cell"]))
            row.append(_para(value, st["cell"]))
        data.append(row)

    table = Table(data, colWidths=[30 * mm, 55 * mm, 30 * mm, 55 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, LIGHT_GRAY),
        ("BACKGROUND", (0, 0), (0, -1), BG_GRAY),
        ("BACKGROUND", (2, 0), (2, -1), BG_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _conclusion_block(result: dict, st: dict) -> Table:
    passed = bool(result.get("passed"))
    color = GREEN if passed else RED
    score = _fmt(result.get("total_score"))
    full = _fmt(result.get("total_full_score"), 0)
    pct = _fmt(result.get("total_percentage"))
    verdict = "通过" if passed else "未通过"

    left = Paragraph(
        f"<font size=11 color='#6b7280'>综合评价结论</font><br/>"
        f"<font size=17 color='{'#34a853' if passed else '#ef4444'}'>{verdict}</font>",
        st["cell"],
    )
    right = Paragraph(
        f"<font size=11 color='#6b7280'>综合得分</font><br/>"
        f"<font size=17 color='#1a73e8'>{score}</font>"
        f"<font size=10 color='#6b7280'> / {full}（{pct}%）</font>",
        st["cell"],
    )
    table = Table([[left, right]], colWidths=[85 * mm, 85 * mm])
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, color),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f6fbf7" if passed
                                                         else "#fef7f7")),
        ("LINEBEFORE", (1, 0), (1, 0), 0.6, LIGHT_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
    ]))
    return table


def _dimension_table(dimensions: list, st: dict) -> Table:
    header = ["评价维度", "得分", "满分", "达标线", "达成率", "判定"]
    data = [[Paragraph(h, st["head"]) for h in header]]
    for dim in dimensions:
        score = dim.get("score")
        full = dim.get("full_score") or 0
        threshold = dim.get("threshold") or 0
        ratio = (score / full) if (score is not None and full) else None
        ok = (score is not None and score >= threshold) if threshold else None
        mark = "达标" if ok else ("未达标" if ok is False else "—")
        mark_color = "#34a853" if ok else ("#ef4444" if ok is False else "#6b7280")
        data.append([
            _para(dim.get("name"), st["cell"]),
            Paragraph(f"<font color='{_ratio_hex(ratio)}'>{_fmt(score)}</font>",
                      st["cell_center"]),
            Paragraph(_fmt(full, 0), st["cell_center"]),
            Paragraph(_fmt(threshold, 0) if threshold else "—", st["cell_center"]),
            Paragraph(f"{_fmt(ratio * 100 if ratio is not None else None, 0)}%"
                      if ratio is not None else "—", st["cell_center"]),
            Paragraph(f"<font color='{mark_color}'>{mark}</font>", st["cell_center"]),
        ])

    table = Table(data, colWidths=[62 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm, 20 * mm],
                  repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("GRID", (0, 0), (-1, -1), 0.4, LIGHT_GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_GRAY]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _threshold_table(items: list, st: dict) -> Table:
    header = ["门槛条件", "标准要求", "核查结论", "判断依据"]
    data = [[Paragraph(h, st["head"]) for h in header]]
    for item in items:
        status = str(item.get("status") or "")
        if status.startswith("✅"):
            color = "#34a853"
        elif status.startswith("⚠️"):
            color = "#f97316"
        else:
            color = "#ef4444"
        data.append([
            _para(item.get("label") or item.get("field"), st["cell"]),
            _para(str(item.get("required") or "—")[:200], st["cell"]),
            Paragraph(f"<font color='{color}'>{escape(status or '—')}</font>",
                      st["cell_center"]),
            _para(str(item.get("detail") or "—")[:300], st["cell"]),
        ])

    table = Table(data, colWidths=[26 * mm, 44 * mm, 22 * mm, 74 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#374151")),
        ("GRID", (0, 0), (-1, -1), 0.4, LIGHT_GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_GRAY]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _bullet_list(items, st: dict, color) -> list:
    flows = []
    for item in items or []:
        text = str(item).strip()
        if not text:
            continue
        flows.append(Paragraph(
            f"<font color='{color}'>&#9632;</font> {escape(text)}", st["body"]))
    if not flows:
        flows.append(Paragraph("暂无", st["body"]))
    return flows


def build_report_pdf(result: dict, ppt_content: str = "", reviewer: str = "",
                     organization: str = "", include_cot: bool = True) -> bytes:
    """Render an evaluation result into a PDF document (bytes)."""
    ensure_fonts()
    st = _styles()
    now = datetime.datetime.now()
    report_no = f"CF-{now:%Y%m%d}-{now:%H%M%S}"
    candidate = result.get("candidate") or {}
    dimensions = result.get("dimensions") or []
    name = candidate.get("name") or "候选人"
    level = candidate.get("applied_level") or ""

    buf = io.BytesIO()
    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=16 * mm, bottomMargin=20 * mm,
        title=f"任职资格评价报告 - {name}",
        author="昌飞任职资格智能评价系统",
        subject="任职资格认证评价报告",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="report", frames=[frame])])

    story: list = []
    _cn = ["", "一", "二", "三", "四", "五", "六", "七", "八"]
    counter = {"n": 0}

    def h(text: str) -> Paragraph:
        counter["n"] += 1
        return Paragraph(f"{_cn[counter['n']]}、{text}", st["h2"])

    threshold_items = (result.get("threshold_check") or {}).get("items") or []

    story.append(Paragraph("任职资格认证评价报告", st["title"]))
    story.append(Paragraph(
        f"报告编号：{report_no}　|　生成时间：{now:%Y-%m-%d %H:%M}"
        + (f"　|　评价单位：{escape(organization)}" if organization else ""),
        st["subtitle"]))
    story.append(Spacer(1, 4 * mm))

    story.append(h("候选人基本信息"))
    story.append(_candidate_rows(candidate, st))
    story.append(Spacer(1, 6 * mm))
    story.append(_conclusion_block(result, st))

    if threshold_items:
        story.append(h("门槛条件核查"))
        story.append(_threshold_table(threshold_items, st))
        story.append(Spacer(1, 3 * mm))

    story.append(h("各维度得分明细"))
    if dimensions:
        story.append(_dimension_table(dimensions, st))
        story.append(Spacer(1, 4 * mm))
        bars = []
        for dim in dimensions:
            bars.append(ScoreBar(
                dim.get("score"), dim.get("full_score") or 0,
                dim.get("threshold") or 0,
                label=str(dim.get("name") or "")[:10]))
        story.append(KeepTogether(bars))
    else:
        story.append(Paragraph("未获取到维度评分数据。", st["body"]))

    story.append(h("综合评价"))
    story.append(Paragraph("综合评语", st["label"]))
    story.append(_para(result.get("summary"), st["body"]))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("核心优势", st["label"]))
    story.extend(_bullet_list(result.get("strengths"), st, "#34a853"))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("待改进方面", st["label"]))
    story.extend(_bullet_list(result.get("improvements"), st, "#f97316"))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("发展建议", st["label"]))
    story.append(_para(result.get("suggestions"), st["body"]))

    if dimensions:
        story.append(PageBreak())
        story.append(h("各维度详细评价"))
        for dim in dimensions:
            score = _fmt(dim.get("score"))
            full = _fmt(dim.get("full_score"), 0)
            pages = dim.get("pages") or []
            page_txt = ("　·　P" + "、P".join(str(p) for p in pages)) if pages else ""
            title = Paragraph(
                f"<font color='#1a73e8'>{escape(str(dim.get('name') or ''))}</font>"
                f"　<font size=9 color='#6b7280'>（{score} / {full} 分{page_txt}）</font>",
                st["body"])
            block = [title]
            if dim.get("comments"):
                block.append(Paragraph("评价意见", st["label"]))
                block.append(_para(dim.get("comments"), st["body"]))
            if dim.get("details"):
                block.append(Paragraph("评分依据", st["label"]))
                block.append(_para(dim.get("details"), st["body"]))

            evidence = dim.get("evidence") or []
            if evidence:
                block.append(Paragraph("举证溯源", st["label"]))
                for item in evidence:
                    page = item.get("page") or 0
                    quote = escape(str(item.get("quote") or ""))
                    note = escape(str(item.get("note") or ""))
                    prefix = f"<font color='#1a73e8'>P{page}</font>　" if page else ""
                    text = f"{prefix}“{quote}”"
                    if note:
                        text += f"<br/><font color='#6b7280' size=9>{note}</font>"
                    block.append(Paragraph(text, st["body"]))
            block.append(Spacer(1, 3 * mm))
            story.append(KeepTogether(block))

    cot = (result.get("chain_of_thought") or "").strip()
    if include_cot and cot:
        story.append(PageBreak())
        story.append(h("思维链推理过程"))
        story.append(_para(cot, st["cot"]))

    if ppt_content.strip():
        excerpt = ppt_content.strip()
        truncated = len(excerpt) > 4000
        if truncated:
            excerpt = excerpt[:4000] + "\n……（材料过长，仅保留前 4000 字）"
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("附：候选人答辩材料摘要", st["h2"]))
        story.append(_para(excerpt, st["small"]))

    story.append(Spacer(1, 12 * mm))
    sign = Table([[
        Paragraph(f"评价人：{escape(reviewer) if reviewer else '　　　　　　'}", st["body"]),
        Paragraph("审核人：　　　　　　", st["body"]),
        Paragraph(f"日期：{now:%Y 年 %m 月 %d 日}", st["body"]),
    ]], colWidths=[60 * mm, 60 * mm, 50 * mm])
    sign.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
    story.append(sign)

    doc.build(story, canvasmaker=NumberedCanvas)
    pdf = buf.getvalue()
    buf.close()
    return pdf


def report_filename(result: dict) -> str:
    """Readable file name for the generated report."""
    candidate = result.get("candidate") or {}
    name = (candidate.get("name") or "候选人").strip()
    level = (candidate.get("applied_level") or "").strip()
    stamp = datetime.datetime.now().strftime("%Y%m%d")
    parts = ["任职资格评价报告", name] + ([level] if level else []) + [stamp]
    return "_".join(parts) + ".pdf"
