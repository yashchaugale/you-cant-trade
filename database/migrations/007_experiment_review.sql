alter table experiments add column result text not null default 'STILL_TESTING';

alter table experiments add column conclusion text not null default '';

alter table experiments add column reviewed_at text;

create index if not exists idx_experiments_reviewed_at
    on experiments(reviewed_at);

