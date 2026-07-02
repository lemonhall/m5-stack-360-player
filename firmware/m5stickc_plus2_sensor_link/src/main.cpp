#include <Arduino.h>
#include <BLE2902.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>

#include "M5StickCPlus2.h"

static constexpr const char* DEVICE_NAME = "M5HeadTracker";
static constexpr const char* M5_HEAD_TRACKER_SERVICE_UUID =
    "7d2f4b8a-6d0e-4f88-9e1f-0c8d2f5f5a01";
static constexpr const char* M5_TELEMETRY_CHARACTERISTIC_UUID =
    "7d2f4b8a-6d0e-4f88-9e1f-0c8d2f5f5a02";
static constexpr uint32_t TELEMETRY_HZ = 30;
static constexpr uint32_t TELEMETRY_INTERVAL_MS = 1000 / TELEMETRY_HZ;
static constexpr int MAIN_BUTTON_PIN = 37;

static BLECharacteristic* telemetryCharacteristic = nullptr;
static bool bleClientConnected = false;
static uint32_t seq = 0;
static uint32_t lastTelemetryMs = 0;
static uint32_t lastPoseMs = 0;
static float yawDeg = 0.0f;
static float pitchDeg = 0.0f;
static float rollDeg = 0.0f;
static bool lastButtonPressed = false;

class ServerCallbacks : public BLEServerCallbacks {
   public:
    void onConnect(BLEServer*) override { bleClientConnected = true; }

    void onDisconnect(BLEServer* server) override {
        bleClientConnected = false;
        server->startAdvertising();
    }
};

static float wrapDegrees(float value) {
    while (value <= -180.0f) {
        value += 360.0f;
    }
    while (value > 180.0f) {
        value -= 360.0f;
    }
    return value;
}

static void setupBle() {
    BLEDevice::init(DEVICE_NAME);
    BLEServer* server = BLEDevice::createServer();
    server->setCallbacks(new ServerCallbacks());

    BLEService* service = server->createService(M5_HEAD_TRACKER_SERVICE_UUID);
    telemetryCharacteristic = service->createCharacteristic(
        M5_TELEMETRY_CHARACTERISTIC_UUID,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
    telemetryCharacteristic->addDescriptor(new BLE2902());
    telemetryCharacteristic->setValue("{\"status\":\"booting\"}");

    service->start();
    BLEAdvertising* advertising = BLEDevice::getAdvertising();
    advertising->addServiceUUID(M5_HEAD_TRACKER_SERVICE_UUID);
    advertising->setScanResponse(true);
    BLEDevice::startAdvertising();
}

static void updatePose(const m5::imu_data_t& data, uint32_t nowMs) {
    if (lastPoseMs == 0) {
        lastPoseMs = nowMs;
        return;
    }
    const float dt = (nowMs - lastPoseMs) / 1000.0f;
    lastPoseMs = nowMs;

    yawDeg = wrapDegrees(yawDeg + data.gyro.z * dt);
    pitchDeg = wrapDegrees(pitchDeg + data.gyro.y * dt);
    rollDeg = wrapDegrees(rollDeg + data.gyro.x * dt);
}

static String buildTelemetryJson(const m5::imu_data_t& data, bool buttonPressed) {
    String json;
    json.reserve(256);
    json += "{";
    json += "\"seq\":";
    json += seq++;
    json += ",\"ms\":";
    json += millis();
    json += ",\"ypr\":[";
    json += String(yawDeg, 3);
    json += ",";
    json += String(pitchDeg, 3);
    json += ",";
    json += String(rollDeg, 3);
    json += "],\"acc\":[";
    json += String(data.accel.x, 5);
    json += ",";
    json += String(data.accel.y, 5);
    json += ",";
    json += String(data.accel.z, 5);
    json += "],\"gyro\":[";
    json += String(data.gyro.x, 5);
    json += ",";
    json += String(data.gyro.y, 5);
    json += ",";
    json += String(data.gyro.z, 5);
    json += "],\"btn\":";
    json += buttonPressed ? "1" : "0";
    json += "}";
    return json;
}

static void drawTelemetry(const m5::imu_data_t& data, bool buttonPressed) {
    StickCP2.Display.setCursor(0, 8);
    StickCP2.Display.clear();
    StickCP2.Display.printf("BLE:%s %luHz\n", bleClientConnected ? "on" : "wait",
                            TELEMETRY_HZ);
    StickCP2.Display.printf("YPR %6.1f %6.1f %6.1f\n", yawDeg, pitchDeg, rollDeg);
    StickCP2.Display.printf("ACC %5.2f %5.2f %5.2f\n", data.accel.x, data.accel.y,
                            data.accel.z);
    StickCP2.Display.printf("GYR %5.2f %5.2f %5.2f\n", data.gyro.x, data.gyro.y,
                            data.gyro.z);
    StickCP2.Display.printf("BTN %s\n", buttonPressed ? "CENTER" : "-");
}

static void notifyTelemetry(const String& json) {
    if (telemetryCharacteristic == nullptr || !bleClientConnected) {
        return;
    }
    telemetryCharacteristic->setValue((uint8_t*)json.c_str(), json.length());
    telemetryCharacteristic->notify();
}

static bool readMainButtonClicked() {
    const bool pressed = digitalRead(MAIN_BUTTON_PIN) == HIGH;
    const bool clicked = pressed && !lastButtonPressed;
    lastButtonPressed = pressed;
    return clicked;
}

void setup() {
    Serial.begin(115200);
    auto cfg = M5.config();
    StickCP2.begin(cfg);
    pinMode(MAIN_BUTTON_PIN, INPUT);
    StickCP2.Display.setRotation(1);
    StickCP2.Display.setTextColor(GREEN);
    StickCP2.Display.setTextDatum(top_left);
    StickCP2.Display.setFont(&fonts::Font0);
    StickCP2.Display.setTextSize(1);
    setupBle();
}

void loop() {
    const bool buttonPressed = readMainButtonClicked();
    const uint32_t nowMs = millis();

    const auto imuUpdate = StickCP2.Imu.update();
    if (!imuUpdate) {
        delay(1);
        return;
    }

    const auto data = StickCP2.Imu.getImuData();
    updatePose(data, nowMs);

    if (nowMs - lastTelemetryMs >= TELEMETRY_INTERVAL_MS) {
        lastTelemetryMs = nowMs;
        const String json = buildTelemetryJson(data, buttonPressed);
        Serial.println(json);
        notifyTelemetry(json);
        drawTelemetry(data, buttonPressed);
    }
}
