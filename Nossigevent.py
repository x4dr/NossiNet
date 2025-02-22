from gevent import monkey
from NossiNet import app
from gevent.pywsgi import WSGIServer

monkey.patch_all()
WSGIServer(("127.0.0.1", 5000), app).serve_forever()
