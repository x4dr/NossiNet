"""Template filters, error handlers, and helper utilities for NossiSite."""

import random
import re
import string
import urllib.parse
from collections.abc import Callable
from pathlib import Path
from typing import Any

import markdown
from flask import (
    Flask,
    Response,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from gamepack.Dice import DescriptiveError
from markupsafe import Markup

from Data import connect_db
from NossiSite.base import app as defaultapp
from NossiSite.base import log


def register(app: Flask | None = None) -> None:
    """Register Jinja template filters, error handlers, and request hooks with the given Flask app.

    Args:
        app: The Flask application to register with. Defaults to the main app instance.

    """
    if app is None:
        app = defaultapp

    app.jinja_env.globals.update(hasattr=hasattr)

    @app.template_filter("quoted")
    def quoted(s: str) -> Any:
        quotedstring = re.findall("'([^']*)'", str(s))
        if quotedstring:
            return quotedstring[0]
        return None

    @app.template_filter("remove_leading_underscore")
    def underscore_remove(s: str) -> str:
        while s and s[0] == "_":
            s = s[1:]
        return s

    @app.template_filter("markdown")
    def markdownfilter(s: str | list[str] | None) -> Markup | list[str] | str:
        if s is None:
            return ""
        if isinstance(s, str):
            return Markup(markdown.markdown(s, extensions=["tables", "toc", "nl2br"]))
        if isinstance(s, list):
            # noinspection PyBroadException
            try:
                n = Markup(
                    markdown.markdown(
                        "  \n".join(s),
                        extensions=["tables", "toc", "nl2br"],
                    ),
                )
                return str(n).split("\n")
            except Exception:
                return "ERRR"
        raise DescriptiveError("Templating error: \n" + str(s) + "\ndoes not belong")

    @app.template_filter("urldecode")
    def filter_urldecode(s: str) -> str:
        return urllib.parse.unquote(s)

    @app.before_request
    def before_request() -> None:
        connect_db("before request")
        if request.endpoint == "/postreceive":  # postreceive does not use csrf
            request.csrf_valid = True  # type: ignore[attr-defined]

    @app.errorhandler(Exception)
    def internal_error(error: Exception) -> Any:
        if error.args and error.args[0] == "REDIR":
            return error.args[1]
        if type(error) is DescriptiveError:
            flash(error.args[0])
            log.exception("Handled Descriptive Error")
            if request.url.endswith("/raw"):
                return error.args[0]
        flash("internal error. sorry", category="error")
        log.exception("Unhandled internal error")
        raise error from None

    @app.errorhandler(404)
    def page_not_found(e: Any) -> tuple[str, int] | Response:
        p = request.path[1:]
        if (Path("NossiSite") / "static" / p).exists():
            return send_from_directory("static", p)
        if e:
            print("404:", request.url)
        return render_template("base/404.html"), 404

    @app.context_processor
    def inject_srs() -> dict[str, Callable[[int], str]]:
        return dict(srs=srs)


def srs(w: int = 8) -> str:
    """Generate a short random ID for use in templating.

    :param w: width of result
    :return: short random string.
    """
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=w))


def checklogin() -> None:
    """Redirect unauthenticated users to the login page.

    Raises:
        Exception: Always raises with REDIR argument to trigger the error handler.

    """
    if not session.get("logged_in"):
        flash("You are not logged in!")
        session["returnto"] = request.url
        raise Exception("REDIR", redirect(url_for("views.login")))
