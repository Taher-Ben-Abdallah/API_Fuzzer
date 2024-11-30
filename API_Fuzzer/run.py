from webapp import start_app, socketio
import eventlet

app = start_app()

if __name__ == "__main__":

    # Eventlet WSGI server instead of socketio.run()
    # eventlet.wsgi.server(eventlet.listen(('0.0.0.0', 5000)), app)
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
