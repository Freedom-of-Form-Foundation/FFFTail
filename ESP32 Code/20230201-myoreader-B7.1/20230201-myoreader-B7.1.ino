// Myoreader.ino: A sketch to log data from a MyoWare. Written by Bleddyn for the FFF, Nov. 9, 2021.
// Edits for consistency and sample rate controll made by Mecknavorz for the FFF, March 10, 2022-
// b7 able to achive consistent 1024 sample rate with minimal deviance
// b7.1 aims to send the data in an exact format for consistent reading
// b7.2 preform handshake to make reading even easier eg things are starting in sync?

#include "BluetoothSerial.h"
//#include "ESP32Time.h"

//make sure we can access bluetooth
#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Bluetooth is not enabled! Please run `make menuconfig` to enable it
#endif

//the pins we're gonna be reading the myoware data from
#define MYOWARE_RAW 37 //raw values
#define MYOWARE_ENV 39 //envolope values

BluetoothSerial SerialBT;

//ESP32Time rtc;
uint32_t myMicros = 0; //for keeping track of time
const int sample_rate = 966; //488 microseconds gives us a rate of 2048Hz, which is what many sEMG systems use

void setup() {
  Serial.begin(230400);
  SerialBT.begin("Myoreader"); //Bluetooth device name
  Serial.println("The device started, now you can pair it with bluetooth!");

  // Disable watchdog timer reset.
  disableCore0WDT();
  
  delay(100);
  
  myMicros = micros();
  Serial.print(myMicros); Serial.println(",Raw value (0--4095),Env value (0--4095)");
  SerialBT.print(myMicros); SerialBT.println(",Raw value (0--4095),Env value (0--4095)");
}

//the most recent values taken
//since these values should only be 0-4095(?) we don't needs more than two byte each
uint16_t nraw = 0;
uint16_t nenv = 0;
void loop() {
  static uint32_t last_check; //to keep track of the last time we printed data
  if(micros() - last_check >= sample_rate){
    if (Serial.availableForWrite() > 8) { //since we're writing 8 bits to cereal (4b+2b+2b) we wanna make sure we have enough space to do so; helps with sync
      last_check = micros(); //update when we'll wanna print next
      //read in the analouge values
      nraw = analogRead(MYOWARE_RAW);
      nenv = analogRead(MYOWARE_ENV);
      //write to serial
      Serial.write(last_check);
      Serial.write(nraw);
      Serial.write(nenv);
      //write data to bluetoothserial
      SerialBT.write(last_check);
      SerialBT.write(nraw);
      SerialBT.write(nenv);
    }
  }
}

//since we need to conver values to strings when we output them
