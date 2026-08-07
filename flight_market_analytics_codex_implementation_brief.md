# Flight Market Analytics Project — Codex Implementation Brief

## 0. Purpose of This Document

This document is the execution plan for steering the existing flight-price project toward the actual product we want to build.

It is **not** a brainstorm and it is **not** a list of optional ideas.

Treat this document as the current project direction.

The existing repository already has a useful foundation:

```text
mock flight data
→ validated Python models
→ SQLite storage
→ append-only price history
→ tests
```

We are **not restarting the project**.

We are changing the direction from a narrow:

> "track prices for a known flight/date"

system into a broader:

> **cost-aware flight market analytics pipeline that discovers cheap travel opportunities, selects useful trips for monitoring, and accumulates historical fare observations to analyze both when to travel and when to book.**

The central questions the finished system should eventually help answer are:

1. **Where should I go?**
2. **When should I travel?**
3. **What does that trip cost now?**
4. **When should I book it?**

Everything implemented during this phase should support one or more of those questions.

---

# 1. Current State

The repository currently contains roughly:

```text
src/flight_tracker/
├── __init__.py
├── models.py
├── mock_provider.py
├── database.py
├── collector.py
├── analysis.py
└── cli.py

tests/
├── test_models.py
├── test_mock_provider.py
├── test_database.py
└── test_analysis.py
```

Current useful capabilities include:

- Python 3.12+
- `uv`
- `pytest`
- `ruff`
- validated domain models
- mock provider
- SQLite storage
- `SearchRun`
- `FlightOffer`
- `PriceObservation`
- append-only historical observations
- chronological price-history queries
- tests that do not consume API quota

The current append-only rule remains important:

```text
Every collection creates a new historical price observation.
Old observations are not overwritten.
```

This is necessary for future booking-window analysis.

---

# 2. What Must Change

The current system begins too late in the problem.

It effectively starts here:

```text
SearchRun
→ FlightOffer
→ PriceObservation
```

But the real system needs to begin higher up:

```text
Market
→ SearchPlan
→ SearchRun
→ DiscoveryResult and/or FlightOffer
→ PriceObservation
```

The missing layers are:

```text
[1] market definition
[2] cheap-period discovery
[3] cheap-destination discovery
[4] search-budget allocation
[5] candidate trip selection
[6] real SerpAPI ingestion
[7] raw response preservation
[8] scheduling / repeated collection
[9] booking-window analytics
[10] travel-period analytics
```

The existing repository should be treated as the storage and ingestion foundation onto which these capabilities are added.

---

# 3. What We Are NOT Doing Right Now

Do not spend significant time on:

- polishing the CLI before real ingestion works
- rewriting the README repeatedly
- building a frontend
- building a mobile app
- machine-learning fare prediction
- complex recommendation models
- Airflow
- Kafka
- Spark
- Hadoop
- AWS Glue
- Kubernetes
- elaborate cloud infrastructure
- premature schema normalization for every possible entity
- airline dimension tables unless they become clearly necessary
- exact "best booking day" claims before enough historical data exists

Do not introduce infrastructure just to make the portfolio look more complicated.

The priority is:

```text
correct data model
→ real ingestion
→ discovery
→ tracking
→ automation
→ data accumulation
→ analytics
```

---

# 4. Product Model

## 4.1 Market

A `Market` describes a travel question that we care about.

Examples:

```text
SEOUL_LONDON
origin airports: ICN, GMP
destination airports: LHR, LGW
purpose: core_route
trip type: round_trip
trip length: 7–14 days
priority: high
```

```text
LONDON_HOLIDAY
origin airports: LHR, LGW
destination: flexible
purpose: destination_discovery
trip type: round_trip
trip length: 4–10 days
priority: medium
```

A market is **not a single API request**.

A market defines what the system wants to learn.

Suggested initial fields:

```python
Market
- market_id
- name
- origin_airports
- destination_airports | None
- purpose
- trip_type
- min_trip_length_days | None
- max_trip_length_days | None
- priority
- active
```

Possible purposes:

```text
core_route
destination_discovery
travel_period_discovery
holiday_route
```

Keep enums small.

Do not over-generalize.

---

## 4.2 SearchPlan

A `SearchPlan` defines **how we spend API quota to investigate a Market**.

Examples:

```text
SEOUL_LONDON_MONTHLY_DISCOVERY
market: SEOUL_LONDON
search type: flexible_date_discovery
frequency: monthly
provider endpoint: google_flights_deals or google_travel_explore
```

```text
SEOUL_LONDON_NOV_TRACKING
market: SEOUL_LONDON
search type: exact_trip_tracking
departure: 2026-11-10
return: 2026-11-20
frequency: weekly
provider endpoint: google_flights
```

Suggested fields:

```python
SearchPlan
- plan_id
- market_id
- search_type
- provider
- frequency
- priority
- active
- departure_date | None
- return_date | None
- date_range_start | None
- date_range_end | None
- min_trip_length_days | None
- max_trip_length_days | None
```

Do not attempt to make one universal model for every SerpAPI parameter.

The goal is to represent our use cases clearly.

---

# 5. The Two Data Modes

The project must distinguish between two fundamentally different data purposes.

## 5.1 Discovery Data

Discovery asks:

> Where or when might be cheap?

Sources may include:

```text
Google Travel Explore
Google Flights Deals
```

Discovery results should capture candidate travel opportunities.

Suggested conceptual model:

```python
DiscoveryResult
- discovery_result_id
- search_run_id
- market_id
- origin
- destination
- departure_date
- return_date
- trip_length_days
- price
- currency
- typical_price | None
- discount_percent | None
- source
- observed_at
```

Discovery is not intended to preserve every airline itinerary.

It is intended to find promising destinations or date windows.

---

## 5.2 Tracking Data

Tracking asks:

> How does the price of this specific trip change as departure approaches?

Primary source:

```text
Google Flights
```

This is where the existing `FlightOffer` and `PriceObservation` concepts remain useful.

Every tracking observation should make it easy to derive:

```python
days_before_departure = departure_date - observed_at
```

This value is central to future booking-window analysis.

Do not treat booking-window calculations as a minor optional feature.

---

# 6. Core Architecture

Target conceptual flow:

```text
                     MARKETS
                        │
                        ▼
                  SEARCH PLANS
                        │
              ┌─────────┴─────────┐
              │                   │
              ▼                   ▼
         DISCOVERY             TRACKING
              │                   │
              ▼                   ▼
     Explore / Deals         Google Flights
              │                   │
              ▼                   ▼
     DiscoveryResult         FlightOffer
              │                   │
              └─────────┬─────────┘
                        ▼
                    DATABASE
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
      Travel-period          Booking-window
         analysis               analysis
```

A more implementation-oriented flow:

```text
Market
→ SearchPlan
→ Scheduler / Planner
→ SearchRun
→ Provider Client
→ Raw Response Storage
→ Parser / Normalizer
→ DiscoveryResult or FlightOffer
→ PriceObservation
→ Analytics
```

---

# 7. Provider Strategy

The project should use SerpAPI carefully because the account has a limited monthly search budget.

The intended division of responsibilities is:

## Discovery

Prefer flexible-search endpoints for broad questions such as:

```text
When is Seoul → London cheap?
Where can I travel cheaply from London?
What date windows look attractive?
```

Candidate endpoints:

```text
google_travel_explore
google_flights_deals
```

## Tracking

Use normal Google Flights for precise observations:

```text
google_flights
```

Example tracking target:

```text
ICN,GMP → LHR,LGW
2026-11-10 → 2026-11-20
economy
round trip
```

Do not brute-force every date using normal Google Flights.

Use broad discovery first, then promote selected candidates into tracking plans.

---

# 8. Search Quota Must Be a First-Class System Constraint

The system has a monthly SerpAPI budget.

Initial assumption:

```python
MONTHLY_SEARCH_BUDGET = 250
```

Do not treat this only as a development warning.

Build the quota constraint into application logic.

At minimum track:

```text
month
successful_api_searches
remaining_budget
search_plan_id
provider
search_type
searched_at
```

The application should be able to answer:

```text
How many searches have we used this month?
How many remain?
Which plans are consuming quota?
How many planned searches remain?
Are low-priority searches safe to run?
```

Initial simple policy:

```text
250 monthly searches

~30   discovery
~140  core-route tracking
~50   holiday/candidate tracking
~30   reserve / experiments
```

These numbers are configuration, not permanent rules.

Do not hard-code allocation logic deep inside business logic.

Put quota settings in configuration.

---

# 9. Initial Market Scope

Do not attempt to track the world.

Start with a small set.

Suggested initial core markets:

```text
Seoul ↔ London
London ↔ Tokyo
London ↔ Kuala Lumpur
Seoul ↔ Tokyo
```

Suggested discovery markets:

```text
London → flexible holiday destinations
Seoul → flexible holiday destinations
```

Airport groups may look like:

```text
Seoul:
ICN, GMP

London:
LHR, LGW

Tokyo:
HND, NRT

Kuala Lumpur:
KUL
```

Treat these as examples/configurable defaults.

Do not assume the market list is immutable.

Store market definitions in a config file or database seed data so they can be edited without changing core application code.

---

# 10. Data Storage Direction

SQLite is acceptable for this phase.

Do not migrate databases merely for prestige.

However, evolve the schema enough to support the new domain.

Likely tables:

```text
markets
search_plans
search_runs
raw_responses
discovery_results
flight_offers        # optional depending on current design
price_observations
quota_usage          # or derive from search_runs if cleanly possible
```

Do not create every table immediately if the domain model can be introduced incrementally.

Prefer migrations or clear schema initialization over ad-hoc table creation scattered across code.

---

# 11. Raw Response Storage

Raw provider responses must be preserved.

Reason:

- parser bugs can be fixed without spending API quota again
- provider schema changes can be investigated
- normalized records can be regenerated
- debugging becomes much easier
- it strengthens the data-engineering story

Initial implementation can use either:

```text
SQLite JSON/text
```

or:

```text
local JSON files referenced from search_runs
```

Choose the simplest option that:

- is deterministic
- is testable
- does not make local development painful
- avoids duplicating large blobs unnecessarily

Do not block the entire project debating the perfect raw-zone architecture.

For the prototype, correctness and recoverability matter more.

---

# 12. Fixture-First SerpAPI Development

Do not develop parsers using repeated paid/live requests.

Workflow:

```text
1. obtain one or a few representative response fixtures
2. save them under tests/fixtures/
3. build parser against fixture
4. write parser tests
5. normalize into project models
6. only then call live API
```

Suggested structure:

```text
tests/
└── fixtures/
    ├── serpapi_google_flights.json
    ├── serpapi_google_flights_deals.json
    └── serpapi_travel_explore.json
```

Add only the fixtures for endpoints we actually implement.

Do not invent response fields.

Parser behavior must be based on real saved responses.

---

# 13. Provider Abstraction

The current mock provider is useful and should remain.

Introduce a provider interface/protocol if one does not already exist cleanly.

Conceptually:

```python
class FlightProvider(Protocol):
    def search(...):
        ...
```

Potential concrete providers:

```text
MockFlightProvider
SerpApiGoogleFlightsProvider
SerpApiDiscoveryProvider
```

Do not build a giant abstract framework.

Only abstract the differences we actually need for tests and provider swapping.

---

# 14. SearchRun Responsibilities

`SearchRun` should become the audit record for every attempted provider search.

It should eventually record enough to answer:

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

```python
SearchRun
- search_run_id
- search_plan_id
- market_id
- provider
- search_type
- searched_at
- request_parameters
- status
- quota_cost
- error_message | None
```

Do not duplicate every search parameter into dedicated database columns unless it is needed for frequent filtering.

Use structured request metadata where appropriate.

---

# 15. PriceObservation Requirements

Preserve append-only behavior.

Every observation should include or be joinable to:

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

Add or derive:

```text
days_before_departure
```

Recommended approach:

- store source dates and timestamps
- derive `days_before_departure` in analysis or transformation code
- store it only if doing so materially simplifies queries and remains deterministic

Whichever approach is chosen, tests must verify correctness.

---

# 16. Candidate Promotion

Discovery results should not automatically cause endless tracking.

Introduce a simple concept of a selected or tracked trip.

For prototype purposes, candidate selection may be manual.

Example:

```text
Discovery finds:
Nov 03–12  £448
Nov 10–19  £462
Feb 04–13  £471
```

Then a human can promote:

```text
Nov 03–12
Feb 04–13
```

into tracking plans.

This is acceptable.

Do **not** build an AI ranking algorithm during this month.

Possible simple workflow:

```text
discover
→ list candidates
→ mark candidate selected
→ create tracking SearchPlan
```

CLI support is useful only once the workflow exists.

---

# 17. Analytics Required for the Prototype

Implement useful analytics only after data ingestion exists.

Minimum useful analysis functions:

```text
latest observed price
lowest observed price
price change since previous observation
price change percentage
observation count
days before departure
median price by booking-window bucket
minimum price by booking-window bucket
candidate travel periods sorted by price
candidate destinations sorted by price
```

Suggested booking-window buckets:

```text
0–14 days
15–30 days
31–60 days
61–90 days
91–180 days
180+ days
```

Do not claim statistical certainty from tiny samples.

Outputs should distinguish:

```text
observed in our dataset
```

from:

```text
general truth
```

---

# 18. Scheduler Direction

By the end of the one-month build, the project should be able to run without manual execution.

The scheduler should eventually:

```text
load active SearchPlans
→ determine which plans are due
→ check monthly quota
→ prioritize plans
→ execute searches
→ store raw responses
→ normalize
→ store observations
→ log result
```

Initial frequency concept:

```text
departure > 180 days away:
monthly

90–180 days:
every 2 weeks

30–90 days:
weekly

14–30 days:
possibly twice weekly

<14 days:
only if we intentionally want dense short-term data
```

This does not need to be fully dynamic in the first implementation.

A fixed weekly schedule is acceptable for the first prototype.

But design the code so cadence can later depend on `days_before_departure`.

---

# 19. Two-Week Prototype Target

The two-week target is not "finished product".

By the end of approximately two weeks, we want:

```text
real SerpAPI fixture parsers
real live API support
markets
search plans
discovery results
candidate selection
tracked-trip price observations
quota logging
basic analytics
tests
```

A successful prototype should demonstrate this flow:

```text
1. configure Seoul → London market
2. run discovery
3. identify cheap candidate travel periods
4. select one candidate
5. create tracking plan
6. run Google Flights tracking search
7. store raw response
8. store normalized observations
9. query current/history data
10. show days-before-departure analytics
```

If that works end-to-end, the prototype is successful.

---

# 20. One-Month Target

By the end of approximately one month, the project should be "leave it running" capable.

Required characteristics:

```text
scheduled execution
persistent storage
safe API-key handling
quota protection
retry/error handling
logging
idempotent schema setup
data-quality checks
tests
documentation
basic operational visibility
```

The goal is:

```text
works unattended
```

not:

```text
has every feature
```

Once stable, reduce development activity and let historical data accumulate.

---

# 21. Concrete Implementation Order

Follow this order unless code constraints clearly require a small adjustment.

## Phase 1 — Domain Redesign

### Task 1.1 — Audit existing models

Inspect:

```text
models.py
database.py
collector.py
analysis.py
cli.py
mock_provider.py
tests/
```

Determine what can be preserved directly.

Do not rewrite working components unnecessarily.

### Task 1.2 — Add `Market`

Implement model + validation + tests.

Acceptance criteria:

- valid market can be created
- invalid airport groups rejected
- market purpose validated
- optional flexible destination supported
- tests pass

### Task 1.3 — Add `SearchPlan`

Implement model + validation + tests.

Acceptance criteria:

- plan belongs to market
- discovery and exact tracking plans are distinguishable
- exact tracking plan requires necessary dates
- flexible discovery plan does not require exact dates
- tests pass

---

## Phase 2 — Schema Evolution

### Task 2.1 — Add market/search-plan storage

Create persistence for:

```text
markets
search_plans
```

Acceptance criteria:

- create/save/load market
- create/save/load search plan
- foreign-key relationship enforced where appropriate
- existing history tests still pass

### Task 2.2 — Expand search-run audit data

Ensure search runs can record:

```text
market
plan
provider
search type
status
request metadata
quota cost
error
```

Acceptance criteria:

- successful and failed runs are distinguishable
- a search can be traced back to a plan
- tests cover failure state

---

## Phase 3 — Raw Response Layer

### Task 3.1 — Implement raw response persistence

Acceptance criteria:

- every live provider response can be preserved
- search run references raw response
- raw response can be loaded later
- parser can run from saved raw data
- tests do not need internet

---

## Phase 4 — SerpAPI Parsers

### Task 4.1 — Add fixture files

Use real representative JSON.

Do not fabricate response structures.

### Task 4.2 — Parse normal Google Flights

Convert relevant response records into project `FlightOffer` data.

Acceptance criteria:

- fixture parses without network
- missing optional fields handled safely
- price/currency parsed correctly
- airport/date fields normalized
- malformed required data raises or skips according to explicit policy
- parser tests exist

### Task 4.3 — Parse one discovery endpoint

Start with **one** of:

```text
Google Flights Deals
Google Travel Explore
```

Do not implement both simultaneously unless the first one is clearly complete.

Acceptance criteria:

- fixture produces `DiscoveryResult`
- travel dates captured
- origin/destination captured
- price captured
- discount/typical price captured if actually available
- parser tests exist

Only after this is working should the second discovery endpoint be considered.

---

# 22. Phase 5 — Live Provider Client

Implement live SerpAPI client after fixture parsing works.

Requirements:

```text
API key from environment
timeouts
error handling
response validation
raw response persistence
quota logging
no hard-coded secrets
```

Add:

```text
.env.example
```

but never commit the real key.

Acceptance criteria:

- one controlled live search can run
- response is stored raw
- normalized records are stored
- API key absent → clear error
- provider error → failed SearchRun recorded
- successful request increments quota usage
- unit tests mock HTTP / provider calls

---

# 23. Phase 6 — Discovery Workflow

Implement a command or service capable of:

```text
run discovery for market
→ persist SearchRun
→ persist raw response
→ persist DiscoveryResults
→ list candidate results
```

Example desired UX:

```text
flight-tracker discover SEOUL_LONDON
```

or equivalent Python service method.

CLI naming is secondary.

The actual workflow matters.

Acceptance criteria:

- discovery can be run for configured market
- results are persisted
- cheapest candidate results can be queried
- quota is checked before live call

---

# 24. Phase 7 — Candidate Tracking Workflow

Implement:

```text
DiscoveryResult
→ selected candidate
→ tracking SearchPlan
```

Selection may initially be manual.

Example conceptual command:

```text
flight-tracker track-candidate <candidate-id>
```

or equivalent service method.

Acceptance criteria:

- candidate can be promoted
- exact travel dates become a tracking plan
- duplicate tracking plans are prevented or clearly handled
- tracking plan can be executed

---

# 25. Phase 8 — Historical Tracking

Connect exact tracking plans to existing collector/storage logic.

Acceptance criteria:

- repeated executions append observations
- previous observations are never overwritten
- same trip searched on multiple days creates multiple historical records
- history can be queried chronologically
- `days_before_departure` is available in analysis

This is where existing project work should be reused heavily.

---

# 26. Phase 9 — Quota-Aware Execution

Implement a minimal quota service.

Conceptual API:

```python
quota.remaining_for_month()
quota.can_run(plan)
quota.record(search_run)
```

Initial policy:

```text
do not execute if monthly hard limit would be exceeded
```

Optional next step:

```text
reserve N searches for high-priority plans
```

Acceptance criteria:

- system refuses a call when budget exhausted
- quota usage comes from persisted runs, not only process memory
- current month resets naturally via date filtering
- tests simulate boundary conditions

---

# 27. Phase 10 — Analytics

Implement after enough pipeline functionality exists.

Functions should include at minimum:

```text
get_latest_price(...)
get_lowest_observed_price(...)
get_price_history(...)
get_price_change(...)
get_booking_window_summary(...)
get_cheapest_discovery_results(...)
```

Booking window output example:

```text
61–90 days:
observations: 12
median: 482
min: 438

31–60 days:
observations: 9
median: 501
min: 459
```

Do not over-interpret sparse data.

---

# 28. Phase 11 — Automation

Choose the simplest reasonable scheduler.

Possible starting choices:

```text
GitHub Actions scheduled workflow
cron
simple cloud scheduler
```

Do not introduce Airflow unless project complexity later genuinely requires it.

Scheduled job should:

```text
load due plans
check quota
execute
persist
log
exit cleanly
```

Acceptance criteria:

- process can run non-interactively
- one failing plan does not corrupt other data
- secrets are externalized
- logs identify failed plan/run
- rerunning does not overwrite historical observations

---

# 29. Phase 12 — Documentation and Portfolio Polish

Only do this after the end-to-end data flow works.

README should eventually explain:

```text
problem
why historical price data must be accumulated
architecture
market vs search plan
discovery vs tracking
quota-aware design
schema
how to run locally
how scheduled collection works
current limitations
sample analytics
```

Do not document features that are not implemented.

---

# 30. Suggested Repository Direction

Do not reorganize files just for aesthetics.

A possible later structure:

```text
src/flight_tracker/
├── __init__.py
├── models.py
├── config.py
├── database.py
├── collector.py
├── quota.py
├── scheduler.py
├── analysis.py
├── cli.py
├── providers/
│   ├── __init__.py
│   ├── base.py
│   ├── mock.py
│   └── serpapi.py
└── parsers/
    ├── __init__.py
    ├── google_flights.py
    └── discovery.py
```

Only move to this structure when the new responsibilities exist.

Do not perform a large refactor before implementing functionality.

---

# 31. Testing Strategy

Every new layer should be testable without spending API quota.

Required categories:

## Domain tests

```text
Market validation
SearchPlan validation
date validation
airport validation
```

## Parser tests

```text
real saved fixture
optional fields
missing fields
invalid values
multiple offers
```

## Database tests

```text
market persistence
plan persistence
search-run persistence
raw response persistence
append-only observations
candidate persistence
```

## Quota tests

```text
0 used
249 used
250 used
month rollover
failed/no-cost searches where policy applies
```

## Workflow tests

Mock provider:

```text
market
→ plan
→ run
→ raw
→ normalized records
→ history
```

Never require real credentials for the core test suite.

---

# 32. Coding Principles for Codex

When implementing, follow these rules.

## Preserve working code

Before replacing an existing abstraction, explain why it no longer fits.

Prefer extending working components over rewriting them.

## Small commits / small changes

Implement one coherent capability at a time.

Avoid touching unrelated files.

## Tests with every behavior change

Do not postpone tests until the end.

## No speculative abstractions

If only one provider behavior exists, do not create five layers of inheritance.

## No premature infrastructure

Local correctness first.

## No API waste

Use fixtures and mocks.

A live call should be intentional.

## Make failures visible

Do not silently swallow provider/parser/database errors.

## Prefer explicit domain names

Use:

```text
Market
SearchPlan
DiscoveryResult
PriceObservation
```

instead of vague names like:

```text
Item
Data
ResultObject
Manager
```

---

# 33. Decision Rules When Unsure

If implementation choices arise, use these priorities:

```text
1. Does it help answer the four core questions?
2. Does it help collect trustworthy historical data?
3. Does it help protect the 250-search budget?
4. Does it improve reliability?
5. Does it improve testability?
6. Does it improve explainability for a portfolio?
```

If a proposed feature mainly improves visual polish or architectural sophistication while delaying real data collection, defer it.

---

# 34. What "Done" Means for Each Stage

A task is not done because code exists.

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

---

# 35. Daily Steering Rule

At the end of each development session, update a short progress note containing:

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

This is intended to prevent the project from drifting into:

```text
README edits
unnecessary refactors
tool experimentation
infrastructure rabbit holes
```

---

# 36. Recommended Immediate Next Actions

Start here.

## Step 1

Inspect the existing code and tests.

Produce a short internal implementation note:

```text
what can remain unchanged
what needs extension
what should be replaced
```

Do **not** begin by refactoring.

## Step 2

Implement:

```text
Market
SearchPlan
```

with tests.

## Step 3

Persist them in SQLite.

## Step 4

Expand `SearchRun` so it is connected to a plan and can audit provider execution.

## Step 5

Implement raw response persistence.

## Step 6

Add one real saved Google Flights fixture.

## Step 7

Implement and test the Google Flights parser.

## Step 8

Add one discovery endpoint fixture and parser.

## Step 9

Implement the live SerpAPI client.

## Step 10

Run the first controlled end-to-end live search.

Only then proceed to:

```text
candidate promotion
quota scheduler
automated tracking
analytics
documentation
```

---

# 37. First End-to-End Milestone

The first major milestone is complete when the repository can demonstrate:

```text
Market: Seoul → London

        ↓

Discovery SearchPlan

        ↓

SerpAPI discovery response

        ↓

raw response stored

        ↓

DiscoveryResult records stored

        ↓

candidate selected

        ↓

exact Tracking SearchPlan created

        ↓

Google Flights response

        ↓

raw response stored

        ↓

FlightOffer / PriceObservation stored

        ↓

history query works
```

Until this works, do not prioritize dashboards or sophisticated infrastructure.

---

# 38. Second Major Milestone

The second milestone is:

```text
the project can run unattended
```

Specifically:

```text
scheduled job starts
→ identifies due plans
→ checks quota
→ runs permitted searches
→ stores raw data
→ stores normalized data
→ logs outcomes
→ exits safely
```

At this point the system can be left alone to accumulate historical data.

---

# 39. Long-Term Analytics Direction

Once sufficient history exists, the interesting dataset becomes:

```text
observed_at
departure_date
return_date
days_before_departure
origin
destination
price
airline
stops
duration
market
```

This can eventually support questions such as:

```text
Which months are cheapest for this route?

Which travel windows repeatedly appear as cheap?

How volatile is this route?

How quickly do fares increase near departure?

Which booking-window bucket had the lowest median observed price?

Does nonstop pricing behave differently from connecting fares?

How large is the premium for preferred airlines?

Are currently observed fares low relative to our own historical observations?
```

Do not attempt all of these immediately.

The current priority is creating the dataset that makes them possible.

---

# 40. Final Project Direction

The project should no longer be steered as:

```text
build a price-history CLI
```

It should be steered as:

```text
build a cost-aware flight market observatory
```

The system should:

```text
DISCOVER
where and when travel looks cheap

SELECT
which opportunities are worth monitoring

TRACK
how those fares change over time

STORE
raw and normalized historical data safely

ANALYZE
when travel is cheap and how booking timing affects observed fares

CONTROL COST
by intelligently operating within a 250-search monthly API budget
```

The immediate success metric is not how many features exist.

It is:

> **Can the system reliably discover a useful trip, begin tracking it, preserve every observation, stay within quota, and continue collecting data without manual intervention?**

Build toward that.
