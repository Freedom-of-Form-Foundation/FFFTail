// SerialSpeedTest-USB2: simple sketch for helping test out the pawshake function and ensure sync between ESP32 and Python code
//Right now A derivative of b7.1 + SerialSpeedTest-USB1; Raw and env stay constant through transmission
// Made by MEcknavorz (T&R), for the FFF, January 8st, 2023

#define MYOWARE_RAW 37
#define MYOWARE_ENV 39

//ESP32Time rtc;
uint32_t myMicros = 0;
const int sample_rate = 966; //488 microseconds gives us a rate of 2048Hz, which is what many sEMG systems use
uint32_t nraw = 0;
uint32_t nenv = 0;

void setup() {
  Serial.begin(230400);
  delay(500);
  while(!Serial); //make sure serial is up
  
  // Disable watchdog timer reset.
  disableCore0WDT();

  pawShake(); //preform the pawshake to make sure both ends are synched
  
  myMicros = micros();
}

//added this function because for some reason trying to run some of this in setup didn't work???
void pawShake(){
  Serial.println("ESP32 started, waiting for pawshake to finish...");   //print a message just to make sure we did indeed start
  //if we still haven't got the start code
  while(!start){
    //see if any bites have been sent to serial
    if(Serial.available() > 0){
      
      //setting these so we have a constant value to search for; to help w/checking sync
      //doing it this way helps makes sure that the bits we're sending will be in the format they would be in the real code
      nraw = analogRead(MYOWARE_RAW); //read the raw values in
      nenv = analogRead(MYOWARE_ENV);
      
      Serial.println("Start signal recived, Sending myoware readings from ESP32 in " + String(wait) + " seconds; Look for Raw: " + String(nraw) + " and Env: " + String(nevn));
      start = true; //make sure our start time is set to true so we break the while loop

      //pause for wait seconds so that the python code has time to get ready
      //might need to adjust this value to account for the second delay?
      delay((wait * 1000) - 100);
    }
    //just wait a bit before trying again
    delay(100);
  }
}

void loop() {
  static uint32_t last_check; //to keep track of the last time we printed data
  if(micros() - last_check >= sample_rate){
    if (Serial.availableForWrite() > 12) { //since we're writing 12 bits to cereal (4b+4b+4b) we wanna make sure we have enough space to do so; helps with sync
      last_check = micros(); //update when we'll wanna print next
      //read in the analouge values
      //Raw: 0-4095   Env: 0-4095
      //write to serial
      Serial.write(last_check);
      Serial.write(nraw);
      Serial.write(nenv);
    }
  }
}
