
create table if not exists  actors
(
	name TEXT not null
		constraint unq
			unique,
	faction TEXT,
	allegiance TEXT,
	clan TEXT,
	tags TEXT
);

create table if not exists chatlogs
(
	linenr INTEGER PRIMARY KEY not null,
	line TEXT not null,
	time INTEGER not null,
	room TEXT not null,
	constraint unq
		unique (linenr, room)
);

create table if not exists dice
(
	amount INTEGER not null,
	difficulty INTEGER not null,
	data TEXT not null,
	constraint unq
		unique (amount, difficulty)
);

create table if not exists entries
(
	id INTEGER
		primary key autoincrement,
	author TEXT not null,
	title TEXT not null,
	text TEXT not null,
	tags TEXT,
	plusoned TEXT
);

create table if not exists messages
(
	id INTEGER
		primary key autoincrement,
	author TEXT not null,
	recipient TEXT not null,
	title TEXT not null,
	text TEXT not null,
	value INTEGER,
	lock BOOLEAN
);

create table if not exists property
(
	name TEXT not null
		constraint unq
			unique,
	owner TEXT not null,
	tags TEXT,
	data TEXT
);

create table if not exists users
(
	username TEXT not null
		primary key,
	passwordhash TEXT not null,
	funds INTEGER not null,
	sheet TEXT not null,
	oldsheets TEXT,
	ip TEXT,
	admin INTEGER
);

create table if not exists configs
(
	user TEXT not null
		references users
			on update cascade on delete cascade,
	option TEXT not null,
	value TEXT not null,
	constraint configs_pk
		unique (user, option)
);

create unique index if not exists configs_user_option_uindex
	on configs (user, option);
