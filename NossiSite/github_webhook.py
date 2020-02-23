import sys
import time
from threading import Thread

from github_webhook import Webhook

from NossiSite import webhook


@webhook.hook()
def on_push(request):
    print("update request:")
    print(request.args)
    print(request.json)
    print("///update")

    def shutdown():
        time.sleep(2)
        sys.exit(4)

    if "check if for real":
        Thread(target=shutdown).start()
