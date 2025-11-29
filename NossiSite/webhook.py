import hmac
import logging
import subprocess

from flask import request, jsonify

from NossiSite.base import csrf

logger = logging.getLogger(__name__)


def register(app):
    def verify_signature():
        header_signature = request.headers.get("X-Hub-Signature-256")
        if not header_signature:
            return False
        sha_name, signature = header_signature.split("=")
        if sha_name != "sha256":
            return False
        local_sig = hmac.new(
            app.config["GITHUB_WEBHOOK_SECRET"].encode(),
            msg=request.get_data(),
            digestmod="sha256",
        )
        return hmac.compare_digest(local_sig.hexdigest(), signature)

    @app.route("/postreceive", methods=["POST"])
    @csrf.exempt
    def on_push():
        if not verify_signature():
            return jsonify({"message": "Invalid signature"}), 400
        repo = request.json.get("repository", {}).get("name", "")
        if repo in ["NossiNet", "Okysa", "Gamepack"]:
            subprocess.Popen(["systemctl", "restart", "nossinet.service"])
            return jsonify({"message": "Update received, restarting..."}), 200
        return jsonify({"message": "Unexpected repo"}), 400
