// Myoreader.ino: A sketch to log data from a MyoWare. Written by Bleddyn for the FFF, Nov. 9, 2021.
// Edits for consistency and sample rate controll made by Mecknavorz for the FFF, March 10, 2022-
// b7 able to achive consistent 1024 sample rate with minimal deviance
// b7.1 aims to send the data in an exact format for consistent reading, should help with bluetooth implementation

//the pins we're gonna be reading the myoware data from
#define MYOWARE_RAW 37 //raw values
#define MYOWARE_ENV 39 //envolope values

//ESP32Time rtc;
uint32_t myMicros = 0; //for keeping track of time
const int sample_rate = 966; //488 microseconds gives us a rate of 2048Hz, which is what many sEMG systems use
const int wait = 3 //wait time in seconds before the code should start running once synch is established

void setup() {
  // Disable watchdog timer reset.
  disableCore0WDT();
  
  //turn on serial
  Serial.begin(230400); //this speed helps ensure we can send data fast enough
  //wait for the controller to say something
  bool start = false;
  //if we still haven't got the start code
  while(!start){
    //621 arbitrary strt code? Needs testing.
    if(Serial.read() == 621){
      Serial.println("Start code recived, Reading from ESP32 in " + wait + " seconds...");
      start = true; //make sure our start time is set to true so we break the while loop
    }
  }
  //wait for time specified above
  //MAKE SURE VALUES MATCH WHAT IS BEING PRINTED
  delay(wait * 1000);
  
  myMicros = micros();
}

//the most recent values taken
//since these values should only be 0-4095(?) we don't needs more than two byte each
uint32_t nraw = 0;
uint32_t nenv = 0;
void loop() {
  static uint32_t last_check; //to keep track of the last time we printed data
  if(micros() - last_check >= sample_rate){
    if (Serial.availableForWrite() > 12) { //since we're writing 12 bits to cereal (4b+4b+4b) we wanna make sure we have enough space to do so; helps with sync
      last_check = micros(); //update when we'll wanna print next
      //read in the analouge values
      //Raw: 0-4095
      //Env: 0-4095
      nraw = analogRead(MYOWARE_RAW);
      nenv = analogRead(MYOWARE_ENV);
      //write to serial
      Serial.write(last_check);
      Serial.write(nraw);
      Serial.write(nenv);
    }
  }
}
