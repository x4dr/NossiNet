from NossiSite import app, socketio
import time
import threading
from flask import render_template, session, request
from flask_socketio import  emit, join_room, leave_room, \
    close_room, rooms, disconnect
thread = None


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while count <2:
        print ("sending status")
        time.sleep(1)
        count += 1
        socketio.emit('Update',
                      {'data': 'nm', 'count': count},
                      namespace='/update')
    global thread
    thread = None


@app.route('/chat/')
def chatsite():
    global thread
    if thread is None:
        thread = threading.Thread(target=background_thread)
        thread.daemon = True
        thread.start()
    return render_template('chat.html')


@socketio.on('ClientServerEvent', namespace='/chat')
def test_message(message):
    print("ClientServerEvent ",message)
    session['receive_count'] = session.get('receive_count', 0) + 1
    print(message['data'])
    emit('Message',
         {'data': message['data'], 'count': session['receive_count']})


@socketio.on('BroadCastEvent', namespace='/chat')
def test_broadcast_message(message):
    print("Broadcast",message)
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('Message',
         {'data': message['data'], 'count': session['receive_count']},
         broadcast=True)


@socketio.on('Join', namespace='/chat')
def join(message):
    print("Join",message)
    join_room(message['room'])
    sessin['receive_count'] = session.get('receive_count', 0) + 1
    emit('Message',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socketio.on('Leave', namespace='/chat')
def leave(message):
    print("Leave",message)
    leave_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('Message',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socketio.on('RoomEvent', namespace='/chat')
def send_room_message(message):
    print("RoomEvent",message)
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('Message',
         {'data': message['data'], 'count': session['receive_count']},
         room=message['room'])


@socketio.on('Disconnect', namespace='/chat')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('Message',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()


@socketio.on('connect', namespace='/chat')
def test_connect():
    emit('Message', {'data': 'Connected', 'count': 0})


@socketio.on('disconnect', namespace='/chat')
def test_disconnect():
    print('Client disconnected', request.sid)






