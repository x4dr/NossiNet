# from NossiPack.RollbackImporter import RollbackImporter
import sys
import os
from NossiSite import app, socketio
from flask.helpers import url_for

print(os.getcwd())
try:
    port = int(sys.argv[1])
except:
    port = 5000


socketio.run(app, "0.0.0.0", debug=False, port=port)
