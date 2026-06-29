with daily as (
    select * from {{ ref('int_runs_daily') }}
),

weekly as (
    select
        date_trunc('week', run_date)::date          as week_start,
        round(sum(distance_km), 2)                  as weekly_distance_km,
        round(sum(duration_min), 1)                 as weekly_duration_min,
        count(*)                                    as run_days,
        sum(sessions)                               as sessions,
        round(sum(duration_min) / sum(distance_km), 2) as avg_pace_min_per_km
    from daily
    group by date_trunc('week', run_date)
),

with_rolling as (
    select
        *,
        round(avg(weekly_distance_km) over (
            order by week_start
            rows between 3 preceding and current row
        ), 2) as rolling_4wk_avg_km
    from weekly
),

with_flags as (
    select
        *,
        round(weekly_distance_km / nullif(rolling_4wk_avg_km, 0), 2) as load_ratio,

        case
            when weekly_distance_km / nullif(rolling_4wk_avg_km, 0) > 1.5 then 'High Risk'
            when weekly_distance_km / nullif(rolling_4wk_avg_km, 0) > 1.3 then 'Caution'
            else 'Normal'
        end as load_flag,

        case
            when year(week_start) <= 2022 then 'Early Training'
            when year(week_start) <= 2024 then 'Gap Period'
            else 'Comeback'
        end as era

    from with_rolling
)

select * from with_flags
order by week_start