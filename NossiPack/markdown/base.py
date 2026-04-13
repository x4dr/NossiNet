class WikiEnvironment:
    def __init__(self, page_name: str, raw_content: str):
        self.page_name = page_name
        self.raw_content = raw_content
        self.html_content = ""
        self.metadata = {}


class NossiTag:
    priority = 0
    registry = []

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
