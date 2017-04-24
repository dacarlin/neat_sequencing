drop table if exists user;
create table user (
  user_id integer primary key autoincrement,
  user_name text not null,
  email text not null,
  pw_hash text not null,
  date_joined integer
);

drop table if exists plate;
create table plate (
  plate_id integer primary key autoincrement,
  owner integer,
  status integer,
  issue integer,
  date_ordered integer,
  foreign key (owner) references user(user_id)
);

drop table if exists sequencing;
create table sequencing (
  sequencing_id integer primary key autoincrement,
  plate_map text not null,
  reference_text text,
  date_ordered integer, 
  status integer, -- will eventually be a code, 0, 1, 2, 3 or something
  issue integer, -- has customer flagged an issue?
  owner integer,
  foreign key (owner) references user(user_id)
);
