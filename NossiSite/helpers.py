import re

from NossiSite import app
import sqlite3
from contextlib import closing
# noinspection PyUnresolvedReferences
from flask import Flask, request, session, g, redirect, url_for, \
    abort, render_template, flash, send_from_directory, Response
# noinspection PyUnresolvedReferences
from jinja2 import Environment
from werkzeug.security import generate_password_hash
import time
import logging

log = logging.Logger("helperlogger")
token = {}


def stream_template(template_name, **context):
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv


def stream_string(s):
    for l in s:
        yield l


def stream_file(f):
    o = open(f, 'rb')
    try:
        streambytes = o.read(500)
        while streambytes != b'':
            yield streambytes
            streambytes = o.read(500)
        yield streambytes
    finally:
        o.close()


def generate_token(seed):
    return generate_password_hash(str(seed) + str(time.clock()))


def init_db():
    print("initializing DB")
    with closing(connect_db()) as db:
        with app.open_resource('../schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


@app.template_filter('quoted')
def quoted(s):
    quotedstring = re.findall('\'([^\']*)\'', str(s))
    if quotedstring:
        return quotedstring[0]
    return None


def connect_db():
    print("connecting to", app.config['DATABASE'])
    return sqlite3.connect(app.config['DATABASE'])


@app.before_request
def before_request():
    g.db = connect_db()


#    try:
#        print(request.remote_addr, " => ", request.path,
#              ">", session.get('user', '?'), "<")
#    except:
#        print("exception while printing before request")


# @app.after_request
# def after_request(x):
#    try:
#        print(x)
#        print(request.remote_addr, " done ", request.path,
#              ">", session.get('user', '?'), "<")
#    except:
#        print("exception while printing after request")
#    return x


@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()
    if exception:
        print(exception)


@app.context_processor
def gettoken():
    gentoken()
    global token
    return dict(token=token.get(session.get('user', None), ''))


def gentoken():
    global token
    if session.get('user', False):
        token[session['user']] = generate_token(session)
        print("generated:", token[session['user']])
        return token[session['user']]
    else:
        return ''


def checktoken():
    global token
    if token.get(session.get('user', None), None) != request.form.get('token', "None"):
        # so that None != "None" but a forged token with just "None" inside never matches
        flash("invalid token!")
        print("Token received:" + request.form.get('token', "None") + " Token expected:",
              token.get(session.get('user', None), "INVALID"))
        return False
    else:
        token.pop(session.get('user', ''))
        return True

@app.errorhandler(404)
def page_not_found(e):
    if e:
        print(e)
    return render_template('404.html'), 404


def openupdb():
    db = connect_db()
    if db is not None:
        db.close()
