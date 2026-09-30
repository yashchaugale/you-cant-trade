create table if not exists experiment_observations (
    id text primary key not null,
    experiment_id text not null,
    trade_id text not null,
    behavior_followed text not null,
    observation_notes text not null default '',
    created_at text not null,
    foreign key (experiment_id) references experiments(id) on delete cascade,
    foreign key (trade_id) references trades(id) on delete cascade,
    unique (experiment_id, trade_id),
    check (behavior_followed in ('YES', 'NO', 'NOT_SURE'))
);

create index if not exists idx_experiment_observations_experiment
    on experiment_observations(experiment_id);

create index if not exists idx_experiment_observations_trade
    on experiment_observations(trade_id);
