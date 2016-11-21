import sys
from NossiSite import app, socketio


# print(os.getcwd()) this is where the database will be, allowing for multiple servers to run on different databases
try:
    port = int(sys.argv[1])
except:
    port = 5000

if __name__ == "__main__":
    socketio.run(app, "0.0.0.0", debug=(port != 80), port=port)
