import re
from typing import Dict, Callable


class DuplicateKeyException(Exception):
    pass


class PartialMatchException(Exception):
    pass


class RegexRouter:
    routes: Dict[re.Pattern, Callable]

    def __init__(self):
        self.routes = {}

    def register(self, route: re.Pattern):
        def save(func):
            self.routes[route] = func
            return func

        return save

    def run(self, decide, require):
        result = {}
        unused = [x.strip() for x in decide]
        for r in self.routes.keys():
            m = r.search(decide)
            if m is None:
                continue
            if require:
                for x in range(*m.span()):
                    unused[x] = ""
            for k, v in self.routes[r](
                {k: v for (k, v) in m.groupdict().items() if v}
            ).items():
                if k in result:
                    raise DuplicateKeyException(
                        f"registered function {self.routes[r].__name__} reused key {k} that was used elsewhere and "
                        f"currently has the value {result[k]}",
                        self.routes[r],
                        k,
                        result[k],
                        v,
                    )
                result[k] = v
        if require:
            if any(unused):
                raise PartialMatchException("Not a Full match")
        return result
