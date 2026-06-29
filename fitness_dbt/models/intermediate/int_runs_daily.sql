with stg as (
    select * from {{ ref('stg_runs') }}
)

select
    run_date,
    round(sum(distance_km), 2)                          as distance_km,
    round(sum(duration_min), 1)                         as duration_min,
    round(sum(duration_min) / sum(distance_km), 2)      as pace_min_per_km,
    count(*)                                            as sessions
from stg
group by run_date