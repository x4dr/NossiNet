import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(scope="function")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "ignore_https_errors": True}


@pytest.fixture(scope="function", autouse=True)
def setup_mecha(page: Page):
    # Capture console logs
    page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))

    page.goto("https://localhost:5000/sheet/mechtest")
    # Clean encounter
    page.click("text=OVERVIEW")
    page.wait_for_selector('#overview-ui button:has-text("NEW")', state="visible")
    page.locator('#overview-ui button:has-text("NEW")').click()
    page.wait_for_load_state("networkidle")

    # Apply Cool loadout for a stable state
    page.locator("select[name='loadout']").select_option("Cool")
    page.wait_for_timeout(500)  # Wait for JS state to update
    page.evaluate("window.commitTurn()")
    page.wait_for_url("**/sheet/mechtest")
    page.wait_for_load_state("networkidle")


def dismiss_overheat_modal(page: Page):
    try:
        # Wait a bit for HTMX to potentially load the modal
        page.wait_for_selector("#overheat-modal", state="visible", timeout=3000)
        page.locator("#overheat-modal button:has-text('DISMISS')").click()
        page.wait_for_selector("#overheat-modal", state="hidden")
    except Exception:
        pass


def test_speed_target_pending(page: Page):
    # Switch to Movement tab
    page.click("text=MOVEMENT")

    # Set target speed
    slider = page.locator("input[name='speed']")
    slider.fill("50")
    slider.dispatch_event("input")

    # Verify in Next Turn tab
    page.click("text=NEXT TURN")
    expect(page.locator("#pending-changes-list")).to_contain_text(
        "Set Target Speed to 50.0 km/h"
    )


def test_undo_redo_playback(page: Page):
    # 1. Apply Cool loadout
    page.click("text=OVERVIEW")
    page.locator("select[name='loadout']").select_option("Cool")

    # 2. Advance to Turn 2 (we are at 1)
    page.click("text=NEXT TURN")
    page.evaluate("window.commitTurn()")
    page.wait_for_url("**/sheet/mechtest")
    page.wait_for_load_state("networkidle")
    dismiss_overheat_modal(page)

    # 3. Advance to Turn 3
    page.click("text=MOVEMENT")
    page.locator("input[name='speed']").fill("20")
    page.locator("input[name='speed']").dispatch_event("input")
    page.click("text=NEXT TURN")
    page.evaluate("window.commitTurn()")
    page.wait_for_url("**/sheet/mechtest")
    page.wait_for_load_state("networkidle")

    # Verify turn is 3
    expect(page.locator(".nav-item:has-text('NEXT TURN')")).to_contain_text(
        "Turn: 3", use_inner_text=True
    )

    # 4. Undo Turn 3
    page.click("text=TIMELINE")
    page.click("button:has-text('UNDO')")
    page.wait_for_url("**/sheet/mechtest")

    # Verify turn is back to 2
    expect(page.locator(".nav-item:has-text('NEXT TURN')")).to_contain_text(
        "Turn: 2", use_inner_text=True
    )


def test_restore_state(page: Page):
    # 1. Commit Turn 2
    page.click("text=NEXT TURN")
    page.evaluate("window.commitTurn()")
    page.wait_for_url("**/sheet/mechtest")
    page.wait_for_load_state("networkidle")

    # 2. Commit Turn 3
    page.click("text=NEXT TURN")
    page.evaluate("window.commitTurn()")
    page.wait_for_url("**/sheet/mechtest")
    page.wait_for_load_state("networkidle")

    # 3. Jump to Turn 2
    page.click("text=TIMELINE")
    # Wait for the view to become active
    page.wait_for_selector("#view-timeline.active", state="visible")
    # Wait for timeline content to load
    page.wait_for_selector(".timeline-turn", state="visible")

    # Click JUMP TO HERE for Turn 2
    page.locator(
        ".timeline-turn:has-text('TURN 2') button:has-text('JUMP TO HERE')"
    ).click()

    # Wait for the reload and turn update
    page.wait_for_url("**/sheet/mechtest")
    page.wait_for_load_state("networkidle")

    # Verify turn is back to 2
    expect(page.locator(".nav-item:has-text('NEXT TURN')")).to_contain_text(
        "Turn: 2", use_inner_text=True
    )


def test_pending_undo(page: Page):
    # 1. Advance to Turn 2 to get heat (setup already did Turn 1)
    page.click("text=NEXT TURN")
    page.evaluate("window.commitTurn()")
    page.wait_for_url("**/sheet/mechtest")
    page.wait_for_load_state("networkidle")

    # 2. Add some pending changes
    page.click("text=MOVEMENT")
    slider = page.locator("input[name='speed']")
    slider.fill("50")
    slider.dispatch_event("input")

    page.click(".nav-item:has-text('HEAT')")
    # Wait for the view-heat to be visible
    page.wait_for_selector("#view-heat.active", state="visible")

    # Wait for system cards to load (they are hx-get="load")
    page.wait_for_selector("#view-heat .system-card", state="visible", timeout=10000)

    vent_card = page.locator("#view-heat .system-card:has-text('Vent')")
    expect(vent_card).to_be_visible()

    vent_slider = vent_card.locator("input[type='range']")
    vent_slider.fill("5")
    vent_slider.dispatch_event("input")

    # Verify both in Next Turn
    page.click(".nav-item:has-text('NEXT TURN')")
    expect(page.locator("#pending-changes-list")).to_contain_text(
        "Set Target Speed to 50.0 km/h"
    )
    expect(page.locator("#pending-changes-list")).to_contain_text(
        "Assign 5.0 total heat to Vent"
    )

    # 3. Remove latest (Heat)
    page.locator("#view-nextturn button:has-text('REMOVE')").last.click()

    # Verify Speed remains, Heat gone
    expect(page.locator("#pending-changes-list")).to_contain_text(
        "Set Target Speed to 50.0 km/h"
    )
    expect(page.locator("#pending-changes-list")).not_to_contain_text(
        "Assign 5.0 total heat to Vent"
    )


def test_loadout_application(page: Page):
    # 1. Switch to FuelConserving loadout
    page.click("text=OVERVIEW")
    page.locator("select[name='loadout']").select_option("FuelConserving")

    # 2. Check Next Turn tab
    page.click("text=NEXT TURN")
    expect(page.locator("#pending-changes-list")).to_contain_text(
        "Apply Loadout: FuelConserving"
    )


def test_new_encounter_naming(page: Page):
    # 1. Apply loadout to change name
    page.click("text=OVERVIEW")
    page.locator("select[name='loadout']").select_option("FuelConserving")
    page.click("text=NEXT TURN")
    page.evaluate("window.commitTurn()")
    page.wait_for_url("**/sheet/mechtest")
    page.wait_for_load_state("networkidle")
    dismiss_overheat_modal(page)

    # 2. Verify name in selector
    page.wait_for_timeout(2000)
    selected = page.locator("select[name='encounter_id']").evaluate(
        "el => el.options[el.selectedIndex].text"
    )
    assert "FuelConserving" in selected
