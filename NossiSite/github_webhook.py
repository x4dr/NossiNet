import sys
import time
from threading import Thread

from NossiSite import webhook


@webhook.hook()
def on_push(request):
    print("update request:")
    print(request)
    print("///update")

    def shutdown():
        time.sleep(2)
        sys.exit(4)

    if "check if for real":
        Thread(target=shutdown).start()
