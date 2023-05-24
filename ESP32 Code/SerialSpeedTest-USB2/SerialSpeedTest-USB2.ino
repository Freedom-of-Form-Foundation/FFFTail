// SerialSpeedTest-USB2: sketch for helping test out the pawshake function and ensure sync between ESP32 and Python code
// Right now A derivative of b7.1 + SerialSpeedTest-USB1; Raw and env stay constant through transmission
// helpful for ensuring alignment to make sure we can be read from easily
// Made by Mecknavorz (T&R), for the FFF, January 8th, 2023

#define MYOWARE_RAW 37
#define MYOWARE_ENV 39

//ESP32Time rtc;
uint32_t myMicros = 0;
const int sample_rate = 966; //488 microseconds gives us a rate of 2048Hz, which is what many sEMG systems use
//these only need to store values between 0-4095; so they don't need to be that big
uint16_t nraw = 0;
uint16_t nenv = 0;
bool start = false;
int wait = 3;

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
      
      Serial.println("Start signal recived, Sending myoware readings from ESP32 in " + String(wait) + " seconds; Look for Raw: " + String(nraw) + " and Env: " + String(nenv));
      start = true; //make sure our start time is set to true so we break the while loop

      //pause for wait seconds so that the python code has time to get ready
      //might need to adjust this value to account for the second delay?
      delay((wait * 1000) - 100);
    }
    //just wait a bit before trying again
    delay(100);
  }
  //alignHelper();
}

//send out a pattern of bytes of a known length/valuyes
//this allows us to look for it at the start when we run our python code
//which in turn allows us to determine where things are divided for the output
void alignHelper(){
  //using prime numbers in order becaues the chance of that sequence appearing at random should be fairly low
  byte helper[16] = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 41, 43, 47, 53, 59};
  Serial.write(helper, 16);
}


//in order to properly utilize serial write we need to convert our multi byte values
//We know exactly how many bytes we need for any given sample, as each data type takes up a set amount of bytes
byte sample[8]; //byte array to store all the data we want to send in a given sample
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
}

void loop() {
  static uint32_t last_check; //to keep track of the last time we printed data
  if(micros() - last_check >= sample_rate){
    if (Serial.availableForWrite() > 12) { //since we're writing 12 bits to cereal (4b+4b+4b) we wanna make sure we have enough space to do so; helps with sync
      last_check = micros(); //update when we'll wanna print next
      byteSample(last_check, nraw, nenv);
      //Raw: 0-4095   Env: 0-4095
      //write to serial
      Serial.write(sample, sizeof(sample));
    }
  }
}
