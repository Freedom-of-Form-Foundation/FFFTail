// Myoreader.ino: A sketch to log data from a MyoWare. Written by Bleddyn for the FFF, Nov. 9, 2021.
// Edits for consistency and sample rate controll made by Mecknavorz for the FFF, March 10, 2022.

#include "BluetoothSerial.h"
//#include "ESP32Time.h"

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Bluetooth is not enabled! Please run `make menuconfig` to enable it
#endif

#define MYOWARE_RAW 37
#define MYOWARE_ENV 39

BluetoothSerial SerialBT;

//ESP32Time rtc;
long unsigned int myMicros = 0;
const int sample_rate = 488; //488 microseconds gives us a rate of 2048Hz, which is what many sEMG systems use

//------------
//buffer stuff
//------------
//"the Buffer" - 3 array storing the time, raw and env which we access when we want to print
int bufferTime[500];
int bufferRaw[500];
int bufferEnv[500];
//inexes to keep track of where the serial and sensor are in the buffer
int serial_id = 0; //index for where serial is
int sensor_id = 0; //index for where the sensor is


void setup() {
  Serial.begin(115200);
  SerialBT.begin("Myoreader"); //Bluetooth device name
  Serial.println("The device started, now you can pair it with bluetooth!");

  // Disable watchdog timer reset.
  disableCore0WDT();
  
  delay(100);
  
  myMicros = micros();
  Serial.print(myMicros); Serial.println(",Raw value (0--4095),Env value (0--4095)");
  SerialBT.print(myMicros); SerialBT.println(",Raw value (0--4095),Env value (0--4095)");
}

uint rawVal = 0;
uint envVal = 0;

//-----------------------------------------------------
//the functions and code that does stuff (end of setup)
//-----------------------------------------------------

void loop() {
  //make sure we stay within the bound of our buffer
  //if this cause problem makke it one if statement instead
  //alteratively try making sure that each if is around it's needed function, eg:
  //if(sensor_id){sensor_manager};
  //if(serial_id)(serial_manager);
  if(serial_id == 499){
    sensor_id = 0;
    serial_id = 0;
  }
  //if(serial_id == 499){sensor_id = 0;}
  //attempt at sample rate control
  if(sensor_id <= 499){sensor_manager();} //collect data from the sensor
  static unsigned int long prev_out; //to keep track of the last time we printed data
  if(micros() - prev_out >= sample_rate){
    prev_out += (unsigned) micros(); //update when we'll wanna print next
    serial_manager(); //print the data
  }
}

void sensor_manager(){
  //trying this with analogue read like above, but might try with digital read to see if it affects speed
  //record the data
  int nraw = analogRead(MYOWARE_RAW);
  int nenv = analogRead(MYOWARE_ENV);
  myMicros = (unsigned) micros(); //record the time
  int nid = sensor_id + 1; //iterate the index for the sensor
  if (nid != serial_id) {
    bufferTime[sensor_id] = myMicros;
    bufferRaw[sensor_id] = nraw;
    bufferEnv[sensor_id] = nenv;
    sensor_id++;
  }
}

void serial_manager(){
  //might try making this a while loop to see if that works like I wawnt
  if(serial_id != sensor_id){ //make sure the serial isn't at the sensor so we actually have data to print
    //print the data
    Serial.print(String(bufferTime[serial_id]) + "," + String(bufferRaw[serial_id]) + "," + String(bufferEnv[serial_id]) + "\n");
    SerialBT.print(String(bufferTime[serial_id]) + "," + String(bufferRaw[serial_id]) + "," + String(bufferEnv[serial_id]) + "\n");
    //increment the serial id
    serial_id++;
  }
}
