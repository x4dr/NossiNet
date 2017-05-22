import time
import json

from NossiSite import app, socketio
# import time
# import threading

from flask import render_template, session, request, flash, url_for, redirect
from flask_socketio import emit, join_room, leave_room, disconnect, rooms
from NossiPack import *
from NossiPack import WoDData

thread = None

userlist = {}
roomlist = [Chatroom('lobby')]
namedStrings = {}


def statusupdate():
    if session['chatmode'] == 'menu':
        emit('Status', {'status': 'Current Mode: Menu.' + namedStrings["helpHelp"]})
    elif session['activeroom'] not in session['roomlist']:
        emit('Status', {'status': 'Currently not in any room.'})
    elif session['activeroom'].name not in [x for x in userlist.values()]:
        emit('Status', {'status': 'Currently talking in: "' + session['activeroom'].name + '".'})
    else:
        emit('Status', {'status': 'Currently talking.'})


def echo(message, sep=": ", err=False):
    if err:
        emit('Message', {'data': sep + message})
    else:
        emit('Message', {'data': session['user'] + sep + message})


with open('strings.json') as json_data:
    namedStrings = json.load(json_data)['namedStrings']


def post(message, sep=": "):
    session['activeroom'].addline(session['user'] + sep + message)


def decider(message):
    if message[0] == '#':
        if message == "#?":
            echo(''.join(namedStrings['generalHelp']))
            return
        if not (("?" in message) or ("=" in message)):
            try:
                t0 = time.time()
                post(message, "'s ROLL: ")
                parser = WoDParser(defines())
                t1 = time.time()
                roll = parser.diceparser(message)
                t1_1 = time.time()
                trigger(parser.triggers)
                t2 = time.time()
                update_dots()
                print(roll.roll_v())
                printroll(roll, parser)
                t3 = time.time()

            except Exception as inst:
                echo(str(inst.args[0]), "ROLLING ERROR: ", err=True)

        elif "?" in message:
            echo(message, "'s TEST: ")
            parser = WoDParser(defines())
            roll = parser.diceparser(message, defines())
            echo(parser.dbg, "'s TEST: ")
            printroll(roll, testing=True)
        elif "=" in message:
            defines(message[1:])

    elif message[0] == '/':
        if menucmds(message[1:], "/"):
            echo(message)
    elif session['chatmode'] == 'menu':
        if menucmds(message):
            echo(message)
    elif session['chatmode'] == 'talk':
        if session['activeroom'] is None:
            emit('Message', {'data': 'you are talking to a wall'})
        else:
            print('room: ' + session['activeroom'].name)
            post(message)
    statusupdate()


def echodict(dict):
    a = list(dict.keys())
    a.sort()
    for i in a:
        echo(("%s" % i).ljust(15) + " : " + str(dict[i]), "", err=True)


def trigger(triggers, user=None):
    if not user:
        user = session['user']
    ul = Userlist()
    u = ul.loaduserbyname(user)
    for t in triggers:
        u.sheet.process_trigger(t)
    ul.saveuserlist()


def defines(message="=", user=None):
    if message[0] == "#":
        message = message[1:]
    message = message.strip()
    if not user:
        user = session['user']
    ul = Userlist()
    u = ul.loaduserbyname(user)
    workdef = u.defines
    if message[:6] == "=clear":

        workdef = {}
        echo("Definitions reset.")
    elif message[:7] == "=delete":
        try:
            test = workdef[message[8:]]
            workdef.pop(message[8:])
            echo("Entry " + message[8:] + " cleared.")
        except:
            echo("Entry " + message[8:] + " not found.")
    elif message[:5] == "=show":
        echodict(workdef)

    elif message[:7] == "=import":
        workdef = {**workdef, **u.sheet.unify()}
        echo("Current charactersheet imported.")
    elif message == "=setup":
        if workdef == {}:
            workdef = u.sheet.unify()
            echo("Definitions reset.")
        workdef = {**workdef, **WoDParser.shorthand(), **WoDData.disciplines(workdef)}
        echo("Presets setup.")
    elif message[0] != "=":  # actually saving a new define
        parts = message.split("=")
        workdef[parts[0].strip()] = parts[1].strip()  # stripping to get whitespace out of the equation
        echo("added define for %s=%s" % (parts[0], parts[1]))
    elif ("=" in message) and (message != "="):
        echo("No valid config command: " + message)
    u.defines = workdef
    if user == session['user']:
        ul.saveuserlist()
    return workdef


def printroll(roll, parser=None, testing=False):
    t0 = time.time()
    if not roll:
        return
    if not roll.rolled:
        return
    if testing:
        deliver = echo
    else:
        deliver = post
    if parser:
        if "§supress_" not in parser.triggers:
            deliver(parser.dbg[:-1], "'s ROLL: \n")
            for r in parser.altrolls:
                printroll(r, testing=testing)
    if roll.difficulty == 0 and roll.max == 1:
        deliver(str(roll.roll_nv()) + ".", " IS ADDING UP TO: ")
        return

    if roll.explodeon <= roll.max:
        deliver("", " IS ROLLING, exploding on " + str(roll.explodeon) + "+: \n")
        for i in roll.roll_vv().split("\n"):
            deliver(i, " ROLL: ")
            time.sleep(0.5)
    elif len(roll.r) > 50:
        deliver(str(roll.roll_nv()), " IS ROLLING: [" + str(len(roll.r)) + " DICEROLLS] ==> ")
    else:
        deliver(roll.roll_v(), " IS ROLLING: ")
    t1 = time.time()


def menucmds(message, stripped=""):
    if message == 'help':
        echo(message, ": /")
        emit('Message', {'data': echo(''.join(namedStrings['chatHelp']))})
        if session['chatmode'] == 'menu':
            emit('SetCmd', {'data': '/talk'})
    elif message == 'menu':
        echo(message, ": /")
        session['chatmode'] = 'menu'
    elif message == 'log':
        echo(message, ": /")
        if session['activeroom'] is not None:
            emit('Message', {'data': namedStrings['startLog'] +
                                     session['activeroom'].getlog(session['user']) +
                                     namedStrings['endLog']})
        else:
            emit('Message', {'data': namedStrings['noLogRoom']})
    elif message == 'userlist':
        echo(message, ": /")
        if session['activeroom'] is not None:
            emit('Message', {'data': namedStrings['startList'] +
                                     session['activeroom'].getuserlist_text() +
                                     namedStrings['endList']})
        else:
            emit('Message', {'data': namedStrings['noListRoom']})
    elif message.split(' ')[0] == 'room':
        echo(message, ": /")
        emit('Message', {'data': " ".join(x.name for x in session['roomlist'] if x != session['roomlist'][0])})
    elif message.split(' ')[0] == 'width':
        echo(message, ": /")
        try:
            width = str(int(message.split(' ')[1])) + "em"
        except:
            width = "90%"
        emit('Message', {'data': '\nadjusting width...\n'})
        emit('Exec', {'command': 'document.getElementById("page_complete").style.width = "' + width + '";'})
    elif message.split(' ')[0] == 'height':
        echo(message, ": /")
        try:
            height = str(int(message.split(' ')[1])) + "em"
        except:
            height = "35em"
        emit('Message', {'data': '\nadjusting height...\n'})
        emit('Exec', {'command': 'document.getElementById("chatbox").style.height = "' + height + '";'})

    elif message.split(' ')[0] == 'join':
        try:
            room = message.split(' ')[1]
        except:
            emit('Message', {'data': 'join where?'})
            emit('SetCmd', {'data': '/join '})
            room = None
        if room is not None:
            emit('Message', {'data': 'subscribing to ' + room + '...'})
            joined = False
            if room in [x.name for x in session['roomlist']]:
                emit('Message', {'data': 'already in there!'})
            else:
                joining = roomlist[0]
                for r in roomlist:
                    if (room == r.name) and (not r.mailbox):
                        r.userjoin(session['user'])
                        session['roomlist'].append(r)
                        joined = True
                        joining = r
                if not joined:
                    joining = Chatroom(room)
                    joining.userjoin(session['user'])
                    session['roomlist'].append(joining)
                    roomlist.append(joining)

                leave_room(session['activeroom'].name)
                session['activeroom'] = joining
                join_room(session['activeroom'].name)
                emit('Message', {'data': 'done joining!'})

    elif message.split(' ')[0] == 'leave':
        echo(message, ": /")
        try:
            room = message.split(' ')[1]
        except:
            room = session['activeroom'].name
        emit('Message', {'data': 'unsubscribing from ' + room + '...'})
        left = False
        for r in session['roomlist']:
            if (room == r.name) and (not r.mailbox):
                r.userleave(session['user'])
                session['roomlist'].remove(r)
                left = True

                emit('Message', {'data': 'removed ' + room})
        if not left:
            emit('Message', {'data': namedStrings["notSubscribedTo"] + room + '!'})

    elif message.split(' ')[0] == 'mailbox':
        echo(message, ": /")
        emit('Message', {'data': namedStrings['startLog'] +
                                 session['roomlist'][0].getlog(session['user']) +
                                 namedStrings['endLog']})
    elif message.split(' ')[0] == 'msg':
        echo(message, ": /")
        try:
            recipient = message.split(' ')[1]
        except:
            emit('Message', {'data': 'message who?'})
            recipient = None
        recipient_message = " ".join(message.split(' ')[2:])
        if (recipient_message == "") or recipient_message.isspace():
            emit('Message', {'data': 'message what?'})
            recipient = None
        if recipient is not None:
            for r in roomlist:
                if r.name == recipient + "_mailbox":
                    r.addline(session['user'] + "->" + recipient + ": " + recipient_message)
            emit('Message', {'data': session['user'] + "->" + recipient + ": " + recipient_message})
            emit('SetCmd', {'data': "/msg " + recipient + " "})

    elif message.split(' ')[0] == 'switch':
        echo(message, ": /")
        room = message.split(' ')[1]
        emit('Message', {'data': 'switching to ' + room + '...'})
        switched = False
        for r in session['roomlist']:
            if (room == r.name) and (not r.mailbox):
                leave_room(session['activeroom'].name)
                session['activeroom'] = r
                join_room(session['activeroom'].name)
                switched = True
                emit('Message', {'data': 'done switching!'})
            if switched:
                break

        if not switched:
            emit('Message', {'data': namedStrings["notSubscribedTo"] + room + '!'})

    elif message == 'talk':
        emit('Message', {'data': ''.join(namedStrings['talkMode'])})
        session['chatmode'] = 'talk'
        join_room(session['activeroom'].name)

    elif message == 'connection established':
        echo(namedStrings['canTalkNow'] + ' ' + namedStrings['helpHelp'])
        return False
    else:
        emit('Message', {'data': namedStrings['cmdNotFound'] + ' ' + namedStrings['helpHelp']})
    return False


@app.route('/chat/')
def chatsite():
    if not session.get('logged_in'):
        flash(namedStrings['notLoggedIn'])
        return redirect(url_for('login'))
    # global thread
    # if thread is None:
    # thread = threading.Thread(target=background_thread)
    # thread.daemon = True
    # thread.start()
    return render_template('chat.html')


@socketio.on('ClientServerEvent', namespace='/chat')
def receive(message):
    print(session.get('user', "NoUser"), ": ", message)
    t0 = time.time()
    decider(message['data'])
    t1 = time.time()
    update_dots()


@socketio.on('connect', namespace='/character')
def char_connect():
    if not session.get('user', False):
        emit('comments', {'prefix': '', 'data': namedStrings['notLoggedIn']})
        return False
    emit('comments', {'data': ''.join(namedStrings['checkHelp'])})
    join_room(session.get("user", "?") + "_dotupdates")
    update_dots()


@socketio.on('ClientServerEvent', namespace='/character')
def receive_message(message):
    update_dots()


def update_dots():
    update = ""
    maxima = ""
    ul = Userlist()
    u = ul.loaduserbyname(session.get('user', "?"))
    update += 'Bloodpool_' + str(u.sheet.special['Bloodpool'])
    maxima += 'Bloodmax_' + str(u.sheet.special['Bloodmax'])
    update += '&'
    maxima += '&'
    update += 'Willpower_' + str(u.sheet.special['Willpower'])
    maxima += 'Willmax_' + str(u.sheet.special['Willmax'])
    health = str(u.sheet.special['Bashing']) + '&' + str(u.sheet.special['Lethal']) + '&' + str(
        u.sheet.special['Aggravated']) + '&' + str(u.sheet.special['Partialheal'])
    emit('DotUpdate', {'data': update + "§" + maxima + "§" + health}, room=session.get("user", "?") + "_dotupdates")


@socketio.on('NoteDots', namespace='/character')
def note_dots(message):
    data = message['data'].split("&")
    ul = Userlist()
    u = ul.loaduserbyname(session.get('user', "?"))
    u.sheet.special['Willpower'] = 0  # initialize with 0 because if 0 on sheet no value will be given
    u.sheet.special['Bloodpool'] = 0
    for d in data:
        if d.split("=")[0] == "Willpower":  # some semblance of santizing
            u.sheet.special['Willpower'] = int(d.split("=")[1])
        if d.split("=")[0] == "Bloodpool":  # some semblance of santizing
            u.sheet.special['Bloodpool'] = int(d.split("=")[1])
    ul.saveuserlist()
    update_dots()


@socketio.on('CheckChar', namespace='/character')
def check_char(message):
    print("CHARACTERSHEET", session.get('user', "NoUser"), ":  ", message)
    if len(message['data']) > 20:  # short messages are malformed
        ul = Userlist()
        u = ul.loaduserbyname(session.get('user', None))
        try:
            old = u.oldsheets[-1]
        except:
            old = None
        formdata = {}
        for f in message['data']:
            formdata[f['name']] = f['value']
        test = Character()
        test.setfromform(formdata)
        emit('comments', {'data': test.get_diff(old=old, extra=True)})


@socketio.on('Disconnect', namespace='/chat')
def disconnect_request():
    emit('Message',
         {'data': 'Disconnected!'})
    disconnect()


# noinspection PyUnresolvedReferences
@socketio.on('connect', namespace='/chat')
def chat_connect():
    if not session.get('logged_in'):
        emit('Message', {'prefix': '', 'data': namedStrings['notLoggedIn']})
        return False
    global userlist
    join_room(session.get("user", "?") + "_dotupdates")
    session['id'] = request.sid
    if session.get('user', False):
        userlist[session['user'].upper()] = session['id']
        mailbox = Chatroom(session['user'], True)
        roomlist.append(mailbox)
        session['roomlist'] = [mailbox, roomlist[0]]
        try:
            prevmode = session['chatmode']
        except:
            prevmode = 'talk'
            session['activeroom'] = session['roomlist'][1]
            join_room(session['activeroom'].name)
        session['chatmode'] = prevmode
        session['activeroom'] = roomlist[0]
        roomlist[0].userjoin(session['user'])
        join_room(roomlist[0])
        emit('Message', {'data': namedStrings['MOTD']})
    else:
        disconnect()
        return False


# noinspection PyUnresolvedReferences
@socketio.on('disconnect', namespace='/chat')
def test_disconnect():
    # DEBUG 
    print(str(session))
    try:
        print('Client disconnected', rooms())
    except:
        print("Last client disconnected.")
    try:
        for r in session['roomlist']:
            r.userleave(session['user'])
    except Exception as inst:
        print(namedStrings['roomlistErr'],inst.args)
