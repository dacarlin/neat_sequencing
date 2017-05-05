drop table if exists user;
create table user (
  id integer primary key autoincrement,
  email text not null,
  pw_hash text not null,
  date_joined date
);

drop table if exists plate;
create table plate (
  id integer primary key autoincrement,
  physical integer,
  owner integer,
  status integer,
  issue integer,
  date_ordered date
);

-- plate states
-- 0. ordered via web
-- 1. we have shipped to customer
-- 2. customer has used the plate in a sequencing order
-- 3. we have received the plate

drop table if exists sequencing;
create table sequencing (
  id integer primary key autoincrement,
  physical integer,
  owner integer,
  map text not null,
  reference_text text,
  date_ordered date,
  status integer,
  issue integer
);

-- sequencing states
-- 0. ordered via the web
-- 1. all plates involved have been received
-- 2. data are on the sequencer
-- 2. results have been uploaded and are available
