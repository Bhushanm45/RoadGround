# RoadGuard AI - Data Collection & Labeling Guide

## 1. Safety Principles (Crucial)

> [!CAUTION]
> **Never deliberately drive at high speed into dangerous potholes or hazards.**
> Field testing must be performed by a designated passenger while the driver focuses 100% on vehicle safety and traffic laws.

1. **Two-Person Protocol:**
   - **Driver:** Operates the vehicle normally adhering to city speed limits and safe driving habits.
   - **Observer/Passenger:** Operates the laptop or labeling tool, tagging road hazards as they occur.
2. **Mounting:**
   - Ensure the ESP32 + MPU6050 enclosure is firmly clamped or bolted to the vehicle body (e.g., floorboard, passenger seat rail, or test rig).
   - Loose sensors will flap and generate spurious high-frequency noise that degrades model accuracy.

---

## 2. Standard CSV Telemetry Schema

Every recorded CSV row adheres to the following specification:

| Column Name | Data Type | Units / Range | Description |
|---|---|---|---|
| `timestamp_ms` | Integer | Milliseconds | Monotonic hardware timestamp from ESP32 `millis()` |
| `ax` | Float | g (±8g) | Lateral acceleration (left/right tilt & turning force) |
| `ay` | Float | g (±8g) | Longitudinal acceleration (braking/acceleration) |
| `az` | Float | g (±8g) | Vertical acceleration (baseline ~1.0g under gravity) |
| `gx` | Float | deg/s (±500) | Angular rate around X-axis (Roll) |
| `gy` | Float | deg/s (±500) | Angular rate around Y-axis (Pitch) |
| `gz` | Float | deg/s (±500) | Angular rate around Z-axis (Yaw) |
| `lat` | Float | Decimal degrees | GPS Latitude from NEO-6M (e.g. 18.520432) |
| `lon` | Float | Decimal degrees | GPS Longitude from NEO-6M (e.g. 73.856743) |
| `gps_valid` | Integer | 0 or 1 | 1 if GPS has a 2D/3D satellite fix, 0 otherwise |
| `ride_id` | String | Identifier | Unique ride/session ID (e.g., `RIDE_20261019_01`) |
| `label` | String | Class label | Ground truth: `POTHOLE`, `SPEED_BREAKER`, `ROUGH_ROAD`, `NORMAL_ROAD` |
| `data_source` | String | Origin | `HARDWARE_MPU6050_NEO6M` or `SYNTHETIC_SIMULATION_DEMO` |

---

## 3. Labeling Definitions & Criteria

1. **`NORMAL_ROAD`:**
   - Smooth asphalt or concrete paving.
   - Vertical acceleration remains tightly bounded between 0.92g and 1.08g.
   - Standard deviation $\sigma < 0.08g$.
2. **`POTHOLE`:**
   - Distinct road cavity or missing asphalt patch.
   - Manifests as an initial negative dip ($a_z < 0.2g$ or negative) as the tire drops into the void, followed by an immediate sharp rebound impact ($a_z > 2.0g$).
   - Waveform duration: typically 150–250 ms.
3. **`SPEED_BREAKER`:**
   - Intentional speed bump or raised traffic calming hump.
   - Smooth, low-frequency upward sinusoidal surge ($a_z \approx 1.5g - 2.2g$) lasting 500–900 ms, followed by return to baseline.
   - Does not have sharp high-frequency kurtosis chatter.
4. **`ROUGH_ROAD`:**
   - Cobblestones, deteriorated gravel, paver blocks, or aged bitumen with continuous micro-cracks.
   - Continuous vibration chatter ($\pm 0.35g$ to $\pm 0.6g$ around 1.0g) spanning several consecutive seconds without a single high-energy isolated spike.

---

## 4. Collecting Real Field Data

To log real data over USB from the ESP32:
```bash
python ml/collect_data.py --port COM3 --baud 115200 --ride-id RIDE_PUNE_FC_ROAD_01
```
Use keyboard shortcuts `[p]`, `[b]`, `[r]`, `[n]` to mark ground truth as your vehicle passes road features.
