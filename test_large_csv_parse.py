#!/usr/bin/env python3
"""
Dry-run test: Parse large CSV, validate structure, test streaming batching.
No database or API required.
"""

import csv
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import time

def parse_large_csv(filepath: str, batch_size: int = 1000):
    """
    Stream-parse CSV file in batches.
    Yields batches of validated reading dicts.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        batch = []
        
        for row_num, row in enumerate(reader, start=2):
            if not row:
                continue
            
            # Parse and validate row
            try:
                inverter_id = row.get('Inverter_ID', '').strip()
                timestamp_str = row.get('Timestamp', '').strip()
                gps_str = row.get('GPS_Location', '').strip()
                kwh_str = row.get('kW_Generated', '').strip()
                
                if not inverter_id or not timestamp_str or not kwh_str:
                    print(f"⚠️  Skipping row {row_num}: missing required fields")
                    continue
                
                # Validate timestamp format
                try:
                    ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except ValueError:
                    raise ValueError(f"Invalid timestamp: {timestamp_str}")
                
                # Parse kWh
                kwh = float(kwh_str)
                
                # Parse GPS (format: "lat,lon")
                if gps_str:
                    gps_parts = gps_str.split(',')
                    if len(gps_parts) == 2:
                        lat, lon = float(gps_parts[0]), float(gps_parts[1])
                    else:
                        lat, lon = 0.0, 0.0
                else:
                    lat, lon = 0.0, 0.0
                
                batch.append({
                    'inverter_id': inverter_id,
                    'timestamp': ts,
                    'lat': lat,
                    'lon': lon,
                    'kwh': kwh,
                    'row_num': row_num
                })
                
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
            
            except Exception as e:
                print(f"❌ Error parsing row {row_num}: {e}")
                continue
        
        # Yield remaining
        if batch:
            yield batch


def run_test():
    csv_path = Path('solar_fleet_data_kw.csv')
    
    if not csv_path.exists():
        print(f"❌ File not found: {csv_path}")
        return False
    
    print(f"📂 Parsing {csv_path} ({csv_path.stat().st_size / (1024*1024):.2f} MB)...")
    print()
    
    start_time = time.time()
    total_rows = 0
    total_batches = 0
    inverters_seen = set()
    daily_totals = defaultdict(float)
    error_rows = 0
    
    try:
        for batch_num, batch in enumerate(parse_large_csv(csv_path, batch_size=5000), 1):
            total_rows += len(batch)
            total_batches += 1
            
            # Track stats
            for row in batch:
                inverters_seen.add(row['inverter_id'])
                ts_date = row['timestamp'].date()
                daily_totals[ts_date] += row['kwh']
            
            if batch_num % 10 == 0 or batch_num == 1:
                elapsed = time.time() - start_time
                rate = total_rows / elapsed if elapsed > 0 else 0
                print(f"✅ Batch {batch_num}: {len(batch)} rows | "
                      f"Total: {total_rows:,} rows | "
                      f"Rate: {rate:.0f} rows/sec | "
                      f"Unique inverters: {len(inverters_seen)}")
    
    except Exception as e:
        print(f"❌ Parse error: {e}")
        return False
    
    elapsed = time.time() - start_time
    
    print()
    print("=" * 70)
    print("📊 PARSING SUMMARY")
    print("=" * 70)
    print(f"Total rows parsed:        {total_rows:,}")
    print(f"Total batches:            {total_batches}")
    print(f"Unique inverters:         {len(inverters_seen)}")
    print(f"Date range:               {min(daily_totals.keys())} to {max(daily_totals.keys())}")
    print(f"Total kWh generated:      {sum(daily_totals.values()):.2f}")
    print(f"Parse time:               {elapsed:.2f}s")
    print(f"Throughput:               {total_rows / elapsed:.0f} rows/sec")
    print()
    
    # Sample inverters
    sample_inverters = sorted(list(inverters_seen))[:5]
    print(f"Sample inverters: {', '.join(sample_inverters)}")
    print()
    
    # Daily stats (first 5 days)
    sorted_dates = sorted(daily_totals.keys())
    print("Daily kWh totals (first 5 days):")
    for date in sorted_dates[:5]:
        total_kwh = daily_totals[date]
        co2_tonnes = (total_kwh * 1.2) / 1000
        print(f"  {date}: {total_kwh:>10.2f} kWh | {co2_tonnes:>8.4f} tonnes CO2")
    
    print()
    print("✅ CSV parsing test completed successfully!")
    print()
    print("💡 Next steps:")
    print("   1. Start the API: uvicorn main:app --reload")
    print("   2. Create inverter records for each unique inverter_id")
    print("   3. Upload this CSV file via the Streamlit dashboard or API")
    print("   4. Monitor database and verify readings ingestion")
    
    return True


if __name__ == '__main__':
    try:
        success = run_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
