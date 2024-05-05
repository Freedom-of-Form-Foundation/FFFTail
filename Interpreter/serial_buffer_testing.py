# important stuff
import sys
import time

# serial read
import serial

# serial stuff
ser = serial.Serial(baudrate=230400, timeout=None)  # serial class
# ser.set_buffer_size(rx_size = 256, tx_size = 256) # default buffer size is 2^16 =65536 #doesn't seem to do anything
verbose = False
ser.port = 'COM3'  # <<<<======== set the port IMPORTANT!!!! CHANGE THIS AS NEEDED!!!!!!!
# ser.setDTR(False) # this line makes the serial data readable
# ser.setRTS(False) # this line makes the serial data readable

# the string where we're gonna store our serial output
serial_record = b''

# function we should call to try and make things in sync
# calling it pawshake instead of handshake because it's funny and furry
def pawshake():
    print("Performing pawshake...")
    shake = False  # for tracking if we actually shook or not
    ser.write(621)  # write some random data to let the esp32 know we're here
    # recoding  how much data is in the input/output buffers for later comparison
    oldout = ser.out_waiting
    oldin = ser.in_waiting
    # since the shake hasn't been confirmed, keep running this loop to check until we get it confirmed
    while not shake:
        # wait to see if the bytes has been sent
        '''SOMETHING TO CONSIDER:'''  # should we check to see if it's zero or just one less than what it was when we started?
        if ser.out_waiting < oldout:
            w = ser.readline()  # .decode() # not sure if the decode is needed
            print(w[-104:-1])  # needs to be tailored to specific start message, current message is 52 char long w/2 end chars
            ser.write(621)
            # see of the ESP32 send a message back
            # trying this by looking at the previous in value instead of
            if ser.in_waiting > oldin:
                # clear the buffer so we don't read junk data by accident
                ser.reset_input_buffer()
                # update our shake so that we can do the rest of the things
                shake = True
        # if we did the shake we don't need to wait
        if not shake:
            time.sleep(.1)  # sleep for .1 seconds before checking to see if there was a response again


if __name__ == "__main__":
    print("Starting!")
    ser.open()
    ser.reset_input_buffer()
    #pawshake()
    print("telling the esp32 to start")
    '''ser.write(621)  # write some random data to let the esp32 know we're here
    if(ser.in_waiting):
        print(ser.in_waiting)
        ser.reset_input_buffer()'''
    pawshake()

    #for just recording a few examples of serial_record at various sample rates
    start_time = time.time()
    while time.time() - start_time < 5:
        if(ser.in_waiting):
            if(verbose):
                print("reading from serial")
            serial_record += ser.read(ser.in_waiting)
    print("Serial Record: \n")
    print(serial_record)
