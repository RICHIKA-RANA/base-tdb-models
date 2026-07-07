import re
from difflib import get_close_matches
from dataclasses import dataclass, field
from typing import List, Optional
from ..base.base import make_id, RunModel
from ...placeholders.placeholder import PlaceholderModel
from ....utils.dataclass import from_dict_safe

# TODO move this to different file
def build_comment_text(ph: PlaceholderModel) -> Optional[str]:
    if not ph.replaced_reference:
        return None

    parts = []

    if ph.replaced_comment:
        parts.append(ph.replaced_comment)

    ref_set = set(ph.replaced_reference)
    lines = []
    for m in ph.matches:
        if m.id in ref_set:
            path = " > ".join(m.heading_path) if m.heading_path else ""
            label = f"{m.filename} > {path}" if path else m.filename
            lines.append(f"- {label}")
    if lines:
        parts.append("Sources:\n" + "\n".join(lines))

    return "\n\n".join(parts) if parts else None


@dataclass
class ParagraphStyleModel:
    name: str
    alignment: Optional[str] = None  # 'LEFT', 'RIGHT', 'CENTER', 'JUSTIFY'
    space_before: Optional[float] = None
    space_after: Optional[float] = None
    outline_level: Optional[int] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    font_size: Optional[float] = None
    font_name: Optional[str] = None
    font_color: Optional[str] = None
    underline: Optional[bool] = None
    case: Optional[str] = None  # 'upper', 'capitalize', 'sentence'

    # Word-specific layout properties
    left_indent: Optional[float] = None
    right_indent: Optional[float] = None
    hanging_indent: Optional[float] = None
    left_tab_stop: Optional[float] = None
    center_tab_stop: Optional[float] = None
    right_tab_stop: Optional[float] = None
    line_spacing_rule: Optional[str] = None  # 'SINGLE', 'AT_LEAST', etc.
    line_spacing_value: Optional[float] = None
    keep_with_next: Optional[bool] = None
    page_break_before: Optional[bool] = None
    widow_control: Optional[bool] = None

    # Footer-specific borders
    add_footer_border_top: Optional[bool] = None
    add_border_top_if_no_text: Optional[bool] = None
    border_style: Optional[str] = None  # 'single', 'double', etc.
    border_color: Optional[str] = None
    border_size: Optional[float] = None

    @classmethod
    def from_dict(cls, data: dict) -> "ParagraphStyleModel":
        return from_dict_safe(cls, data)

    def classify_style(self):
        if not self or not self.name:
            return None, None

        def normalize(s: str) -> str:
            return s.lower().strip() if s else ""

        def is_fuzzy_match(name: str, patterns: list, cutoff=0.7) -> bool:
            name = normalize(name)
            return bool(get_close_matches(name, patterns, cutoff=cutoff))

        def extract_heading_level(style_name: str) -> Optional[int]:
            if not style_name:
                return None

            match = re.search(r"heading\s*(\d+)", style_name, re.I)
            return int(match.group(1)) if match else None

        name = normalize(self.name)

        if is_fuzzy_match(name, ["caption"]):
            return "caption", None

        if is_fuzzy_match(name, ["heading"]):
            level = extract_heading_level(name)
            return "heading", level

        return None, None


@dataclass
class ParagraphModel:
    style: Optional[ParagraphStyleModel] = None
    runs: List[RunModel] = field(default_factory=list)
    type: str = "Paragraph"
    id: Optional[str] = None

    parent_ref_id: Optional[str] = None

    is_caption: Optional[bool] = False
    is_heading: Optional[bool] = False
    heading_level: Optional[int] = None

    is_example: Optional[bool] = False
    is_instruction: Optional[bool] = False

    is_list: Optional[bool] = False
    list_type: Optional[str] = None
    list_level: Optional[int] = 0
    page: Optional[int]=None

    @classmethod
    def from_dict(cls, data: dict) -> "ParagraphModel":
        if data.get("style") is not None:
            data["style"] = ParagraphStyleModel.from_dict(data["style"])

        data["runs"] = [
            RunModel.from_dict(run)
            for run in data.get("runs", [])
        ]

        return from_dict_safe(cls, data)

    def assign_ids(self, parent_id: str, index: int):
        self.id = make_id(parent_id, "para", index)

        for i, run in enumerate(self.runs):
            run.assign_ids(self.id, i)

    def to_text(self, mode="full") -> str:
        return "".join(r.to_text(mode) or "" for r in self.runs)

    def to_html(self) -> str:

        styles = []

        if self.style:
            s = self.style

            if s.alignment:
                align_map = {
                    "LEFT": "left",
                    "RIGHT": "right",
                    "CENTER": "center",
                    "JUSTIFY": "justify",
                }
                if s.alignment in align_map:
                    styles.append(f"text-align: {align_map[s.alignment]}")

            if s.space_before is not None:
                styles.append(f"margin-top: {s.space_before}pt")

            if s.space_after is not None:
                styles.append(f"margin-bottom: {s.space_after}pt")

            if s.left_indent is not None:
                styles.append(f"margin-left: {s.left_indent}pt")

            if s.right_indent is not None:
                styles.append(f"margin-right: {s.right_indent}pt")

            if s.hanging_indent is not None:
                styles.append(f"text-indent: {-s.hanging_indent}pt")

            if s.line_spacing_rule and s.line_spacing_value:
                styles.append(f"line-height: {s.line_spacing_value}")

            if s.page_break_before:
                styles.append("break-before: page")

        style_attr = f' style="{"; ".join(styles)}"' if styles else ""

        inner_html = "".join(r.to_html()
                             for r in self.runs if r.to_text())

        if not inner_html:
            inner_html = "&nbsp;"

        return f"<p{style_attr}>{inner_html}</p>"

    def classify_intent(self) -> Optional[str]:
        def hex_to_rgb(hex_color: str):
            hex_color = hex_color.replace("#", "")
            if len(hex_color) != 6:
                return None
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        def color_distance(c1, c2):
            return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5

        GREEN_REF = hex_to_rgb("00B050")
        RED_REF = hex_to_rgb("C9211E")
        COLOR_THRESHOLD = 60

        colors = []

        for run in self.runs:
            color = run.get_color()
            if not color:
                return None

            rgb = hex_to_rgb(color)
            if not rgb:
                return None

            colors.append(rgb)

        if not colors:
            return None

        base = colors[0]
        if any(color_distance(base, c) > 10 for c in colors):
            return None

        if color_distance(base, GREEN_REF) < COLOR_THRESHOLD:
            return "instruction"

        if color_distance(base, RED_REF) < COLOR_THRESHOLD:
            return "example"

        return None

    @staticmethod
    def apply_inline_placeholder(
        para: "ParagraphModel",
        ph: PlaceholderModel,
    ) -> bool:
        if not ph.replaced_text:
            return False

        full_text = para.to_text(mode="full")
        if ph.text not in full_text:
            return False

        comment_text = build_comment_text(ph)

        para.runs = RunModel.replace_text(
            para.runs,
            ph.text,
            ph.replaced_text,
            comment_text=comment_text,
        )
        return True

    @staticmethod
    def from_text(text: str) -> "ParagraphModel":
        return ParagraphModel(
            style=None,
            runs=[RunModel.from_text(text)]
        )

    @staticmethod
    def apply_deleted_placeholder(
        para: "ParagraphModel",
        ph: PlaceholderModel,
    ) -> bool:
        full_text = para.to_text(mode="full")
        if ph.text not in full_text:
            return False

        para.runs = RunModel.drop_text(
            para.runs,
            ph.text,
        )
        return True
