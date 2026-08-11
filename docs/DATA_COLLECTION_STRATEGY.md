# Data Collection Strategy

## Phase 1 Provider Scope

Phase 1 uses only:

```text
SerpAPI engine = google_flights
```

Do not use yet:

- Google Travel Explore
- Google Flights Deals
- random destination exploration
- where-should-I-go recommendations

Each API call should represent:

```text
one directional city route
+
one fixed departure date
+
one fixed return date
+
one requested travel_class
+
round trip
```

## Fixed City Groups

Initial city-airport groups:

```text
Seoul: ICN, GMP
London: LHR, LGW
Tokyo: HND, NRT
Kuala Lumpur: KUL
```

London may later expand to:

```text
STN, LTN
```

Do not change the initial London scope without discussion.

API queries may use multiple airports for a city, but actual returned departure and arrival airports must be preserved.

## Twelve Directional Routes

With four cities, there are six unordered city pairs. Direction may matter, so Phase 1 tracks twelve directional routes:

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

These are the permanent Phase 1 analytical backbone.

## Controlled 7-Day Baseline Cohorts

A `TripCohort` is one fixed round-trip travel period that is observed repeatedly over time.

For the controlled baseline dataset:

```text
trip duration = 7 days
```

Why:

```text
same trip duration
same methodology
same lead-time checkpoints
systematic departure-date selection
```

This creates cleaner comparisons across routes, months, and cabin classes.

Later, other durations such as 14 days may be added as separate cohorts. Do not mix them into the baseline until the first system is stable.

## Monthly Baseline Cohorts

For each directional route, create:

```text
1 baseline departure cohort per calendar month
```

Each route gets twelve baseline cohorts per year.

Dates should be selected using a systematic calendar rule, not manually chosen because they look cheap.

Possible rule:

```text
second Tuesday of every month
-> return exactly seven days later
```

This rule is unresolved. Do not lock it into code until weekday bias has been discussed and approved.

## Booking Lead-Time Checkpoints

Each baseline cohort should be observed at:

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

These correspond roughly to:

```text
6 months
4 months
3 months
2 months
4 weeks
3 weeks
2 weeks
1 week
```

They support questions like:

- Is 3 months ahead cheaper than 1 month?
- What happens between 4 weeks and 1 week?
- Is buying 6 months ahead unnecessarily early?

## Economy And Business Class Collection

The project must support:

```text
economy
business
```

A `TripCohort` represents route and travel dates. Searches and observations must preserve requested cabin class with an explicit `travel_class` field.

A single cohort may produce separate observations for:

```text
economy
business
```

Do not aggregate economy and business prices together.

Open decision:

```text
Does SerpAPI require separate google_flights calls for economy and business?
```

Before changing quota assumptions or schedules, determine and explain actual SerpAPI behavior.

If separate calls are required, collecting both classes could roughly double the baseline search usage. Do not silently make that change.

Scheduled checkpoint identity should include:

```text
cohort_id + scheduled_lead_time_days + travel_class
```

## Daily Scheduler vs Non-Daily API Searching

The program may run every day.

Daily execution should only ask:

```text
Which cohort checkpoints are due today, for which travel classes?
```

If no cohort is at a checkpoint:

```text
0 API searches
```

If two cohort/class checkpoints are due:

```text
2 API searches
```

This keeps collection systematic without wasting quota.

## Append-Only Historical Observations

Every collection creates new historical observations.

Old observations are never overwritten.

This is essential for booking-window analysis because the project needs to know what prices were visible at each observation point.

## API Quota

Assume:

```text
250 successful searches per month
```

Persist enough information to calculate:

- searches used this month
- searches remaining
- searches by route
- searches by cohort type
- searches by lead-time checkpoint
- searches by travel class

The application must refuse to exceed the configured hard limit.

Prior economy-only rough estimate:

```text
12 routes * 8 observations per cohort lifecycle ~= 96 searches/month average
```

This does not mean 96 searches happen when cohorts are created. Searches are distributed over time.

Business-class support means this estimate may need revision. Do not intentionally spend all 250 searches from the beginning.

## Raw Response Preservation

Do not normalize live API data and discard the original JSON.

Every successful live response should be recoverable.

Reasons:

- parser bugs can be corrected later
- normalized tables can be rebuilt
- API schema changes can be investigated
- API quota does not need to be spent again
- debugging is easier
- data lineage is clearer

Initial implementation can use either:

```text
SQLite text / JSON storage
```

or:

```text
local raw JSON files referenced by search_runs
```

Choose the simplest reliable approach, but discuss the decision before implementation.

## Fixture-First SerpAPI Development

Do not develop parsers using repeated paid/live requests.

Workflow:

```text
1. obtain one representative real response fixture
2. save it under tests/fixtures/
3. build parser against fixture
4. write parser tests
5. normalize into project records
6. only then call live API
```

Do not fabricate provider JSON fields.

## Event And Personal Cohorts

Event and personal cohorts use the same observation mechanism as baseline cohorts.

### Event

Examples:

- Lunar New Year
- Christmas
- New Year
- summer holiday
- Chuseok
- Golden Week

Purpose:

```text
understand special-period behavior
```

### Personal

Examples:

- parents visiting London
- returning to Korea
- administrative trip
- visa-related trip
- family holiday

Purpose:

```text
make the project genuinely useful while feeding the same historical data infrastructure
```

## Possible Later Expansion

After the fixed baseline is stable and quota usage is understood, possible expansions include:

- multiple monthly cohorts per route
- additional trip durations, such as 14 days
- London airport expansion to STN/LTN
- date exploration within the same fixed routes
- flexible event/personal windows, such as departure any day in Feb 1-15 with trip length 7-10 days
- additional cities

Do not implement these until the baseline collection lifecycle is reliable.

Flexible date-window search is a different data collection mode from fixed `TripCohort` tracking. It should be designed separately so it does not muddy the controlled baseline dataset.
