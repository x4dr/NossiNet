"""Gevent-based WSGI server runner for NossiNet."""

from gevent import monkey
from gevent.pywsgi import WSGIServer

from NossiNet import app

monkey.patch_all()
WSGIServer(("127.0.0.1", 5000), app).serve_forever()
