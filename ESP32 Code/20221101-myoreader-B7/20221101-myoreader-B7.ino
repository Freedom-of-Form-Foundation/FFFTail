// Myoreader.ino: A sketch to log data from a MyoWare. Written by Bleddyn for the FFF, Nov. 9, 2021.
// Edits for consistency and sample rate controll made by Mecknavorz for the FFF, March 10, 2022-
// b7 able to achive consistent 1024 sample rate with minimal deviance

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
int nraw = 0;
int nenv = 0;
void loop() {
  static uint32_t last_check; //to keep track of the last time we printed data
  if(micros() - last_check >= sample_rate){
    last_check = micros(); //update when we'll wanna print next
    //read in the analouge values
    nraw = analogRead(MYOWARE_RAW);
    nenv = analogRead(MYOWARE_ENV);
    //print to bluetooth
    Serial.print(String(last_check) + "," + String(nraw) + "," + String(nenv) + "\n");
    //print to serial
    SerialBT.print(String(last_check) + "," + String(nraw) + "," + String(nenv) + "\n");
  }
}
