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
//"the Buffer" - 2d array storing the time, raw and env which we access when we want to print
//sbuffer[n][m]
//n = Our input data types: 0 = Time; 1 = Raw; 2= Env
//m = buffer length
int sbuffer[3][500];
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
int nprint = 0;
void loop() {
  //make sure we stay within the bound of our buffer
  //when we reach full buffer, print
  if(sensor_id == 500){
    sensor_id = 0;
    serial_manager(); //prints the buffer
  }
  //collect data from the sensor
  if(sensor_id <= 499){
    sensor_manager();
    delayMicroseconds(sample_rate); //this delay of microseconds will give us a sample rate of 2048Hz ideally
  }
}

void sensor_manager(){
  //trying this with analogue read like above, but might try with digital read to see if it affects speed
  //record the data
  int nraw = analogRead(MYOWARE_RAW);
  int nenv = analogRead(MYOWARE_ENV);
  myMicros = micros(); //record the time
  //add the recorded data to the array
  sbuffer[0][sensor_id] = myMicros;
  sbuffer[1][sensor_id] = nraw;
  sbuffer[2][sensor_id] = nenv;
  //iterate our tracker
  sensor_id++;
}

void serial_manager(){
  //this should run ever buffer length * saple rate seconds
  //determine the length of the buffer in bytes, this will be used for printing
  int datalen = sizeof(sbuffer);
  //print the buffer
  Serial.write(sbuffer, datalen);
}
