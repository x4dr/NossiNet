"""Test data setup script for UI integration tests."""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from gamepack.WikiPage import WikiPage

from Data import connect_db
from NossiPack.User import Config, Userlist


def setup() -> None:
    """Create a test character sheet and register a test user."""
    # 1. Create a markdown file for the sheet
    WikiPage.set_wikipath(Path("./wiki_test"))
    wiki_dir = Path("./wiki_test")
    wiki_dir.mkdir(exist_ok=True)

    sheet_path = wiki_dir / "testchar.md"
    sheet_content = """---
title: Test Character
tags: [fen]
---
# Character
Name: TestBot

# Values
## Stats
Strength: 3
Athletics: 2
"""
    sheet_path.write_text(sheet_content)
    print(f"Created sheet at {sheet_path}")

    # 2. Register user
    ul = Userlist()
    username = "TESTUSER"
    password = "password123"

    # Force delete existing user if any
    with connect_db("setup") as db:
        db.execute("DELETE FROM users WHERE username = ?", (username.upper(),))
        db.execute("DELETE FROM configs WHERE user = ?", (username.upper(),))
        db.commit()

    err = ul.adduser(username, password)
    if err is None:
        print(f"Registered user {username}")
        # 3. Configure sheet
        Config.save(username, "character_sheet", "testchar")
        print(f"Configured sheet for {username}")
    else:
        print(f"Failed to register user {username}: {err}")


if __name__ == "__main__":
    setup()
