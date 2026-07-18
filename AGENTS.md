# AGENTS.md

## Project

This is a flights-only data project for tracking flight prices over time.

The goal is to build a reliable data pipeline that collects flight-price observations, stores them historically, and supports analysis of price trends by route, departure date, airline, and booking window.

This is not a flight-booking app. Prioritize data collection, data quality, storage, transformation, testing, and analysis over frontend features.

## Current Milestone

Build the smallest local version first:

```text
mock flight data
→ normalize records
→ store observations in SQLite
→ query price history
```

Do not add AWS, Airflow, Spark, Kafka, dashboards, or a real API until the local pipeline works.

## Language and Environment

Use Python 3.12+.

Use `uv` for dependency management, virtual environments, and running commands.

Prefer:

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
uv run python -m flight_tracker.cli
```

Do not use raw `pip install` or manually managed virtual environments unless there is a clear reason.

Docker may be added later for reproducible local execution or service-based development. Do not introduce Docker before the local Python pipeline works.

## Initial Structure

Start simple:

```text
src/flight_tracker/
├── __init__.py
├── models.py
├── mock_provider.py
├── collector.py
├── database.py
├── analysis.py
└── cli.py

tests/
├── test_models.py
├── test_mock_provider.py
├── test_database.py
└── test_analysis.py
```

Split files into subfolders only when the code becomes large enough to justify it.

## Core Data Rules

A flight price is a historical observation.

Do not overwrite old prices. If the same route and departure date are collected again, insert a new price observation with a new `observed_at` timestamp.

Keep these concepts separate:

* `FlightOffer`: the flight or itinerary found
* `PriceObservation`: the price seen at a specific time
* `SearchRun`: one collection attempt

Important fields include:

* origin
* destination
* departure time
* arrival time
* observed time
* price amount
* currency
* airline
* number of stops
* provider

## Coding Guidelines

* Use type annotations.
* Prefer simple, readable code.
* Keep functions focused.
* Keep I/O, storage, transformation, and analysis logic separate.
* Use `Decimal` for money where practical.
* Use timezone-aware datetimes.
* Avoid unnecessary abstractions.
* Do not modify unrelated files.
* Do not create empty future-facing folders before they are needed.
* Do not claim tests passed unless they were actually run.

## Testing

Use `pytest`.

Add or update tests for meaningful behavior changes.

Important cases:

* valid flight records
* invalid airport codes
* negative or missing prices
* same origin and destination
* arrival before departure
* empty provider response
* repeated collection creates multiple observations
* price-history query returns observations in chronological order

Tests must not call live paid APIs.

## Commands

Use these commands when available:

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```

If a command is missing or fails because setup is incomplete, do not invent results. Report what happened clearly.

## Secrets and Data

Never commit:

* API keys
* `.env` files
* large raw datasets
* generated database files
* personal data
* cache directories

Use `.env.example` for required environment variable names only.

Small sample fixtures are allowed when they are useful for tests.

## Agent Workflow

Before making changes:

1. inspect the existing repository
2. identify the smallest useful change
3. implement only that change
4. add or update tests
5. run relevant checks
6. summarize what changed and what remains

Prefer a working end-to-end pipeline over adding new technologies.

## Priority

The first priority is to prove this behavior:

```text
collect the same mock route multiple times
→ store each result as a separate price observation
→ query the full price history
```

Once this works, the project can later grow into real API ingestion, raw data storage, cloud infrastructure, orchestration, and analytical reporting.
