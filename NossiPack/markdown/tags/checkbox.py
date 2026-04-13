import re

from NossiPack.markdown.base import NossiTag, WikiEnvironment


class CheckboxTag(NossiTag):
    """
    Handles checklist syntax: - [ ] and - [x]
    Transforms into hx-get checkboxes.
    """

    priority = 30
    checkbox_re = re.compile(r"\[(?P<checked>.)] (?P<text>.*)")

    def pre_process(self, text: str, env: WikiEnvironment) -> str:
        def _sub(match):
            m = self.checkbox_re.match(match.group(0)[2:])
            if not m:
                return match.group(0)
            checked = "checked" if m.group("checked").strip() == "x" else ""
            txt = m.group("text").strip()
            return (
                f'<input type="checkbox" {checked} hx-get="/checkbox/{txt}/{env.page_name}" '
                f'hx-swap="outerHTML" hx-trigger="load"> {txt}'
            )

        return re.sub(r"- \[.?]\s*.*", _sub, text)
