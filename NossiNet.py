import sqlite3
from contextlib import closing

from flask import Flask, request, session, g, redirect, url_for, \
    abort, render_template, flash

from NossiPack.User import *


# configuration



DATABASE = '/home/maric/workspace/PycharmProjects/NossiNet/NN.db'
# DEBUG = True
SECRET_KEY = 'ajdjJFeiJjFnnm88e4ko94VBPhzgY34'
# USERNAME = 'admin'
# PASSWORD = 'default'

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
    cur = g.db.execute('SELECT author, title, text FROM entries ORDER BY id DESC')
    entries = [dict(author=row[0], title=row[1], text=row[2]) for row in cur.fetchall()]
    return render_template('show_entries.html', entries=entries)


@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    g.db.execute('INSERT INTO entries (author, title, text) VALUES (?, ?, ?)',
                 [session.get('user'), request.form['title'], request.form['text']])
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
                    error = u.adduser(User(username, password))
                    if error is not None:
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
    u = Userlist()
    if request.method == 'POST':
        user = request.form['username']
        user.upper()
        if not u.valid(user, request.form['password']):
            error = 'invalid username/password combination'
        else:
            session['logged_in'] = True
            session['user'] = user
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
    print("nncalled")
    return render_template('show_entries.html', \
                           entries=[
                               dict(author='the NOSFERATU NETWORK', title='WeLcOmE tO tHe NoSfErAtU nEtWoRk', text='')],
                           heads=['<META HTTP-EQUIV="refresh" CONTENT="5;url=/">'])


@app.route('/resetdb/')
def resetdb():
    init_db()
    return "ok "


@app.route('/user/<username>')
def show_user_profile(username):
    ul = Userlist()
    if ul.contains(username):
        u = ul.getuserbyname(username)
        return render_template('userinfo.html', user=u)
    return render_template('layout.html', error='User not found')


@app.errorhandler(404)
def page_not_found(error):
    return error


if __name__ == '__main__':
    app.run(debug=True)  #False, host='0.0.0.0')
