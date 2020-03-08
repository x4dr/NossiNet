import sys

from NossiSite import app, socketio, views, chat, extra, wiki, webhook

# register the endpoints


views.register(app)
chat.register(app, socketio)
wiki.register(app)
extra.register(app)
webhook.register(app)

if __name__ == "__main__":
    print("Nosferatu net being run directly, DO NOT USE IN PRODUCTION")
    test = False
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test = True

    if test:
        app.config["TESTING"] = True
        with app.test_client() as client:
            res = client.get("/")
            if res.status_code != 200:
                print("Unable to successfully request home page")
                print("Quick test failed")
                sys.exit(1)
            else:
                print("Quick test successful")

    else:
        try:
            port = int(sys.argv[1])
        except:
            port = 5000
        socketio.run(app, "0.0.0.0", debug=False, port=port)

        print("Nosferatu net closing")
