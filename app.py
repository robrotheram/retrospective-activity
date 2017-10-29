import os
from threading import Lock

import datetime

import uuid as uuid

import flask
from bson import json_util
from flask import Flask, render_template, session, request
from flask import json
from flask import make_response
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect
from flask_pymongo import PyMongo
from flask import jsonify

from bson.json_util import dumps


# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
app.config['SECRET_KEY'] = str(uuid.uuid4());
socketio = SocketIO(app, async_mode=async_mode)

app.config['MONGO_HOST'] = os.getenv('MONGO_HOST', '127.0.0.1')
app.config['MONGO_PORT'] = int(os.getenv('MONGO_PORT', 27017))
app.config['MONGO_DBNAME'] = 'retrospectives'
mongo = PyMongo(app, config_prefix='MONGO')

thread = None
thread_lock = Lock()


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socketio.sleep(10)
        count += 1
        socketio.emit('my_response',
                      {'data': 'Server generated event', 'count': count},
                      namespace='/test')


@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)

@app.route('/repo/<id>/')
def repo(id):
    data = {"room":id}
    if 'retrospective_user_id' in flask.request.cookies:
        name = request.cookies['retrospective_user_id']
        session['id'] = name
        return render_template('retro.html', data=data, async_mode=socketio.async_mode)
    else:
        id = str(uuid.uuid4())
        session['id'] = id
        response = make_response(render_template('retro.html', data=data, async_mode=socketio.async_mode))
        response.set_cookie("retrospective_user_id", id, expires=datetime.datetime.now() + datetime.timedelta(days=30))
        return response

@app.route('/repo/<id>/data')
def repo_data(id):
    result = mongo.db[id].find({})
    output = []
    for r in result:
        d = r['data']
        results = mongo.db[session['id']].find({"retrospectiveId": d['id']})
        if results.count() == 0:
            output.append({'message': d['message'], 'type': d['type'], 'id':d['id'], 'value': d['value'], 'vote_enabled': True})
        else:
            output.append({'message': d['message'], 'type': d['type'], 'id': d['id'], 'value': d['value'], 'vote_enabled': False})

    return jsonify(output)


@app.route('/messages')
def messages():
    collection = mongo.db.drone_detection
    data = {"name":"test"}
    _id = collection.insert_one(data).inserted_id
    print("ID: {}, data: {}".format(_id, data))
    return str(_id)



@socketio.on('my_event', namespace='/test')
def test_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']})


@socketio.on('my_broadcast_event', namespace='/test')
def test_broadcast_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         broadcast=True)


@socketio.on('join', namespace='/test')
def join(message):
    join_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socketio.on('leave', namespace='/test')
def leave(message):
    leave_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socketio.on('close_room', namespace='/test')
def close(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.',
                         'count': session['receive_count']},
         room=message['room'])
    close_room(message['room'])


@socketio.on('my_room_event', namespace='/test')
def send_room_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    _id = mongo.db[message['room']].insert_one(message).inserted_id
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         room=message['room'])


@socketio.on('retrospective_change', namespace='/test')
def retrospective_change_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    results = mongo.db[session['id']].find({"retrospectiveId": message['data']["id"]})
    if results.count() == 0:
        mongo.db[message['room']].update_one({'data.id': message['data']["id"]}, {"$set": {'data.value':message['data']['value']}}, upsert=False)
        mongo.db[session['id']].insert_one({"retrospectiveId": message['data']["id"]})
        emit('my_response_update',
         {'data': message['data'], 'count': session['receive_count']},
         room=message['room'])

@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()


@socketio.on('my_ping', namespace='/test')
def ping_pong():
    emit('my_pong')


@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread)
    emit('my_response', {'data': 'Connected', 'count': 0})


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)


if __name__ == '__main__':
    socketio.run(app,host='0.0.0.0', debug=True)