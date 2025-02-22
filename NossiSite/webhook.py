import hmac
import logging
import os
import threading

from flask import jsonify, request

from NossiSite.base import app as defaultapp, csrf

logger = logging.getLogger(__name__)


def register(app=None):
    if app is None:
        app = defaultapp

    def verify_signature():
        header_signature = request.headers.get("X-Hub-Signature-256")

        if not header_signature:
            return False

        sha_name, signature = header_signature.split("=")
        if sha_name != "sha256":
            return False

        local_signature = hmac.new(
            app.config["SECRET_KEY"].encode(),
            msg=request.get_data(),
            digestmod="sha256",
        )
        return hmac.compare_digest(local_signature.hexdigest(), signature)

    @app.route("/postreceive", methods=["POST"])
    @csrf.exempt
    def on_push():
        if not verify_signature():
            return jsonify({"message": "Invalid signature"}), 400
        req = request.json
        repo = req["repository"]["name"]
        if repo in ["NossiNet", "Okysa", "Gamepack"]:
            response = jsonify({"message": "Update received, restarting..."})
            threading.Timer(1, os._exit, [1]).start()  # shut down to be restarted
            return response
        else:
            logger.error(f"got unexpected request from: {req['repository']['name']}")
