import re

import os

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
wikipath = "~/wiki/"
token = {}


def stream_template(template_name, **context):
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv


wikitags = {}
wikistamp = 0


def wikindex():
    global wikistamp
    global wikitags
    mds = []
    for p in os.listdir(os.path.expanduser(wikipath)):
        if p.endswith(".md"):
            mds.append(p[:-3])
    return sorted(mds), wikitags, wikistamp


def stream_string(s):
    for l in s:
        yield l


def wikisave(page, author, title, tags, body):
    print("saving ...")
    with open(os.path.expanduser(wikipath + page + ".md"), 'w+') as f:
        f.write("title: " + title + "  \n")
        f.write("tags: " + " ".join(tags) + "  \n")
        f.write(body)
    with open(os.path.expanduser(wikipath) + "control", "a+") as f:
        f.write(page + " edited by " + author + "\n")
    print(page + " edited by " + author)
    os.system(os.path.expanduser("~/") + "bin/wikiupdate & ")


def wikiload(page):
    with open(os.path.expanduser(wikipath + page + ".md")) as f:
        mode = "meta"
        title = ""
        tags = []
        body = ""
        for line in f.readlines():
            if mode and line.startswith("tags:"):
                tags += [t for t in line.strip("tags:").strip().split(" ") if t]
                continue
            if mode and line.startswith("title:"):
                title = line.strip("title:").strip()
                continue
            if mode and not line.strip():
                mode = ""
                continue
            body += line
        return title, tags, body


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
    global wikistamp
    if len(wikitags.keys()) == 0:
        updatewikitags()


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
    global wikistamp
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()
    if exception:
        print("exception caught by teardown:", exception)
    if time.time() - wikistamp > 3600:
        updatewikitags()


def updatewikitags():
    global wikistamp
    print("it has been " + str(time.time() - wikistamp) + " seconds since the last wiki indexing")
    wikistamp = time.time()
    for m in wikindex()[0]:
        wikitags[m] = wikiload(m)[1]
    print("index took: " + str(1000 * (time.time() - wikistamp)) + " milliseconds")


@app.context_processor
def gettoken():
    gentoken()
    global token
    return dict(token=token.get(session.get('user', None), [''])[-1])


def token_clear():
    global token
    if session.get('user'):
        token.pop(session['user'])
    else:
        print("logging out nonexistent user...")
        print("still logged in are " + ", ".join(token.keys()) + ".")


def gentoken():
    global token
    if session.get('user', False):
        token[session['user']] = token.get(session['user'], [])[-2:] + [generate_token(session)]
        print("generated:", token[session['user']])
        return token[session['user']][-1]
    else:
        return ''


def checktoken():
    global token
    ts = token.get(session.get('user', None), None)
    ts = ts if ts else []
    if request.form.get('token', "None") not in ts:
        # so that None != "None" but a forged token with just "None" inside never matches
        flash("invalid token!")
        print("Token received:" + request.form.get('token', "None") + " Tokens expected:",
              token.get(session.get('user', None), "INVALID"))
        return False
    else:
        token[session.get('user', '')].remove(request.form.get('token', "None"))
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
