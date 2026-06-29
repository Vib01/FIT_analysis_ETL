with source as (
    select * from raw_runs
),

cleaned as (
    select
        cast(date as date)      as run_date,
        distance_km,
        duration_min,
        pace_min_per_km,
        source_file
    from source
    where
        distance_km >= 0.5
        and duration_min between 1 and 300
        and pace_min_per_km between 2.5 and 20.0
)

select * from cleaned