import re
import traceback

import markdown
from flask import request, session, redirect, url_for, render_template, flash
from markupsafe import Markup

from NossiPack.krypta import DescriptiveError, connect_db
from NossiSite.base import app as defaultapp, log


def register(app=None):
    if app is None:
        app = defaultapp

    @app.template_filter("quoted")
    def quoted(s):
        quotedstring = re.findall("'([^']*)'", str(s))
        if quotedstring:
            return quotedstring[0]
        return None

    @app.template_filter("remove_leading_underscore")
    def underscore_remove(s):
        while s and s[0] == "_":
            s = s[1:]
        return s

    @app.template_filter("markdown")
    def markdownfilter(s):
        if s is None:
            return ""
        if isinstance(s, str):
            return Markup(markdown.markdown(s, extensions=["tables", "toc", "nl2br"]))
        if isinstance(s, list):
            n = Markup(
                markdown.markdown("  \n".join(s), extensions=["tables", "toc", "nl2br"])
            )
            return str(n).split("\n")
        raise DescriptiveError("Templating error: \n" + str(s) + "\ndoes not belong")

    @app.before_request
    def before_request():
        connect_db("before request")

    @app.teardown_request
    def teardown_request(exception: Exception):
        # close_db() currently disabled(letting the connection live as long as the worker)
        if exception:
            if exception.args and exception.args[0] == "REDIR":
                return exception.args[1]
            log.exception("exception caught by teardown:", exception)
            traceback.print_exc()
        return None

    @app.context_processor
    def gettoken():
        gentoken()
        return dict(token=session.get("print", None))

    @app.errorhandler(Exception)
    def internal_error(error: Exception):
        if error.args and error.args[0] == "REDIR":
            return error.args[1]
        if type(error) is DescriptiveError:
            flash(error.args[0])
            log.exception("Handled Descriptive Error")
            if request.url.endswith("/raw"):
                return error.args[0]
        if app.testing:
            raise error
        flash("internal error. sorry", category="error")
        log.exception("Unhandled internal error")
        return render_template("show_entries.html")

    @app.errorhandler(404)
    def page_not_found(e):
        if e:
            print("404:", request.url)
        return render_template("404.html"), 404


def generate_token():
    if not session["logged_in"]:
        raise DescriptiveError("Not Logged in.")
    return session["print"]  # only one token per session for now.


def gentoken():
    return session.get("print", None)


def checklogin():
    if not session.get("logged_in"):
        flash("You are not logged in!")
        raise Exception("REDIR", redirect(url_for("login", r=request.path[1:])))


def checktoken():
    if request.form.get("token", "None") != session.get("print", None):
        flash("invalid token!")
        session["retrieve"] = request.form
        return False
    return True
