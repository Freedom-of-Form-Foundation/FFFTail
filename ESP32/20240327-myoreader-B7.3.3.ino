// Myoreader.ino: A sketch to log data from a MyoWare. Written by Bleddyn for the FFF, Nov. 9, 2021.
// Edits for consistency and sample rate controll made by Mecknavorz for the FFF, March 10, 2022-
// b7 able to achive consistent 1024 sample rate with minimal deviance
// b7.3 aims to integrate hardware timer techniques to ensure no time drift in samples as well as boost consistency
// b7.3.3 fixes timestamp correction code from b7.3.2

#include "esp_timer.h"

//the pins we're gonna be reading the myoware data from
#define MYOWARE_RAW 37 // raw values
#define MYOWARE_ENV 39 // envolope values

uint32_t myMicros = 0; // for keeping track of time
const int sample_rate = 1000; // 488 microseconds gives us a rate of 2048Hz, which is what many sEMG systems use
const int wait = 3; // wait time in seconds before the code should start running once synch is established
bool start = false; // used to help us control when the full code starts vs just listening to make sure the python end is up and running
bool sent_first = false; // used to know if we have already transmitted data or not

TimerHandle_t tmr;

// in order to properly utilize serial write we need to convert our multi byte values
// We know exactly how many bytes we need for any given sample, as each data type takes up a set amount of bytes
byte sample[12]; // byte array to store all the data we want to send in a given sample
bool byteSample(uint32_t t, uint16_t r, uint16_t e){
  // since time is stored as uint32_t, we need 4 bytes for it in the array
  sample[0] = (t >> 24) & 255;
  sample[1] = (t >> 16) & 255;
  sample[2] = (t >> 8) & 255;
  sample[3] = t & 255;
  
  // raw is uint_16, we need 2 bytes for it in the array
  sample[4] = (r >> 8) & 255;
  sample[5] = r & 255;
  
  // env is uint_16, we need 2 bytes for it in the array
  sample[6] = (e >> 8) & 255;
  sample[7] = e & 255;
  
  // adding a duplicate tijme for identification potentially
  // since it's only an additional 4 bytes I don't expect it to impact speed signifnicantly
  sample[8] = sample[0];
  sample[9] = sample[1];
  sample[10] = sample[2];
  sample[11] = sample[3];
  
  return true; //we want to make this not a void function to ensure that it completes before we send any data
}

//used for making sure our time samples are on corrected intervals
//using hardware timers usually results in them being ~3us off from exact (eg 997 instead of 1000)
uint32_t time_correction(uint32_t timestamp){
  uint32_t mod = timestamp % sample_rate;
  if(timestamp != 0){
    if(timestamp < sample_rate){
      return sample_rate;
    } else if (mod != 0){
      return timestamp - mod  + sample_rate;
    } else{
      return timestamp;
    }
  } else{
    return timestamp;
  }
}

// all the variables which used to be in loop() which we are getting rid of
static uint32_t last_check; // to keep track of the last time we printed data
static uint32_t start_time; // used to zero times from the esp32's clock so that we start transmitting from zero
  
// the most recent values taken
// since these values should only be 0-4095(?) we don't needs more than two byte each
uint16_t nraw = 0;
uint16_t nenv = 0;

hw_timer_t *Timer0_Cfg = NULL;

//we want this to execute on a timer every sample_rate microseconds
void IRAM_ATTR sendSample(){ //void * parameter //old parameters to use with FreeRTOS
  //if(collected < num_samples){
    uint32_t corrected_time; // the value we'll crunch though our byteSample function
    if(Serial.availableForWrite() > 12) { // since we're writing 12 bits to cereal (4b+2b+2b+4b) we wanna make sure we have enough space to do so; helps with sync
      //consider adding function to ensure samples are multiples of our sample rate in us
      //may hold off, could mess with precision
      if(!sent_first){
        // this makes sure we set the start_time to when we start transmitting data
        // this way we can make sure that our first data sample is at zero
        start_time = micros(); // update when we'll wanna print next
        last_check = start_time; // this is to make sure we don't execute the next sample check too early
        corrected_time = 0;
        sent_first = true;
      } else {
        last_check = micros(); // update recorded time
        // this makes it so the time we return is aligned with when we started transmitting and not when the esp32 turned on
        //corrected_time = last_check - start_time;
        corrected_time = time_correction(last_check - start_time);
      }
      // read in the analouge values
      // Raw: 0-4095
      // Env: 0-4095
      nraw = analogRead(MYOWARE_RAW);
      nenv = analogRead(MYOWARE_ENV);
      
      // convert everything to proper bytes for sedning
      byteSample(corrected_time, nraw, nenv);
      // write to serial
      Serial.write(sample, sizeof(sample));
    }
}

void setup() {
  Serial.begin(230400);  // turn on serial; this speed helps ensure we can send data fast enough
  delay(500);
  while(!Serial); // make sure serial is up
  
  // Disable watchdog timer reset.
  // makes sure our output ins't occasionally peppered with junk errors
  // also makes sure the code doesn't reset from running too little too fast :/ :/
  disableCore0WDT();
  
  delay(5000);
  
  myMicros = micros();

  Timer0_Cfg = timerBegin(0, 80, true); //configure timer zero to have precaller of 80; cause the esp32 is 80Mhz and we want to work with microsecond intervauls
  timerAttachInterrupt(Timer0_Cfg, &sendSample, true);
  timerAlarmWrite(Timer0_Cfg, sample_rate, true);
  timerAlarmEnable(Timer0_Cfg);
}

void loop(){
}
