import time

from NossiSite import app, socketio
# import time
# import threading
import re
from flask import render_template, session, request, flash, url_for, redirect
from flask_socketio import emit, join_room, leave_room, disconnect
from NossiPack.Chatrooms import Chatroom
import NossiPack.Character
from NossiPack.User import Userlist
from NossiPack.WoDDice import WoDDice

thread = None

userlist = {}
rooms = [Chatroom('lobby')]


def statusupdate():
    if session['chatmode'] == 'menu':
        emit('Status', {'status': 'Current Mode: Menu. Type "help" for help.'})
    elif session['activeroom'] not in session['rooms']:
        emit('Status', {'status': 'currently not in any room.'})
    elif session['activeroom'].name not in [x for x in userlist.values()]:
        emit('Status', {'status': 'Currently talking in: "' + session['activeroom'].name + '".'})
    else:
        emit('Status', {'status': 'Currently talking.'})


def echo(message, sep=": ", err=False):
    if err:
        emit('Message', {'data': sep + message})
    else:
        emit('Message', {'data': session['user'] + sep + message})


def post(message, sep=": "):
    session['activeroom'].addline(session['user'] + sep + message)


def decider(message):
    if message[0] == '#':
        if message == "#?":
            echo('\nmessages prefixed with # are passed to the diceroller'
                 '\nit expects a number following # and then options '
                 '\nfollowed by numbers again. Options are'
                 '\ndXX : sets sidedness of dice to XX. (standard: 10)'
                 '\neXX : sets difficulty to XX and discards 1s'
                 '\nfXX : sets difficulty to XX and subtracts 1s (standard: 6)'
                 '\n!   : sets explosions, use multiple for cumulative effect'
                 '\n#XX : load define named XX'
                 '\n=XX : command for defines:'
                 '\n\t =clear  : clears all definitions'
                 '\n\t =import : imports/reloads the values from the sheet'
                 '\n\t =setup  : a usefull basic set of definitions'
                 '\n\t =show   : shows all currently defined Definitions'
                 '\nA=B : defines #A to resolve to B. B resolves recursively'
                 '\n      If B is two values they will be added.'
                 '\n      If there is a _ after something (on the lowest level) '
                 '\n      it will resolve to -1 instead of 0 (useful for abilities)'
                 '\nExample: Try: "#=setup<enter> #dmg=#str+2<enter> ##dmg<enter> and see what happens!'
                 '\nRemember that you can always add ? to a command to inspect what'
                 ' its doing instead of actually sending it.')
            return
        if not (("?" in message) or ("=" in message)):
            post(message[1:], "'s ROLL: ")
        printroll(diceparser(message[1:]))
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


def defines(message="="):
    ul = Userlist()
    u = ul.loaduserbyname(session['user'])
    workdef = u.defines
    if message == "=clear":
        workdef = {}
        echo("Definitions reset.")
    elif message == "=show":
        echodict(workdef)

    elif message == "=import":
        workdef = {**workdef, **u.sheet.unify()}
        echo("Current charactersheet imported.")
    elif message == "=setup":
        if workdef == {}:
            workdef = u.sheet.unify()
            echo("Definitions reset.")
        workdef = {**workdef, **WoDDice.shorthand()}
        echo("Presets setup.")
    if message[0] != "=":
        parts = message.split("=")
        workdef[parts[0]] = parts[1]
        echo("added define for %s=%s" % (parts[0], parts[1]))
    u.defines = workdef
    ul.saveuserlist()


def resolvedefine(message, reclvl=0, trace=False, user=None):
    try:
        return int(message)
    except:
        if reclvl > 100:
            echo("Problem resolving " + message, " ERROR:")
            return 0

    finder = re.compile(r'(.*?)\((.*?)\)(.*)')
    for i in finder.findall(message):
        print("match:", i)
        roll = diceparser(i[1]).roll_nv()
        if not roll:
            roll = ""
        # else:
            # post(str(roll), " RESOLVED ("+i[1]+") TO: ")
        message = i[0]+str(roll)+i[2]
    finder = re.compile(r'§([^ ]+)(.*)')
    for i in finder.findall(message):
        if i[0] in session['activeroom'].getuserlist_text():
            message = message.replace("§"+"".join(i), resolvedefine(i[1], reclvl=reclvl + 1, trace=trace, user=i[0]))
            break
    ul = Userlist()

    if user is None:
        u = ul.loaduserbyname(session.get('user', '?'))
    elif not u.sheetpublic:
        u = NossiPack.Character.Character()

    u = ul.loaduserbyname(user)
    if not u:
        echo("user " + user + " not found!", "NAMEERROR: ", err=True)
        return
    workdef = u.defines.copy()
    if trace:
        echo(" DEFINITIONS FOR " + user, "", err=True)
        echodict(workdef)
    message = message.replace("§" + user, "")
    finder = re.compile(r'#([^ +#]+)_')
    for i in finder.findall(message):
        toreplace = str(resolvedefine(workdef.get(i, "0"), reclvl + 1, trace, user))
        if toreplace == "0":
            toreplace = "-1"
        if trace:
            echo(i + ":" + str(workdef.get(i, "-1")))
        message = message.replace("#" + i, " " + toreplace + " ")
    finder = re.compile(r'#([^ +#]+)')
    while not finder.findall(message) == []:
        for i in finder.findall(message):

            toreplace = str(resolvedefine(workdef.get(i, "0"), reclvl + 1, trace, user))
            if trace:
                echo(i + ":" + str(workdef.get(i, "0")))
            message = message.replace("#" + i, " " + toreplace + " ")
    message = message.replace("+", " + ")
    action = True
    adder = re.compile(r'((\b-?\d+) +\+? +(-?[0-9]+\b))')
    if trace:
        echo("adding: " + message)
    while action:
        a = adder.findall(message)
        try:
            a = a[0]
            message = message.replace(a[0], str(int(a[1]) + int(a[2])))
        except:
            action = False
    message = message.replace(" ", "").replace("_", "")
    return message


def diceparser(message, rec=False, testing=False):
    if ";" in message:
        for m in message.split(";"):
            diceparser(m)
        return
    subones = 1
    if "?" in message:
        testing = True
        message = message.replace("?", "")

    amountfilter = re.compile(r'(^[0-9]*)')
    dicefilter = re.compile(r'd([0-9]*)', re.IGNORECASE)
    explodefilter = re.compile(r'!+')
    if ("e" in message) or ("E" in message):
        difffilter = re.compile(r'e([0-9]*)', re.IGNORECASE)
        subones = 0
    else:
        difffilter = re.compile(r'f([0-9]*)', re.IGNORECASE)
    amount = amountfilter.findall(message, endpos=3)  # max of 999 dice
    explode = explodefilter.findall(message)
    dice = dicefilter.findall(message)
    diff = difffilter.findall(message)
    if amount[0] == '':
        if "=" in message:
            defines(message)
            return
        else:
            if not rec:
                return diceparser(str(resolvedefine(message, trace=testing)), rec=True, testing=testing)
            else:
                if '\\' not in message:
                    return echo(' Diceroller couldn\'t parse: ' + str(message), "ROLLERERROR: ", err=True)

    if not testing:
        post(message.replace("\\", ""), " RESOLVED TO: ")
    if '\\' not in message:
        amount = int(amount[0])
        if not dice:
            dice = ['10']
        elif dice == ['']:
            echo('Malformed dice code. Thre have to be digits after d.', "ROLLERERROR: ", err=True)
            return
        dice = int(dice[0])
        if not diff:
            diff = ['6']
        elif diff == ['']:
            echo('Malformed difficulty code. There have to be digits after e or f.', "ROLLERERROR: ", err=True)
            return
        diff = int(diff[0])
        if not explode:
            explode = 0
        else:
            explode = dice + 1 - len(explode[0])
        if subones:
            onebehaviour = "subtracting"
        else:
            onebehaviour = "ignoring"
        if explode > 0:
            explodebehaviour = ", exploding on rolls of " + str(explode) + " or more"
        else:
            explodebehaviour = ""
        post(str(amount) + " " + str(dice) + " sided dice against " + str(
            diff) + ", " + onebehaviour + " ones" + explodebehaviour + ".", " ROLLS: ")
        roll = WoDDice(dice, diff, subones, explode)
        roll.roll(amount)
        if testing:
            return echo("test complete:" + message)
        return roll


def printroll(roll):
    if not roll:
        return
    print(roll.roll_nv())
    if roll.explodeon <= roll.max:
        post("", " IS ROLLING, exploding on " + str(roll.explodeon) + "+: \n")
        for i in roll.roll_vv().split("\n"):
            post(i, " ROLL: ")
            time.sleep(0.5)
    elif len(roll.r) > 50:
        post(str(roll.roll_nv()), " IS ROLLING: [" + str(len(roll.r)) + " DICEROLLS] ==> ")
    else:
        post(roll.roll_v(), " IS ROLLING: ")


def menucmds(message, stripped=""):
    if message == 'help':
        echo(message, ": /")
        emit('Message', {'data': '\navailable subscripts:'
                                 '\nwidth  <n>: adjusts page width (35 is standart)'
                                 '\nheight <n>: adjusts height of this box (in pixel)'
                                 '\njoin   <s>: joins room'
                                 '\nleave  <s>: leaves that specific room'
                                 '\nswitch <s>: makes the specified room active'
                                 '\nmenu      : to switch to menu mode'
                                 '\ntalk      : to begin talking'
                                 '\nmailbox   : to check the log of messages send to you'
                                 '\nlog       : to get the log of the room you are in '
                                 '\n#         : Diceroller type #? for more info'
                                 '\n'})
        if session['chatmode'] == 'menu':
            emit('SetCmd', {'data': '/talk'})
    elif message == 'menu':
        echo(message, ": /")
        session['chatmode'] = 'menu'
    elif message == 'log':
        echo(message, ": /")
        if session['activeroom'] is not None:
            emit('Message', {'data': '\n#####START###LOG#####\n' +
                                     session['activeroom'].getlog(session['user']) +
                                     '######END####LOG#####\n'})
        else:
            emit('Message', {'data': 'no room to get log from!'})
    elif message == 'userlist':
        echo(message, ": /")
        if session['activeroom'] is not None:
            emit('Message', {'data': '\n#####START###LIST####\n' +
                                     session['activeroom'].getuserlist_text() +
                                     '######END####LIST####\n'})
        else:
            emit('Message', {'data': 'no room to get list from!'})
    elif message.split(' ')[0] == 'room':
        echo(message, ": /")
        emit('Message', {'data': " ".join(x.name for x in session['rooms'] if x != session['rooms'][0])})
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
            if room in [x.name for x in session['rooms']]:
                emit('Message', {'data': 'already in there!'})
            else:
                joining = rooms[0]
                for r in rooms:
                    if (room == r.name) and (not r.mailbox):
                        r.userjoin(session['user'])
                        session['rooms'].append(r)
                        joined = True
                        joining = r
                if not joined:
                    joining = Chatroom(room)
                    joining.userjoin(session['user'])
                    session['rooms'].append(joining)
                    rooms.append(joining)

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
        for r in session['rooms']:
            if (room == r.name) and (not r.mailbox):
                r.userleave(session['user'])
                session['rooms'].remove(r)
                left = True

                emit('Message', {'data': 'removed ' + room})
        if not left:
            emit('Message', {'data': 'not subsrcribed to ' + room + '!'})

    elif message.split(' ')[0] == 'mailbox':
        echo(message, ": /")
        emit('Message', {'data': '\n#####START###LOG#####\n' +
                                 session['rooms'][0].getlog(session['user']) +
                                 '######END####LOG#####\n'})
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
            for r in rooms:
                if r.name == recipient + "_mailbox":
                    r.addline(session['user'] + "->" + recipient + ": " + recipient_message)
            emit('Message', {'data': session['user'] + "->" + recipient + ": " + recipient_message})
            emit('SetCmd', {'data': "/msg " + recipient + " "})

    elif message.split(' ')[0] == 'switch':
        echo(message, ": /")
        room = message.split(' ')[1]
        emit('Message', {'data': 'switching to ' + room + '...'})
        switched = False
        for r in session['rooms']:
            if (room == r.name) and (not r.mailbox):
                leave_room(session['activeroom'].name)
                session['activeroom'] = r
                join_room(session['activeroom'].name)
                switched = True
                emit('Message', {'data': 'done switching!'})
            if switched:
                break

        if not switched:
            emit('Message', {'data': 'not subscribed to ' + room + '!'})

    elif message == 'talk':
        emit('Message', {'data': '\nentering talk mode, prefix further commands with "/"'
                                 '\nand dice roll codes with #.'
                                 '\nEverything else will be sent to the active chat!\n\n'})
        session['chatmode'] = 'talk'
        join_room(session['activeroom'].name)

    elif message == 'connection established':
        emit('SetCmd', {'data': '/help'})
        return True
    else:
        emit('Message', {'data': 'command not found. Type help for help.'})
    return False


@app.route('/chat/')
def chatsite():
    if not session.get('logged_in'):
        flash('You are not logged in!')
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
    decider(message['data'])


@socketio.on('connect', namespace='/character')
def char_connect():
    if not session.get('user', False):
        emit('comments', {'prefix': '', 'data': 'Not logged in.'})
        return False
    emit('comments', {'data': "Click \"Check\" down below to check if this sheet "
                              "is a valid starting character (If your history is empty), "
                              "or calculate the difference in XP to the last sheet in "
                              "your history."})


@socketio.on('ClientServerEvent', namespace='/character')
def receive(message):
    print(session.get('user', "NoUser"), ":\t", message)
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
        test = NossiPack.Character.Character()
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
        emit('Message', {'prefix': '', 'data': 'Not logged in.'})
        return False
    global userlist
    session['id'] = request.sid
    if session.get('user', False):
        userlist[session['user'].upper()] = session['id']
        mailbox = Chatroom(session['user'], True)
        rooms.append(mailbox)
        session['rooms'] = [mailbox, rooms[0]]

        try:
            prevmode = session['chatmode']
        except:
            prevmode = 'talk'
            session['activeroom'] = session['rooms'][1]
            join_room(session['activeroom'].name)
        session['chatmode'] = prevmode
        session['activeroom'] = rooms[0]
        rooms[0].userjoin(session['user'])
        join_room(rooms[0])
        emit('Message', {'data': 'Hello and Welcome to the NosferatuNetwork Chatserver.\n'})
    else:
        disconnect()
        return False


# noinspection PyUnresolvedReferences
@socketio.on('disconnect', namespace='/chat')
def test_disconnect():
    print('Client disconnected', request.sid)
    for r in session['rooms']:
        r.userleave(session['user'])
