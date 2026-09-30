create table if not exists experiments_v2 (
    id text primary key not null,
    title text not null,
    behavior text not null,
    hypothesis text not null default '',
    baseline_metric text not null default '',
    target_metric text not null default '',
    sample_target integer not null default 10,
    start_date text not null,
    end_date text,
    status text not null default 'ACTIVE',
    related_pattern_id text,
    notes text not null default '',
    created_at text not null,
    completed_at text,
    check (status in ('DRAFT', 'ACTIVE', 'COMPLETED', 'ABANDONED'))
);

insert or ignore into experiments_v2 (
    id,
    title,
    behavior,
    hypothesis,
    baseline_metric,
    target_metric,
    sample_target,
    start_date,
    end_date,
    status,
    related_pattern_id,
    notes,
    created_at,
    completed_at
)
select
    id,
    title,
    behavior,
    hypothesis,
    baseline_metric,
    target_metric,
    sample_target,
    start_date,
    end_date,
    case
        when status = 'ARCHIVED' then 'ABANDONED'
        when status = 'PAUSED' then 'ACTIVE'
        else status
    end,
    related_pattern_id,
    notes,
    created_at,
    completed_at
from experiments
where exists (
    select 1
    from sqlite_master
    where type = 'table' and name = 'experiments'
);

drop table if exists experiments;

alter table experiments_v2 rename to experiments;
