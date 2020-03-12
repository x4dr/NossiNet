import sys

from NossiSite import app, socketio, views, chat, extra, wiki, webhook, helpers

# register the endpoints
views.register(app)
chat.register(app, socketio)
wiki.register(app)
extra.register(app)
webhook.register(app)
helpers.register(app)

if __name__ == "__main__":
    print("Nosferatu net being run directly, DO NOT USE IN PRODUCTION")
    test = False

    try:
        port = int(sys.argv[1])
    except:
        port = 5000
    socketio.run(app, "0.0.0.0", debug=True, port=port)

    print("Nosferatu net closing")
