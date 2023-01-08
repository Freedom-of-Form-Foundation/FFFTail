// SerialSpeedTest-USB1: simple sketch for helping measure speed of usb output of ESP32 chip.
// Made by MEcknavorz (T&R), for the FFF, January 8st, 2023

#define MYOWARE_RAW 37
#define MYOWARE_ENV 39

//ESP32Time rtc;
uint32_t myMicros = 0;
const int sample_rate = 488; //488 microseconds gives us a rate of 2048Hz, which is what many sEMG systems use

void setup() {
  Serial.begin(230400);
  Serial.println("The device started, now you can pair it with bluetooth!");

  // Disable watchdog timer reset.
  disableCore0WDT();
  
  delay(100);
  
  myMicros = micros();
  Serial.print(myMicros); Serial.println(",Raw value (0--4095),Env value (0--4095)");
}

int nraw = 0;
int nenv = 0;
void loop() {
  static uint32_t last_check; //to keep track of the last time we printed data
  if(micros() - last_check >= sample_rate){
    last_check = micros(); //update when we'll wanna print next
    nraw = analogRead(MYOWARE_RAW);
    nenv = analogRead(MYOWARE_ENV);
    Serial.print(String(last_check) + "," + String(nraw) + "," + String(nenv) + "\n");
  }
}
