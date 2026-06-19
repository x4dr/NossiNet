"""Core tag registry and rendering environment for the NossiNet markdown pipeline."""

from typing import Any, ClassVar


class WikiEnvironment:
    """Container for page rendering context passed through the markdown pipeline."""

    def __init__(self, page_name: str, raw_content: str):
        """Initialize the environment with page metadata.

        Args:
            page_name: The name of the wiki page being rendered.
            raw_content: The unprocessed markdown source text.
        """
        self.page_name = page_name
        self.raw_content = raw_content
        self.html_content = ""
        self.metadata: dict[str, Any] = {}


class NossiTag:
    """Base class for custom markdown tag extensions.

    Subclasses are automatically registered in the global tag registry
    and sorted by priority. Each tag can implement pre-processing (on raw
    markdown text) and post-processing (on rendered HTML).
    """

    priority = 0
    registry: ClassVar[list[Any]] = []

    # Metadata for editor integration (override in subclasses)
    tag_id: str = ""
    syntax: str = ""
    description: str = ""
    example: str = ""
    category: str = "other"
    pattern: str | None = None
    flags: str = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Auto-register subclasses and validate priority uniqueness.

        Args:
            **kwargs: Forwarded to the parent ``__init_subclass__``.

        Raises:
            ValueError: If another registered tag shares the same priority.
        """
        super().__init_subclass__(**kwargs)
        # Check for priority conflict
        conflicts = [tag for tag in NossiTag.registry if tag.priority == cls.priority]
        if conflicts:
            conflicting = ", ".join(type(tag).__name__ for tag in conflicts)
            msg = f"Priority conflict: {cls.__name__} has same priority" f" ({cls.priority}) as: {conflicting}"
            raise ValueError(
                msg,
            )
        NossiTag.registry.append(cls())
        NossiTag.registry.sort(key=lambda x: x.priority)

    def pre_process(self, text: str, env: WikiEnvironment) -> str:  # noqa: ARG002
        """Transform raw markdown text before the core markdown renderer runs.

        Override in subclasses to implement custom pre-processing.

        Args:
            text: The raw markdown source.
            env: The current rendering environment.

        Returns:
            The modified markdown text.
        """
        return text

    def post_process(self, html: str, env: WikiEnvironment) -> str:  # noqa: ARG002
        """Transform rendered HTML after the core markdown renderer runs.

        Override in subclasses to implement custom post-processing.

        Args:
            html: The rendered HTML content.
            env: The current rendering environment.

        Returns:
            The modified HTML text.
        """
        return html

    def to_dict(self) -> dict[str, Any]:
        """Serialize tag metadata to a dictionary for editor integration.

        Returns:
            A dictionary of tag properties (id, name, priority, syntax,
            description, example, category, doc, pattern, flags).
        """
        cls = type(self)
        doc = (cls.__doc__ or "").strip()
        return {
            "id": self.tag_id or cls.__name__.replace("Tag", "").lower(),
            "name": cls.__name__,
            "priority": self.priority,
            "syntax": self.syntax,
            "description": self.description or doc.split("\n")[0] if doc else "",
            "example": self.example,
            "category": self.category,
            "doc": doc,
            "pattern": self.pattern,
            "flags": self.flags,
        }
