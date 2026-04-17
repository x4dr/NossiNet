from NossiPack.markdown.tags.infolet import InfoletTag


def infolet_filler(context):
    def wrap(s):
        # We need to simulate fill_infolet. Maybe it's not needed anymore?
        # Let's see what it does.
        return s

    return wrap


def infolet_extractor(x):
    m = InfoletTag.infolet_re.match(str(x))
    if not m:
        return str(x)
    return m.group("name")
