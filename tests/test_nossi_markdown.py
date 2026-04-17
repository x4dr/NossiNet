import pytest

from NossiPack.markdown import NossiMarkdownProcessor, NossiTag, WikiEnvironment


# A test tag that reverses text in pre-processing
class ReverseTag(NossiTag):
    priority = 11

    def pre_process(self, text: str, env: WikiEnvironment) -> str:
        return text[::-1]


# A test tag that appends to html in post-processing
class AppendTag(NossiTag):
    priority = 21

    def post_process(self, html: str, env: WikiEnvironment) -> str:
        return html + "<p>appended</p>"


def test_nossi_markdown_processor():
    processor = NossiMarkdownProcessor()
    # "Hello" reversed is "olleH", which is a valid MD string
    # Then processed into <p>olleH</p>
    # Then appended
    result = processor.render("Hello", "testpage")
    assert "olleH" in result
    assert "<p>appended</p>" in result


def test_priority_conflict():
    with pytest.raises(ValueError, match="Priority conflict"):

        class ConflictTag1(NossiTag):
            priority = 5

        class ConflictTag2(NossiTag):
            priority = 5
