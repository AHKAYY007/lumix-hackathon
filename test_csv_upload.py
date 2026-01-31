#!/usr/bin/env python3
"""
Test script for CSV upload endpoint
"""

import requests
import sys

API_BASE = "http://localhost:8000"

def test_csv_upload():
    """Test the CSV upload endpoint"""
    
    # First, create an inverter
    print("📡 Creating test inverter...")
    response = requests.post(
        f"{API_BASE}/inverters/",
        json={
            "gps_lat": 6.5244,
            "gps_lon": 3.3792,
            "capacity_kw": 10.0
        }
    )
    
    if response.status_code != 201:
        print(f"❌ Failed to create inverter: {response.text}")
        return False
    
    inverter = response.json()
    inverter_id = inverter.get("id")
    print(f"✅ Inverter created with ID: {inverter_id}")
    
    # Upload CSV readings
    print(f"\n📤 Uploading CSV readings for inverter {inverter_id}...")
    
    with open("sample_readings.csv", "rb") as f:
        files = {"file": (f.name, f, "text/csv")}
        response = requests.post(
            f"{API_BASE}/inverters/{inverter_id}/readings",
            files=files
        )
    
    if response.status_code != 200:
        print(f"❌ Failed to upload readings: {response.text}")
        return False
    
    readings = response.json()
    print(f"✅ Successfully uploaded {len(readings)} readings")
    
    # Display the uploaded readings
    print("\n📊 Uploaded readings:")
    for i, reading in enumerate(readings, 1):
        ts = reading.get("timestamp", "")[:19]
        kwh = reading.get("kwh", 0)
        co2 = reading.get("co2_kg", 0) / 1000
        print(f"  {i}. {ts} | {kwh:.2f} kWh | {co2:.4f} tonnes CO2")
    
    return True

if __name__ == "__main__":
    try:
        success = test_csv_upload()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
