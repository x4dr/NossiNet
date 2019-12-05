from NossiPack import WoDData, WoDParser, Userlist, VampireCharacter
from NossiPack.Chatrooms import Chatroom
import time
import json

from NossiSite import app, socketio

from flask import render_template, session, request, flash, url_for, redirect
from flask_socketio import emit, join_room, leave_room, disconnect


def q_echo(n, printline=True):
    session['message to send'] = session.get('message to send', "") + n + ("\n" if printline else "")


def q_send(message, prepend=True):
    tosend = session.pop('message to send', "")
    if tosend:
        if prepend:
            tosend = "==> " + message + "\n" + tosend
        emit("Message", {'data': tosend})
    # else:
    #   emit("Message", {'data': "no reply for '" + message + "'"})


def cards_help():
    q_echo("It appears that I have not made any help available yet. Tell me about this.")


def backlog(user=None, message=None):
    with open("backlog.crd", 'r+') as f:
        messages = [x.split(": ", 1) for x in f.readlines() if len(x.split(": ", 1)) > 1]
        new = []
        for recipient, msg in messages:
            if recipient == session['user']:
                q_echo(msg)
            else:
                new.append(recipient + ": " + msg + "\n")
        if user and message:
            new.append(user + ": " + message + "\n")
            emit("Update", room=user)
        f.seek(0)
        f.writelines(new)
        f.truncate()


def duelstate(state=None, opponent=None):
    with open("duels.crd", 'r+') as f:
        duels = [x.split(": ", 1) for x in f.readlines() if len(x.split(": ", 1)) > 1]
        pick = [x for x in duels if session['user'] in x[0].split("-", 1)]
        if not pick:
            if state is not None and opponent:
                duels.append([session['user']+"-"+opponent,state])
                f.seek(0)
                f.writelines([x[0]+": "+x[1]+"\n" for x in duels])
                f.truncate()
                return state, opponent
            else:
                return None, None
        elif len(pick) > 1:
            raise Exception("what the fuck two duels? i fucked that check up somewhere")
        else:
            pick = pick[0]
            fighters = pick[0].split("-", 1)
            return pick[1], fighters[0] if fighters[1] == session['user'] else fighters[1]


def cards(message: str):
    backlog()
    state, opponent = duelstate()
    if state:
        session['cards_mode'] = "duel"
        emit("Status", {"status": "duelling " + opponent})

    if message == "///silent":
        return q_send("", False)
    elif session.get('cards_mode', None) is None:
        lobby(message)
    elif session.get('cards_mode', None) == "duel":
        duel(message,)
    q_send(message)

def duel(message:str):
    state, opponent = duelstate()
    owndeck = extract_owndeck(state)
    if message == "draw":
        message = "hand"
        hand = draw(owndeck, 5)
        state= update_ownhand(state, hand)
    if message == "hand":
        hand = extract_ownhand(state)
        q_echo(hand);



def lobby(message: str):
    if message == "help":
        cards_help()
    else:
        if message == "list":
            q_echo("nope")
        elif message.startswith("challenge "):
            opponent = message[10:109].upper()
            with open("challenges.crd", 'r+') as f:
                challenges = [x.split(" -> ") for x in f.readlines()]
                outgoing = [x for x in challenges if x[0] == session['user']]
                if outgoing:
                    q_echo("You are already challenging " + outgoing[0][1])
                else:
                    match = [x for x in challenges if x[1] == session['user'] and x[0] == opponent]
                    if match:
                        duelstate("",opponent)
                        q_echo("CHALLENGE ACCEPTED")
                        backlog(opponent, session['user'] + " ACCEPTED YOUR CHALLENGE")
                    else:
                        challenges.append([session['user'], opponent])
                        q_echo("CHALLENGED " + opponent)
                        backlog(opponent, session['user'] + " CHALLENGED YOU")

                f.seek(0)
                f.writelines([x[0] + " -> " + x[1] for x in challenges])
                f.truncate()
        elif message.startswith("retract challenge "):
            opponent = message[18:117].upper()
            with open("challenges.crd", 'r+') as f:
                challenges = [x.split(" -> ") for x in f.readlines()]
                match = [x for x in challenges if x[0] == session['user'] and x[1] == opponent]
                if match:
                    q_echo("CHALLENGE RETRACTED")
                    challenges.remove(match[0])
                    backlog(opponent, session['user'] + " RETRACTED THEIR CHALLENGE")
                else:
                    q_echo(opponent + " was not challenged.")

                f.seek(0)
                f.writelines([x[0] + " -> " + x[1] for x in challenges])
                f.truncate()
        else:
            emit("Message", {'data': "[" + time.strftime("%H:%M") + "] " + session['user'] + ": " + message},
                 room="lobby")