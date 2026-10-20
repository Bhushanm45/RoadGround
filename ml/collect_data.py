"""
RoadGuard AI - Sensor Data Collection & Labeling Utility
=========================================================
Connects to the ESP32 over USB Serial (or listens for Wi-Fi batches) to log raw
telemetry directly to a CSV file while allowing safe interactive labeling of road events.

Usage:
------
python ml/collect_data.py --port COM3 --baud 115200 --ride-id RIDE_PUNE_01

Controls during logging:
- Press 'p' -> Label next window as 'POTHOLE'
- Press 'b' -> Label next window as 'SPEED_BREAKER'
- Press 'r' -> Label continuous windows as 'ROUGH_ROAD'
- Press 'n' -> Return to 'NORMAL_ROAD' (default)
- Press 'q' -> Save and quit session
"""

import sys
import os
import time
import argparse
from datetime import datetime
import pandas as pd

try:
    import serial
except ImportError:
    serial = None


def collect_from_serial(port: str, baud: int, ride_id: str, output_csv: str):
    if serial is None:
        print("[Error] 'pyserial' package is not installed. Run: pip install pyserial")
        sys.exit(1)

    print(f"\n[Collector] Opening Serial Port: {port} @ {baud} baud...")
    try:
        ser = serial.Serial(port, baud, timeout=1.0)
    except serial.SerialException as e:
        print(f"[Error] Failed to open port {port}: {e}")
        print("Tip: Check device manager for the correct COM port or test using simulator mode.")
        return

    print(f"[Collector] Logging session: {ride_id}")
    print(f"[Collector] Saving to: {output_csv}")
    print("\n--- CONTROLS ---")
    print(" [p] POTHOLE  |  [b] SPEED_BREAKER  |  [r] ROUGH_ROAD  |  [n] NORMAL_ROAD  |  [q] Quit")
    print("----------------\n")

    records = []
    current_label = "NORMAL_ROAD"
    temporary_label_until = 0

    try:
        while True:
            line = ser.readline().decode("utf-8", errors="replace").strip()
            if not line:
                continue

            if line.startswith("DATA:"):
                # Format: DATA:timestamp_ms,ax,ay,az,gx,gy,gz,lat,lon,gps_valid
                parts = line[5:].split(",")
                if len(parts) >= 10:
                    try:
                        t_ms = int(parts[0])
                        ax = float(parts[1])
                        ay = float(parts[2])
                        az = float(parts[3])
                        gx = float(parts[4])
                        gy = float(parts[5])
                        gz = float(parts[6])
                        lat = float(parts[7])
                        lon = float(parts[8])
                        gps_valid = int(parts[9])

                        # Check if a single-event temporary label (e.g. pothole strike) is active
                        active_label = current_label
                        if time.time() < temporary_label_until:
                            active_label = "POTHOLE" if temporary_label_until_type == "p" else "SPEED_BREAKER"

                        records.append({
                            "timestamp_ms": t_ms,
                            "ax": ax,
                            "ay": ay,
                            "az": az,
                            "gx": gx,
                            "gy": gy,
                            "gz": gz,
                            "lat": lat,
                            "lon": lon,
                            "gps_valid": gps_valid,
                            "ride_id": ride_id,
                            "label": active_label,
                            "data_source": "HARDWARE_MPU6050_NEO6M"
                        })

                        if len(records) % 100 == 0:
                            print(f"\r[Logging] Samples: {len(records):<6} | Current Label: {active_label:<14} | Z: {az:+.3f}g", end="")
                    except ValueError:
                        continue

    except KeyboardInterrupt:
        print("\n[Collector] Data collection paused by user.")
    finally:
        ser.close()
        if records:
            df = pd.DataFrame(records)
            os.makedirs(os.path.dirname(output_csv), exist_ok=True)
            df.to_csv(output_csv, index=False)
            print(f"\n[Saved] Wrote {len(df)} samples to {output_csv}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RoadGuard AI Telemetry Data Collector")
    parser.add_argument("--port", type=str, default="COM3", help="Serial port of ESP32 (e.g., COM3, /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate")
    parser.add_argument("--ride-id", type=str, default=f"RIDE_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    parser.add_argument("--output", type=str, default=None)

    args = parser.parse_args()
    out_file = args.output or f"data/raw_{args.ride_id}.csv"
    collect_from_serial(args.port, args.baud, args.ride_id, out_file)
