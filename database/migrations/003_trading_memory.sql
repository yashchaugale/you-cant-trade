-- You Can't Trade trading memory.
-- Stores persistent evidence-linked findings separately from canonical trades.

pragma foreign_keys = on;

create table if not exists memory_findings (
    id text primary key not null,
    type text not null,
    statement text not null,
    sample_size integer not null default 0,
    evidence_strength text not null,
    first_observed text not null,
    last_verified text,
    status text not null default 'OBSERVED',
    contract_version integer not null default 1,
    created_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    check (type in (
        'EDGE',
        'LEAK',
        'SETUP',
        'CONTEXT',
        'BEHAVIOR',
        'EXECUTION',
        'EXPERIMENT_RESULT'
    )),
    check (evidence_strength in (
        'INSUFFICIENT',
        'LIMITED',
        'MODERATE',
        'STRONG'
    )),
    check (status in (
        'OBSERVED',
        'ACTIVE',
        'CHALLENGED',
        'RETIRED'
    )),
    check (sample_size >= 0)
);

create table if not exists memory_finding_trades (
    finding_id text not null references memory_findings(id) on delete cascade,
    trade_id text not null references trades(id) on delete cascade,
    primary key (finding_id, trade_id)
);

create index if not exists memory_findings_status_idx
    on memory_findings(status);

create index if not exists memory_findings_type_idx
    on memory_findings(type);

create index if not exists memory_findings_evidence_idx
    on memory_findings(evidence_strength);

create index if not exists memory_findings_verified_idx
    on memory_findings(last_verified desc);

create index if not exists memory_finding_trades_trade_idx
    on memory_finding_trades(trade_id);

create index if not exists memory_finding_trades_finding_idx
    on memory_finding_trades(finding_id);
