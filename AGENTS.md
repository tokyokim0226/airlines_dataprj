# AGENTS.md

## Current Project Definition

This project is a cost-aware longitudinal flight-market data pipeline.

For now, it should systematically sample twelve directional routes between Seoul, London, Kuala Lumpur, and Tokyo at fixed travel cohorts and predefined booking lead times, preserving historical fare observations so seasonality, route behavior, and booking-window patterns can be analyzed over time.

The immediate objective is:

```text
build a reliable controlled dataset
```

Do not treat this as a flight-booking app, a dashboard project, or a broad destination-discovery tool.

The one question to focus on now is:

```text
How does one baseline TripCohort get created, scheduled, searched, stored, and accumulated over time?
```

Do not jump ahead.

## Working Style

Do not rush ahead and build the whole system at once.

Before implementing a new phase, explain:

```text
1. what is being added
2. why it exists
3. what data it creates
4. how it helps answer the project questions
5. then implement it
```

For major design decisions, stop before implementation and explain options, recommendation, and impact.

Major decisions include:

- baseline monthly departure-date rule
- whether London includes STN/LTN
- raw JSON storage strategy
- database schema changes
- scheduler implementation
- dbt introduction
- date-exploration expansion

Minor implementation details do not need approval.

## Project Goal

We are building a longitudinal flight-market analytics dataset.

The purpose is to collect flight prices over time in a systematic way so that, after months or years of accumulation, we can investigate questions such as:

- When is it cheapest to travel on a route?
- How far in advance is it usually cheapest to book?
- Is booking 3 months ahead better than 1 month ahead?
- Is booking 6 months ahead better or worse than 3 months ahead?
- How much do prices rise inside the final 4 / 3 / 2 / 1 weeks?
- Which months are expensive or cheap?
- Does booking behavior differ between routes?
- Does London -> Seoul behave differently from Seoul -> London?
- How much more expensive are holiday periods such as Lunar New Year or Christmas?
- If travel dates are fixed, how early should tickets ideally be bought based on our own historical data?

Google Flights tells us what is available now. This system preserves what was available at many different points in time and turns those observations into reusable historical datasets.

## Portfolio Goal

This is an analytics-engineering portfolio project.

The finished project should eventually demonstrate:

- external API ingestion
- cost-aware data collection
- append-only historical data
- raw-data preservation
- data modeling
- clear analytical grain
- SQL transformations
- dbt, after ingestion is stable
- staging / intermediate / mart layers
- tests and data quality
- documentation
- automated collection
- CI
- analytical outputs that answer real questions

Do not turn this into a project whose main achievement is:

```text
Python script -> API -> chart
```

Target analytics-engineering story:

```text
API
-> raw observations
-> clean staging models
-> reusable intermediate models
-> analytical marts
-> questions about seasonality and booking lead time
```

## Current Scope

For Phase 1, do not implement destination exploration.

Do not use:

- Google Travel Explore
- Google Flights Deals
- random holiday destination search
- where-should-I-go recommendations

Use only:

```text
SerpAPI engine = google_flights
```

The first stable version studies a fixed family of cities:

```text
Seoul
London
Kuala Lumpur
Tokyo
```

The focus is:

```text
travel timing
+
booking timing
+
route differences
```

## Fixed City Groups

Use these initial city-airport groups.

```text
Seoul: ICN, GMP
London: LHR, LGW
Tokyo: HND, NRT
Kuala Lumpur: KUL
```

London may later expand to STN/LTN, but do not change the initial scope without discussion.

API queries may use multiple airports for a city. When storing returned itineraries, preserve the actual departure and arrival airports so city-level and airport-level analysis are both possible later.

## Fixed Directional Routes

With four cities there are six unordered city pairs. Direction may matter, so treat them as twelve directional markets/routes:

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

These twelve directional routes are the permanent analytical backbone for the first stable version.

## Core Domain Concepts

### Route

A route represents one directional city market.

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

A `TripCohort` is one deliberately selected future round-trip journey that will be observed repeatedly.

Example:

```text
route: Seoul -> London
departure_date: 2027-02-10
return_date: 2027-02-17
trip_duration_days: 7
cohort_type: baseline
```

The cohort remains the same. Only the observation date changes.

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

Do not build a broader abstract planning framework before `TripCohort` is understood and working.

### SearchRun

A search run is one API request executed at one point in time.

It should eventually record:

```text
search_run_id
cohort_id
scheduled_lead_time_days
observed_at
provider
request_parameters
status
quota_cost
raw_response_reference
```

### Flight Offer Observation

A flight offer observation is one itinerary returned by one search run.

Preserve useful returned fields such as:

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
search_run_id
```

Do not assume the exact provider schema. Build parsing from real saved SerpAPI fixtures.

## Controlled Baseline Dataset

For the first baseline dataset:

```text
trip duration = 7 days
```

Why: comparisons are cleaner when route/date observations use the same methodology, same trip duration, same lead-time checkpoints, and systematic departure-date selection.

Later, 14-day or other durations may be added as separate cohorts. Do not mix them into the baseline until the first system is stable.

## Baseline Departure Cohorts

For each directional route, create:

```text
1 baseline departure cohort per calendar month
```

That means each route gets twelve baseline cohorts per year.

Dates must be selected using a systematic calendar rule, not manually chosen because they look cheap.

Possible rule:

```text
second Tuesday of every month
-> return exactly seven days later
```

Do not lock this rule into code until weekday bias has been discussed and approved.

The principle is that the date-selection rule should be consistent and reproducible.

## Booking Lead-Time Checkpoints

Each baseline cohort should be observed at these approximate lead times:

```text
180 days before departure
120 days
90 days
60 days
28 days
21 days
14 days
7 days
```

These support questions such as:

- Is 3 months ahead cheaper than 1 month?
- What happens between 4 weeks and 1 week?
- Is buying 6 months ahead unnecessarily early?

Each scheduled cohort observation should be identifiable by something like:

```text
cohort_id
lead_time_days
```

This lets the system know, for example, that the 90-day observation has already completed and prevents accidental re-execution.

For every actual observation derive:

```text
days_before_departure = departure_date - observed_at
```

If useful, preserve both:

```text
scheduled_lead_time_days
actual_days_before_departure
```

## Scheduler Direction

The scheduler can run daily without searching daily.

Daily execution should ask:

```text
Which observations are due today?
```

If no cohort is at a checkpoint:

```text
0 API searches
```

If two cohorts reach checkpoints:

```text
2 API searches
```

Preferred logic:

```text
cohort departure date
+
configured lead-time checkpoints
=
expected observation dates
```

Persist executed observations so reruns do not accidentally duplicate the same scheduled checkpoint unless explicitly intended.

## API Strategy

Use only SerpAPI `google_flights` for Phase 1.

Each API call should represent:

```text
one directional city route
+
one fixed departure date
+
one fixed return date
+
economy
+
round trip
```

One API call may return many itineraries. Store relevant returned offers.

Do not develop parsers using repeated paid/live requests. Use fixture-first development.

Workflow:

```text
1. obtain representative real response fixture
2. save fixture under tests/fixtures/
3. build parser against fixture
4. write parser tests
5. normalize into project records
6. only then call live API
```

Do not fabricate provider JSON fields.

## Raw Responses

Every successful live response must be recoverable.

Reasons:

- parser bugs can be corrected later
- normalized tables can be rebuilt
- API schema changes can be investigated
- API quota does not need to be spent again
- debugging is easier
- data lineage is clearer

Implementation can begin with either SQLite text/JSON storage or local raw JSON files referenced by search runs. Choose the simplest reliable approach, but discuss the decision before implementation.

## API Quota

Assume:

```text
250 successful searches per month
```

The project must persist enough information to calculate:

```text
searches used this month
searches remaining
searches by route
searches by cohort type
searches by lead-time checkpoint
```

The application must refuse to exceed the configured hard limit.

Approximate baseline steady-state workload:

```text
12 directional routes * 8 observations per cohort lifecycle
~= 96 searches/month average
```

Do not interpret this as 96 searches at cohort creation. Searches are distributed over time.

Do not intentionally spend all 250 searches from the beginning.

## Cohort Types

### Baseline

Systematically generated.

Purpose:

```text
general seasonality
route comparison
booking-window analysis
```

### Event

Meaningful recurring period, such as:

```text
Lunar New Year
Christmas
New Year
summer holiday
Chuseok
Golden Week
```

Purpose:

```text
understand special-period behavior
```

Use the same observation mechanism initially unless later configured differently.

### Personal

A real trip someone is considering, such as family visits, return trips, administrative trips, or holidays.

Purpose:

```text
make the project genuinely useful while feeding the same historical data infrastructure
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

## Analytics Engineering Evolution

Do not add dbt before ingestion is stable.

Future target direction:

```text
SerpAPI
-> raw_search_runs / raw_responses / raw_offers
-> dbt staging
-> dbt intermediate
-> dbt marts
-> analysis / dashboard
```

Possible dbt structure later:

```text
models/staging/stg_search_runs.sql
models/staging/stg_flight_offers.sql
models/staging/stg_routes.sql
models/staging/stg_trip_cohorts.sql
models/intermediate/int_flight_observations.sql
models/intermediate/int_booking_windows.sql
models/marts/mart_route_prices.sql
models/marts/mart_booking_windows.sql
models/marts/mart_seasonality.sql
```

This is future work, not the immediate next coding task.

## Existing Code

Preserve useful existing concepts:

```text
FlightOffer
SearchRun
PriceObservation
mock provider
SQLite
collector
analysis
tests
```

Keep the append-only rule:

```text
every collection creates new historical observations
old observations are never overwritten
```

Do not restart the repository.

Do not perform a large refactor merely because this document introduces new terminology.

Extend gradually.

## What Not To Build Yet

Do not implement these in Phase 1:

- random destination exploration
- Google Travel Explore
- Google Flights Deals
- where-should-I-holiday recommendations
- machine-learning fare prediction
- dynamic airfare alerts
- Airflow
- Kafka
- Spark
- Hadoop
- AWS Glue
- complex frontend
- mobile app
- dbt before ingestion is stable

Do not add technology for CV appearance. First build a trustworthy, automated longitudinal dataset.

## Immediate Implementation Order

### Step 1 - Inspect Existing Code

Inspect:

```text
models.py
database.py
collector.py
mock_provider.py
analysis.py
cli.py
tests/
```

Before changing anything, summarize:

```text
what can stay
what must change
what should be added
```

Do not refactor yet.

### Step 2 - Implement Route Configuration

Represent the twelve fixed directional routes.

Add validation and tests.

### Step 3 - Implement TripCohort

Support:

```text
baseline
event
personal
```

Add validation and tests.

### Step 4 - Decide And Implement Baseline Date Rule

Do not choose the rule silently.

Before coding, present the proposed rule and implications.

Once approved, create a generator for monthly baseline cohorts.

### Step 5 - Implement Checkpoint Scheduling

Given a cohort departure date, determine due observations for:

```text
180, 120, 90, 60, 28, 21, 14, 7
```

Add tests.

### Step 6 - Persist Routes And Cohorts

Extend SQLite.

Do not migrate away from SQLite yet.

### Step 7 - Extend SearchRun

Connect every executed search to:

```text
cohort
scheduled checkpoint
actual observation time
quota cost
status
```

### Step 8 - Implement Raw Response Storage

Do this before live data collection.

### Step 9 - Add A Real Saved Google Flights Fixture

Do not fabricate provider JSON.

### Step 10 - Implement Google Flights Parser

Parse fixture into existing or updated domain records.

### Step 11 - Add Live SerpAPI Client

Only after parser tests work.

### Step 12 - Execute One Controlled Live Search

Use one route and one cohort.

Verify:

```text
search run stored
raw response stored
offers stored
quota recorded
```

### Step 13 - Implement Daily Due-Check Runner

It should:

```text
load active cohorts
find due checkpoints
check quota
run required searches
store results
exit
```

### Step 14 - Automate

Only after the local daily runner is reliable.

## Milestones

### First Real Milestone

```text
one cohort successfully moves through the system
```

Example:

```text
Route: Seoul -> London
Cohort: Feb 2027 baseline
Checkpoint: 120 days
-> scheduler recognizes it is due
-> SerpAPI Google Flights request
-> raw JSON stored
-> search run stored
-> offers normalized
-> historical observations stored
-> quota count updated
```

Do not prioritize dashboard work before this exists.

### Second Milestone

```text
all twelve routes can automatically maintain future baseline cohorts
```

At this point, the system can begin accumulating useful historical data.

### Third Milestone

After stable collection, introduce dbt and the analytics-engineering layer.

First useful marts should answer:

- How has price changed as departure approaches?
- What is the observed cheapest booking window by route?
- How does price differ by departure month?
- How many observations support each conclusion?

Always include observation counts.

## Data Quality Expectations

Eventually test:

- `route_id` not null
- `cohort_id` unique
- `search_run_id` unique
- `price >= 0`
- `currency` not null
- departure before return for round trips
- scheduled lead time in accepted set
- cohort type in accepted values
- baseline trip duration = 7 days
- actual days before departure >= 0

Add tests as behavior becomes real.

## Commands

Use Python 3.12+ and `uv`.

Preferred commands:

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
uv run python -m flight_tracker.cli
```

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

## Development Session Format

At the end of each session, update a private progress note containing:

```text
WHAT WE BUILT
- concrete behavior that now works

WHY IT EXISTS
- which project question it supports

WHAT DATA IT CREATES
- records / tables / fields

WHAT I SHOULD UNDERSTAND
- short explanation of important implementation concepts

NEXT STEP
- exactly one next implementation target

DEFERRED
- things intentionally not being built yet
```

This prevents the project from becoming opaque.
