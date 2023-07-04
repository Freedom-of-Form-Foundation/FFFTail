// Myoreader.ino: A sketch to log data from a MyoWare. Written by Bleddyn for the FFF, Nov. 9, 2021.
// Edits for consistency and sample rate controll made by Mecknavorz for the FFF, March 10, 2022-
// b7 able to achive consistent 1024 sample rate with minimal deviance
// b7.1 aims to send the data in an exact format for consistent reading, should help with bluetooth implementation

//the pins we're gonna be reading the myoware data from
#define MYOWARE_RAW 37 //raw values
#define MYOWARE_ENV 39 //envolope values

uint32_t myMicros = 0; //for keeping track of time
const int sample_rate = 966; //488 microseconds gives us a rate of 2048Hz, which is what many sEMG systems use
const int wait = 3; //wait time in seconds before the code should start running once synch is established
bool start = false; //used to help us control when the full code starts vs just listening to make sure the python end is up and running

void setup() {
  Serial.begin(230400);  //turn on serial; this speed helps ensure we can send data fast enough
  delay(500);
  while(!Serial); //make sure serial is up
  
  // Disable watchdog timer reset.
  //makes sure our output ins't occasionally peppered with junk errors
  //also makes sure the code doesn't reset from running too little too fast :/ :/
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
      Serial.println("Start signal recived, Sending myoware readings from ESP32 in " + String(wait) + " seconds...");
      start = true; //make sure our start time is set to true so we break the while loop

      //pause for wait seconds so that the python code has time to get ready
      delay(wait * 1000);
    }
  }
}

//in order to properly utilize serial write we need to convert our multi byte values
//We know exactly how many bytes we need for any given sample, as each data type takes up a set amount of bytes
//byte sample[8]; //byte array to store all the data we want to send in a given sample
byte sample[12]; //byte array to store all the data we want to send in a given sample
void byteSample(uint32_t t, uint16_t r, uint16_t e){
  //since time is stored as uint32_t, we need 4 bytes for it in the array
  sample[0] = (t >> 24) & 255;
  sample[1] = (t >> 16) & 255;
  sample[2] = (t >> 8) & 255;
  sample[3] = t & 255;
  //raw is uint_16, we need 2 bytes for it in the array
  sample[4] = (r >> 8) & 255;
  sample[5] = r & 255;
  //env is uint_16, we need 2 bytes for it in the array
  sample[6] = (e >> 8) & 255;
  sample[7] = e & 255;
  //adding a duplicate tijme for identification potentially
  //since it's only an additional 4 bytes I don't expect it to impact speed signifnicantly
  sample[8] = sample[0];
  sample[9] = sample[1];
  sample[10] = sample[2];
  sample[11] = sample[3];
}


//the most recent values taken
//since these values should only be 0-4095(?) we don't needs more than two byte each
uint32_t nraw = 0;
uint32_t nenv = 0;
void loop() {
  //Serial.println("Hewwo! rawr!"); //coment out after testing
  static uint32_t last_check; //to keep track of the last time we printed data
  if(micros() - last_check >= sample_rate){
    if (Serial.availableForWrite() > 12) { //since we're writing 12 bits to cereal (4b+2b+2b+4b) we wanna make sure we have enough space to do so; helps with sync
      last_check = micros(); //update when we'll wanna print next
      //read in the analouge values
      //Raw: 0-4095
      //Env: 0-4095
      nraw = analogRead(MYOWARE_RAW);
      nenv = analogRead(MYOWARE_ENV);
      //convert everything to proper bytes for sedning
      byteSample(last_check, nraw, nenv);
      //write to serial
      Serial.write(sample, sizeof(sample));
    }
  }
}
