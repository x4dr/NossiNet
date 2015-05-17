drop table if exists entries;
create table entries (
  id integer primary key autoincrement,
  author TEXT NOT NULL,
  title text not null,
  text text not null
);