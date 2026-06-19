"""User account, configuration, and character sheet management."""

import pickle

from flask import flash
from frozendict import frozendict
from gamepack.Dice import DescriptiveError
from werkzeug.security import check_password_hash, generate_password_hash

from NossiPack.VampireCharacter import VampireCharacter

__author__ = "maric"

from typing import TYPE_CHECKING, Any

from Data import connect_db as condb
from NossiSite.base import log

if TYPE_CHECKING:
    import sqlite3


class User:
    """Represents a NossiNet user account with sheet and config management."""

    oldsheets: dict[int, VampireCharacter]
    db = None

    def __init__(
        self,
        username: str,
        password: str = "",
        passwordhash: str | None = None,
        funds: int = 0,
        admin: str = "",
        sheet_data: bytes | bytearray | int | str | None = None,
    ) -> None:
        """Initialize a User.

        Args:
            username: The user's name.
            password: Cleartext password (will be hashed).
            passwordhash: Pre-computed password hash (mutually exclusive
                with password).
            funds: Account funds.
            admin: Admin status string.
            sheet_data: Serialized sheet data (bytes) or sheet ID (int/str).
        """
        self.username = username.strip().upper()
        if passwordhash is not None:
            self.pw_hash = passwordhash
        elif password:
            self.pw_hash = generate_password_hash(password)
        else:
            self.pw_hash = ""

        self.funds = funds
        self.sheet = "unused"
        self._loadedsheet = None
        self.oldsheets = {}
        self.admin = admin
        self.sheetid = None

        if isinstance(sheet_data, (bytes, bytearray)) and sheet_data:
            try:
                self._loadedsheet = VampireCharacter.deserialize(bytes(sheet_data))
            except Exception:
                log.exception(f"Failed to deserialize sheet for {self.username}")
        elif isinstance(sheet_data, int) or (isinstance(sheet_data, str) and sheet_data.isdigit()):
            self.sheetid = int(sheet_data)

    @classmethod
    def connect_db(cls) -> sqlite3.Connection:
        """Connect to the user database.

        Returns:
            An sqlite3 Connection instance.
        """
        cls.db = condb("User")
        return cls.db

    def set_password(self, newpassword: str) -> bool:
        """Set a new password hash for the user.

        Args:
            newpassword: Cleartext new password.

        Returns:
            True.
        """
        self.pw_hash = generate_password_hash(newpassword)
        return True

    def loadsheet(self, num: int | None = None) -> VampireCharacter | None:
        """Load a character sheet from the database.

        Args:
            num: Optional sheet ID. Defaults to the user's active sheet.

        Returns:
            A VampireCharacter instance or None if not found.
        """
        if self._loadedsheet and num is None:
            return self._loadedsheet
        db = self.connect_db()
        res = db.execute(
            "SELECT sheet_id, sheetdata FROM sheets WHERE owner LIKE :user " "AND sheet_id = :id;",
            dict(user=self.username, id=self.sheetid if num is None else num),
        ).fetchone()
        if not res:
            return None
        return VampireCharacter.deserialize(res[1])

    def getsheet(self, num: int | None = None) -> VampireCharacter:
        """Get a character sheet, creating a new one if none exists.

        Args:
            num: Optional sheet ID.

        Returns:
            A VampireCharacter instance (loaded or blank).
        """
        sheet = self.loadsheet(num) or VampireCharacter()
        if num is None:
            self._loadedsheet = sheet
        return sheet

    def loadoldsheets(self) -> dict[int, VampireCharacter]:
        """Load all historical sheets for the user.

        Returns:
            A dict mapping sheet IDs to VampireCharacter instances.
        """
        db = self.connect_db()
        res = db.execute(
            "SELECT sheet_id, sheetdata FROM sheets WHERE owner LIKE :user;",
            dict(user=self.username),
        ).fetchall()
        self.oldsheets = {r[0]: VampireCharacter.deserialize(r[1]) for r in res} if res else {}
        return {int(r[0]): VampireCharacter.deserialize(r[1]) for r in res} if res else {}

    def savetodb(self) -> None:
        """Persist the user record to the database."""
        db = self.connect_db()
        if self._loadedsheet:
            self._loadedsheet = None  # clear to load from db next time
        d = dict(
            username=self.username,
            pwhash=self.pw_hash,
            funds=self.funds,
            sheet=0,
            admin=self.admin,
        )
        db.execute(
            "INSERT OR REPLACE INTO users "
            "(username, passwordhash, funds, sheet, admin) "
            "VALUES (:username,:pwhash, :funds, :sheet, :admin)",
            d,
        )
        db.commit()

    def configs(
        self,
    ) -> frozendict[str, str]:
        """Load all user configuration options.

        Returns:
            A frozendict of option names to values.
        """
        # central place to store default values for users
        res = {
            "discord": "not set",
            "fensheet_dots": "1",
            "fensheet_dot_max": "5",
            "character_sheet": "",
            # anything but a valid charactersheet defaults to vampire sheet
        }

        res.update(Config.loadall(self.username))

        return frozendict(res)

    def config(self, option: str, default: str | None = None) -> str | None:
        """Load a single user configuration option.

        Args:
            option: The option name.
            default: Value to return if option is not set.

        Returns:
            The option value or default.
        """
        val = Config.load(self.username, option)
        return val if val is not None else default

    @staticmethod
    def deserialize_old_sheets(inp: bytes) -> Any:
        """Deserialize a pickled list of old character sheets.

        Args:
            inp: Bytes from a pickle dump.

        Returns:
            A sorted list of Character instances.
        """
        if inp == b"":
            return []
        oldsheets = pickle.loads(inp)
        for o in oldsheets:
            o.legacy_convert()
        oldsheets.sort(key=lambda x: x.timestamp)
        return oldsheets

    def check_password(self, password: str) -> bool:
        """Verify a password against the stored hash.

        Args:
            password: Cleartext password to check.

        Returns:
            True if the password matches, False otherwise.
        """
        return check_password_hash(self.pw_hash, password)

    def update_sheet(self, form: dict[str, Any]) -> None:
        """Update the character sheet from form data.

        Args:
            form: The submitted form data dict.
        """
        if "newsheet" in form:
            self.sheetid = self.savesheet(VampireCharacter().setfromform(form))
        else:
            self.savesheet(self.getsheet().setfromform(form), self.sheetid)

    def savesheet(self, sheet: Any, num: int | None = None) -> Any:
        """Save a character sheet to the database.

        Args:
            sheet: The VampireCharacter to save.
            num: Optional existing sheet ID to update.

        Returns:
            The sheet ID of the saved record.
        """
        if not isinstance(sheet, VampireCharacter):
            flash(f"UPDATING LEGACY CHAR FROM {self.username}@{sheet.timestamp}")
            sheet = VampireCharacter.from_character(sheet)
            sheet.legacy_convert()
        db = self.connect_db()
        if num:
            dbc = db.cursor()  # need cursor to get affected rowcount
            dbc.execute(
                "UPDATE sheets SET sheetdata=(:sheetdata) " "WHERE owner=(:username) AND sheet_id=(:id);",
                {
                    "username": self.username,
                    "sheetdata": pickle.dumps(sheet),
                    "id": num,
                },
            )
            if dbc.rowcount:
                db.commit()
                return num
            raise Exception("NO UPDATE HAPPENED!", self.username, num)
        db.execute(
            "INSERT INTO sheets (owner, sheetdata) VALUES (:username,:sheetdata);",
            {"username": self.username, "sheetdata": pickle.dumps(sheet)},
        )
        res = db.execute("SELECT last_insert_rowid();").fetchone()
        return res[0]

    @property
    def sheetpublic(self) -> bool:
        """Check if the character sheet is marked as public.

        Returns:
            True if the sheet notes contain 'public'.
        """
        return "public" in self.getsheet().meta["Notes"][:22]

    @classmethod
    def load(cls, username: str) -> User | None:
        """Load a user from the database by username.

        Args:
            username: The username to look up.

        Returns:
            A User instance or None if not found.
        """
        db = cls.connect_db()
        cur = db.execute(
            "SELECT username, passwordhash, funds, " "sheet, admin FROM users WHERE username = (?)",
            [username],
        )
        row = cur.fetchone()
        if row is None:
            return None
        return User(
            username=row[0],
            passwordhash=row[1],
            funds=row[2],
            admin=row[4],
            sheet_data=row[3],
        )

    def claimsheet(self, x: str) -> None:
        """Claim an unowned sheet by ID.

        Args:
            x: The sheet ID to claim.
        """
        db = self.connect_db()
        c = db.cursor()
        res = c.execute(
            "UPDATE sheets SET owner = :user WHERE owner IS NULL AND sheet_id = :id;",
            dict(user=self.username, id=int(x)),
        )
        if res.rowcount:
            flash("success")
        else:
            flash("You cannot claim sheet " + str(x))
        db.commit()

    @classmethod
    def freesheet(cls, x: str) -> None:
        """Release a claimed sheet back to unowned.

        Args:
            x: The sheet ID to free.
        """
        x_int = int(x)
        flash(
            "If you ever want to restore this sheet, write this number down:" + str(x_int),
        )
        db = cls.connect_db()
        db.execute("UPDATE sheets SET owner=NULL WHERE sheet_id=?", [x_int])
        db.commit()


class Config:
    """Static helper for user configuration storage and retrieval."""

    @staticmethod
    def load(user: str, option: str, db: sqlite3.Connection | None = None) -> str | None:
        """Load a single config option for a user.

        Args:
            user: The username.
            option: The option name.
            db: Optional database connection (creates one if None).

        Returns:
            The option value or None.
        """
        db = db or User.connect_db()
        res = db.execute(
            "SELECT value FROM configs WHERE user LIKE :user AND option LIKE :option;",
            dict(user=user, option=option),
        ).fetchone()
        return res[0] if res else None

    @staticmethod
    def loadall(user: str, db: sqlite3.Connection | None = None) -> dict[str, str]:
        """Load all config options for a user.

        Args:
            user: The username.
            db: Optional database connection.

        Returns:
            A dict of option names to values.
        """
        db = db or User.connect_db()
        res = db.execute(
            "SELECT option, value FROM configs WHERE user LIKE :user;",
            dict(user=user),
        ).fetchall()
        return {r[0]: r[1] for r in res} if res else {}

    @staticmethod
    def check(db: sqlite3.Connection) -> None:
        """Verify that no character sheet is claimed by multiple users.

        Args:
            db: Database connection.
        """
        res = db.execute(
            "SELECT value FROM configs WHERE option LIKE 'character_sheet';",
        ).fetchall()
        res = [x[0] for x in res if x[0].strip()]
        if len(res) != len(set(res)):
            db.rollback()
            raise DescriptiveError("every charactersheet can only be chosen once!")

    @staticmethod
    def save(user: str, option: str, value: str, db: sqlite3.Connection | None = None) -> None:
        """Save a config option for a user.

        Args:
            user: The username.
            option: The option name.
            value: The value to store.
            db: Optional database connection.
        """
        db = db or User.connect_db()
        if Config.load(user, option, db) is not None:
            db.execute(
                "UPDATE configs SET value = :value " "WHERE user LIKE :user AND option LIKE :option;",
                dict(user=user, option=option, value=value),
            )
        else:
            db.execute(
                "INSERT INTO configs(user,option,value) " "VALUES (:user, :option, :value);",
                dict(user=user, option=option, value=value),
            )
        Config.check(db)
        db.commit()

    @staticmethod
    def delete(user: str, option: str, db: sqlite3.Connection | None = None) -> None:
        """Delete a config option for a user.

        Args:
            user: The username.
            option: The option name to delete.
            db: Optional database connection.
        """
        db = db or User.connect_db()
        if Config.load(user, option, db) is not None:
            db.execute(
                "DELETE FROM configs WHERE user LIKE :user AND option LIKE :option;",
                dict(user=user, option=option),
            )
        db.commit()
        # else it does not exist

    @staticmethod
    def users_with_option_value(option: str, value: str, db: sqlite3.Connection | None = None) -> list[Any]:
        """Find all users with a specific config option value.

        Args:
            option: The option name.
            value: The value to match.
            db: Optional database connection.

        Returns:
            A list of matching user rows.
        """
        db = db or User.connect_db()
        return db.execute(
            "SELECT user FROM configs WHERE option LIKE :option AND value LIKE :value;",
            dict(option=option, value=value),
        ).fetchall()


class Userlist:
    """Manages a collection of active User instances."""

    userlist: list[User]

    def __init__(self) -> None:
        """Initialize an empty Userlist."""
        self.userlist = []

    def saveuserlist(self) -> None:
        """Persist all users in the list to the database."""
        for u in self.userlist:
            u.savetodb()

    @classmethod
    def adduser(cls, user: str, password: str) -> str | None:
        """Add a user to the database.

        :param user: username
        :param password: password (cleartext, will be hashed)
        :return: None if success, str with errormessage on failure.
        """
        if cls().loaduserbyname(user) is None:
            u = User(username=user, password=password)
            u.savetodb()
            return None
        return f"Username {user} is taken!"

    def loaduserbyname(self, username: str) -> User | None:
        """Load a user by username, caching in the local list.

        Args:
            username: The username to load.

        Returns:
            A User instance or None if not found.
        """
        username = username.upper()
        t = [x for x in self.userlist if x.username.upper() == username]
        if t:
            return t[0]
        newuser: User | None = User.load(username)
        if newuser:
            self.userlist.append(newuser)
        return newuser

    def valid(self, user: str, password: str) -> bool:
        """Check if credentials are valid.

        :param user: username
        :param password: userpassword (cleartext)
        :return: True if user with these credentials exists, False otherwise.
        """
        try:
            u = self.loaduserbyname(user)
            if u is None:  # technically vulnerable to timing attacks
                return False
            return u.check_password(password)
        except Exception:
            log.exception("exception while checking user credentials for {user}")
            raise
