import subprocess
import sys
import time
from threading import Thread

from NossiSite.base import webhook


@webhook.hook()
def on_push(request):
    print("update request:")
    print(request["repository"])
    print("///update")
    res = subprocess.run(["nossilint", request["after"]], capture_output=True, encoding="utf-8")
    result = res.stdout
    print(result)

    def shutdown():
        time.sleep(2)
        sys.exit(4)

    if request["repository"]["name"] == "NossiNet":
        if not result.strip():
            Thread(target=shutdown).start()
        else:
            raise Exception("Didnt pass lint!")
