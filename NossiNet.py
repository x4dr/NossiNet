import random
from contextlib import closing
import time

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


@app.route('/kudosloan/<user>', methods=['GET'])
def loankudos(user):
    ul = Userlist()
    loaner = ul.getuserbyname(session.get('user'))
    loanee = ul.getuserbyname(user)
    loanee.add_kudosoffer(loaner.username)
    ul.saveuserlist()
    flash("Extended offer for vouching")
    return redirect(url_for('kudosloan'))


@app.route('/kudosloan/', methods=['GET', 'POST'])
def kudosloan():
    ul = Userlist()
    u = ul.getuserbyname(session.get('user'))
    entries = u.get_kudosdebts()
    if request.method == 'POST':
        id = request.form['id']
        print(id.__class__.__name__)
        entry = None
        for e in entries:
            if e.get('id') == id:
                entry = e
        if entry is not None:
            if entry.get('state') == 'unaccepted':
                entry['state'] = 'accepted'
                n = ul.getuserbyname(entry.get('loaner'))
                amount = int(n.kudos * 0.1)
                n.kudos += -amount * 2
                u.kudos += amount
                entry['original'] = str(amount)
                entry['remaining'] = str(amount * 4)
    u.set_kudosdebts(entries)
    ul.saveuserlist()
    for e in entries:
        e['currentkudos'] = ul.getuserbyname(e.get('loaner')).kudos
    return render_template('loankudos.html', entries=entries)




@app.route('/')
def show_entries():
    cur = g.db.execute('SELECT author, title, text, plusOned, id FROM entries ORDER BY id DESC')
    entries = [dict(author=row[0], title=row[1], text=row[2], plusoned=row[3], id=row[4]) for row in cur.fetchall()]
    for e in entries:
        if e.get('plusoned') is not None:
            esplit = e.get('plusoned').split(' ')
            e['plusoned'] = ((session.get('user') in esplit) or (session.get('user') == e.get('author')))
        else:
            e['plusoned'] = (session.get('user') == e.get('author'))
    return render_template('show_entries.html', entries=entries)


@app.route('/timestep/', methods=['GET', 'POST'])
def timestep():
    ul = Userlist()
    # u = ul.getuserbyname('THEOTOKOS')
    # u.set_password(" ", "Pestilenz")
    # u.kudos = 10000
    error = None
    keyprovided = session.get('amount') is not None
    if not keyprovided:
        keyprovided = None
    if request.method == 'POST':
        try:
            amount = int(request.form['amount'])
            if amount > 0:
                key = int(time.time())
                key = generate_password_hash(str(key))
                print(timestep)
                print(amount)
                print(key)
                session['timekey'] = key[-10:]
                session['timeamount'] = amount
                keyprovided = True
            else:
                error = 'need positive amount'
        except Exception as inst:
            # print(type(inst))
            # print(inst.args)  # arguments stored in .args
            # print(inst)  # __str__ allows args to be printed directly
            try:
                key = request.form['key'][-10:]
                if key == session.pop('timekey'):
                    flash('Passing ' + str(session.get('timeamount')) + ' Days!')
                    for d in range(int(session.pop('timeamount'))):
                        for u in ul.userlist:
                            if u.kudos > 100:
                                u.kudos = int(u.kudos * 0.997)  # ^30 ~= 0.9 => 10% tax per month

                else:
                    error = 'wrong key, TimeMagic fizzled..'
                    session.pop('timeamount')
                    session.pop('timekey')
            except Exception as ins:
                print(type(ins))
                print(ins.args)  # arguments stored in .args
                print(ins)  # __str__ allows args to be printed directly
                error = 'invalid transaction'

    ul.saveuserlist()
    return render_template('timestep.html', user=u, error=error, keyprovided=keyprovided)


@app.route('/plusone/<ident>', methods=['POST'])
def plusone(ident):
    cur = g.db.execute('SELECT author, title, text, plusOned, id FROM entries WHERE id = ?', [ident])
    for row in cur.fetchall():  # SHOULD only run once
        entry = dict(author=row[0], title=row[1], text=row[2], plusoned=row[3], id=row[4])
    ul = Userlist()
    u = ul.getuserbyname(entry.get('author'))
    if entry.get('author') == session.get('user'):
        flash('upvoting your own posts?')
        return redirect(url_for('show_entries'))

    if entry.get('plusoned') is not None:
        if session.get('user') not in entry.get('plusoned').split(' '):
            entry['plusoned'] = entry.get('plusoned') + ' ' + session.get('user')
            u.kudos += 1
            flash('Gave ' + entry.get('author') + ' Kudos for this post.')
        else:
            flash('already done that')
            return redirect(url_for('show_entries'))
    else:
        entry['plusoned'] = session.get('user')
        u.kudos += 1
        flash('You were the first to give ' + entry.get('author') + ' Kudos for this post.')
    ul.saveuserlist()
    g.db.execute('UPDATE entries SET plusOned = ? WHERE ID = ?', [entry.get('plusoned'), ident])
    g.db.commit()
    return redirect(url_for('show_entries'))


@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    g.db.execute('INSERT INTO entries (author, title, text) VALUES (?, ?, ?)',
                 [session.get('user'), request.form['title'], request.form['text']])
    g.db.commit()
    flash('New entry was successfully posted')
    return redirect(url_for('show_entries'))


@app.route('/buy_funds/', methods=['GET', 'POST'])
def add_funds():
    ul = Userlist()
    u = ul.getuserbyname(session.get('user'))
    error = None
    keyprovided = session.get('amount') is not None
    if not keyprovided:
        keyprovided = None
    if request.method == 'POST':
        try:
            amount = int(request.form['amount'])
            if amount > 0:
                key = int(time.time())
                key = generate_password_hash(str(key))
                print(amount)
                print(key)
                session['key'] = key[-10:]
                session['amount'] = amount
                keyprovided = True
            else:
                error = 'need positive amount'
        except Exception as inst:
            # print(type(inst))
            # print(inst.args)  # arguments stored in .args
            # print(inst)  # __str__ allows args to be printed directly
            try:
                key = request.form['key'][-10:]
                if key == session.pop('key'):
                    flash('Transfer of ' + str(session.get('amount')) + ' Credits was successfull!')
                    u.funds += int(session.pop('amount'))
                else:
                    error = 'wrong key, transaction invalidated.'
                    session.pop('amount')
                    session.pop('key')
            except Exception as ins:
                # print(type(ins))
                # print(ins.args)  # arguments stored in .args
                # print(ins)  # __str__ allows args to be printed directly
                error = 'invalid transaction'

    ul.saveuserlist()
    return render_template('funds.html', user=u, error=error, keyprovided=keyprovided)


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
                if len(password) > 0:
                    print("creating user", username)
                    error = u.adduser(User(username, password))
                    print("error is", error)
                    if error is None:
                        flash('User successfully created.')
                        return redirect(url_for('start'))
                else:
                    error = 'Password has to be not empty!'
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
        user = user.upper()
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
    session.clear()
    flash('You were logged out')
    return redirect(url_for('show_entries'))


@app.route('/nn')
def start():
    print("nncalled")
    return render_template('show_entries.html', \
                           entries=[
                               dict(author='the NOSFERATU NETWORK', title='WeLcOmE tO tHe NoSfErAtU nEtWoRk', text='')],
                           heads=['<META HTTP-EQUIV="refresh" CONTENT="5;url=/">'])


@app.route('/regendb/')
def resetdb():
    init_db()
    return "ok "


@app.route('/user/<username>')
def show_user_profile(username):
    msgs = []
    if username == session.get('user'):  # get messages for this user if looking at own page
        cur = g.db.execute(
            'SELECT author,title,text,value,lock,honored, id FROM messages WHERE recipient = ? ORDER BY id DESC',
            [session.get('user')])
        for row in cur.fetchall():
            msg = dict(author=row[0], title=row[1], text=row[2], value=row[3], lock=row[4], honored=row[5], id=row[6])
            cur2 = g.db.execute('SELECT kudosrep, kudosaut FROM messages WHERE id = ?', [msg['id']])
            for row2 in cur2.fetchall():
                msg['kudosrep'] = row2[0]
                msg['kudosaut'] = row2[1]
            if msg['lock']:
                msg['text'] = '[locked until you pay]'
            if msg['value'] <= 0:  # usually we dont need the special stuff
                msg.pop('honored')
                msg.pop('lock')
            msgs.append(msg)
            #  else:

    ul = Userlist()
    if ul.contains(username):
        u = ul.getuserbyname(username)
    else:
        u = User(username, "")
        u.kudos = random.randint(0, 10000)
    site = render_template('userinfo.html', user=u, msgs=msgs)
    return site


@app.route('/sendmsg/<username>', methods=['POST'])
def send_msg(username):
    error = None
    if not session.get('logged_in'):
        error = 'You are not logged in!'
        return redirect(url_for('login'))
    g.db.execute('INSERT INTO messages (author,recipient,title,text,value,lock,honored) VALUES (?, ?, ?, ?, ?, ?, ?)',
                 [session.get('user'), username, request.form['title'], request.form['text'], request.form['value'],
                  not check0(request.form['value']), check0(request.form['value'])])
    g.db.commit()
    flash('Message sent')
    return redirect(url_for('show_entries'))  # , error = error)


def check0(a):  # used in sendmsg because typecasts in THAT line would make things even worse
    return int(a) == 0


@app.route('/honor/<ident>')
def honor(ident):
    honored = 1
    ul = Userlist()
    error = None
    lock = 0
    u = ul.getuserbyname(session.get('user'))
    cur = g.db.execute('SELECT author, value, lock, honored FROM messages WHERE id = ?', [ident])
    for row in cur.fetchall():
        author = row[0]
        # value = row[1]
        lock = row[2]
        honored = row[3]
    n = ul.getuserbyname(author)
    if lock != 1:
        if honored != 0:
            error = "This agreement has already been honored."
        else:
            cur = g.db.execute('SELECT kudosrep, kudosaut FROM messages WHERE id = ?', [ident])
            for row in cur.fetchall():
                kudosrep = row[0]
                kudosaut = row[1]
            u.addkudos(kudosrep)
            n.addkudos(kudosaut)
            g.db.execute('UPDATE messages SET honored = 1 WHERE id = ?', [ident])
            cur = g.db.execute('SELECT * FROM messages')
            for row in cur.fetchall():
                print(row)
            flash("Transfer complete. Check the received messsage and "
                  "press the Honor Button if is was what you ordered.")
            g.db.commit()
            ul.saveuserlist()
    else:
        flash('already unlocked!')
    return render_template('userinfo.html', user=u, error=error,
                           heads=['<META HTTP-EQUIV="refresh" CONTENT="5;url=' + url_for('show_user_profile',
                                                                                         username=u.username) + '">'])


@app.route('/unlock/<ident>')
def unlock(ident):
    ul = Userlist()
    error = None
    lock = 0
    author = ''
    value = sys.maxsize
    u = ul.getuserbyname(session.get('user'))
    cur = g.db.execute('SELECT author, value, lock FROM messages WHERE id = ?', [ident])
    for row in cur.fetchall():
        author = row[0]
        value = row[1]
        lock = row[2]
    n = ul.getuserbyname(author)  # n because n = u seen from the other side of the table
    if lock == 1:
        if u.kudos * 0.9 < value:
            error = "You do not have enough kudos for this transaction!"
        elif n.kudos * 0.9 < value:
            error = "Your partner has not enough kudos for this transaction!"
        elif u.funds < value:
            error = "Not enough funds."
        else:
            u.funds -= value
            uescrow = int(
                0.1 * u.kudos + value)  # (10% of the total Kudos now + twice the value)will be paid upon redemption
            u.addkudos(-uescrow)  # but 10% and the value are deducted now
            uescrow += value
            aftertax = int(value * 0.99)
            tax = value - aftertax  # TAX
            print('taxed')
            print(tax)
            n.funds = int((n.funds + aftertax))
            nescrow = int(0.1 * n.kudos + value)
            n.addkudos(-nescrow)
            nescrow += value
            g.db.execute('UPDATE messages SET lock = 0, kudosrep=?, kudosaut=? WHERE id = ?',
                         [uescrow, nescrow, ident])
            # cur = g.db.execute('SELECT * FROM messages')
            # for row in cur.fetchall():
            #    print(row)
            flash("Transfer complete. Check the received messsage and "
                  "press the Honor Button if is was what you ordered.")
            g.db.commit()
            ul.saveuserlist()
    else:
        flash('already unlocked!')
    return render_template('userinfo.html', user=u, error=error,
                           heads=['<META HTTP-EQUIV="refresh" CONTENT="5;url=' + url_for('show_user_profile',
                                                                                         username=u.username) + '">'])


@app.route('/payout/', methods=['GET', 'POST'])
def payout():
    ul = Userlist()
    u = ul.getuserbyname(session.get('user'))
    error = None
    if request.method == 'POST':
        try:
            amount = int(request.form['amount'])
            u.funds += -amount
            print('DEDUCT')
            print(session.get('user'))
            print(amount)
            flash('Deduct successfull')
        except:
            flash('ERROR')
    ul.saveuserlist()
    return render_template('payout.html', user=u, error=error)


@app.errorhandler(404)
def page_not_found(error):
    return error


@app.route('/deathanddestruction')
def deldb():
    db = connect_db()
    db.execute('DROP TABLE IF EXISTS entries')
    db.execute('DROP TABLE IF EXISTS messages')
    db.commit()
    init_db()
    session.clear
    return "<link rel=stylesheet type=text/css href=\"/static/style.css\"> death and destruction has been brought forth"


def openupdb():
    db = connect_db()
    # db.execute('DELETE FROM entries WHERE ID = 3')
    # cur = db.execute('SELECT  FROM entries ORDER BY id DESC')
    # print (cur.fetchall())
    # cur =
    if db is not None:
        db.close()


openupdb()

if __name__ == '__main__':
    # app.run(debug=True)
    app.run(debug=False, host='0.0.0.0')
