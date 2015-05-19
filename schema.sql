CREATE TABLE IF NOT EXISTS entries (
  id     INTEGER PRIMARY KEY AUTOINCREMENT,
  author TEXT NOT NULL,
  title  TEXT NOT NULL,
  text   TEXT NOT NULL
);
--DROP TABLE messages;
CREATE TABLE IF NOT EXISTS messages (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  author  TEXT NOT NULL,
  recipient TEXT NOT NULL,
  title     TEXT NOT NULL,
  text    TEXT NOT NULL,
  value   INTEGER,
  lock    BOOLEAN,
  honored BOOLEAN
);

CREATE TABLE IF NOT EXISTS users (
  username     TEXT PRIMARY KEY NOT NULL,
  passwordhash TEXT             NOT NULL,
  kudos        INTEGER          NOT NULL
)