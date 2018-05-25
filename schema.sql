--DROP TABLE entries;
CREATE TABLE IF NOT EXISTS entries (
  id     INTEGER PRIMARY KEY AUTOINCREMENT,
  author TEXT NOT NULL,
  title  TEXT NOT NULL,
  text   TEXT NOT NULL,
  tags   TEXT,
  plusoned TEXT
);
--DROP TABLE messages;
CREATE TABLE IF NOT EXISTS messages (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  author    TEXT NOT NULL,
  recipient TEXT NOT NULL,
  title     TEXT NOT NULL,
  text      TEXT NOT NULL,
  value   INTEGER,
  lock    BOOLEAN
);

--DROP TABLE users;
CREATE TABLE IF NOT EXISTS users (
  username     TEXT PRIMARY KEY NOT NULL,
  passwordhash TEXT             NOT NULL,
  funds        INTEGER          NOT NULL,
  sheet        TEXT             NOT NULL,
  oldsheets    TEXT,
  defines      TEXT,
  ip           TEXT,
  admin        INTEGER
);
--DROP TABLE chatlogs;
CREATE TABLE IF NOT EXISTS chatlogs (
  linenr        INTEGER             NOT NULL,
  line          TEXT                NOT NULL,
  time          INTEGER             NOT NULL,
  room          TEXT                NOT NULL,
  CONSTRAINT unq UNIQUE (linenr, room)
);
--DROP TABLE dice;
CREATE TABLE IF NOT EXISTS dice (
  amount        INTEGER             NOT NULL,
  difficulty    INTEGER             NOT NULL,
  data          TEXT                NOT NULL,
  CONSTRAINT unq UNIQUE (amount, difficulty)
);
--DROP TABLE property;
CREATE TABLE IF NOT EXISTS property (
  name          TEXT                NOT NULL,
  owner         TEXT                NOT NULL,
  tags          TEXT,
  data          TEXT,
  CONSTRAINT unq UNIQUE (name)
);
--DROP TABLE actors;
CREATE TABLE IF NOT EXISTS actors (
  name          TEXT                NOT NULL,
  faction       TEXT,
  allegiance    TEXT,
  clan          TEXT,
  tags          TEXT,
  CONSTRAINT unq UNIQUE (name)
);