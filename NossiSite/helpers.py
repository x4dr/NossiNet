from NossiSite import app
import sqlite3
from contextlib import closing
from flask import Flask, request, session, g, redirect, url_for, \
    abort, render_template, flash, send_from_directory
from werkzeug.security import generate_password_hash
import time


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


@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()


@app.errorhandler(404)
def page_not_found(error):
    return "error"


def openupdb():
    db = connect_db()
    # db.execute('DELETE FROM entries WHERE ID = 3')
    # cur = db.execute('SELECT  FROM entries ORDER BY id DESC')
    # print (cur.fetchall())
    # cur =
    if db is not None:
        db.close()
