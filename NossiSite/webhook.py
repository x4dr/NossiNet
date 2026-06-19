"""GitHub webhook handler for automatic deployment of NossiNet repositories."""

import hmac
import logging
import subprocess

from flask import Flask, Response, jsonify, request

from NossiSite.base import csrf

logger = logging.getLogger(__name__)


def register(app: Flask) -> None:
    """Register the GitHub webhook endpoint with the given Flask app.

    Args:
        app: The Flask application to register the endpoint with.

    """

    def verify_signature() -> bool:
        """Verify the X-Hub-Signature-256 header against the webhook secret.

        Returns:
            True if the signature is valid, False otherwise.

        """
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
    @csrf.exempt  # type: ignore[untyped-decorator]
    def on_push() -> tuple[Response, int]:
        """Handle a push event webhook from GitHub.

        If the pushed repository matches a known service repository, triggers a restart.

        Returns:
            A JSON response with a message and HTTP status code.

        """
        if not verify_signature():
            return jsonify({"message": "Invalid signature"}), 400
        repo = request.json.get("repository", {}).get("name", "")
        if repo in ["NossiNet", "Okysa", "Gamepack"]:
            subprocess.Popen(["systemctl", "restart", "nossinet.service"])
            return jsonify({"message": "Update received, restarting..."}), 200
        return jsonify({"message": "Unexpected repo"}), 400
