import sqlite3
from flask import Flask, request, session, g, redirect, url_for, \
    abort, render_template, flash
from contextlib import closing
from NossiPack.krypta import *

from NossiPack.User import *

# configuration


DATABASE = '/home/maric/workspace/PycharmProjects/NossiNet/NN.db'
DEBUG = True
SECRET_KEY = 'key'
USERNAME = 'admin'
PASSWORD = 'default'

app = Flask(__name__)
app.config.from_object(__name__)


def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
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


@app.route('/')
def show_entries():
    cur = g.db.execute('SELECT title, text FROM entries ORDER BY id DESC')
    entries = [dict(title=row[0], text=row[1]) for row in cur.fetchall()]
    return render_template('show_entries.html', entries=entries)


@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    g.db.execute('INSERT INTO entries (title, text) VALUES (?, ?)',
                 [request.form['title'], request.form['text']])
    g.db.commit()
    flash('New entry was successfully posted')
    return redirect(url_for('show_entries'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    u = Userlist(None)
    if request.method == 'POST':
        username = request.form['username']
        if len(username) > 2:
            username = username.upper()
            if request.form['password'] == request.form['passwordcheck']:
                password = request.form['password']
                if len(password) > 5:
                    u.adduser(User(username, password))
                    flash('User successfully created.')
                    return redirect(url_for('start'))
                else:
                    error = 'Password is too short!'
            else:
                error = 'Passwords do not match!'
        else:
            error = 'Username is too short!'
    return render_template('register.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))


@app.route('/nn')
def start():
    return 'WeLcOmE tO tHe NoSfErAtU nEtWoRk '


@app.route('/resetdb/')
def resetdb():
    init_db()
    return "ok "


@app.route('/user/<username>')
def show_user_profile(username):
    return render_template('layout.html', username)
    # , 'User {0} has {1} Kudos'.format(username, random.randint(1, 100000)))


@app.errorhandler(404)
def page_not_found(error):
    return error


if __name__ == '__main__':
    app.run(debug=True)
