# RoadGuard AI: ESP32 Hardware Integration & Firmware Guide

**Target Microcontroller:** ESP32 DevKit V1 (30-Pin Standard)  
**Inertial Sensor:** MPU6050 6-DOF Accelerometer & Gyroscope (I2C)  
**GPS Receiver:** u-blox NEO-6M / NEO-7M / NEO-M8N Multi-GNSS Module (UART2)  
**Department:** ENTC, PICT Pune • Team: 404: Ground Not Found  

---

## 1. Verified Hardware Pinout Table

Connect your modules to the ESP32 DevKit V1 (30-pin) according to the verified hardware layout:

| Component | Pin Name | ESP32 Pin | Signal / Protocol | Notes & Recommendations |
|---|---|---|---|---|
| **MPU6050** | VCC | **VIN (5V)** or **3.3V** | Power | Use VIN/5V if breakout has 662K 3.3V LDO regulator; else 3.3V |
| **MPU6050** | GND | **GND** | Ground | Common system reference ground |
| **MPU6050** | SCL | **GPIO 22** | I2C Clock (SCL) | Fast I2C mode: 400 kHz |
| **MPU6050** | SDA | **GPIO 21** | I2C Data (SDA) | Fast I2C mode: 400 kHz |
| **NEO-6M / 7M / M8N** | VCC | **VIN (5V)** | Power Supply | GPS patch antenna active LNA draws ~45–55 mA during acquisition |
| **NEO-6M / 7M / M8N** | GND | **GND** | Ground | Common system reference ground |
| **NEO-6M / 7M / M8N** | TX | **GPIO 16 (RX2)** | HardwareSerial2 RX | **Serial Crossover:** GPS TX connects to ESP32 RX2 |
| **NEO-6M / 7M / M8N** | RX | **GPIO 17 (TX2)** | HardwareSerial2 TX | **Serial Crossover:** GPS RX connects to ESP32 TX2 |
| **Piezo Buzzer (Opt)** | Positive (+) | **GPIO 4** | Active HIGH Output | Sounds real-time 120ms chime on confirmed pothole impact |
| **Piezo Buzzer** | Negative (-) | **GND** | Ground | System ground |
| **Built-in LED** | Onboard | **GPIO 2** | Digital Output | Solid BLUE = Wi-Fi Connected; Off = Reconnecting |

> [!IMPORTANT]
> **UART Crossover Rule:** Ensure the GPS module's **TX** pin connects to ESP32 **GPIO 16 (RX2)**, and the GPS module's **RX** pin connects to ESP32 **GPIO 17 (TX2)**.

---

## 2. Wi-Fi Configuration & Secrets Separation

To keep your personal Wi-Fi credentials out of version control:
1. In `firmware/esp32_roadguard/`, duplicate `secrets.h.example` and rename it to `secrets.h`:
   ```bash
   cp firmware/esp32_roadguard/secrets.h.example firmware/esp32_roadguard/secrets.h
   ```
2. Open `secrets.h` and enter your Wi-Fi SSID, Password, and your Laptop's Local IP Address:
   ```cpp
   #ifndef SECRETS_H
   #define SECRETS_H

   const char* WIFI_SSID     = "Your_Phone_Hotspot";        // e.g. "Aryan_Galaxy"
   const char* WIFI_PASSWORD = "your_hotspot_password";
   const char* BACKEND_URL   = "http://192.168.43.100:5000/api/telemetry"; // Laptop IP & port

   #endif
   ```
3. `secrets.h` is automatically ignored in `.gitignore`, keeping your credentials private.

---

## 3. Arduino IDE Flashing Procedure

1. **Install ESP32 Board Core:**
   - Open Arduino IDE -> `File` -> `Preferences`.
   - Add Boards Manager URL: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
   - Open `Tools` -> `Board` -> `Boards Manager`, search for `esp32` by Espressif, and install version `2.0.x` or `3.0.x`.
2. **Install TinyGPS++ Library (Recommended):**
   - In Arduino IDE, navigate to `Sketch` -> `Include Library` -> `Manage Libraries...`.
   - Search for **TinyGPSPlus** by Mikal Hart and click **Install**.
   - *(Note: The firmware includes a zero-dependency native NMEA parser fallback, so it compiles and runs even if TinyGPSPlus is not installed).*
3. **Select Target Board & Port:**
   - Board: `DOIT ESP32 DEVKIT V1` (or `ESP32 Dev Module`).
   - Upload Speed: `921600` (or `115200` if upload times out).
   - Port: Select your ESP32 COM port (e.g., `COM3`, `COM4`).
4. **Compile & Upload:**
   - Click **Upload** (Ctrl + U).
   - If the upload prompt gets stuck at `Connecting......____....`, press and hold the physical **BOOT** button on the ESP32 board for 2 seconds until uploading begins.

---

## 4. Starting Backend Gateway Server & Dashboard

### Step 1: Open Port 5000 in Windows Firewall
Run PowerShell as **Administrator** once:
```powershell
New-NetFirewallRule -DisplayName "RoadGuard AI Flask Gateway" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

### Step 2: Start the Flask Backend Server
In PowerShell:
```powershell
cd "C:\Users\aryan\.gemini\antigravity\scratch\RoadGuard-AI"
py backend/app.py
```
The server will bind to `0.0.0.0:5000` and load the Random Forest ML model.

### Step 3: Open the RoadGuard AI Dashboard
In your web browser, navigate to:
- **Dashboard:** [http://localhost:5000/](http://localhost:5000/)
- **Road Condition Map:** [http://localhost:5000/map](http://localhost:5000/map)
- **PMPML Bus Fleet:** [http://localhost:5000/fleet](http://localhost:5000/fleet)

---

## 5. Comprehensive GPS Troubleshooting Guide

If the ESP32 Serial Monitor shows NMEA sentences but no satellite fix (`0 Sats`, `fix_valid = false`):

### 1. Indoor Signal Attenuation
- **Cause:** GPS signals transmit at ~1575.42 MHz (L1 band). Satellite signals are extremely faint (-130 dBm) and cannot penetrate concrete ceilings, metallic roofs, or thick tinted glass.
- **Fix:** Move the antenna near an open window or test outdoors on a balcony/open terrace. Direct line-of-sight to the sky is required for the initial lock.

### 2. Cold Start Acquisition Time
- **Cause:** When a GPS module is powered on in a new location or after being powered off for hours, it must download complete satellite almanac and ephemeris orbital data (*Cold Start*).
- **Fix:** Allow 45 to 120 seconds of continuous power in an open area. Do not power-cycle the module during satellite acquisition.

### 3. Ceramic Patch Antenna Orientation
- **Cause:** Ceramic patch antennas are directional.
- **Fix:** Ensure the metallic/ceramic square face of the patch antenna is **facing upwards toward the sky**, not face-down toward the breadboard or vehicle chassis.

### 4. PPS (Pulse Per Second) LED Indicator
- **Searching:** The small red/green PPS LED on the NEO-6M board is **OFF** or solid when searching for satellites.
- **Lock Acquired:** The PPS LED begins **blinking at exactly 1 Hz (once per second)** as soon as 3D satellite synchronization is established.

### 5. Baud Rate Mismatch
- **Standard Baud:** u-blox NEO-6M, NEO-7M, and NEO-M8N modules default to **9600 baud**.
- **Fix:** Keep `GPSSerial.begin(9600, SERIAL_8N1, 16, 17);`. Only the USB debug serial monitor uses `115200 baud`.

### 6. Power Supply Voltage & Current
- **Cause:** GPS patch antenna LNAs (Low Noise Amplifiers) draw up to 55 mA during active satellite search. If powered from a weak 3.3V rail or faulty breadboard rail, the module may brown out.
- **Fix:** Power the GPS `VCC` pin from the ESP32 `VIN` (5V USB rail) pin. The NEO-6M breakout has an onboard 3.3V LDO regulator that safely steps 5V down to 3.3V.

---

## 6. Verification Status: Physical Hardware vs Simulation

| Feature / Subsystem | Verification Method | Status |
|---|---|---|
| **NEO-6M UART GPS Parser** | Unit tested against NMEA `$GPRMC` & `$GPGGA` sentences | **Verified** |
| **Strict Null Island (0,0) Rejection** | Tested in `test_null_island_rejection_in_telemetry` | **Verified** |
| **Stale GPS Fix Rejection (>10s)** | Tested in `test_stale_gps_telemetry_rejection` | **Verified** |
| **Hardware Position REST Endpoint** | Tested in `test_hardware_position_endpoint_valid_fix` | **Verified** |
| **Real Vehicle Map Tracking Marker** | Tested in Dashboard with live position updates & popup | **Verified** |
| **Unlocated Hazard Quarantine** | Hazards detected without GPS fix are quarantined as UNLOCATED | **Verified** |
| **Hardware vs Simulation Mode Segregation**| Tested in `test_mode_segregation_in_hotspots` | **Verified** |
| **Physical ESP32 Edge Device** | Ready for flashing via Arduino IDE (`esp32_roadguard.ino`) | **Ready for Hardware Demo** |
