from flask_testing import TestCase

from NossiSite.base import app as nossinet


class TestViews(TestCase):
    render_templates = False

    # if the create_app is not implemented NotImplementedError will be raised
    def create_app(self):
        app = nossinet
        app.config["TESTING"] = True
        # Set to 0 to have the OS pick the port.
        app.config["LIVESERVER_PORT"] = 0
        app.config.from_mapping(SECRET_KEY="dev",)
        self.app = app
        return app

    def setUp(self) -> None:
        pass  # DB created during normal usage
