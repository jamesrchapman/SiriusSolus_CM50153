#include <NimBLEDevice.h>
#include <Stepper.h>

#define SERVICE_UUID        "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
#define COMMAND_CHAR_UUID   "6e400002-b5a3-f393-e0a9-e50e24dcca9e"

const int stepsPerRevolution = 2048; 
Stepper myStepper(stepsPerRevolution, 14, 27, 26, 25);

NimBLECharacteristic* commandChar;

class CommandCallback : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic* pCharacteristic, NimBLEConnInfo& connInfo) override {
    std::string command = pCharacteristic->getValue();
    Serial.print("Received command: ");
    Serial.println(command.c_str());

    if (command.rfind("PUSH:", 0) == 0) {
      float units = atof(command.substr(5).c_str());
      int steps = (int)(units * stepsPerRevolution);
      Serial.print("Stepping ");
      Serial.print(steps);
      Serial.println(" steps.");
      myStepper.step(steps);
    }
  }
};



void setup() {
  Serial.begin(115200);
  Serial.println("Starting BLE...");

  myStepper.setSpeed(10);  // RPM — slower is safer
  Serial.println("Stepper ready.");

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

// 🚀 Add the device name to the advertising payload
NimBLEAdvertisementData advertisementData;
advertisementData.setName("SolusPump");  // 👈 this is the real fix
advertisementData.addServiceUUID(SERVICE_UUID);
pAdvertising->setAdvertisementData(advertisementData);

pAdvertising->start();




  Serial.println("BLE started and advertising.");
}

void loop() {
  // Idle – wait for BLE input
  delay(100);
}

