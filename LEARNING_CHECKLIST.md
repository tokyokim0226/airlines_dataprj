# Flight Tracker Learning Checklist

Use this as a running map while walking through the first implementation.

## 1. Problem And Goal

- [x] Explain why the original `airlines` package name was a mismatch.
- [x] Explain why this project is a data pipeline, not a booking app.
- [x] Explain the first end-to-end behavior we needed to prove.

## 2. Project Setup

- [x] Explain what `pyproject.toml` controls.
- [x] Explain why `.python-version` was changed to Python 3.12.
- [x] Explain what `uv.lock` is for.
- [x] Explain why `pytest` and `ruff` were added as development dependencies.

## 3. Code Structure

- [ ] Explain the role of `models.py`.
- [ ] Explain the role of `mock_provider.py`.
- [ ] Explain the role of `database.py`.
- [ ] Explain the role of `collector.py`.
- [ ] Explain the role of `analysis.py`.
- [ ] Explain the role of `cli.py`.

## 4. Data Model And Rules

- [ ] Explain the difference between `FlightOffer`, `SearchRun`, and `PriceObservation`.
- [x] Explain why price observations should never overwrite older observations.
- [ ] Explain why `Decimal` is used for prices.
- [ ] Explain why datetimes should be timezone-aware.
- [ ] Explain the validation rules for airport codes, route, price, and flight times.

## 5. Storage And Flow

- [ ] Trace what happens when `collect_prices(...)` runs.
- [ ] Explain how SQLite stores separate historical observations.
- [ ] Explain how price history is queried chronologically.
- [ ] Explain what happens if the provider returns no offers.

## 6. Tests And Verification

- [ ] Explain what each test file covers.
- [ ] Explain how the repeated-collection test proves old prices are not overwritten.
- [ ] Explain what `uv run pytest` did.
- [ ] Explain what `uv run ruff check .` did.

## 7. Broader Context

- [ ] Explain why this minimal local pipeline comes before real APIs.
- [ ] Explain what future features this foundation can support.
- [ ] Identify one thing we intentionally did not add yet and why.
