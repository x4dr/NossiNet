from NossiPack.LocalMarkdown import LocalMarkdown

lm = LocalMarkdown()


def infolet_filler(context):
    def wrap(s):
        return lm.fill_infolet(s, context)

    return wrap


def infolet_extractor(x):
    m = lm.infolet_re.match(str(x))
    if not m:
        return str(x)
    return m.group("name")
