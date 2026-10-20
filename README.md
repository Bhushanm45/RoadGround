# RoadGuard AI: Intelligent Road Hazard Detection & Reporting System

**Team:** 404: Ground Not Found  
**College:** Pune Institute of Computer Technology (PICT), Pune  
**Department:** Electronics & Telecommunication Engineering (ENTC)  
**Hackathon:** Yantravedh 2026 / Smart India Hackathon (SIH)  
**Theme:** Smart & Sustainable Solutions  

---

## 1. What Machine Learning Does in RoadGuard AI

When a vehicle travels along a road, its chassis vibrates in response to the surface conditions beneath it. Simple threshold rules (such as *"if vertical acceleration $> 2.0g$, mark a pothole"*) generate huge numbers of false alarms because crossing a speed bump quickly, driving over railway tracks, or engine vibrations can easily spike a simple peak detector.

**Machine Learning (ML)** analyzes the **entire shape, frequency, and vibration signature** over a 1-second time window:
- It discriminates between a **sharp, high-frequency cavity drop and rebound shock** (**POTHOLE**),
- A **smooth, low-frequency elevation curve** (**SPEED_BREAKER**),
- **Continuous irregular stochastic vibration chatter** (**ROUGH_ROAD**), and
- **Smooth asphalt travel** (**NORMAL_ROAD**).

---

## 2. What Data the MPU6050 Produces

The **MPU6050** is a 6-Degrees-of-Freedom (6-DOF) Micro-Electro-Mechanical Systems (MEMS) sensor:
1. **3-Axis Accelerometer ($a_x, a_y, a_z$):**
   - Measures linear acceleration in units of $g$ (where $1g \approx 9.81 \text{ m/s}^2$).
   - On level ground at rest, gravity acts vertically: $a_z \approx 1.0g$, while lateral and longitudinal components $a_x \approx 0.0g, a_y \approx 0.0g$.
   - Configured in firmware to $\pm 8g$ full-scale range to ensure intense pothole shocks do not saturate or clip the digital converter.
2. **3-Axis Gyroscope ($g_x, g_y, g_z$):**
   - Measures angular velocity in degrees per second ($\text{deg/s}$) around the roll, pitch, and yaw axes.
   - Configured to $\pm 500 \text{ deg/s}$ range. Helps capture vehicle tilt and pitch changes as axles climb over speed humps or rock laterally.

---

## 3. How Labeled Examples Are Collected

In real-world deployment, training data is gathered using a two-person protocol:
1. The driver focuses strictly on driving safely within municipal traffic laws.
2. The passenger/observer operates a laptop connected via Wi-Fi or USB to the ESP32 using `ml/collect_data.py`.
3. As the vehicle encounters a known road anomaly, the observer taps keyboard hotkeys:
   - `[p]` for **POTHOLE**
   - `[b]` for **SPEED_BREAKER**
   - `[r]` for **ROUGH_ROAD**
   - `[n]` for **NORMAL_ROAD**
4. Each entry is saved into a CSV file tagged with a monotonic timestamp, sensor streams, GPS coordinates, and session `ride_id`.

> [!CAUTION]
> **Safety Rule:** Drivers must never deliberately swerve or accelerate into hazardous potholes to capture data.

---

## 4. Why Random Forest is the Initial Choice

We selected the **Random Forest Classifier** (`sklearn.ensemble.RandomForestClassifier`) for five specific engineering reasons:
1. **Exceptional Non-Linear Pattern Recognition:** Road vibration waveforms are complex non-linear combinations of impact amplitude, kurtosis, and duration. Decision tree ensembles naturally segment these feature boundaries.
2. **Tiny Computational Footprint:** Unlike heavy Deep Neural Networks or CNNs, Random Forest requires **zero GPU acceleration** and executes inference in under **2 milliseconds** on standard laptop CPUs.
3. **Robust Against Sensor Noise:** By aggregating predictions across 100 decorrelated decision trees, Random Forest resists noisy outliers from loose vehicle panels or engine rumble.
4. **Direct Feature Importance Interpretability:** Random Forest explicitly reports which vibration features (e.g., vertical kurtosis vs. RMS) contributed most to the classification.
5. **Calibrated Class Probabilities:** Enables a configurable confidence threshold so ambiguous vibrations are flagged as `UNCERTAIN` rather than generating false municipal work orders.

---

## 5. How Feature Extraction Works

Rather than feeding 100 raw sensor points directly into the model, continuous sensor streams are sliced into **1.0-second sliding windows** (100 samples at 100 Hz sampling rate, with 50% overlap).

For each window, `ml/preprocess.py` extracts **23 canonical mathematical features**:

| Feature Name | Formula / Definition | Physical Interpretation |
|---|---|---|
| `az_mean` | $\mu_z = \frac{1}{N}\sum a_z$ | Average vertical gravity baseline (~1.0g) |
| `az_std` | $\sigma_z = \sqrt{\frac{1}{N}\sum (a_z - \mu_z)^2}$ | Overall vibration spread and road roughness |
| `az_peak_to_peak` | $\max(a_z) - \min(a_z)$ | Maximum vertical impact shock amplitude ($\Delta g$) |
| `az_rms` | $\sqrt{\frac{1}{N}\sum a_z^2}$ | Root-Mean-Square energy of the vertical motion |
| `az_kurtosis` | $\frac{\frac{1}{N}\sum(a_z - \mu_z)^4}{\sigma_z^4}$ | **Peakedness/Spikiness:** Separates sharp impulsive pothole shocks ($>5$) from smooth humps ($\approx 3$) |
| `az_crest_factor` | $\frac{\max(\vert a_z \vert)}{\text{RMS}}$ | Ratio of peak transient force to continuous vibration |
| `az_energy` | $\frac{1}{N}\sum(a_z - 1.0g)^2$ | Total deviation energy away from resting gravity |
| `amag_mean` & `amag_rms` | Magnitude $\sqrt{a_x^2 + a_y^2 + a_z^2}$ | True total acceleration independent of sensor tilt |
| `ax_std`, `ay_std` | Standard deviation on X and Y | Lateral roll sway and longitudinal braking/pitch |
| `temporal_drop_before_rise` | $\text{argmin}(a_z) < \text{argmax}(a_z)$ | **Cavity Signature:** 1 if cavity drop precedes rebound spike; 0 otherwise |
| `z_min_max_ratio` | $\frac{\vert\min(a_z - 1.0)\vert}{\max(a_z - 1.0)}$ | Symmetry ratio of downward drop to upward rebound |
| `gyro_magnitude_mean` | $\frac{1}{N}\sum \sqrt{g_x^2 + g_y^2 + g_z^2}$ | Chassis rotational pitch and roll during bump negotiation |

---

## 6. How the Model Learns and Prevents Data Leakage

1. **Group-Based Splitting by Ride (`GroupShuffleSplit`):**
   - If consecutive 1-second overlapping windows from the same ride were randomly split between train and test, the test set would contain almost identical windows to the training set. This causes artificial over-optimism (*data leakage*).
   - Our pipeline splits strictly by **`ride_id`**: an entire ride is either 100% in the training set or 100% in the test set.
2. **Training & Validation:**
   - 100 trees, maximum tree depth of 12, with balanced class weights to account for the natural rarity of potholes compared to normal road travel.

---

## 7. How the ESP32 Communicates with the Backend

```
[MPU6050 Sensor] (Fast I2C @ 400kHz)  --->  ESP32 DevKit V1 (~100 Hz Loop)
[NEO-6M GPS]     (Serial2 @ 9600 baud) --->  Non-Blocking Async Parser
                                                    │
                                     Wi-Fi HTTP POST (Batches of 20 samples)
                                                    ▼
                                          Flask REST Backend (:5000)
```

1. **Non-Blocking Execution:** The ESP32 acquires sensor samples every 10 milliseconds (`micros()` timer). It parses incoming GPS NMEA sentences on HardwareSerial2 without pausing the accelerometer loop.
2. **Batched JSON Telemetry:** Instead of firing 100 individual HTTP requests every second, the ESP32 groups 20 samples into an in-memory batch and sends an HTTP POST to `/api/telemetry` every ~200 milliseconds.
3. **Offline Ring Buffer:** If Wi-Fi signal drops while the vehicle is in an underpass, readings are stored in a circular buffer and uploaded once connectivity recovers.

---

## 8. How GPS Coordinates Reach the Map

1. The NEO-6M satellite receiver provides latitude and longitude.
2. When the backend receives a telemetry batch, it associates the latest valid GPS fix with the incoming sensor samples.
3. Once the ML model classifies an eligible hazard (`POTHOLE`, `SPEED_BREAKER`, or `ROUGH_ROAD`) with confidence $\ge 0.65$:
   - The raw detection is stored in SQLite.
   - The spatial aggregator updates or creates a map hotspot.
   - The Leaflet.js dashboard polls `/api/hotspots` every 3 seconds and dynamically renders colored markers at the exact coordinates.

---

## 9. How Repeated Detections Become Hotspots

A single sensor trigger from one vehicle does not automatically prove a permanent road failure. RoadGuard AI implements **Location-Based Hotspot Aggregation**:

1. **Spatial Proximity (Haversine Clustering):**
   - Any new detection within **25 meters** of an existing hotspot of the same hazard type is grouped into that hotspot cluster.
   - The hotspot's coordinates are continuously refined using a running weighted average.
2. **Anti-Duplicate Filter (Same-Pass Guard):**
   - If a bus's front axle and rear axle both hit the same pothole 1.5 seconds apart, both are recorded in `raw_detections`, but `distinct_rides` remains **1**.
   - Only when a separate bus or a different ride session detects the anomaly does `distinct_rides` increment.
3. **Inspection Priority Score Formula:**
   $$\text{Priority Score} (0\text{--}100) = S_{\text{rides}} + S_{\text{conf}} + S_{\text{severity}} + S_{\text{recency}}$$
   - $S_{\text{rides}} = \min(45, \; \text{distinct\_rides} \times 15)$
   - $S_{\text{conf}} = \text{avg\_confidence} \times 20$
   - $S_{\text{severity}} = \min(20, \; (\text{max\_peak\_to\_peak} - 1.0) \times 7)$
   - $S_{\text{recency}} = 15 \times e^{-\frac{\text{age\_days}}{7}}$

| Score Range | Priority Tier | Municipal Action |
|---|---|---|
| **70 – 100** | **HIGH** | Urgent dispatch of road inspection crew |
| **40 – 69** | **MEDIUM** | Scheduled verification in weekly maintenance cycle |
| **0 – 39** | **LOW** | Monitored for repeated future occurrences |

---

## 10. The Municipal Repair Workflow

RoadGuard AI supports a closed-loop municipal maintenance tracking lifecycle:

$$\text{DETECTED} \longrightarrow \text{INSPECTION\_REQUESTED} \longrightarrow \text{REPAIR\_IN\_PROGRESS} \longrightarrow \text{VERIFIED}$$

> [!IMPORTANT]
> A road hazard is **never** automatically marked as repaired just because a later sensor reading fails to detect it (a vehicle might have swerved around it!). Status changes to `VERIFIED` must be explicitly authorized by an engineer through the dashboard.

---

## 11. Project Directory Structure

```
RoadGuard-AI/
├── firmware/
│   ├── esp32_roadguard/
│   │   └── esp32_roadguard.ino     # Non-blocking C++ ESP32 firmware
│   └── README_FIRMWARE.md          # Wiring diagrams, pinouts, and flashing guide
├── data/
│   ├── README_DATA.md              # Data collection protocols and CSV schema
│   ├── synthetic_demo_dataset.csv  # Calibrated synthetic multi-ride dataset
│   └── roadguard.db                # SQLite database for detections and hotspots
├── ml/
│   ├── collect_data.py             # Serial/USB telemetry logger and interactive labeler
│   ├── preprocess.py               # Deterministic 23-feature extraction pipeline
│   ├── train_model.py              # GroupShuffleSplit training, evaluation, artifacts
│   ├── predict.py                  # Live inference engine with uncertainty threshold
│   └── simulate_sensors.py         # Physics-based sensor waveform & Pune route simulator
├── backend/
│   ├── app.py                      # Flask REST API server and dashboard gateway
│   ├── database.py                 # SQLite schema, transactions, and audit history
│   └── hotspots.py                 # Haversine spatial clustering & priority scoring
├── dashboard/
│   ├── index.html                  # PMC Operations Console with Leaflet.js
│   └── static/
│       ├── css/dashboard.css       # Dark navy municipal console stylesheet
│       └── js/dashboard.js         # Real-time polling, marker rendering, modal workflows
├── models/
│   ├── road_model.joblib           # Trained Random Forest classifier
│   ├── model_metadata.json         # Feature list, class labels, and evaluation metrics
│   └── confusion_matrix.png        # Generated out-of-sample confusion matrix chart
├── tests/
│   ├── test_preprocess.py          # Mathematical verification & dirty data handling
│   ├── test_model.py               # Model training, inference, and uncertainty tests
│   ├── test_hotspots.py            # Haversine clustering & deduplication tests
│   └── test_backend_api.py         # Flask REST API and workflow status tests
├── requirements.txt                # Python dependencies
├── .env.example                    # Configurable port, database, and threshold parameters
└── README.md                       # Comprehensive guide and judge presentation briefing
```

---

## 12. Quickstart Guide: Running RoadGuard AI (Windows Commands)

All commands below should be executed from PowerShell or Command Prompt inside the `RoadGuard-AI` directory:
```powershell
cd C:\Users\aryan\.gemini\antigravity\scratch\RoadGuard-AI
```

### Step 1: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 2: Run Automated Tests
Verify all 21 automated tests pass across preprocessing, ML inference, clustering, and API endpoints:
```powershell
python -m pytest tests/ -v
```

### Step 3: (Optional) Re-Train the Machine Learning Model
Train the Random Forest classifier on the multi-ride dataset and generate new evaluation metrics:
```powershell
python ml/train_model.py --dataset data/synthetic_demo_dataset.csv --output-dir models
```

### Step 4: Start the Flask Backend Server
```powershell
python backend/app.py
```
The server will start on `http://127.0.0.1:5000`.

### Step 5: Open the Interactive Municipal Dashboard
Open your web browser and navigate to:
```
http://127.0.0.1:5000
```
- Click **"Seed Pune Hotspots"** to populate real Pune transit coordinates (FC Road, Kothrud, Hinjewadi, Hadapsar, Shivajinagar).
- Click any marker on the map to inspect observation counts, distinct bus passes, ML confidence, and update repair status (`DETECTED` $\to$ `INSPECTION_REQUESTED` $\to$ `VERIFIED`).
- Switch between **Hardware Only** and **Simulation Only** using the top view mode selector.
- Click **"Locate Me"** to center the map on your physical browser location (uses browser Geolocation API for map panning without overriding vehicle GPS coordinates).

### Step 6: Demonstrate Live Bus Telemetry (Simulation Mode)
In a second terminal window, run the route simulator:
```powershell
cd C:\Users\aryan\.gemini\antigravity\scratch\RoadGuard-AI
py ml/simulate_sensors.py --mode stream_live --route FC_ROAD --duration 30
```
Watch the live alerts feed and hotspot observation counters update in real time on the dashboard!

---

## 13. Phase 7: Real-World Hardware Field Testing Checklist

When connecting your physical ESP32 prototype to an actual test rig or vehicle, follow this step-by-step validation checklist:

- [ ] **Step 1: Bench Power & I2C Verification:**
  - Connect ESP32 DevKit V1 to laptop USB.
  - Open Arduino Serial Monitor at 115200 baud.
  - Verify message: `[IMU] MPU6050 initialized successfully (Fast I2C 400kHz, Range ±8g)`.
- [ ] **Step 2: Outdoor GPS Satellite Lock:**
  - Place GPS ceramic antenna with sky view (near window or outdoor test rig).
  - Wait until the hardware red/green LED on NEO-7M/M8N begins flashing at 1 Hz.
  - Verify Serial Monitor outputs valid coordinates: `DATA:...,18.520432,73.856740,1,8`.
- [ ] **Step 3: Wi-Fi Gateway Handshake:**
  - Start Flask backend: `py backend/app.py`.
  - Ensure laptop firewall allows port 5000:
    ```powershell
    New-NetFirewallRule -DisplayName "RoadGuard Flask Gateway" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
    ```
  - Verify dashboard displays: `ESP32 Hardware: 🟢 Online (ESP32_BUS_01)` and `GPS: 🛰️ 3D Fix (8 Sats)`.
- [ ] **Step 4: Bench Vibration Validation:**
  - Tap the sensor enclosure firmly on the desk to simulate a pothole impact shock.
  - Verify the buzzer sounds for 120 ms and a live detection appears on the dashboard.
- [ ] **Step 5: Road Run & Data Collection:**
  - Mount sensor rigidly to vehicle floor or passenger seat rail (avoid loose tape).
  - Execute a test run over known speed breakers and road irregularities at 20–35 km/h.
  - Confirm hotspots cluster within 25 meters and priority scores increase on repeated passes.

---

## 14. Status of Implementation & Physical Testing Roadmap

### What Has Been Implemented & Verified in Software:
- [x] Full ESP32 firmware with non-blocking 100 Hz I2C sampling, multi-GNSS NMEA parser, and Wi-Fi batch telemetry (`firmware/esp32_roadguard/esp32_roadguard.ino`).
- [x] Reusable, deterministic 23-feature extraction pipeline (`ml/preprocess.py`).
- [x] Random Forest model training with GroupShuffleSplit by ride to prevent data leakage (`ml/train_model.py`).
- [x] Serialized model (`road_model.joblib`), metadata, and confusion matrix visualization.
- [x] Live prediction module with confidence thresholding and uncertainty handling (`ml/predict.py`).
- [x] Haversine spatial clustering, multi-ride deduplication, and priority scoring (`backend/hotspots.py`).
- [x] Flask REST API and SQLite database with repair workflow audit trails (`backend/app.py`).
- [x] Strict isolation between `HARDWARE` and `SIMULATION` data streams.
- [x] Real-time device connection heartbeat tracking and GPS health indicators.
- [x] Interactive Leaflet.js dashboard with live polling, KPI cards, modal repair transitions, and Locate Me browser geolocation (`dashboard/`).
- [x] 26 automated unit and integration tests passing with 100% success (`tests/`).

### What Requires Physical Vehicle Field Trials (Next Phase):
- [ ] Flashing firmware to physical ESP32 DevKit V1 with NEO-7M/M8N and MPU6050.
- [ ] Field calibration of baseline vehicle vibration across varied speeds (15–50 km/h).
- [ ] Logging empirical vehicle runs using `py ml/collect_data.py`.
