import pytest
from pathlib import Path
from flask import render_template
from NossiSite.base import app
from gamepack.WikiPage import WikiPage
from gamepack.endworld.Mecha import Mecha
from gamepack.endworld.System import System
from gamepack.endworld.HeatSystem import HeatSystem
from gamepack.endworld.EnergySystem import EnergySystem
from gamepack.endworld.MovementSystem import MovementSystem


@pytest.fixture
def mecha_instance():
    m = Mecha()
    m.Offensive["Gun"] = System(
        "Gun", {"energy": 10, "heat": 5, "enabled": "[x]", "amount": 1}
    )
    m.Heat["Sink"] = HeatSystem(
        "Sink", {"capacity": 100, "flux": 10, "enabled": "[x]", "amount": 1}
    )
    m.Energy["Reactor"] = EnergySystem(
        "Reactor", {"energy": 100, "mass": 10, "amount": 1}
    )
    m.Movement["Wheels"] = MovementSystem(
        "Wheels",
        {
            "thrust": 400,
            "anchor": 0.5,
            "dynamics": 5,
            "mass": 2,
            "amount": 10,
            "enabled": "[x]",
        },
    )
    return m


@pytest.fixture
def test_app():
    # Mock set_wikipath to prevent errors during import
    WikiPage.set_wikipath = lambda path: None

    from NossiSite import sheets, views, wiki

    if "sheets" not in app.blueprints:
        app.register_blueprint(sheets.views)
    if "views" not in app.blueprints:
        app.register_blueprint(views.views)
    if "wiki" not in app.blueprints:
        app.register_blueprint(wiki.views)
    from NossiSite.helpers import register as register_helpers

    register_helpers(app)

    # Ensure wikipath is set for tests
    try:
        WikiPage.set_wikipath(Path("wiki"))
    except Exception:
        pass

    return app


def test_render_htmx_fragments(test_app, mecha_instance):
    with test_app.test_request_context():
        # Test generic system
        rendered = render_template(
            "sheets/mechasheet_htmx/generic.html",
            system=mecha_instance.Offensive["Gun"],
            identifier="test",
            sys_category="offensive",
        )
        assert "Gun" in rendered

        # Test heat system
        rendered = render_template(
            "sheets/mechasheet_htmx/heat.html",
            system=mecha_instance.Heat["Sink"],
            identifier="test",
            sys_category="heat",
        )
        assert "Sink" in rendered
        assert "Storage" in rendered

        # Test energy system
        rendered = render_template(
            "sheets/mechasheet_htmx/energy.html",
            system=mecha_instance.Energy["Reactor"],
            identifier="test",
            sys_category="energy",
        )
        assert "Reactor" in rendered

        # Test movement system
        rendered = render_template(
            "sheets/mechasheet_htmx/movement.html",
            system=mecha_instance.Movement["Wheels"],
            identifier="test",
            sys_category="movement",
        )
        assert "Wheels" in rendered

        # Test heat UI
        rendered = render_template(
            "sheets/mechasheet_htmx/heat_ui.html",
            systems=list(mecha_instance.Heat.values()),
            max_flux=10,
            current_flux=5,
            projected_flux=7,
            identifier="test",
        )
        assert "FLUX POOL" in rendered

        # Test movement graph
        speeds = mecha_instance.speeds()
        rendered = render_template(
            "sheets/mechasheet_htmx/movement_graph.html",
            speeds=speeds,
            max_time=10,
            max_speed=100,
            identifier="test",
        )
        assert "speed-graph" in rendered
