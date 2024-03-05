# important stuff
import sys
import time

# serial read
import serial

# serial stuff
ser = serial.Serial(baudrate=230400, timeout=None)  # serial class
# ser.set_buffer_size(rx_size = 256, tx_size = 256) # default buffer size is 2^16 =65536 #doesn't seem to do anything
ser.port = 'COM3'  # <<<<======== set the port IMPORTANT!!!! CHANGE THIS AS NEEDED!!!!!!!
# ser.setDTR(False) # this line makes the serial data readable
# ser.setRTS(False) # this line makes the serial data readable

# the string where we're gonna store our serial output
serial_record = b''

if __name__ == "__main__":
    print("Starting!")
    ser.open()
    ser.reset_input_buffer()
    #pawshake()
    print("telling the esp32 to start")
    ser.write(621)  # write some random data to let the esp32 know we're here
    if(ser.in_waiting):
        print(ser.in_waiting)
        ser.reset_input_buffer()

    #for just recording a few examples of serial_record at various sample rates
    start_time = time.time()
    while time.time() - start_time < 30:
        if(ser.in_waiting):
            print("reading from serial")
            serial_record += ser.read(ser.in_waiting)
    print("Serial Record: \n")
    print(serial_record)
