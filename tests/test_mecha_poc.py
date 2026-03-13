import pytest
from unittest.mock import patch
from gamepack.WikiPage import WikiPage
from gamepack.endworld.Mecha import Mecha
from NossiSite.mecha_history import MechaEncounterManager
from NossiSite.base import app


@pytest.fixture
def temp_wiki(tmp_path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "backups").mkdir()
    return wiki


@pytest.fixture
def test_client(temp_wiki):
    from NossiSite import sheets

    if "sheets" not in app.blueprints:
        app.register_blueprint(sheets.views)
    WikiPage._wikipath = None
    with patch.object(WikiPage, "_wikipath", temp_wiki):
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["TESTING"] = True
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user"] = "TESTUSER"
                sess["logged_in"] = True
            yield client


def test_mecha_turn_property():
    m = Mecha()
    assert m.turn == 0
    m.turn = 5
    assert m.turn == 5


def test_mecha_next_turn():
    m = Mecha()
    m.turn = 1
    summary = m.next_turn()
    assert m.turn == 2
    assert summary["turn"] == 2
    assert "thermals" in summary


def test_system_booting():
    from gamepack.endworld.System import System

    m = Mecha()
    s = System("TestSys", {"boot": 2, "enabled": "[x]", "energy": 10, "amount": 1})
    m.Offensive["TestSys"] = s

    # Turn 1: Booting starts
    assert s.is_booting()
    assert not s.is_active()

    m.next_turn()  # Turn 1 -> 2
    assert s.boot_progress == 1
    assert s.is_booting()

    m.next_turn()  # Turn 2 -> 3
    assert s.boot_progress == 2
    assert not s.is_booting()
    assert s.is_active()


def test_encounter_manager(temp_wiki):
    mgr = MechaEncounterManager(temp_wiki, "test_mech")

    # Start encounter
    enc_id = mgr.start_new_encounter()
    assert enc_id is not None

    # Log event
    mgr.log_event(enc_id, {"type": "TURN_COMMIT", "turn": 1})

    # Verify
    latest_id = mgr.get_latest_encounter_id()
    assert latest_id == enc_id
    data = mgr.load_encounter(enc_id)
    assert data is not None
    assert len(data["events"]) == 2  # LOADOUT_APPLY and TURN_COMMIT
    assert data["events"][1]["turn"] == 1


def test_pending_heat():
    m = Mecha()
    m.pending_heat = 10
    m.next_turn()
    # Assuming add_heat(10) works and there's a HeatSystem
    # For now just check it resets
    assert m.pending_heat == 0


def test_projected_flux():
    from gamepack.endworld.System import System

    m = Mecha()
    s1 = System("ActiveSys", {"heat": 5, "enabled": "[x]", "amount": 1})
    s1.boot_progress = 0  # active
    s1.activation_rounds = 0
    m.Offensive["S1"] = s1

    s2 = System("BootingSys", {"heat": 10, "enabled": "[x]", "boot": 1, "amount": 1})
    s2.boot_progress = 0
    m.Offensive["S2"] = s2

    # s1 is active, s2 will be active next turn
    assert m.projected_flux() == 15


def test_heat_assignment():
    from gamepack.endworld.HeatSystem import HeatSystem

    m = Mecha()
    h = HeatSystem("Sink", {"capacity": 100, "flux": 10, "enabled": "[x]", "amount": 1})
    m.Heat["Sink"] = h

    m.fluxpool = 20
    # Assign 5 heat
    taken, _ = m.assign_heat("Sink", 5)
    assert taken == 5
    assert h.current == 5
    assert m.fluxpool == 15

    # Assign more than remaining flux (wait, flux assignment is absolute delta now in server,
    # but assign_heat helper is still relative)
    # Actually assign_heat in Mecha.py takes amount.

    # h.current is 5. h.capacity is 100. spare is 95.
    # m.fluxpool is 15.
    # assign_heat("Sink", 10) -> can_take = min(10, 15, 95) = 10.
    taken, _ = m.assign_heat("Sink", 10)
    assert taken == 10
    assert h.current == 15
    assert m.fluxpool == 5


def test_speed_transition():
    from gamepack.endworld.MovementSystem import MovementSystem

    m = Mecha()
    ms = MovementSystem(
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
    m.Movement["Wheels"] = ms

    m.current_speed = 0
    m.target_speed = 100

    m.next_turn()
    assert m.current_speed > 0
    assert m.current_speed <= 100

    # Test deceleration
    m.current_speed = 100
    m.target_speed = 0
    m.next_turn()
    assert m.current_speed < 100
    assert m.current_speed >= 0


def test_system_library_loading(temp_wiki):
    # Create a system in the library
    sys_dir = temp_wiki / "systems" / "movement"
    sys_dir.mkdir(parents=True, exist_ok=True)
    with open(sys_dir / "TestWheels.md", "w") as f:
        f.write("| | Thrust | Mass |\n|---|---|---|\n| TestWheels | 500 | 5 |")

    # Mock wikipath
    with patch.object(WikiPage, "_wikipath", temp_wiki):
        m = Mecha()
        data = m.load_system_data("TestWheels", "Movement")
        assert data["Thrust"] == "500"
        assert data["Mass"] == "5"
