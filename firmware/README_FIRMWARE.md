# RoadGuard AI: ESP32 Hardware Integration & Firmware Guide

**Target Board:** ESP32 DevKit V1 (30-Pin Standard)  
**Sensors:** MPU6050 6-DOF IMU + u-blox NEO-7M / NEO-M8N Multi-GNSS GPS Receiver  
**Team:** 404: Ground Not Found (PICT ENTC)  

---

## 1. Verified Wiring & Pinout Table

Connect your modules to the ESP32 DevKit V1 (30-pin) as follows:

| Component | Pin Name | ESP32 GPIO | Wire Color (Rec.) | Notes |
|---|---|---|---|---|
| **MPU6050** | VCC | **3.3V** or **VIN/5V** | Red | Use 5V if module has onboard 3.3V LDO regulator; else 3.3V |
| **MPU6050** | GND | **GND** | Black | Common system ground |
| **MPU6050** | SCL | **GPIO 22** | Yellow | Hardware I2C Clock (Fast Mode: 400 kHz) |
| **MPU6050** | SDA | **GPIO 21** | Blue | Hardware I2C Data |
| **NEO-7M / M8N** | VCC | **VIN (5V)** | Red | GPS patch antenna draws ~45–55 mA during lock search |
| **NEO-7M / M8N** | GND | **GND** | Black | Common system ground |
| **NEO-7M / M8N** | TX | **GPIO 16 (RX2)** | Green | ESP32 HardwareSerial2 Receive connects to GPS Transmit |
| **NEO-7M / M8N** | RX | **GPIO 17 (TX2)** | Orange | ESP32 HardwareSerial2 Transmit connects to GPS Receive |
| **Buzzer (Optional)** | Pos (+) | **GPIO 4** | White | 5V Active Piezo Buzzer for real-time hazard chime |
| **Buzzer** | Neg (-) | **GND** | Black | Ground |

> [!IMPORTANT]
> **Serial Crossover Rule:** Ensure GPS **TX** goes to ESP32 **GPIO 16 (RX2)**, and GPS **RX** goes to ESP32 **GPIO 17 (TX2)**.

---

## 2. Arduino IDE Flashing Instructions

1. **Install ESP32 Board Core:**
   - Open Arduino IDE -> `File` -> `Preferences`.
   - Add URL: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_exp32_index.json`
   - Open `Tools` -> `Board` -> `Boards Manager`, search for `esp32` by Espressif, and install version `2.0.x` or `3.0.x`.
2. **Select Board & Port:**
   - Board: `DOIT ESP32 DEVKIT V1` (or `ESP32 Dev Module`).
   - Upload Speed: `921600` (or `115200` if upload times out).
   - Port: Select your ESP32 COM port (e.g., `COM3`, `COM4`).
3. **Configure Network in `esp32_roadguard.ino`:**
   Open [`firmware/esp32_roadguard/esp32_roadguard.ino`](file:///C:/Users/aryan/.gemini/antigravity/scratch/RoadGuard-AI/firmware/esp32_roadguard/esp32_roadguard.ino) and update lines 46–48:
   ```cpp
   const char* WIFI_SSID     = "Your_Phone_Hotspot";        // e.g. Aryan_Galaxy
   const char* WIFI_PASSWORD = "your_hotspot_password";
   const char* BACKEND_URL   = "http://192.168.43.100:5000/api/telemetry"; // Replace with your laptop IP!
   ```
4. **Compile and Upload:**
   - Click **Upload** (Ctrl + U).
   - If stuck on `Connecting......____....`, press and hold the physical **BOOT** button on the ESP32 for 2 seconds.

---

## 3. Finding Laptop IP & Windows Firewall Setup

The ESP32 communicates with your laptop over Wi-Fi. Follow these steps so your laptop accepts incoming connections:

### Step 1: Find Laptop Local IPv4 Address
In PowerShell:
```powershell
ipconfig
```
Look for **IPv4 Address** under your Wi-Fi adapter (e.g., `192.168.43.100`).

### Step 2: Open Port 5000 in Windows Firewall
Run PowerShell **as Administrator** and execute:
```powershell
New-NetFirewallRule -DisplayName "RoadGuard AI Flask Gateway" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

### Step 3: Verify Connectivity from Your Phone or Another Device
With Flask running (`py backend/app.py`), open your phone's browser connected to the same hotspot and navigate to:
```
http://192.168.43.100:5000/api/system-status
```
If you see JSON `{"status": "online", "model_readiness": "MODEL_READY"}`, your local network configuration is 100% verified!

---

## 4. GPS Validation & Testing Procedure

The u-blox NEO-7M / NEO-M8N multi-GNSS receiver requires direct line-of-sight to the sky for satellite acquisition:
1. **First Lock Indoors vs Outdoors:**
   - Indoors, GPS satellite signals are heavily attenuated by concrete roofs. Test near an open window or outdoors on a balcony/terrace.
   - Initial satellite search (*Cold Start*) typically takes 45–90 seconds.
2. **Hardware LED Fix Indicator:**
   - The tiny red/green LED on the GPS breakout board will begin **blinking at 1 Hz** once a 3D satellite fix is established.
3. **Serial Verification:**
   Open Arduino Serial Monitor at **115200 baud**. You will see:
   ```
   DATA:14520,-0.0120,0.0240,0.9980,0.12,-0.20,0.05,18.520432,73.856740,1,8
   ```
   - Last two fields are `fix_valid` (1 = True) and `satellites` (e.g. 8 satellites).
   - Coordinates `(0.0, 0.0)` are strictly rejected by the backend to prevent false "Null Island" map markers.

---

## 5. Live Dashboard Hardware Status

Once the ESP32 is powered on and transmitting:
- The dashboard top strip dynamically displays:
  - `ESP32 Hardware: 🟢 Online (ESP32_BUS_01 • seen 1.2s ago)`
  - `GPS: 🛰️ 3D Fix (8 Sats • HDOP 1.1)`
  - `Showing: Hardware Data`
- When you cross a pothole, the model triggers inference, logs the detection with physical GPS coordinates, clusters it into a hotspot, and triggers the ESP32 onboard buzzer chime.
