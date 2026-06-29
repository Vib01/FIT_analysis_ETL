with daily as (
    select * from {{ ref('int_runs_daily') }}
)

select
    run_date,
    distance_km,
    duration_min,
    pace_min_per_km,
    sessions,

    -- Pace formatted as MM:SS string for display
    lpad(cast(floor(pace_min_per_km) as varchar), 2, '0')
        || ':'
        || lpad(cast(round((pace_min_per_km % 1) * 60) as varchar), 2, '0')
        as pace_display,

    -- Era label
    case
        when year(run_date) <= 2022 then 'Early Training'
        when year(run_date) <= 2024 then 'Gap Period'
        else 'Comeback'
    end as era

from daily
where run_date is not null
order by run_date