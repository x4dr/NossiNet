import os
import sys
from NossiSite import app, socketio
import random
import string

# print(os.getcwd()) this is where the database will be, allowing for multiple servers to run on different databases
try:
    port = int(sys.argv[1])
except:
    port = 5000

with open(os.path.join(os.path.expanduser('~'), 'key'), 'w') as keyfile:
    keyfile.write(''.join(random.SystemRandom().choice(string.printable) for _ in range(48)))

if __name__ == "__main__":
    socketio.run(app, "0.0.0.0", debug=(port != 80), port=port)
