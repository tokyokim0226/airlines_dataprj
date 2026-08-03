# 2026-08-03: Models And Project Structure Walkthrough

## Purpose Of This Note

This note organizes what we discussed while walking through the first local flight-price tracking implementation.

The goal is not to memorize every line. The goal is to understand why the project is shaped this way, what each file is responsible for, and how `models.py` defines the core data vocabulary.

## Big Project Goal

This project is a flights-only data project for tracking flight prices over time.

It is not a flight-booking app. We are not building a UI where someone searches and buys a ticket.

The first milestone is:

```text
mock flight data
-> normalize records
-> store observations in SQLite
-> query price history
```

The most important behavior is:

```text
Collect the same route and departure date multiple times.
Store each collection as a separate historical price observation.
Query the full price history later.
```

That means old prices should not be overwritten. If we overwrite old prices, we lose the historical evidence needed for analysis.

## Naming Cleanup

The original generated package was:

```text
src/airlines/
```

That was too broad for the actual project. The project is not about airlines generally. It is specifically about tracking flight prices over time.

So the package became:

```text
src/flight_tracker/
```

That makes imports clearer:

```python
from flight_tracker.models import FlightOffer
```

## Project Setup Files

### `pyproject.toml`

`pyproject.toml` is the main project configuration file.

It controls things like:

- project name
- version
- description
- required Python version
- dependencies
- command-line script entry points
- build backend

The important parts are:

```toml
name = "flight-tracker"
requires-python = ">=3.12"
```

and:

```toml
[project.scripts]
flight-tracker = "flight_tracker.cli:main"
```

That script line means:

```text
When someone runs the `flight-tracker` command,
call the `main()` function in `src/flight_tracker/cli.py`.
```

### `.python-version`

`.python-version` tells local Python tooling which Python version to use in this repo.

It was changed to:

```text
3.12
```

because the project instructions said to use Python 3.12+, and `pyproject.toml` declares:

```toml
requires-python = ">=3.12"
```

This mattered because `uv run pytest` originally tried Python 3.10, which did not satisfy the project requirement.

### `uv.lock`

`uv.lock` records the exact dependency versions that `uv` resolved.

Mental model:

```text
pyproject.toml = what versions are allowed
uv.lock = the exact versions selected
```

For example:

```text
pyproject.toml might say pytest >= 8.0.0
uv.lock records the exact pytest version actually installed
```

### `pytest` And `ruff`

`pytest` checks behavior by running tests.

```bash
uv run pytest
```

`ruff` checks code quality and lint issues.

```bash
uv run ruff check .
```

Short version:

```text
pytest = behavior checker
ruff = code cleanliness checker
```

## File Structure And Dependencies

The main Python files are:

```text
src/flight_tracker/
├── __init__.py
├── models.py
├── mock_provider.py
├── database.py
├── collector.py
├── analysis.py
└── cli.py
```

The dependency direction is:

```text
models.py
  used by mock_provider.py
  used by database.py
  used by collector.py
  used by analysis.py

mock_provider.py
  creates fake FlightOffer objects

database.py
  stores and reads SearchRun and PriceObservation objects

collector.py
  coordinates provider -> models -> database

analysis.py
  exposes query functions for stored history

cli.py
  wires everything together for terminal use
```

Runtime flow:

```text
User runs CLI
    ↓
cli.py creates database + mock provider
    ↓
cli.py calls collect_prices()
    ↓
collector.py creates a SearchRun
    ↓
collector.py asks mock_provider.py for FlightOffer objects
    ↓
collector.py turns each offer into a PriceObservation
    ↓
database.py inserts observations into SQLite
    ↓
analysis.py queries price history
    ↓
cli.py prints results
```

## Why Split The Files This Way?

We split files by responsibility so the project stays understandable as it grows.

If everything lived in one file, these concerns would be mixed together:

- validation
- fake data generation
- SQL storage
- collection workflow
- analysis queries
- terminal argument parsing

The current structure follows the project rule:

```text
Keep I/O, storage, transformation, and analysis logic separate.
```

## `models.py`: Main Purpose

`models.py` defines the core data shapes and validation rules.

It answers:

```text
What does a flight offer look like?
What does one search attempt look like?
What does one historical price observation look like?
What data is invalid?
```

It does not:

- call real APIs
- save to SQLite
- run the whole pipeline
- print CLI output

## `from __future__ import annotations`

This line:

```python
from __future__ import annotations
```

is not a file or folder. It is a special Python import.

It makes Python handle type hints more flexibly by delaying when annotations are evaluated.

Beginner mental model:

```text
It makes type hints easier and safer to use, especially as code grows.
```

You do not need to worry deeply about it right now.

## Dataclasses

This import:

```python
from dataclasses import dataclass
```

lets us write classes that mostly store data without manually writing repetitive setup code.

Without a dataclass, we would need to write something like:

```python
class FlightOffer:
    def __init__(self, origin, destination, departure_time):
        self.origin = origin
        self.destination = destination
        self.departure_time = departure_time
```

With a dataclass, we can write:

```python
@dataclass(frozen=True)
class FlightOffer:
    origin: str
    destination: str
    departure_time: datetime
```

Python automatically creates the initializer for us.

## Why Helper Function Names Start With `_`

Functions like:

```python
_validate_airport_code(...)
_validate_aware_datetime(...)
_validate_currency(...)
```

start with `_` by convention.

That means:

```text
This is an internal helper for this file.
It is not meant to be the public feature people use directly.
```

The public concepts are:

```python
FlightOffer
SearchRun
PriceObservation
```

## Airport Code Validation

The airport validator checks:

```python
len(value) != 3 or not value.isalpha() or not value.isupper()
```

This means airport codes must be:

- exactly 3 characters
- only letters
- uppercase

Why use both `isalpha()` and `isupper()`?

Because `isupper()` alone is not enough.

Example:

```python
"A1B".isupper()
```

can be true because the letters are uppercase and the number is not lowercase.

But `A1B` is not a valid airport code.

So:

```text
isalpha() rejects numbers/symbols
isupper() rejects lowercase letters
```

## `__post_init__`

Dataclasses automatically create `__init__`.

If a dataclass defines:

```python
def __post_init__(self) -> None:
```

Python runs it immediately after the object is created.

That gives us a clean place to validate fields.

Flow:

```text
Create dataclass object
Set its fields
Run __post_init__
Raise ValueError if data is invalid
```

Small spelling note:

```text
Correct: __post_init__
Not: __post__init
```

## `frozen=True`

This:

```python
@dataclass(frozen=True)
```

means the object cannot be changed after it is created.

Example:

```python
offer.price_amount = Decimal("100.00")
```

would fail.

Why use it here?

Because these objects represent facts or snapshots. If a price changes later, we should create a new `PriceObservation`, not mutate the old one.

That supports the historical tracking rule:

```text
Append new observations. Do not overwrite old observations.
```

## Why Use `Decimal`

`Decimal` comes from Python's standard library:

```python
from decimal import Decimal
```

It is not an extra installed package.

We use it for money because normal floating point numbers can create tiny precision errors.

Example idea:

```text
0.1 + 0.2 can become 0.30000000000000004
```

That kind of behavior is not good for money.

Mental model:

```text
float = good for approximate measurements
Decimal = better for exact money-like values
```

## The Three Data Classes

### `FlightOffer`

`FlightOffer` represents one flight or itinerary returned by a provider.

It includes:

- `origin`
- `destination`
- `departure_time`
- `arrival_time`
- `price_amount`
- `currency`
- `airline`
- `stops`
- `provider`

Example meaning:

```text
Mock Air has a nonstop LAX -> JFK flight
departing at 2026-08-01 09:00 UTC
arriving later
priced at 250.00 USD
from the mock provider
```

This answers:

```text
What flight did we find?
```

### `SearchRun`

`SearchRun` represents one attempt to search a route and departure date.

It includes:

- `origin`
- `destination`
- `departure_date`
- `provider`
- `started_at`
- optional database `id`

Example meaning:

```text
On 2026-07-01 at 10:00 UTC,
we searched LAX -> JFK
for departure date 2026-08-01
using the mock provider.
```

This answers:

```text
When did we search, what did we search for, and which provider did we use?
```

Important: a search run can exist even if no offers are found. That may matter later because "we searched and got no results" is still useful information.

### `PriceObservation`

`PriceObservation` represents the price seen at one specific observation time.

It includes:

- `offer`
- `observed_at`
- optional `search_run_id`
- optional database `id`

Example meaning:

```text
At 2026-07-01 10:00 UTC,
we saw this LAX -> JFK offer at 250.00 USD.
```

This answers:

```text
What price did we observe, and when?
```

This is the central object for historical price tracking.

## Is `FlightOffer` Temporary?

The exact fields may change later, but the concept is not temporary.

Later, real provider data might come from something like SerpAPI / Google Flights.

That raw provider data may be messy or shaped differently:

```text
raw API response
    ↓
provider-specific parsing / normalization
    ↓
FlightOffer
```

So `FlightOffer` is the internal clean shape that the rest of the project can rely on.

If a real API gives strings, nested JSON, or provider-specific field names, we should convert those into our internal model instead of letting raw provider data leak everywhere.

## Database Tables Related To The Models

The current SQLite database creates two tables.

### `search_runs`

Stores each collection attempt.

Columns:

- `id`
- `origin`
- `destination`
- `departure_date`
- `provider`
- `started_at`

This maps closely to the `SearchRun` dataclass.

### `price_observations`

Stores each historical price observation.

Columns:

- `id`
- `search_run_id`
- `origin`
- `destination`
- `departure_time`
- `arrival_time`
- `observed_at`
- `price_amount`
- `currency`
- `airline`
- `stops`
- `provider`

This maps to `PriceObservation` plus the fields inside its nested `FlightOffer`.

### Relationship

The relationship is:

```text
One SearchRun can have many PriceObservations.
```

In database terms:

```text
price_observations.search_run_id -> search_runs.id
```

In plain English:

```text
One search attempt may produce zero, one, or many prices.
Each observed price belongs to the search attempt that found it.
```

## Why This Matters

The project is about useful future analysis.

To analyze prices over time, the project needs clean historical data:

- clean route fields
- valid dates and times
- precise money values
- provider information
- separate collection attempts
- separate price observations

`models.py` protects the rest of the project from bad or unclear data.

If bad data gets into the database, future analysis becomes unreliable.

## Summary

- `models.py` defines the project's core vocabulary.
- `FlightOffer` is the flight or itinerary found.
- `SearchRun` is one collection attempt.
- `PriceObservation` is the price seen at a specific time.
- `__future__ import annotations` helps Python handle type hints flexibly.
- `dataclass` reduces repetitive class setup code.
- `__post_init__` runs validation after dataclass creation.
- `_helper_name` means the function is intended for internal use.
- `isalpha()` and `isupper()` are both needed for strict airport-code validation.
- `frozen=True` prevents accidental mutation of snapshot-like data.
- `Decimal` is used because money should not be represented with imprecise floats.
- The database currently has `search_runs` and `price_observations`.
- The core relationship is: one search run can produce many price observations.
- The design supports historical analysis by appending new observations instead of overwriting old ones.
