import re
from urllib.parse import quote

from NossiPack.markdown.base import NossiTag, WikiEnvironment


class CheckboxTag(NossiTag):
    """
    Task list: `- [ ] task` and `- [x] done`

    Transforms list items into HTMX-powered toggle checkboxes.
    Inside code blocks (backtick-wrapped) checkboxes are left as plain text.

    Examples:
      - [ ] unfinished
      - [x] completed
    """

    priority = 30
    tag_id = "checkbox"
    syntax = "- [ ] task or - [x] done"
    description = "Interactive task list checkboxes"
    example = "- [ ] unfinished\n- [x] completed"
    category = "interactive"
    checkbox_re = re.compile(r"\[(?P<checked>.)] (?P<text>.*)")

    @staticmethod
    def _is_inside_code(text: str, pos: int) -> bool:
        before = text[:pos]
        return before.count("`") % 2 == 1

    def pre_process(self, text: str, env: WikiEnvironment) -> str:
        def _sub(match):
            if self._is_inside_code(text, match.start()):
                return match.group(0)
            m = self.checkbox_re.match(match.group(0)[2:])
            if not m:
                return match.group(0)
            checked = "checked" if m.group("checked").strip() == "x" else ""
            txt = m.group("text").strip()
            return (
                f'<input type="checkbox" {checked} hx-get="/checkbox/{quote(txt)}/{env.page_name}" '
                f'hx-swap="outerHTML" hx-trigger="change"> {txt}'
            )

        return re.sub(r"- \[.?]\s*.*", _sub, text)
