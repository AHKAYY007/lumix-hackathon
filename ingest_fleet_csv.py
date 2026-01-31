#!/usr/bin/env python3
"""
Transform solar_fleet_data_kw.csv into readings format and ingest via API.
Handles CSV structure: Inverter_ID, Timestamp, GPS_Location, Base_kWh_Daily, Max_kW_Capacity, kW_Generated, Status
Target format: inverter_id, timestamp, kwh
"""

import csv
import requests
import sys
from pathlib import Path
from collections import defaultdict

API_BASE = "http://localhost:8000"

def transform_csv_to_readings(csv_path: str):
    """
    Parse the fleet CSV and return a generator of reading dicts per inverter.
    Groups by inverter_id and yields (inverter_id, csv_bytes_io) for upload.
    """
    inverter_files = defaultdict(list)
    inverter_gps = {}
    inverter_capacity = {}
    
    print(f"📖 Reading {csv_path}...")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, start=2):
            try:
                inverter_id = row.get('Inverter_ID', '').strip()
                timestamp = row.get('Timestamp', '').strip()
                gps = row.get('GPS_Location', '').strip()
                kwh = row.get('kW_Generated', '').strip()
                capacity = row.get('Max_kW_Capacity', '').strip()
                
                if not inverter_id or not timestamp or not kwh:
                    continue
                
                # Store GPS and capacity for later
                if gps and inverter_id not in inverter_gps:
                    parts = gps.split(',')
                    if len(parts) == 2:
                        inverter_gps[inverter_id] = (float(parts[0]), float(parts[1]))
                
                if capacity and inverter_id not in inverter_capacity:
                    inverter_capacity[inverter_id] = float(capacity)
                
                # Store reading
                inverter_files[inverter_id].append({
                    'timestamp': timestamp,
                    'kwh': float(kwh)
                })
                
            except Exception as e:
                print(f"⚠️  Skipping row {row_num}: {e}")
                continue
    
    print(f"✅ Parsed {sum(len(v) for v in inverter_files.values())} readings from {len(inverter_files)} inverters")
    
    return inverter_files, inverter_gps, inverter_capacity


def create_inverter(inverter_id: str, lat: float, lon: float, capacity: float) -> int:
    """Create inverter and return its ID."""
    try:
        response = requests.post(
            f"{API_BASE}/inverters/",
            json={
                "gps_lat": lat,
                "gps_lon": lon,
                "capacity_kw": capacity
            },
            timeout=10
        )
        response.raise_for_status()
        inverter = response.json()
        return inverter.get('id')
    except Exception as e:
        print(f"❌ Failed to create inverter {inverter_id}: {e}")
        return None


def upload_readings_csv(inverter_db_id: int, readings: list) -> bool:
    """Create CSV in memory and upload to API."""
    try:
        import io
        import csv as csv_module
        
        # Create in-memory CSV
        csv_buffer = io.StringIO()
        writer = csv_module.DictWriter(csv_buffer, fieldnames=['timestamp', 'kwh'])
        writer.writeheader()
        writer.writerows(readings)
        
        csv_content = csv_buffer.getvalue()
        csv_bytes = io.BytesIO(csv_content.encode('utf-8'))
        
        # Upload
        files = {'file': ('readings.csv', csv_bytes, 'text/csv')}
        response = requests.post(
            f"{API_BASE}/inverters/{inverter_db_id}/readings",
            files=files,
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        return len(result) > 0
    
    except Exception as e:
        print(f"❌ Failed to upload readings for inverter {inverter_db_id}: {e}")
        return False


def main():
    csv_path = Path('solar_fleet_data_kw.csv')
    
    if not csv_path.exists():
        print(f"❌ File not found: {csv_path}")
        return False
    
    print("=" * 70)
    print("🚀 LARGE CSV INGESTION TEST")
    print("=" * 70)
    print()
    
    # Parse CSV
    inverter_files, inverter_gps, inverter_capacity = transform_csv_to_readings(str(csv_path))
    print()
    
    # Check API connectivity
    print("🔗 Checking API connectivity...")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        response.raise_for_status()
        print(f"✅ API is alive at {API_BASE}")
    except Exception as e:
        print(f"❌ API not reachable at {API_BASE}: {e}")
        print("   Start the API with: uvicorn main:app --reload")
        return False
    
    print()
    
    # Create inverters and upload readings
    success_count = 0
    fail_count = 0
    
    for inverter_id, readings in sorted(inverter_files.items())[:5]:  # Test with first 5 inverters
        print(f"📡 Processing {inverter_id} ({len(readings)} readings)...")
        
        # Get GPS and capacity
        lat, lon = inverter_gps.get(inverter_id, (6.5244, 3.3792))
        capacity = inverter_capacity.get(inverter_id, 10.0)
        
        # Create inverter
        db_id = create_inverter(inverter_id, lat, lon, capacity)
        if not db_id:
            fail_count += 1
            continue
        
        # Upload readings
        if upload_readings_csv(db_id, readings):
            print(f"  ✅ Uploaded {len(readings)} readings to inverter ID {db_id}")
            success_count += 1
        else:
            print(f"  ❌ Failed to upload readings")
            fail_count += 1
    
    print()
    print("=" * 70)
    print("📊 INGESTION SUMMARY")
    print("=" * 70)
    print(f"Total unique inverters in CSV: {len(inverter_files)}")
    print(f"Successfully processed:         {success_count}")
    print(f"Failed:                         {fail_count}")
    print()
    
    if success_count > 0:
        print("✅ Large CSV ingestion test passed!")
        print()
        print("💡 Next: Check Streamlit dashboard to see uploaded data and charts")
        return True
    else:
        print("❌ No successful uploads")
        return False


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
