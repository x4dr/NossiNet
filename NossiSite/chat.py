from NossiSite import app, socketio
import time
import threading
from flask import render_template, session, abort, request
from flask_socketio import emit, join_room, leave_room, \
    rooms, disconnect
import uuid

thread = None

userlist = {}


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while count < -1:
        print("sending status")
        time.sleep(10)
        count += 1
        socketio.emit('PING',
                      {'data': 'not implemented yet'},
                      namespace='/chat')
    global thread
    thread = None


@app.route('/chat/')
def chatsite():
    if not session.get('logged_in'):
        abort(401)
    global thread
    if thread is None:
        thread = threading.Thread(target=background_thread)
        thread.daemon = True
        thread.start()
    return render_template('chat.html')


@socketio.on('ClientServerEvent', namespace='/chat')
def test_message(message):
    print(session.get('user', "NoUser"), "\t", message)
    emit('Message',
         {'prefix': message.get('prefix', ''), 'data': message['data']})
    if "userlist" in message['data']:
        ul = ""
        for sessid, socket in socketio.wsgi_server.sockets.items():
            ul += socket['/chat'].session['user'] + " "
        emit('Message', {'prefix': 'Userlist:', 'data': ul})


@socketio.on('BroadCastEvent', namespace='/chat')
def test_broadcast_message(message):
    emit('Message',
         {'data': message['data'], 'prefix': message['prefix']},
         broadcast=True)


@socketio.on('Join', namespace='/chat')
def join(message):
    join_room(message['room'][:30])
    emit('Message',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'prefix': message['prefix']})


@socketio.on('Leave', namespace='/chat')
def leave(message):
    leave_room(message['room'][:30])
    emit('Message',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'prefix': message['prefix']})


@socketio.on('RoomEvent', namespace='/chat')
def send_room_message(message):
    print(message)
    emit('Message',
         {'data': message['data'], 'prefix': message['room']+'/'+message['prefix']},
         room=message['room'])


@socketio.on('PrivateAnonymousMessage', namespace='/chat')
def send_anon_message(message):
    recipient = userlist.get(message['recipient'].upper())
    if recipient is None:
        emit('Message', {'prefix':'','data':'recipient not found'})
    else:
        emit('Message', {'prefix':message['prefix'], 'data':message['data']}, room=recipient)

@socketio.on('Disconnect', namespace='/chat')
def disconnect_request():
    emit('Message',
         {'data': 'Disconnected!', 'prefix': ''})
    disconnect()


@socketio.on('connect', namespace='/chat')
def chat_connect():
    if not session.get('logged_in'):
        emit('Message', {'prefix': '', 'data': 'Not logged in.'})
        disconnect()
        return 0
    global userlist
    session['id'] = request.sid
    if session['user']:
        userlist[session['user'].upper()] = session['id']
        join_room(request.sid)
        emit('Message', {'data': 'session created', 'prefix': ''})
    else:
        disconnect()


@socketio.on('disconnect', namespace='/chat')
def test_disconnect():
    print('Client disconnected', request.sid)
    for user, sid in userlist.items():
        if sid == request.sid:
            userlist.pop(user)
