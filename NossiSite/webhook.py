import base64
import json
import logging
from urllib.parse import parse_qs

from OpenSSL.crypto import Error as SignatureError
from OpenSSL.crypto import verify, load_publickey, FILETYPE_PEM, X509
from flask import request, abort
from github_webhook import Webhook

from NossiSite.base import app as defaultapp


def register(app=None):
    if app is None:
        app = defaultapp
    ghwh = Webhook(app, endpoint="/postreceive", secret=app.config["SECRET_KEY"])

    @ghwh.hook()
    def on_push(req):
        if app.config.get("TRAVIS"):
            return
        if req["repository"]["name"] == "NossiNet":
            exit(0)
        else:
            print("got request from:", req["repository"]["name"])

    @app.route("/travis", methods=["POST"])
    def travis():
        import requests

        def _get_travis_public_keys():
            """
            Returns the PEM encoded public
            key from the Travis CI /config endpoint
            """
            sig = []
            for travis_config_url in [
                "https://api.travis-ci.com/config",
                "https://api.travis-ci.org/config",
            ]:
                response = requests.get(travis_config_url, timeout=10.0)
                response.raise_for_status()
                sig.append(
                    response.json()["config"]["notifications"]["webhook"]["public_key"]
                )
            return sig

        logger = logging.getLogger(__name__)
        fh = logging.FileHandler("nossilog.log", mode="a")
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)
        logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s")
        logger.setLevel(logging.DEBUG)

        def check_authorized(sig, pkey, payload):
            """
            Convert the PEM encoded public key to a format palatable for pyOpenSSL,
            then verify the signature
            """
            pkey_public_key = load_publickey(FILETYPE_PEM, pkey)
            certificate = X509()
            certificate.set_pubkey(pkey_public_key)
            verify(certificate, sig, payload, str("sha1"))

        def _get_signature():
            """
            Extract the raw bytes of the request signature provided by travis
            """
            print("HEADERS:", request.headers)
            return base64.b64decode(request.headers["Signature"])

        signature = _get_signature()
        body = request.get_data()
        qs = parse_qs(body.decode())
        print("QS", qs)
        json_payload = qs["payload"][0]
        print("PAYLOAD:", json_payload)
        try:
            public_keys = _get_travis_public_keys()
        except requests.Timeout:
            logger.error(
                {
                    "message": "Timed out when attempting to retrieve Travis CI public key"
                }
            )
            return (
                {"status": "failed"},
                400,
                {"Content-Type": "text/json; charset=utf-8"},
            )
        except requests.RequestException as e:
            logger.error(
                {
                    "message": "Failed to retrieve Travis CI public key",
                    "error": str(e.args),
                }
            )
            return (
                {"status": "failed"},
                400,
                {"Content-Type": "text/json; charset=utf-8"},
            )
        print("PUBLIC_KEYs:", "\n".join(public_keys))
        try:
            check_authorized(signature, public_keys[0], json_payload)
        except SignatureError:
            try:
                check_authorized(signature, public_keys[0], json_payload)
            except SignatureError:
                logger.error(f"Unauthorized request by {request.headers['X-Real-Ip']}")
                return abort(400)
        json_data = json.loads(json_payload)
        logger.info(f"RECEIVED: {json_data}")
        if (
            json_data["type"] == "push"
            and json_data["state"] == "passed"
            and json_data["branch"] == "master"
        ):
            exit(0)
            print("restart triggered by travis")
        return {"status": "received"}
