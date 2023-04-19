import bleach

ALLOWED_TAGS = frozenset(
    list(bleach.ALLOWED_TAGS)
    + [
        "br",
        "u",
        "p",
        "table",
        "th",
        "tr",
        "td",
        "tbody",
        "thead",
        "tfoot",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "div",
        "hr",
    ]
)
