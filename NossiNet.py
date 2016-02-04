from NossiPack.RollbackImporter import RollbackImporter

RbI = RollbackImporter()

from NossiSite import app, socketio


socketio.run(app, "0.0.0.0", debug=False, port=80)
