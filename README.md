# Lumix dMRV Engine

Digital MRV (Measurement, Reporting, and Verification) engine for carbon credits.

## Overview

This backend system ingests solar inverter kWh data, verifies it against NASA POWER satellite irradiance data, calculates daily avoided CO2 emissions, detects fraud, and exposes all data via async FastAPI endpoints.

## Carbon Credit Logic

- **1 Carbon Credit = 1 metric tonne CO2**
- **Nigeria baseline**: petrol/diesel generators
- **Emission factor**: 1.2 kg CO2 per 1 kWh
- **CO2 avoided (tonnes)**: `(kWh * 1.2) / 1000`

## Verification Logic

The system cross-references inverter production with NASA POWER API data:

1. Fetches satellite irradiance data (`ALLSKY_SFC_SW_DWN`) for inverter GPS location
2. Calculates maximum theoretical solar output based on irradiance and inverter capacity
3. Compares inverter output curve vs satellite-derived theoretical curve
4. Calculates correlation coefficient
5. **Verification criteria**:
   - If correlation > 90% and no fraud detected → **VERIFIED**
   - If inverter output > theoretical output → **FLAGGED**
   - Otherwise → **PENDING**

## Credit Status Lifecycle

- `PENDING`: Initial state, awaiting verification
- `VERIFIED`: Correlation > 90% and no fraud detected
- `FLAGGED`: Fraud detected (output exceeds theoretical maximum)
- `SUBMITTED`: Logical state (no real registry integration)

## Tech Stack

- Python 3.11+
- `uv` for dependency management
- FastAPI (async only)
- SQLModel (async) with SQLite
- aiosqlite driver
- httpx (async HTTP calls)
- python-dotenv

## Setup

1. Install dependencies:
```bash
uv sync
```

2. Create `.env` file (see `.env.example` or use the provided `.env`)

3. Run the application:
```bash
uv run uvicorn app.main:app --reload
```

4. Access API docs at: http://localhost:8000/docs

## Optional: Seed Data

```bash
uv run python app/db/seed.py
```

## API Endpoints

### Health
- `GET /health` - Health check
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe

### Inverters
- `POST /inverters` - Create inverter
- `GET /inverters/{inverter_id}` - Get inverter
- `POST /inverters/{inverter_id}/readings` - Ingest readings (JSON/CSV)
- `GET /inverters/{inverter_id}/readings` - Get readings

### Credits
- `POST /credits/calculate` - Calculate daily CO2 avoided
- `GET /credits/{inverter_id}/{date}` - Get credit
- `GET /credits/{inverter_id}` - Get all credits for inverter
- `POST /credits/{inverter_id}/{date}/verify` - Verify credit
- `PATCH /credits/{inverter_id}/{date}/status` - Update credit status

### Reports
- `GET /reports/fleet/summary` - Fleet-level aggregation
- `GET /reports/inverters/{inverter_id}/audit` - Single-inverter auditor view
- `GET /reports/credits?status={status}` - Get credits by status

## Example Request/Response

### Create Inverter
```json
POST /inverters
{
  "gps_lat": 6.5244,
  "gps_lon": 3.3792,
  "capacity_kw": 10.0
}
```

### Ingest Readings
```json
POST /inverters/1/readings
[
  {
    "timestamp": "2025-01-15T10:00:00",
    "kwh": 5.5
  },
  {
    "timestamp": "2025-01-15T11:00:00",
    "kwh": 7.2
  }
]
```

### Calculate Credit
```
POST /credits/calculate?inverter_id=1&credit_date=2025-01-15
```

### Verify Credit
```
POST /credits/1/2025-01-15/verify
```

Response:
```json
{
  "id": 1,
  "date": "2025-01-15",
  "inverter_id": 1,
  "tonnes": 0.123,
  "status": "VERIFIED",
  "correlation": 0.95,
  "flagged_reason": null
}
```

## Project Structure

```
app/
├── main.py                 # FastAPI app with async lifespan
├── core/
│   ├── config.py          # Environment configuration
│   ├── database.py        # Async SQLModel setup
│   └── constants.py       # Emission factors, thresholds
├── models/
│   ├── inverter.py        # Inverter SQLModel table
│   ├── reading.py         # InverterReading table
│   ├── satellite.py       # SatelliteReading table
│   ├── credit.py          # CarbonCredit table
│   └── audit.py           # AuditLog table
├── handlers/
│   ├── ingestion.py       # Data ingestion logic
│   ├── carbon.py          # CO2 calculations
│   ├── nasa.py            # NASA POWER API integration
│   ├── verification.py    # Fraud detection & verification
│   └── reports.py         # Aggregation logic
├── routes/
│   ├── health.py          # Health endpoints
│   ├── inverters.py       # Inverter endpoints
│   ├── credits.py         # Credit endpoints
│   └── reports.py         # Report endpoints
├── utils/
│   ├── hashing.py         # Audit trail hashing
│   └── time.py            # Time utilities
└── db/
    └── seed.py            # Optional dev seeding
```

## Notes

- All database access is async (SQLModel async session)
- All routes and handlers are async
- Append-only audit trail with SHA-256 hashing
- No blockchain, auth, or payment systems (per requirements)
- Designed for consumption by Streamlit dashboard

