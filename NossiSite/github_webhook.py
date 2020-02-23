import sys
import time
from threading import Thread

from NossiSite.base import webhook


@webhook.hook()
def on_push(request):
    print("update request:")
    print(request["repository"])
    print("///update")

    def shutdown():
        time.sleep(2)
        sys.exit(4)

    if request["repository"]["name"] == "NossiNet":
        Thread(target=shutdown).start()
