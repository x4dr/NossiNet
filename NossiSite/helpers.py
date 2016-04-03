from NossiSite import app
import sqlite3
from contextlib import closing
from flask import Flask, request, session, g, redirect, url_for, \
    abort, render_template, flash, send_from_directory, Response
from jinja2 import Environment
from werkzeug.security import generate_password_hash
import time
import logging

log = logging.Logger("helperlogger")


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
        bytes = o.read(500)
        while bytes != b'':
            yield bytes
            bytes = o.read(500)
        yield bytes
    finally:
        o.close()


def generate_token(seed):
    return generate_password_hash(str(seed) + str(time.clock()))


def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('../schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


def connect_db():
    return sqlite3.connect(app.config['DATABASE'])


@app.before_request
def before_request():
    g.db = connect_db()
#    try:
#        print(request.remote_addr, " => ", request.path,
#              ">", session.get('user', '?'), "<")
#    except:
#        print("exception while printing before request")


#@app.after_request
#def after_request(x):
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


@app.errorhandler(404)
def page_not_found(error):
    return str(error)


def openupdb():
    db = connect_db()
    if db is not None:
        db.close()
