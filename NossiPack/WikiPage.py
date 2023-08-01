from dataclasses import dataclass


@dataclass
class WikiPage:
    """
    Class to represent a wiki page.
    """

    title: str
    tags: list
    body: str
    links: list
    meta: list
