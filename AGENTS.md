# AGENTS.md

## Current Project Direction

This project is now a cost-aware flight market analytics pipeline.

Do not treat it as only a narrow route/date price tracker. The existing code is a useful foundation and should be preserved where it still fits, but the target product is broader:

```text
Market
-> SearchPlan
-> SearchRun
-> Provider Client
-> Raw Response Storage
-> Parser / Normalizer
-> DiscoveryResult and/or FlightOffer
-> PriceObservation
-> Analytics
```

The finished system should eventually help answer four questions:

```text
1. Where should I go?
2. When should I travel?
3. What does that trip cost now?
4. When should I book it?
```

Everything implemented should support one or more of those questions.

## Existing Foundation

The repository already has useful local pipeline work:

```text
mock flight data
-> validated Python models
-> SQLite storage
-> append-only price history
-> tests
```

Do not restart the project. Extend the foundation carefully.

Current useful concepts that should remain unless there is a clear reason to change them:

- Python 3.12+
- `uv`
- `pytest`
- `ruff`
- `FlightOffer`
- `SearchRun`
- `PriceObservation`
- mock provider
- SQLite
- append-only historical observations
- tests that do not consume API quota

The append-only rule remains critical:

```text
Every collection creates a new historical price observation.
Old observations are not overwritten.
```

## What Must Change

The current system starts too late in the problem:

```text
SearchRun
-> FlightOffer
-> PriceObservation
```

The new direction begins higher up:

```text
Market
-> SearchPlan
-> SearchRun
-> DiscoveryResult and/or FlightOffer
-> PriceObservation
```

Missing layers to add incrementally:

- market definition
- search plans
- cheap-period discovery
- cheap-destination discovery
- search-budget allocation
- candidate trip selection
- real SerpAPI ingestion
- raw response preservation
- repeated/scheduled collection
- booking-window analytics
- travel-period analytics

## What Not To Do Right Now

Do not spend significant time on:

- polishing the CLI before real ingestion works
- repeatedly rewriting the README before the data flow works
- frontend or mobile app work
- machine-learning fare prediction
- complex recommendation models
- AI ranking algorithms
- Airflow
- Kafka
- Spark
- Hadoop
- AWS Glue
- Kubernetes
- elaborate cloud infrastructure
- premature schema normalization for every possible entity
- airline dimension tables unless clearly necessary
- exact best-booking-day claims before enough historical data exists

Do not introduce infrastructure to make the portfolio look more complicated.

Priority order:

```text
correct data model
-> real ingestion
-> discovery
-> tracking
-> automation
-> data accumulation
-> analytics
```

## Domain Model Direction

### Market

A `Market` describes a travel question the system cares about. It is not one API request.

Suggested initial fields:

```text
market_id
name
origin_airports
destination_airports | None
purpose
trip_type
min_trip_length_days | None
max_trip_length_days | None
priority
active
```

Possible purposes should stay small:

```text
core_route
destination_discovery
travel_period_discovery
holiday_route
```

Airport groups should be configurable, not hard-coded deep in business logic.

### SearchPlan

A `SearchPlan` defines how API quota is spent to investigate a market.

Suggested initial fields:

```text
plan_id
market_id
search_type
provider
frequency
priority
active
departure_date | None
return_date | None
date_range_start | None
date_range_end | None
min_trip_length_days | None
max_trip_length_days | None
```

Do not make one universal model for every SerpAPI parameter. Represent our use cases clearly.

### DiscoveryResult

Discovery asks:

```text
Where or when might be cheap?
```

Suggested conceptual fields:

```text
discovery_result_id
search_run_id
market_id
origin
destination
departure_date
return_date
trip_length_days
price
currency
typical_price | None
discount_percent | None
source
observed_at
```

Discovery results are intended to identify promising destinations or date windows, not preserve every itinerary detail.

### Tracking Data

Tracking asks:

```text
How does the price of this specific trip change as departure approaches?
```

`FlightOffer` and `PriceObservation` remain useful here.

Every tracking observation should include or be joinable to:

```text
observed_at
origin
destination
departure_date
return_date
price
currency
airline / itinerary identifier where available
search_run_id
```

Booking-window analysis is central. Store source dates and derive `days_before_departure` in analysis/transformation code unless storing it materially simplifies deterministic queries.

## Discovery vs Tracking

Keep two data modes distinct:

```text
Discovery = broad search for cheap destinations or date windows.
Tracking = repeated exact-trip observation over time.
```

Provider direction:

```text
Discovery endpoints: google_travel_explore or google_flights_deals
Tracking endpoint: google_flights
```

Do not brute-force every date using normal Google Flights. Use broad discovery first, then promote selected candidates into tracking plans.

Candidate promotion may be manual for the prototype:

```text
discover
-> list candidates
-> mark candidate selected
-> create tracking SearchPlan
```

Do not build an AI ranking algorithm in this phase.

## SerpAPI Quota Is A First-Class Constraint

Assume a monthly search budget of:

```text
250 searches/month
```

Do not treat this as only a warning. Build quota awareness into the application.

At minimum, the system should eventually answer:

```text
How many searches have been used this month?
How many remain?
Which plans are consuming quota?
Are low-priority searches safe to run?
```

Initial allocation policy can be configuration, for example:

```text
~30 discovery
~140 core-route tracking
~50 holiday/candidate tracking
~30 reserve / experiments
```

Do not hard-code allocation logic deep in business logic. Put quota settings in configuration.

## Initial Market Scope

Do not track the world.

Suggested initial core markets:

```text
Seoul <-> London
London <-> Tokyo
London <-> Kuala Lumpur
Seoul <-> Tokyo
```

Suggested discovery markets:

```text
London -> flexible holiday destinations
Seoul -> flexible holiday destinations
```

Example airport groups:

```text
Seoul: ICN, GMP
London: LHR, LGW
Tokyo: HND, NRT
Kuala Lumpur: KUL
```

Treat these as configurable defaults, not immutable code.

## Storage Direction

SQLite is acceptable for this phase. Do not migrate databases for prestige.

Likely tables over time:

```text
markets
search_plans
search_runs
raw_responses
discovery_results
flight_offers        # optional depending on design
price_observations
quota_usage          # or derive from search_runs if cleanly possible
```

Do not create every table immediately if the domain can be introduced incrementally.

Prefer clear schema initialization or migrations over ad-hoc table creation scattered across code.

## Raw Response Storage

Raw provider responses must be preserved.

Reasons:

- parser bugs can be fixed without spending API quota again
- provider schema changes can be investigated
- normalized records can be regenerated
- debugging becomes easier
- it strengthens the data-engineering portfolio story

Initial raw storage can use SQLite JSON/text or local JSON files referenced from search runs. Choose the simplest option that is deterministic, testable, and not painful locally.

## Fixture-First SerpAPI Development

Do not develop parsers using repeated paid/live requests.

Workflow:

```text
1. obtain representative real response fixtures
2. save fixtures under tests/fixtures/
3. build parser against fixtures
4. write parser tests
5. normalize into project models
6. only then call live API
```

Suggested fixture paths only when endpoints are implemented:

```text
tests/fixtures/serpapi_google_flights.json
tests/fixtures/serpapi_google_flights_deals.json
tests/fixtures/serpapi_travel_explore.json
```

Do not invent response fields. Parser behavior must be based on real saved responses.

## Provider Abstraction

Keep the mock provider.

Introduce provider interfaces only as needed for tests and provider swapping.

Potential concrete providers:

```text
MockFlightProvider
SerpApiGoogleFlightsProvider
SerpApiDiscoveryProvider
```

Do not build a giant abstract framework.

## SearchRun Responsibilities

`SearchRun` should become the audit record for every attempted provider search.

It should eventually answer:

```text
What did we search?
Why did we search it?
Which plan triggered it?
When?
Which provider?
Did it succeed?
Did it consume quota?
Where is the raw response?
How many normalized results were produced?
```

Possible fields:

```text
search_run_id
search_plan_id
market_id
provider
search_type
searched_at
request_parameters
status
quota_cost
error_message | None
```

Do not duplicate every provider parameter into dedicated columns unless needed for frequent filtering. Use structured request metadata where appropriate.

## Immediate Implementation Order

Follow this unless code constraints require a small adjustment.

1. Audit existing code and tests.
   - Identify what remains unchanged.
   - Identify what needs extension.
   - Identify what should be replaced.
   - Do not begin by refactoring.

2. Add `Market` model + validation + tests.
   - valid market can be created
   - invalid airport groups rejected
   - market purpose validated
   - optional flexible destination supported

3. Add `SearchPlan` model + validation + tests.
   - plan belongs to market
   - discovery and exact tracking plans are distinguishable
   - exact tracking requires dates
   - flexible discovery does not require exact dates

4. Persist markets and search plans in SQLite.
   - create/save/load market
   - create/save/load search plan
   - foreign-key relationship enforced
   - existing history tests still pass

5. Expand `SearchRun` audit data.
   - connect searches to market/plan
   - record provider, search type, status, request metadata, quota cost, error
   - tests cover success and failure states

6. Implement raw response persistence.
   - every live response can be preserved
   - search run references raw response
   - raw response can be loaded later
   - parser can run from saved raw data

7. Add one real saved Google Flights fixture.

8. Implement and test Google Flights parser.

9. Add one discovery endpoint fixture and parser.

10. Implement live SerpAPI client.
    - API key from environment
    - timeouts
    - error handling
    - response validation
    - raw response persistence
    - quota logging
    - no hard-coded secrets

11. Implement discovery workflow.

12. Implement candidate promotion workflow.

13. Connect exact tracking plans to append-only historical tracking.

14. Add quota-aware execution.

15. Add analytics.

16. Add simple automation/scheduler.

17. Polish documentation only after end-to-end data flow works.

## Analytics Direction

Minimum useful analytics after ingestion exists:

```text
get_latest_price(...)
get_lowest_observed_price(...)
get_price_history(...)
get_price_change(...)
get_booking_window_summary(...)
get_cheapest_discovery_results(...)
```

Suggested booking-window buckets:

```text
0-14 days
15-30 days
31-60 days
61-90 days
91-180 days
180+ days
```

Do not claim statistical certainty from tiny samples. Outputs should distinguish observed-in-our-dataset from general truth.

## Testing Strategy

Every new layer should be testable without spending API quota.

Required categories:

```text
Domain tests: Market, SearchPlan, dates, airports
Parser tests: real fixtures, optional/missing fields, invalid values
Database tests: market, plan, search run, raw response, append-only observations
Quota tests: 0 used, 249 used, 250 used, month rollover
Workflow tests: market -> plan -> run -> raw -> normalized records -> history
```

Never require real credentials for the core test suite.

## Coding Principles

- Preserve working code.
- Before replacing an existing abstraction, explain why it no longer fits.
- Implement one coherent capability at a time.
- Avoid touching unrelated files.
- Add/update tests with every behavior change.
- Avoid speculative abstractions.
- Keep local correctness before infrastructure.
- Do not waste API quota.
- Use fixtures and mocks.
- Make failures visible.
- Prefer explicit domain names like `Market`, `SearchPlan`, `DiscoveryResult`, and `PriceObservation`.

## Commands

Use `uv`:

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

Small representative test fixtures are allowed when useful and safe.

## Decision Rules When Unsure

Use these priorities:

```text
1. Does it help answer the four core questions?
2. Does it help collect trustworthy historical data?
3. Does it protect the 250-search budget?
4. Does it improve reliability?
5. Does it improve testability?
6. Does it improve explainability for a portfolio?
```

If a proposed feature mainly improves visual polish or architectural sophistication while delaying real data collection, defer it.

## Definition Of Done

A task is done when:

```text
implementation exists
+ tests exist
+ behavior is demonstrated
+ failure cases are handled
+ existing tests still pass
```

For live integrations:

```text
fixture test passes
+ one controlled live call works
+ raw response is stored
+ normalized data is stored
+ quota usage is recorded
```

## Daily Steering Rule

At the end of each development session, update a short private progress note containing:

```text
DONE
- what became usable today

CURRENTLY WORKING
- one active implementation target

NEXT
- the single next concrete task

BLOCKERS
- only real blockers

DO NOT DO YET
- tempting but deferred work
```

This is intended to prevent drift into repeated README edits, unnecessary refactors, tool experimentation, or infrastructure rabbit holes.
