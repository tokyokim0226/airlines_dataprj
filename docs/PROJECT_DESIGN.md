# Project Design

## What This Project Is

This project is a cost-aware longitudinal flight-market analytics dataset and pipeline.

It is meant to collect flight prices over time in a systematic way so that route seasonality, booking lead time, directionality, and cabin-class price behavior can be analyzed from our own accumulated observations.

It is not a flight-booking website.

It is also not trying to compete with Google Flights at finding the cheapest flight today.

Google Flights tells us what is available now. This project preserves what was available at many different points in time and turns those observations into reusable historical datasets.

## Why It Exists

The project is useful because recurring travel decisions are real:

- family visiting London
- travel between Korea, the UK, Malaysia, and Japan
- holiday periods
- Lunar New Year
- Christmas
- planned return trips
- administrative travel
- family holidays

The system should eventually help answer questions such as:

- When is it cheapest to travel on a route?
- How far in advance is it usually cheapest to book?
- Is booking 3 months ahead better than 1 month ahead?
- Is booking 6 months ahead better or worse than 3 months ahead?
- How much do prices rise inside the final 4 / 3 / 2 / 1 weeks?
- Which months are expensive?
- Which months are cheap?
- Does booking behavior differ between routes?
- Does London -> Seoul behave differently from Seoul -> London?
- How much more expensive are holiday periods such as Lunar New Year or Christmas?
- If travel dates are fixed, how early should tickets ideally be bought based on our own historical data?

The value comes from systematic accumulation, not one-time search results.

## Current Product Definition

For now, the project is:

```text
A cost-aware longitudinal flight-market data pipeline that systematically samples
twelve directional routes between Seoul, London, Kuala Lumpur and Tokyo at fixed
travel cohorts and predefined booking lead times, preserving historical fare
observations so seasonality, route behavior, cabin-class differences, and
booking-window patterns can be analyzed over time.
```

The immediate objective is:

```text
build a reliable controlled dataset
```

Once that exists, event cohorts, personal cohorts, date exploration, and additional destinations can be added deliberately rather than speculatively.

## Longitudinal Observations

A normal flight search is a snapshot:

```text
What does this trip cost right now?
```

This project turns repeated snapshots into a panel-like historical dataset:

```text
What did this same trip cost at 180, 120, 90, 60, 28, 21, 14, and 7 days before departure?
```

That lets us later analyze price curves as departure approaches.

Example cohort:

```text
Route: Seoul -> London
Departure: 2027-02-10
Return: 2027-02-17
Trip duration: 7 days
Cohort type: baseline
```

Possible accumulated observations:

```text
days_before_departure    cheapest_observed_price
180                      520
120                      490
90                       462
60                       441
28                       476
21                       495
14                       550
7                        640
```

These observations are never overwritten.

## Cohort Concepts

### Baseline Cohorts

Baseline cohorts are systematically generated.

They support:

- general seasonality
- route comparison
- booking-window analysis
- cabin-class comparison over consistent trip definitions

For the controlled baseline, Phase 1 uses 7-day round trips.

### Event Cohorts

Event cohorts represent meaningful recurring periods, such as:

- Lunar New Year
- Christmas
- New Year
- summer holiday
- Chuseok
- Golden Week

They answer questions such as:

- How much more expensive is Lunar New Year than a normal February baseline?
- How early should London -> Seoul tickets be bought for Lunar New Year?
- Does the Christmas premium appear 2 months ahead or only near departure?

After multiple years, repeated event cohorts become especially useful.

### Personal Cohorts

Personal cohorts represent real trips someone is considering:

- parents visiting London
- returning to Korea
- administrative trip
- visa-related trip
- family holiday

They make the project practically useful while feeding the same historical data infrastructure.

## Economy And Business Class

The project must support both economy and business class.

Business-class pricing is personally relevant for older family members and also creates an important analytical dimension.

A `TripCohort` represents route and travel dates. Searches and observations must preserve requested cabin class as `travel_class`.

Economy and business observations must never be aggregated together accidentally.

## Future Extension: Date Exploration

Date exploration may be added later.

Example future question:

```text
My parents can travel anytime in May. Which week currently looks cheapest?
```

That is different from baseline collection.

Do not implement this until fixed baseline collection is stable and actual quota usage is understood.

The controlled baseline remains unchanged even after exploration is added.

## Major Design Rationale

The project should avoid adding technology for appearance.

First priority:

```text
trustworthy, automated longitudinal data collection
```

Only after that should the project grow toward dbt, marts, dashboards, or broader exploration.

The first meaningful milestone is one cohort moving through the entire lifecycle:

```text
route -> cohort -> scheduled checkpoint -> provider request -> raw storage -> normalized observations -> quota update
```
