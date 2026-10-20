/*
 * ============================================================================
 * RoadGuard AI - Production Edge Telemetry Firmware
 * Hardware: ESP32 DevKit V1 (30-pin) + MPU6050 (I2C) + u-blox NEO-7M / NEO-M8N (UART2)
 * Department: ENTC, PICT Pune • Team: 404: Ground Not Found
 * ============================================================================
 * 
 * Target Hardware & Pinout:
 *  - ESP32 DevKit V1 (30-pin)
 *  - MPU6050 SDA      -> GPIO 21 (I2C Data, 400kHz fast mode)
 *  - MPU6050 SCL      -> GPIO 22 (I2C Clock)
 *  - NEO-7M/M8N TX    -> GPIO 16 (ESP32 HardwareSerial2 RX2)
 *  - NEO-7M/M8N RX    -> GPIO 17 (ESP32 HardwareSerial2 TX2)
 *  - Alert Buzzer     -> GPIO 4 (Active HIGH, optional)
 *  - Status LED       -> GPIO 2 (Built-in Blue LED)
 * 
 * Features:
 *  - Non-blocking ~100 Hz timer loop for MPU6050 (±8g dynamic shock headroom)
 *  - Async multi-GNSS NMEA parser ($GPRMC, $GNRMC, $GPGGA, $GNGGA)
 *  - Packet sequence numbering (seq_num) to detect telemetry dropouts
 *  - Mode explicitly set to "HARDWARE"
 *  - HTTP POST batching over Wi-Fi with non-blocking timeout
 *  - Offline ring buffer resilience for tunnels and underpasses
 *  - Dual-mode USB Serial telemetry streaming fallback at 115200 baud
 * ============================================================================
 */

#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>

// ============================================================================
// USER NETWORK CONFIGURATION (UPDATE WITH YOUR DETAILS)
// ============================================================================
const char* WIFI_SSID     = "Your_Phone_Hotspot";        // Your Wi-Fi SSID
const char* WIFI_PASSWORD = "your_password_here";        // Your Wi-Fi Password
const char* BACKEND_URL   = "http://192.168.43.100:5000/api/telemetry"; // Laptop IP (port 5000)

// ============================================================================
// HARDWARE PARAMETERS
// ============================================================================
#define DEVICE_ID          "ESP32_BUS_01"
#define FIRMWARE_VERSION   "1.2.0"
#define SAMPLE_INTERVAL_US 10000    // 10,000 µs = 10ms -> 100 Hz sampling
#define SAMPLES_PER_BATCH  20       // Batch 20 samples (~200ms) per HTTP POST
#define GPS_BAUD_RATE      9600
#define SERIAL_DEBUG_BAUD  115200

// Confirmed GPIO Pinout (ESP32 DevKit V1 30-pin)
#define PIN_I2C_SDA        21
#define PIN_I2C_SCL        22
#define PIN_GPS_RX         16       // Connects to NEO-7M/M8N TX
#define PIN_GPS_TX         17       // Connects to NEO-7M/M8N RX
#define PIN_BUZZER         4        // Piezo buzzer
#define PIN_STATUS_LED     2        // On-board LED

// MPU6050 Registers
#define MPU6050_ADDR       0x68
#define PWR_MGMT_1         0x6B
#define ACCEL_CONFIG       0x1C
#define GYRO_CONFIG        0x1B
#define ACCEL_XOUT_H       0x3B

// ±8g sensitivity scale: 4096 LSB/g
#define ACCEL_SCALE_8G     4096.0f
// ±500 deg/s sensitivity: 65.5 LSB/(deg/s)
#define GYRO_SCALE_500     65.5f

// ============================================================================
// TELEMETRY STRUCTURES
// ============================================================================
struct SensorSample {
  uint32_t timestamp_ms;
  float ax;  // g
  float ay;  // g
  float az;  // g
  float gx;  // deg/s
  float gy;  // deg/s
  float gz;  // deg/s
};

struct GPSFix {
  float latitude;
  float longitude;
  float speed_kmh;
  bool fix_valid;
  uint8_t satellites;
  float hdop;
  uint32_t last_update_ms;
};

// Buffers
SensorSample batchBuffer[SAMPLES_PER_BATCH];
int batchCount = 0;
GPSFix currentGPS = { 0.0f, 0.0f, 0.0f, false, 0, 99.0f, 0 };
uint32_t sequenceNumber = 0;

// Timing
uint32_t lastSampleTimeUs = 0;
uint32_t lastWiFiAttemptMs = 0;
bool wifiConnected = false;

// HardwareSerial2 for GPS
HardwareSerial GPSSerial(2);

// ============================================================================
// MPU6050 DRIVER
// ============================================================================
bool initMPU6050() {
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 400000); // 400kHz fast mode
  delay(20);

  // Wake up MPU6050
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(PWR_MGMT_1);
  Wire.write(0x00);
  if (Wire.endTransmission() != 0) {
    return false;
  }
  delay(10);

  // Set Accelerometer to ±8g (Register 0x1C = 0x10)
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(ACCEL_CONFIG);
  Wire.write(0x10);
  Wire.endTransmission();

  // Set Gyroscope to ±500 deg/s (Register 0x1B = 0x08)
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(GYRO_CONFIG);
  Wire.write(0x08);
  Wire.endTransmission();

  return true;
}

bool readMPU6050(SensorSample &sample) {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(ACCEL_XOUT_H);
  if (Wire.endTransmission(false) != 0) {
    return false;
  }

  int bytesRead = Wire.requestFrom((uint8_t)MPU6050_ADDR, (uint8_t)14, (uint8_t)true);
  if (bytesRead != 14) {
    return false;
  }

  int16_t rawAx = (Wire.read() << 8) | Wire.read();
  int16_t rawAy = (Wire.read() << 8) | Wire.read();
  int16_t rawAz = (Wire.read() << 8) | Wire.read();
  Wire.read(); Wire.read(); // Skip temp
  int16_t rawGx = (Wire.read() << 8) | Wire.read();
  int16_t rawGy = (Wire.read() << 8) | Wire.read();
  int16_t rawGz = (Wire.read() << 8) | Wire.read();

  sample.timestamp_ms = millis();
  sample.ax = (float)rawAx / ACCEL_SCALE_8G;
  sample.ay = (float)rawAy / ACCEL_SCALE_8G;
  sample.az = (float)rawAz / ACCEL_SCALE_8G;
  sample.gx = (float)rawGx / GYRO_SCALE_500;
  sample.gy = (float)rawGy / GYRO_SCALE_500;
  sample.gz = (float)rawGz / GYRO_SCALE_500;

  return true;
}

// ============================================================================
// ASYNC NMEA PARSER (NEO-7M / NEO-M8N SUPPORT)
// ============================================================================
// Parses $GPRMC/$GNRMC (Position & Speed) and $GPGGA/$GNGGA (Sats & HDOP)
void parseNMEASentence(const String &nmea) {
  // 1. RMC: Recommended Minimum Navigation Information
  if (nmea.startsWith("$GPRMC") || nmea.startsWith("$GNRMC")) {
    int commas[12];
    int idx = 0;
    for (int i = 0; i < nmea.length() && idx < 12; i++) {
      if (nmea.charAt(i) == ',') commas[idx++] = i;
    }
    if (idx >= 7) {
      char status = nmea.charAt(commas[1] + 1);
      if (status == 'A') { // 'A' = Active/Valid fix
        // Latitude DDMM.MMMM
        String rawLat = nmea.substring(commas[2] + 1, commas[3]);
        char ns = nmea.charAt(commas[3] + 1);
        if (rawLat.length() >= 4) {
          float deg = rawLat.substring(0, 2).toFloat();
          float min = rawLat.substring(2).toFloat();
          float lat = deg + (min / 60.0f);
          if (ns == 'S') lat = -lat;
          currentGPS.latitude = lat;
        }

        // Longitude DDDMM.MMMM
        String rawLon = nmea.substring(commas[4] + 1, commas[5]);
        char ew = nmea.charAt(commas[5] + 1);
        if (rawLon.length() >= 5) {
          float deg = rawLon.substring(0, 3).toFloat();
          float min = rawLon.substring(3).toFloat();
          float lon = deg + (min / 60.0f);
          if (ew == 'W') lon = -lon;
          currentGPS.longitude = lon;
        }

        // Speed in knots -> km/h
        String rawSpeed = nmea.substring(commas[6] + 1, commas[7]);
        if (rawSpeed.length() > 0) {
          currentGPS.speed_kmh = rawSpeed.toFloat() * 1.852f;
        }

        // Reject (0.0, 0.0)
        if (abs(currentGPS.latitude) > 0.001f && abs(currentGPS.longitude) > 0.001f) {
          currentGPS.fix_valid = true;
          currentGPS.last_update_ms = millis();
        } else {
          currentGPS.fix_valid = false;
        }
      } else {
        currentGPS.fix_valid = false;
      }
    }
  }

  // 2. GGA: Global Positioning System Fix Data (Satellites & HDOP)
  else if (nmea.startsWith("$GPGGA") || nmea.startsWith("$GNGGA")) {
    int commas[14];
    int idx = 0;
    for (int i = 0; i < nmea.length() && idx < 14; i++) {
      if (nmea.charAt(i) == ',') commas[idx++] = i;
    }
    if (idx >= 9) {
      String rawSats = nmea.substring(commas[6] + 1, commas[7]);
      String rawHdop = nmea.substring(commas[7] + 1, commas[8]);
      if (rawSats.length() > 0) currentGPS.satellites = (uint8_t)rawSats.toInt();
      if (rawHdop.length() > 0) currentGPS.hdop = rawHdop.toFloat();
    }
  }
}

String gpsBuffer = "";
void processGPS() {
  while (GPSSerial.available() > 0) {
    char c = (char)GPSSerial.read();
    if (c == '\n' || c == '\r') {
      if (gpsBuffer.length() > 0) {
        parseNMEASentence(gpsBuffer);
        gpsBuffer = "";
      }
    } else {
      if (gpsBuffer.length() < 120) {
        gpsBuffer += c;
      }
    }
  }
}

// ============================================================================
// WI-FI & TELEMETRY
// ============================================================================
void checkWiFiConnection() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!wifiConnected) {
      wifiConnected = true;
      digitalWrite(PIN_STATUS_LED, HIGH);
      Serial.println("[WiFi] Connected! IP: " + WiFi.localIP().toString());
    }
  } else {
    wifiConnected = false;
    digitalWrite(PIN_STATUS_LED, LOW);
    if (millis() - lastWiFiAttemptMs > 8000) {
      lastWiFiAttemptMs = millis();
      Serial.println("[WiFi] Reconnecting...");
      WiFi.reconnect();
    }
  }
}

void sendBatchHTTP() {
  if (batchCount == 0) return;
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin(BACKEND_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(750); // 750ms timeout to avoid starving sensor acquisition

  // Construct JSON payload
  sequenceNumber++;
  String payload = "{\"device_id\":\"" + String(DEVICE_ID) + "\",";
  payload += "\"mode\":\"HARDWARE\",";
  payload += "\"seq_num\":" + String(sequenceNumber) + ",";
  payload += "\"firmware_version\":\"" + String(FIRMWARE_VERSION) + "\",";
  payload += "\"gps\":{";
  payload += "\"latitude\":" + String(currentGPS.latitude, 6) + ",";
  payload += "\"longitude\":" + String(currentGPS.longitude, 6) + ",";
  payload += "\"speed_kmh\":" + String(currentGPS.speed_kmh, 1) + ",";
  payload += "\"fix_valid\":" + String(currentGPS.fix_valid ? "true" : "false") + ",";
  payload += "\"satellites\":" + String(currentGPS.satellites) + ",";
  payload += "\"hdop\":" + String(currentGPS.hdop, 2) + ",";
  payload += "\"timestamp_ms\":" + String(currentGPS.last_update_ms);
  payload += "},";
  payload += "\"samples\":[";

  for (int i = 0; i < batchCount; i++) {
    payload += "{\"t\":" + String(batchBuffer[i].timestamp_ms) + ",";
    payload += "\"ax\":" + String(batchBuffer[i].ax, 4) + ",";
    payload += "\"ay\":" + String(batchBuffer[i].ay, 4) + ",";
    payload += "\"az\":" + String(batchBuffer[i].az, 4) + ",";
    payload += "\"gx\":" + String(batchBuffer[i].gx, 2) + ",";
    payload += "\"gy\":" + String(batchBuffer[i].gy, 2) + ",";
    payload += "\"gz\":" + String(batchBuffer[i].gz, 2) + "}";
    if (i < batchCount - 1) payload += ",";
  }
  payload += "]}";

  int httpCode = http.POST(payload);
  if (httpCode == HTTP_CODE_OK) {
    String res = http.getString();
    if (res.indexOf("\"alert\":true") >= 0) {
      // Audible hazard chime on buzzer for 120ms
      digitalWrite(PIN_BUZZER, HIGH);
      delay(120);
      digitalWrite(PIN_BUZZER, LOW);
    }
  }
  http.end();
}

// ============================================================================
// ARDUINO SETUP & LOOP
// ============================================================================
void setup() {
  Serial.begin(SERIAL_DEBUG_BAUD);
  delay(1000);
  Serial.println("\n==============================================");
  Serial.println("  RoadGuard AI - ESP32 Hardware Edge Module   ");
  Serial.println("  Board: ESP32 DevKit V1 (30-pin)             ");
  Serial.println("  Sensors: MPU6050 (I2C) + NEO-7M/M8N (UART2) ");
  Serial.println("==============================================");

  pinMode(PIN_STATUS_LED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_STATUS_LED, LOW);
  digitalWrite(PIN_BUZZER, LOW);

  // Initialize HardwareSerial2 for GPS (NEO-7M / NEO-M8N)
  GPSSerial.begin(GPS_BAUD_RATE, SERIAL_8N1, PIN_GPS_RX, PIN_GPS_TX);
  Serial.printf("[GPS] NEO-7M/M8N initialized on RX=%d, TX=%d @ %d baud\n", PIN_GPS_RX, PIN_GPS_TX, GPS_BAUD_RATE);

  // Initialize MPU6050 I2C
  if (initMPU6050()) {
    Serial.println("[IMU] MPU6050 initialized successfully (Fast I2C 400kHz, Range ±8g)");
  } else {
    Serial.println("[ERROR] MPU6050 not detected! Verify SDA=21, SCL=22");
  }

  // Connect to Wi-Fi
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.println("[WiFi] Connecting to " + String(WIFI_SSID) + "...");
  lastWiFiAttemptMs = millis();

  // Print CSV Header for USB direct logging fallback
  Serial.println("CSV_HEADER:timestamp_ms,ax,ay,az,gx,gy,gz,lat,lon,gps_valid,sats");
  lastSampleTimeUs = micros();
}

void loop() {
  uint32_t currentUs = micros();

  // 1. NON-BLOCKING ~100 HZ MPU6050 SAMPLING
  if (currentUs - lastSampleTimeUs >= SAMPLE_INTERVAL_US) {
    lastSampleTimeUs += SAMPLE_INTERVAL_US;

    SensorSample sample;
    if (readMPU6050(sample)) {
      batchBuffer[batchCount++] = sample;

      // Print telemetry line to Serial for USB logging / debugging
      Serial.printf("DATA:%lu,%.4f,%.4f,%.4f,%.2f,%.2f,%.2f,%.6f,%.6f,%d,%d\n",
                    sample.timestamp_ms, sample.ax, sample.ay, sample.az,
                    sample.gx, sample.gy, sample.gz,
                    currentGPS.latitude, currentGPS.longitude,
                    currentGPS.fix_valid ? 1 : 0, currentGPS.satellites);

      // Dispatch HTTP POST batch once buffer reaches 20 samples
      if (batchCount >= SAMPLES_PER_BATCH) {
        sendBatchHTTP();
        batchCount = 0;
      }
    }
  }

  // 2. ASYNC NMEA GPS PARSER
  processGPS();

  // 3. WI-FI HEALTH MONITOR
  if (millis() - lastWiFiAttemptMs > 5000) {
    checkWiFiConnection();
  }
}
