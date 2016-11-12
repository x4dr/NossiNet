--DROP TABLE entries;
CREATE TABLE IF NOT EXISTS entries (
  id     INTEGER PRIMARY KEY AUTOINCREMENT,
  author TEXT NOT NULL,
  title  TEXT NOT NULL,
  text     TEXT NOT NULL,
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
  kudosrep  INTEGER,
  kudosaut  INTEGER,
  lock    BOOLEAN,
  honored BOOLEAN
);

--DROP TABLE users;
CREATE TABLE IF NOT EXISTS users (
  username     TEXT PRIMARY KEY NOT NULL,
  passwordhash TEXT             NOT NULL,
  kudos        INTEGER          NOT NULL,
  funds        INTEGER          NOT NULL,
  kudosdebt    TEXT             NOT NULL,
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
)