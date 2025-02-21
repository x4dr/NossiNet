import re

from markdown import markdown

from NossiSite.helpers import srs
from gamepack.Dice import DescriptiveError
from gamepack.Item import Item
from gamepack.MDPack import traverse_md, MDObj
from gamepack.WikiPage import WikiPage


class LocalMarkdown:
    extensions = ["nl2br", "tables", "toc"]
    transclude_re = re.compile(r"!\[(?P<text>.*?)]\((?P<link>.*?)\)", re.IGNORECASE)
    transclude_inner_re = re.compile(r"!\[(?P<link>.*?]?)](?!\()", re.IGNORECASE)
    clock_re = WikiPage.clock_re

    transcluded_clock_re = re.compile(r"\[clock\|(?P<name>.*?)@(?P<page>.*?)]")

    headline_re = re.compile(
        r"<h(?P<level>\d+)(?P<attributes>.*?)>\s*(?P<text>.*?)\s*</h(?P=level)>"
    )

    re_links = re.compile(r"\[(.+?)]\((?P<ref>.+?)\)")
    headers = re.compile(
        r"<(?P<h>h\d*)\b(?P<extra>[^>]*)>(?P<content>.*?)</(?P=h)\b[^>]*>",
        re.IGNORECASE | re.DOTALL,
    )
    infolet_re = re.compile(r"\[!q:(?P<name>.*?)]", re.IGNORECASE)

    @classmethod
    def transclude(cls, match: re.Match):
        heading = match.group("text")
        bracketed = "!" if heading.startswith("[") and heading.endswith("]") else ""
        if bracketed:
            heading = heading[1:-1]
        newtext = cls.transclude_inner(match)
        if newtext == match.group(0):
            return match.group(0)
        old_heading = newtext.split("\n")[0]
        if not old_heading.strip().startswith("#"):
            old_heading = ""
        newtext = newtext[len(old_heading) :].lstrip()
        if not newtext:
            return match.group(0)
        if heading:
            if heading.strip().startswith("#"):
                level = len(heading.strip()) - len(heading.strip().lstrip("#"))
            else:
                level = len(old_heading.strip()) - len(old_heading.strip().lstrip("#"))
            return f"{'#'*(level+1)}{bracketed} {heading}\n{newtext}"
        elif bracketed:
            return f"#!\n{newtext}"
        return f"{newtext}"

    @classmethod
    def transclude_inner(cls, match: re.Match):
        path = match.group("link")
        current_level = 0
        # position of the last headline
        recent_headline = match.string[: match.span()[0]].rfind("#") + 1
        if recent_headline > 0:
            current_level = match.string[:recent_headline].splitlines()[-1].count("#")
        bracketed = path.startswith("[") and path.endswith("]")
        if bracketed:
            path = path[1:-1]
        if not path:
            return match.group(0)
        pagename, *path = path.split("#")
        try:
            page = WikiPage.load_str(pagename)
        except DescriptiveError:
            return match.group(0)
        if path:
            newtext = cls.recursive_traverse(page.body, path)
        else:
            newtext = page.body
        if not newtext:
            newtext = f"!!! not found: {'#'.join(path)} in {pagename}"
        newlines = []
        for line in newtext.splitlines(keepends=True):
            if line.strip().startswith("#"):
                line = f"{'#'*current_level}{line.lstrip()}"
            newlines.append(line)

        newtext = "".join(newlines)
        if bracketed and newtext.strip().startswith("#"):
            # replace the first #+ with #+! for foldable
            newtext = re.subn(r"^(#+)", r"\1!", newtext, 1)
            return f"{newtext}"
        return f"{newtext}"

    @classmethod
    def find_hidespans(cls, md: MDObj, level=0) -> [(str, str)]:
        hidespans = []
        children = [(name, child) for name, child in md.children.items()]
        i = 0
        for name, child in children:
            if name.startswith("!"):
                i += 1
                if len(children) > i:
                    hidespans.append((name.strip("_"), children[i][0].rstrip("_")))
                else:
                    hidespans.append((name, None))
            hidespans.extend(cls.find_hidespans(child, level + 1))
        return hidespans

    @classmethod
    def local_clock_make(cls, page: str):
        def local_clock(match: re.Match):
            name = match.group("name")
            return (
                f'<div id="parent-{name}-{page}" '
                f'hx-ws="connect:/active_element?name={name}&page={page}" >'
                f'<div id="{name}-{page}">Loading {name}</div></div>'
            )

        return local_clock

    @classmethod
    def transcluded_clock(cls, match: re.Match):
        page = match.group("page")
        return cls.local_clock_make(page)(match)

    @classmethod
    def pre_process(cls, text: str, page: str) -> (str, [(str, str)]):
        text = cls.transclude_re.sub(cls.transclude, text)
        text = cls.transclude_inner_re.sub(cls.transclude_inner, text)
        text = cls.transcluded_clock_re.sub(cls.transcluded_clock, text)
        text = cls.clock_re.sub(cls.local_clock_make(page), text)
        md = MDObj.from_md(text)
        hidespans = cls.find_hidespans(md)

        return text, hidespans

    @classmethod
    def markdown(cls, text: str) -> str:
        return markdown(text, extensions=cls.extensions)

    @classmethod
    def process(self, text: str, page: str) -> str:
        text, hidespans = self.pre_process(text, page)
        text = self.markdown(text)
        text = self.post_process(text, hidespans)
        return text

    @classmethod
    def hide_span(
        cls, text: str, header: str, next_header: str, start_position: int
    ) -> (str, int):
        pattern = r"<h(?P<level>\d+).*?>\s*{}\s*</h(?P=level)>"
        r1 = re.compile(pattern.format(re.escape(header)))
        done = text[:start_position]
        text = text[start_position:]
        m = r1.search(text)
        start = m.span()[0]
        level = m.group("level")

        if next_header:
            r2 = re.compile(pattern.format(re.escape(next_header)))
            m2 = (
                [x for x in r2.finditer(text, start + 1) if x.group("level") == level]
                or [None]
            )[0]
            end = m2.span()[0] if m2 else len(text)
        else:
            end = len(text)
        processed = text[:start] + cls.hide(text[start:end])
        return done + processed + text[end:], len(done) + len(processed)

    @classmethod
    def post_process(cls, text, hidespans):
        text = cls.re_links.sub(r'<a href="/wiki/\g<2>"> \g<1> </a>', text)
        pos = 0
        for s in hidespans:
            text, pos = cls.hide_span(text, s[0], s[1], pos)
        return cls.headers.sub(cls.headerfix, text)

    @classmethod
    def recursive_traverse(cls, focus, path) -> str:
        for seek in path:
            focus = traverse_md(focus.rstrip("\n"), seek.strip())
        return focus

    @classmethod
    def headerfix(cls, text: re.Match):
        if "\n" not in text.group("content"):
            return text.group()
        return (
            f"<{text.group('h')} {text.group('extra')}> "
            f"{text.group('content').splitlines()[0]}</{text.group('h')}>"
            + "\n".join(text.group("content").splitlines()[1:])
        )

    @classmethod
    def hide(cls, text):
        random_code = srs()
        header = cls.headline_re.match(text)
        text = text[header.end() :]
        headline = (
            f"<h{header.group('level')} {header.group('attributes')} class=hider data-for={random_code}> "
            f"{header.group('text')[1:]} </h{header.group('level')}>\n"
        )
        return headline + f'<div id="{random_code}" class="hiding">{text}</div>'

    @classmethod
    def fill_infolet(cls, s, context):
        s = str(s)
        if not (m := cls.infolet_re.match(s)):
            return s
        infolet = m.group("name")
        if any(
            s.lower().strip().startswith(prefix)
            for prefix in ["!q:", "[!q:", "!p:", "[!p:"]
        ):
            if "#" in infolet:
                pass
                # page, *path = infolet.split("#")
                # newtext = cls.recursive_traverse(WikiPage.locate(page), path)
                # todo
            result = Item.item_cache.get(infolet)
            if not result:
                itemspage = WikiPage.load_str("items")
                itemsmd = itemspage.md()
                itemstable = itemsmd.tables[0]
                itemstable.rows.append([infolet])
                seen = set()
                new_rows = []
                for row in itemstable.rows:
                    if row[0] not in seen:
                        seen.add(row[0])
                        new_rows.append(row)
                itemstable.rows = new_rows
                Item.item_cache[infolet] = Item(infolet, 0, 0, "", 1)
                itemspage.body = itemsmd.to_md()
                itemspage.save_low_prio("automatically added item")
        return cls.inline_load(infolet)

    @classmethod
    def inline_load(cls, text: str) -> str:
        i: Item = Item.item_cache.get(text)
        if not i:
            return text
        if not i.description:
            return text
        return f'<div class="tooltip">{text}<span class="tooltiptext">{i.description}</span></div>'
