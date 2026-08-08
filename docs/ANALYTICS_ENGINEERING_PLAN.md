# Analytics Engineering Plan

```text
FUTURE WORK AFTER INGESTION IS STABLE
```

This document describes where the project should go after reliable ingestion, raw response storage, cohort scheduling, quota tracking, and normalized observations exist.

Do not let this document drive premature implementation.

## Analytics-Engineering Story

The project should eventually demonstrate more than:

```text
Python script -> API -> chart
```

The intended story is:

```text
SerpAPI
-> raw observations
-> clean staging models
-> reusable intermediate models
-> analytical marts
-> questions about seasonality, booking lead time, and cabin class
```

## Future dbt Direction

Do not add dbt before ingestion is stable.

Once enough raw and normalized data exists, introduce a dbt layer.

Possible structure:

```text
models/
├── staging/
│   ├── stg_search_runs.sql
│   ├── stg_flight_offers.sql
│   ├── stg_routes.sql
│   └── stg_trip_cohorts.sql
├── intermediate/
│   ├── int_flight_observations.sql
│   └── int_booking_windows.sql
└── marts/
    ├── mart_route_prices.sql
    ├── mart_booking_windows.sql
    └── mart_seasonality.sql
```

## Analytical Grain

Make row grain explicit.

```text
SearchRun:
1 row = one API request executed at one point in time

Flight Offer Observation:
1 row = one itinerary returned by one search run

TripCohort:
1 row = one fixed round-trip travel period being monitored

Future Booking Window Mart:
1 row = route * travel-period grouping * booking-window bucket
```

## Useful Derived Fields

Potential derived fields:

- actual_days_before_departure
- scheduled_lead_time_days
- booking_window_bucket
- departure_month
- departure_year
- trip_duration_days
- route_direction
- origin_city
- destination_city
- requested travel_class
- is_nonstop
- cohort_type
- is_event
- event_name
- actual origin airport
- actual destination airport

Suggested booking-window buckets:

```text
0-14 days
15-30 days
31-60 days
61-90 days
91-180 days
180+ days
```

## Future Analytical Questions

### Seasonality

- Which months are cheapest for Seoul -> London?
- How much more expensive is December than November?
- Does Tokyo -> London have strong summer seasonality?

### Booking Windows

- Is 90 days ahead generally cheaper than 28 days?
- Is 180 days too early?
- How sharply do fares rise in the final 14 days?
- What is the observed cheapest booking window by route?

Always include observation counts. Do not claim statistical certainty from tiny samples.

### Route Direction

- Does London -> Seoul behave differently from Seoul -> London?
- Which routes are most volatile?
- Which directional markets have the steepest final-month price rise?

### Cabin-Class Differences

- Do business-class fares have different booking-window behavior from economy fares?
- Are business-class fares more volatile near departure?
- Are event-period premiums different by cabin class?

Economy and business observations must stay distinguishable throughout the modeling layer.

### Nonstop Premium

- How much more expensive are nonstop itineraries than one-stop itineraries?
- Does the nonstop premium differ by route or month?

### Airport Differences

- Does LHR vs LGW materially affect returned fares?
- Does HND vs NRT differ for Tokyo routes?
- Are some airport pairs consistently cheaper within the same city-level route?

## Data Quality Ideas

Eventually test:

- `route_id` not null
- `cohort_id` unique
- `search_run_id` unique
- `price >= 0`
- `currency` not null
- `travel_class` in accepted values
- departure before return for round trips
- scheduled lead time in accepted set
- cohort type in accepted values
- baseline trip duration = 7 days
- actual days before departure >= 0
- route cities are in the configured city family
- actual returned airports are valid airport codes

Add tests as behavior becomes real.

## Portfolio / CV Framing

Eventually frame the project like:

```text
Flight Market Analytics Pipeline — Designed a quota-aware longitudinal data
pipeline collecting Google Flights pricing across 12 directional international
markets; preserved raw API snapshots and historical fare observations, then
modeled them into tested analytics datasets for route seasonality,
booking-window, and cabin-class analysis.
```

Later replace vague claims with real numbers:

```text
X search runs
Y flight offers
Z months of history
12 directional routes
2 cabin classes
250-request monthly acquisition constraint
```

## Why This Is Not Merely An API Scraper

An API scraper usually stops at:

```text
request -> JSON -> table/chart
```

This project should demonstrate:

- controlled sampling methodology
- quota-aware collection
- raw-data preservation
- append-only observations
- explicit row grain
- repeatable transformations
- testable data quality
- business-relevant analytical marts
- transparent limitations and observation counts

That is the analytics-engineering value.
