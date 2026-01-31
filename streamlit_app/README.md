# Lumix dMRV Engine - Streamlit Dashboard

A modern web-based dashboard for managing solar inverters and verifying carbon credits.

## Features

- 📊 **Dashboard**: Real-time fleet metrics and CO2 tracking
- ☀️ **Inverter Management**: Create and monitor solar inverters
- 🌱 **Carbon Credits**: Record and manage carbon credit verification
- 🔍 **Health Monitoring**: API health checks and diagnostics

## Installation

From the root directory:

```bash
pip install -r requirements.txt
```

## Running the App

From the `streamlit_app` directory:

```bash
streamlit run main.py
```

Or from the root directory:

```bash
streamlit run streamlit_app/main.py
```

The app will be available at `http://localhost:8501`

## Configuration

The API URL can be configured via the sidebar in the app. Default is `http://localhost:8000`

## API Requirements

Ensure the Lumix dMRV API is running from the root directory:

```bash
uvicorn main:app --reload
```

## Project Structure

```
streamlit_app/
├── main.py                  # Main Streamlit application
├── .streamlit/
│   └── config.toml         # Streamlit configuration
└── README.md               # This file
```

## Features Breakdown

### Dashboard Tab
- Fleet-wide statistics (inverters, credits, CO2)
- Status breakdown charts
- Real-time health monitoring

### Inverters Tab
- List all registered inverters
- Create new inverters with GPS coordinates and capacity
- View inverter details

### Credits Tab
- View and filter carbon credits by status
- Record new carbon credit entries
- Track correlation and verification status
- Monitor flagged credits

### Health Tab
- API connection testing
- Available endpoints reference
- Health status information
