# AGENTS.md

## Project Overview

(need shorten)

This repository contains a portfolio project for collecting, storing, and analysing flight-price data over time.

The project should demonstrate practical data engineering and analytics skills through the following pipeline:

```text
collect → normalize → store → transform → analyze → present
```

The initial goal is not to build a complete flight-booking product. It is to build a reliable, understandable flight-price data system that can later support features such as:

* analysing how prices change as departure approaches
* comparing prices across routes, dates, airlines, and seasons
* finding cheaper travel dates
* finding cheaper destinations from a selected origin
* eventually estimating whether a user should buy now or wait

This is an individual portfolio project. Prefer a small, working system over an unnecessarily complex production architecture.

---

## Core Principles

### 1. Keep the project data-focused

The main value of this repository is the data pipeline, historical dataset, analysis, and resulting insights.

Do not prioritise frontend complexity before the data pipeline works.

### 2. Remain provider-agnostic

Flight data may come from different APIs or local sample data.

Provider-specific responses must not flow directly into the rest of the application. Every provider must convert its response into the project's shared domain model before storage.

The system should be able to replace one provider without requiring major changes to the storage or analysis layers.

### 3. Build incrementally

Implement the smallest useful version first.

The preferred order is:

1. define the domain models
2. implement a mock or sample-data provider
3. collect and normalize observations
4. store observations in SQLite
5. add tests
6. add basic SQL and Python analysis
7. connect a real flight-data provider
8. add a simple dashboard or API
9. consider PostgreSQL, dbt, orchestration, or deployment later

Do not introduce infrastructure simply because it might be useful eventually.

### 4. Preserve historical observations

A flight price is an observation at a particular point in time.

Do not overwrite an older price when the same itinerary is observed again. Store the new observation with its own collection timestamp.

This historical behaviour is central to the project.

---

## Initial Scope

The first working version should support a concrete example such as:

```text
Observe flight prices for Tokyo → London once per day
and analyse how those prices change over time.
```

The first version should be able to:

* accept an origin and destination
* accept a departure date
* retrieve offers from a provider
* normalize the offers
* store the observations
* query historical prices
* calculate simple summary statistics
* run locally with clear instructions

The first version does not need:

* user accounts
* payment functionality
* flight booking
* a recommendation model
* real-time distributed processing
* microservices
* Kubernetes
* a complex frontend
* multiple databases

---

## Technology Choices

Use the following defaults unless there is a clear reason to change them:

* Python 3.12+
* SQL
* SQLite for the initial version
* `pytest` for tests
* `ruff` for formatting and linting
* `mypy` or Pyright-compatible type annotations
* `pydantic` or standard-library dataclasses for validated models

Possible later additions include:

* PostgreSQL
* dbt
* DuckDB
* FastAPI
* Prefect or another lightweight orchestrator
* Streamlit or a small web dashboard
* Docker
* GitHub Actions

Do not add these later-stage tools until the current implementation requires them.

---

## Suggested Repository Structure

```text
.
├── AGENTS.md
├── README.md
├── pyproject.toml
├── .gitignore
├── data/
│   ├── raw/
│   └── processed/
├── notebooks/
├── sql/
├── src/
│   └── flight_intel/
│       ├── __init__.py
│       ├── domain/
│       │   ├── __init__.py
│       │   └── models.py
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   └── mock.py
│       ├── ingestion/
│       │   ├── __init__.py
│       │   └── collect.py
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── database.py
│       │   └── repository.py
│       ├── analysis/
│       │   ├── __init__.py
│       │   └── price_history.py
│       └── cli.py
└── tests/
    ├── test_models.py
    ├── test_providers.py
    ├── test_ingestion.py
    └── test_storage.py
```

This structure may evolve, but changes should remain proportional to the project's size.

---

## Domain Model

Use clear shared models instead of passing unstructured dictionaries between modules.

A normalized flight-price observation should contain fields similar to:

```text
origin
destination
departure_at
arrival_at
observed_at
price_amount
price_currency
airline
flight_number
number_of_stops
duration_minutes
cabin_class
provider
provider_offer_id
```

Not every provider will return every field. Optional values should be represented explicitly rather than filled with invented data.

Important distinctions:

* `departure_at` is when the flight departs.
* `observed_at` is when the project collected the price.
* `price_amount` should use a decimal-safe representation.
* airport codes should be normalized to uppercase IATA codes.
* timestamps should be timezone-aware where possible.
* durations should use one consistent unit.
* currencies should use standard three-letter codes.

Do not perform analysis directly on raw provider payloads.

---

## Provider Interface

Every flight-data provider should implement a shared interface.

Conceptually:

```python
class FlightProvider(Protocol):
    def search(self, request: FlightSearchRequest) -> list[FlightOffer]:
        ...
```

Each provider is responsible for:

* making or simulating the external request
* validating the response
* handling provider-specific fields
* converting results into normalized domain models
* raising meaningful provider-specific errors

The rest of the application should depend on the interface, not on a concrete API.

Begin with a deterministic mock provider so that development and tests do not depend on API access.

Potential real providers may include Google Flights data through a search API or another individually accessible service. Do not tightly couple the repository to Amadeus Self-Service or Skyscanner partner access.

Never commit API keys.

---

## Storage Rules

The initial database should use SQLite.

Store observations in an append-oriented table. A repeated search should normally add new observations rather than update previous rows.

A reasonable initial schema includes:

### `flight_offers`

* internal ID
* provider name
* provider offer ID
* origin
* destination
* departure timestamp
* arrival timestamp
* airline
* flight number
* number of stops
* duration in minutes
* cabin class

### `price_observations`

* internal ID
* flight-offer reference or itinerary identifier
* observed timestamp
* price amount
* currency
* search-run reference

### `search_runs`

* internal ID
* origin
* destination
* requested departure date
* collection timestamp
* provider
* status
* number of results
* error message, when applicable

The precise schema may change as implementation reveals better boundaries.

Database migrations or schema-versioning tools are not required for the first small version, but schema creation must be repeatable.

---

## Data Quality Rules

Validate data before saving it.

At minimum:

* origin and destination must be valid-looking three-letter codes
* origin and destination must not be identical
* price must be greater than zero
* currency must be present
* departure must occur before arrival
* observation time must be present
* number of stops must not be negative
* duration must be positive when available
* duplicate records within the same provider response should be handled deliberately

Do not silently discard invalid records. Return or log enough information to understand why they failed.

Keep raw responses during early development when practical, but do not use raw data as the main analytical model.

---

## Analysis Priorities

Begin with descriptive analysis rather than machine learning.

Useful initial metrics include:

* minimum observed price by route and departure date
* average and median observed price
* daily price change
* percentage price change
* cheapest observation date
* number of days before departure
* price by booking window
* price by day of week
* price by airline
* direct versus connecting-flight price
* price volatility

Use SQL for relational aggregation where appropriate. Use Python for analysis that is difficult or unclear in SQL.

A buy-now-versus-wait recommendation should only be added after enough historical data exists to evaluate it honestly.

Do not present a heuristic as a predictive machine-learning model.

---

## Coding Standards

All production code should:

* use type annotations
* use clear names
* keep functions focused
* avoid unnecessary inheritance
* separate I/O from business logic
* avoid global mutable state
* provide useful error messages
* include docstrings where behaviour is not obvious
* use `pathlib` instead of manually constructed file paths
* use `Decimal` rather than binary floating-point values for money where practical
* use timezone-aware datetimes

Prefer readable code over clever code.

Do not create abstractions until there are at least two meaningful cases or a clear testing benefit.

---

## Testing Expectations

Tests should not depend on live external APIs.

Use fixture data and mock providers.

At minimum, test:

* domain-model validation
* provider-response normalization
* preservation of observation timestamps
* database insertion and retrieval
* repeated observations of the same itinerary
* invalid price handling
* invalid date handling
* empty provider responses
* provider errors
* basic analytical calculations

Each bug fix should include a regression test when practical.

Use temporary databases in tests rather than modifying the development database.

---

## External API Rules

API credentials must be loaded from environment variables.

Use a `.env.example` file containing variable names but no secrets.

Example:

```text
FLIGHT_API_KEY=
FLIGHT_API_BASE_URL=
```

The actual `.env` file must be excluded through `.gitignore`.

External API code should include:

* explicit timeouts
* error handling
* rate-limit awareness
* controlled retries
* response validation
* logging that does not expose secrets

Do not repeatedly call a paid API during tests or routine development when saved fixtures can be used instead.

Because API availability and pricing can change, provider configuration should be isolated and documented.

---

## Data and Git Rules

Do not commit:

* API keys
* `.env` files
* large raw datasets
* generated database files
* personal data
* cache directories
* notebook output that creates large diffs

Small sample datasets and sanitized API fixtures may be committed when they are necessary for reproducible tests or demonstrations.

Generated artifacts should be placed in clearly named directories.

---

## Documentation Expectations

The README should explain:

1. what the project does
2. why historical flight-price observations are useful
3. the current project status
4. the architecture
5. how to install dependencies
6. how to run the collector
7. how to run tests
8. how to inspect the stored data
9. current limitations
10. planned next steps

Commands in the README must be tested before being documented.

Keep the README honest. Clearly distinguish implemented features from planned features.

---

## Agent Workflow

Before making a substantial change:

1. inspect the existing repository
2. identify the smallest coherent change
3. state any important assumptions
4. preserve existing working behaviour
5. implement the change
6. add or update tests
7. run the relevant checks
8. summarize what changed

When asked to implement a feature, do not rewrite unrelated parts of the repository.

When requirements are incomplete, choose the simplest design consistent with this file and document the assumption.

Do not claim that commands or tests passed unless they were actually run.

---

## Definition of Done

A task is complete when:

* the requested behaviour is implemented
* code follows the existing structure
* relevant tests exist
* tests pass
* formatting and linting pass
* no secrets are committed
* documentation is updated when behaviour or usage changes
* the final response explains important decisions and remaining limitations

---

## Current Milestone

The current milestone is to create a minimal end-to-end local pipeline:

```text
mock provider
    ↓
normalized flight offers
    ↓
SQLite historical storage
    ↓
simple price-history query
    ↓
command-line output
```

Prioritise this milestone over dashboards, deployment, machine learning, and production infrastructure.
