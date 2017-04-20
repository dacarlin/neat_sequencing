drop table if exists user;
create table user (
  user_id integer primary key autoincrement,
  user_name text not null,
  email text not null,
  pw_hash text not null, 
  admin boolean
);

drop table if exists plate;
create table plate (
  plate_id integer primary key autoincrement,
  owner integer,
  foreign key (owner) references user(user_id)
);

drop table if exists sequencing;
create table sequencing (
  sequencing_id integer primary key autoincrement,
  owner integer,
  foreign key (owner) references user(user_id),
  plate_map text not null, -- pandas df
  reference_text text not null
);
