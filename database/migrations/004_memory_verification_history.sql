-- You Can't Trade trading memory verification history.
-- Preserves deterministic recheck results without overwriting prior verification history.

pragma foreign_keys = on;

create table if not exists memory_verifications (
    id text primary key not null,
    finding_id text not null references memory_findings(id) on delete cascade,
    verified_at text not null,
    status text not null,
    sample_size integer not null,
    evidence_strength text not null,
    supporting_trade_count integer not null default 0,
    supporting_trade_ids_json text not null default '[]',
    contract_version integer not null default 1,
    created_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    check (status in (
        'OBSERVED',
        'ACTIVE',
        'CHALLENGED',
        'RETIRED'
    )),
    check (evidence_strength in (
        'INSUFFICIENT',
        'LIMITED',
        'MODERATE',
        'STRONG'
    )),
    check (sample_size >= 0),
    check (supporting_trade_count >= 0)
);

create index if not exists memory_verifications_finding_idx
    on memory_verifications(finding_id, verified_at desc);

create index if not exists memory_verifications_status_idx
    on memory_verifications(status);

create index if not exists memory_verifications_verified_idx
    on memory_verifications(verified_at desc);
