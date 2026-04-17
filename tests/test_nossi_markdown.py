import pytest
from NossiPack.markdown import NossiMarkdownProcessor, NossiTag, WikiEnvironment


def test_nossi_markdown_processor():
    # Define tags inside the test so they don't get imported globally by accident
    # but they still trigger __init_subclass__
    class ReverseTag(NossiTag):
        priority = 999

        def pre_process(self, text: str, env: WikiEnvironment) -> str:
            return text[::-1]

    class AppendTag(NossiTag):
        priority = 1000

        def post_process(self, html: str, env: WikiEnvironment) -> str:
            return html + "<p>appended</p>"

    try:
        processor = NossiMarkdownProcessor()
        # "Hello" reversed is "olleH", which is a valid MD string
        # Then processed into <p>olleH</p>
        # Then appended
        result = processor.render("Hello", "testpage")
        assert "olleH" in result
        assert "<p>appended</p>" in result
    finally:
        # Clean up global registry to not break other tests
        NossiTag.registry = [
            t for t in NossiTag.registry if not isinstance(t, (ReverseTag, AppendTag))
        ]


def test_priority_conflict():
    class ConflictTag1(NossiTag):
        priority = 5

    try:
        with pytest.raises(ValueError, match="Priority conflict"):

            class ConflictTag2(NossiTag):
                priority = 5

    finally:
        NossiTag.registry = [
            t for t in NossiTag.registry if not isinstance(t, ConflictTag1)
        ]
