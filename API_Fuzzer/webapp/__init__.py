from flask import Flask

from flask_socketio import SocketIO
from .main.routes import main

from config import Config


socketio = SocketIO(async_mode="eventlet", logger=True, engineio_logger=True)

fuzzer_conf = Config()
session = None


def start_app():
    app = Flask(__name__, template_folder="templates")

    # Socket IO config
    socketio.init_app(app=app)
    # Importing the routes AFTER initializing Socketio
    from .main import socket_routes

    app.register_blueprint(main)

    return app
