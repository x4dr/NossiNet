class WikiEnvironment:
    def __init__(self, page_name: str, raw_content: str):
        self.page_name = page_name
        self.raw_content = raw_content
        self.html_content = ""
        self.metadata = {}


class NossiTag:
    priority = 0
    registry = []

    # Metadata for editor integration (override in subclasses)
    tag_id: str = ""
    syntax: str = ""
    description: str = ""
    example: str = ""
    category: str = "other"
    pattern: str | None = None
    flags: str = ""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Check for priority conflict
        conflicts = [tag for tag in NossiTag.registry if tag.priority == cls.priority]
        if conflicts:
            conflicting_names = [type(tag).__name__ for tag in conflicts]
            raise ValueError(
                f"Priority conflict: {cls.__name__} has same priority ({cls.priority}) as: {', '.join(conflicting_names)}"
            )
        NossiTag.registry.append(cls())
        NossiTag.registry.sort(key=lambda x: x.priority)

    def pre_process(self, text: str, env: WikiEnvironment) -> str:
        return text

    def post_process(self, html: str, env: WikiEnvironment) -> str:
        return html

    def to_dict(self) -> dict:
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
