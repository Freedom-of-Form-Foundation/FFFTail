// Myoreader.ino: A sketch to log data from a MyoWare. Written by Bleddyn for the FFF, Nov. 9, 2021.
// Edits for consistency and sample rate control made by Mecknavorz for the FFF, March 10, 2022-
// b7 able to achieve consistent 1024 sample rate with minimal deviance
// b7.3 aims to integrate FreeRTOS techniques to ensure no time drift in samples as well as boost consistency

//FreeRTOS stuff
#if CONFIG_FREERTOS_UNICORE
#define ARDUINO_RUNNING_CORE 0
#else
#define ARDUINO_RUNNING_CORE 1
#endif 

#include "freertos/timers.h"

#include "esp_timer.h"

//the pins we're gonna be reading the myoware data from
#define MYOWARE_RAW 37 // raw values
#define MYOWARE_ENV 39 // envelope values

uint32_t myMicros = 0; // for keeping track of time
const int sample_rate = 100000; // 488 microseconds gives us a rate of 2048Hz, which is what many sEMG systems use
const int wait = 3; // wait time in seconds before the code should start running once synch is established
bool start = false; // used to help us control when the full code starts vs just listening to make sure the python end is up and running
bool sent_first = false; // used to know if we have already transmitted data or not
static uint32_t last_check; // to keep track of the last time we printed data
static uint32_t start_time; // used to zero times from the esp32's clock so that we start transmitting from zero
uint16_t nraw = 0; // most recent raw value
uint16_t nenv = 0; // most recent envelope value

hw_timer_t *Timer0_Cfg = NULL;

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

  // adding a duplicate time for identification potentially
  // since it's only an additional 4 bytes I don't expect it to impact speed significantly
  sample[8] = sample[0];
  sample[9] = sample[1];
  sample[10] = sample[2];
  sample[11] = sample[3];

  return true; //we want to make this not a void function to ensure that it completes before we send any data
}


//used for making sure our time samples are on corrected intervals
//using hardware timers usually results in them being ~3us off from exact (eg 997 instead of 1000)
uint32_t time_correction(uint32_t timestamp){
  uint32_t mod = 0;

  mod = timestamp % sample_rate;

  if (mod != 0){
    return timestamp - mod + sample_rate;
  } else {
    return timestamp;
  }
}


//we want this to execute on a timer every sample_rate microseconds
void IRAM_ATTR sendSample(){ //void * parameter //old parameters to use with FreeRTOS
    uint32_t corrected_time; // the value we'll crunch though our byteSample function
    if(Serial.availableForWrite() > 12) { // since we're writing 12 bits to serial (4b+2b+2b+4b) we wanna make sure we have enough space to do so; helps with sync
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
        corrected_time = time_correction(last_check - start_time);
      }
      // read in the analogue values
      // Raw: 0-4095
      // Env: 0-4095
      nraw = analogRead(MYOWARE_RAW);
      nenv = analogRead(MYOWARE_ENV);
        
      // convert everything to proper bytes for sending
      //Serial.println("corrected time: " + String(corrected_time));
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
  // makes sure our output isn't occasionally peppered with junk errors
  // also makes sure the code doesn't reset from running too little too fast :/ :/
  disableCore0WDT();
  
  myMicros = micros();

  Timer0_Cfg = timerBegin(0, 80, true); //configure timer zero to have pre-caller of 80; cause the esp32 is 80Mhz and we want to work with microsecond intervals
  timerAttachInterrupt(Timer0_Cfg, &sendSample, true);
  timerAlarmWrite(Timer0_Cfg, sample_rate, true);
  timerAlarmEnable(Timer0_Cfg);
}

void loop() {
}
