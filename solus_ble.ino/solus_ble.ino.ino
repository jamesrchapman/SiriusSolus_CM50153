#include <NimBLEDevice.h>

#define SERVICE_UUID        "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
#define COMMAND_CHAR_UUID   "6e400002-b5a3-f393-e0a9-e50e24dcca9e"

NimBLECharacteristic* commandChar;

class CommandCallback : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic* pCharacteristic) override {
    std::string command = pCharacteristic->getValue();
    Serial.print("Received command: ");
    Serial.println(command.c_str());
    // TODO: Parse & execute command (e.g. "PUSH:5")
  }
};

void setup() {
  Serial.begin(115200);
  Serial.println("Starting BLE...");

  NimBLEDevice::init("SolusPump");
  NimBLEServer* pServer = NimBLEDevice::createServer();

  NimBLEService* pService = pServer->createService(SERVICE_UUID);
  commandChar = pService->createCharacteristic(
                    COMMAND_CHAR_UUID,
                    NIMBLE_PROPERTY::WRITE
                );
  commandChar->setCallbacks(new CommandCallback());

  pService->start();
  NimBLEAdvertising* pAdvertising = NimBLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->start();

  Serial.println("BLE started and advertising.");
}

void loop() {
  // In future: push logs, handle timers, etc.
  delay(1000);
}
