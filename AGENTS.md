# AGENTS.md

## Current Project Definition

This project is a cost-aware longitudinal flight-market data pipeline.

For Phase 1, it should systematically sample twelve directional routes between Seoul, London, Kuala Lumpur, and Tokyo using fixed travel cohorts and predefined booking lead-time checkpoints. The goal is to preserve historical fare observations so route seasonality, booking-window behavior, directionality, and cabin-class differences can be analyzed over time.

This is not a flight-booking app, dashboard-first project, or broad destination-discovery tool.

Single current implementation focus:

```text
Make one baseline TripCohort lifecycle concrete:
Route -> TripCohort -> scheduled checkpoint -> search run -> raw response -> normalized offers -> historical observations -> quota count
```

Do not jump ahead.

Detailed rationale lives in:

- `docs/PROJECT_DESIGN.md`
- `docs/DATA_COLLECTION_STRATEGY.md`
- `docs/ANALYTICS_ENGINEERING_PLAN.md`
- `progress_check/CURRENT_STATE.md`

If `AGENTS.md` and a detailed document conflict, `AGENTS.md` is the active direction.

## Working Style

Do not build the whole system at once.

Before implementing a new phase, explain:

```text
1. what is being added
2. why it exists
3. what data it creates
4. how it helps answer the project questions
5. then implement it
```

For major design decisions, stop before implementation and explain options, recommendation, and impact. Major decisions include:

- baseline monthly departure-date rule
- whether London includes STN/LTN
- raw JSON storage strategy
- database schema changes
- scheduler implementation
- SerpAPI quota behavior for economy + business class
- dbt introduction
- date-exploration expansion

Minor implementation details do not need approval.

At the end of meaningful development sessions, update `progress_check/CURRENT_STATE.md`.

## Phase 1 Scope

Use only:

```text
SerpAPI engine = google_flights
```

Do not implement yet:

- Google Travel Explore
- Google Flights Deals
- random destination exploration
- where-should-I-go recommendations
- machine-learning fare prediction
- dynamic airfare alerts
- Airflow, Kafka, Spark, Hadoop, AWS Glue
- complex frontend or mobile app
- dbt before ingestion is stable

First build a trustworthy, automated longitudinal dataset.

## Fixed City Groups

Initial city-airport groups:

```text
Seoul: ICN, GMP
London: LHR, LGW
Tokyo: HND, NRT
Kuala Lumpur: KUL
```

London may later expand to STN/LTN, but do not change the initial scope without discussion.

API queries may use multiple airports for a city. Stored itinerary records must preserve actual returned departure and arrival airports.

## Fixed Directional Routes

Treat the four cities as twelve directional routes:

```text
Seoul -> London
London -> Seoul
Seoul -> Kuala Lumpur
Kuala Lumpur -> Seoul
Seoul -> Tokyo
Tokyo -> Seoul
London -> Kuala Lumpur
Kuala Lumpur -> London
London -> Tokyo
Tokyo -> London
Kuala Lumpur -> Tokyo
Tokyo -> Kuala Lumpur
```

These routes are the Phase 1 analytical backbone.

## Core Domain Concepts

### Route

One directional city market.

Conceptual fields:

```text
route_id
origin_city
destination_city
origin_airports
destination_airports
active
```

Keep city-level and airport-level information separate.

### TripCohort

One fixed round-trip travel period monitored repeatedly over time.

Conceptual fields:

```text
cohort_id
route_id
cohort_type
departure_date
return_date
trip_duration_days
label / event_name if relevant
active
created_at
```

Supported cohort types:

```text
baseline
event
personal
```

For baseline cohorts, Phase 1 uses a controlled 7-day trip duration.

A `TripCohort` represents route and travel dates. It does not represent cabin class by itself.

### SearchRun

One provider API request executed at one point in time.

It should eventually record:

```text
search_run_id
cohort_id
scheduled_lead_time_days
travel_class
observed_at
provider
request_parameters
status
quota_cost
raw_response_reference
```

### FlightOffer / PriceObservation

A returned itinerary and its observed price.

Stored observations must preserve:

```text
actual origin airport
actual destination airport
departure timestamp
arrival timestamp
airline
flight number if available
number of stops
duration
price
currency
travel_class
search_run_id
```

Append-only rule:

```text
Every collection creates new historical observations.
Old observations are never overwritten.
```

## Economy And Business Class

The project must support both:

```text
economy
business
```

This is a Phase 1 requirement, not a future afterthought.

`travel_class` must be explicit on searches and observations so economy and business prices are never aggregated together accidentally.

Before changing quota assumptions or schedules, explain actual SerpAPI behavior and quota implications. If economy and business require separate API calls, the previous baseline usage estimate may change substantially. Do not silently double planned API usage.

See `docs/DATA_COLLECTION_STRATEGY.md` for the collection-design rationale.

## Controlled Baseline Rules

Phase 1 baseline:

```text
trip duration = 7 days
1 baseline cohort per route per calendar month
```

The monthly baseline departure-date selection rule is unresolved. A possible rule is:

```text
second Tuesday of every month -> return exactly seven days later
```

Do not lock this into code until weekday bias has been discussed and approved.

## Booking Lead-Time Checkpoints

Each baseline cohort should be observed at:

```text
180, 120, 90, 60, 28, 21, 14, 7 days before departure
```

Each scheduled observation should be identifiable by:

```text
cohort_id + scheduled_lead_time_days + travel_class
```

This prevents accidental duplicate execution of the same checkpoint/class.

For every actual observation, derive:

```text
actual_days_before_departure = departure_date - observed_at
```

## Scheduler Direction

The scheduler can run daily without searching daily.

Daily execution should ask:

```text
Which cohort checkpoints are due today, for which travel classes?
```

If nothing is due, perform 0 API searches.

Persist executed checkpoints so reruns do not duplicate observations unless explicitly intended.

## API Quota Constraint

Assume:

```text
250 successful searches per month
```

Persist enough information to calculate:

```text
searches used this month
searches remaining
searches by route
searches by cohort type
searches by lead-time checkpoint
searches by travel_class
```

The application must refuse to exceed the configured hard limit.

The previous rough estimate for economy-only baseline sampling was:

```text
12 routes * 8 observations per cohort lifecycle ~= 96 searches/month average
```

This estimate must be recalculated before supporting both economy and business if they require separate SerpAPI requests.

Do not intentionally spend all 250 searches from the beginning.

## Raw Responses And Fixtures

Every successful live provider response must be recoverable.

Raw response storage must exist before live data collection.

Use fixture-first SerpAPI development:

```text
1. obtain representative real response fixture
2. save fixture under tests/fixtures/
3. build parser against fixture
4. write parser tests
5. normalize into project records
6. only then call live API
```

Do not fabricate provider JSON fields.

Discuss raw storage strategy before implementation: SQLite text/JSON vs local JSON files referenced by search runs.

## Immediate Implementation Order

1. Inspect existing code and tests.
   - `models.py`
   - `database.py`
   - `collector.py`
   - `mock_provider.py`
   - `analysis.py`
   - `cli.py`
   - `tests/`

2. Before changing code, summarize:

```text
what can stay
what must change
what should be added
```

3. Implement fixed `Route` configuration with validation and tests.

4. Implement `TripCohort` with validation and tests.

5. Discuss and approve the baseline monthly date rule.

6. Implement checkpoint scheduling for:

```text
180, 120, 90, 60, 28, 21, 14, 7
```

7. Persist routes and cohorts in SQLite.

8. Extend `SearchRun` to connect to cohort, scheduled checkpoint, actual observation time, travel class, quota cost, and status.

9. Implement raw response storage.

10. Add a real saved Google Flights fixture.

11. Implement Google Flights parser.

12. Add live SerpAPI client only after parser tests work.

13. Execute one controlled live search.

14. Implement local daily due-check runner.

15. Automate only after the local runner is reliable.

## First Real Milestone

One cohort successfully moves through the system:

```text
Route: Seoul -> London
Cohort: Feb 2027 baseline
Checkpoint: 120 days
Travel class: economy or business
-> scheduler recognizes it is due
-> SerpAPI Google Flights request
-> raw JSON stored
-> search run stored
-> offers normalized
-> historical observations stored
-> quota count updated
```

Do not prioritize dashboard work before this exists.

## Commands And Testing

Use Python 3.12+ and `uv`.

Preferred commands:

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
uv run python -m flight_tracker.cli
```

Add or update tests for meaningful behavior changes.

Never require real credentials for the core test suite.

Do not claim checks passed unless they were actually run.

## Secrets And Data

Never commit:

- API keys
- `.env` files
- large raw datasets
- generated database files
- personal data
- cache directories

Use `.env.example` for required environment variable names only.

Small representative fixtures are allowed when useful and safe.
