#T&R 2023 (@Mecknavorz)
#important stuff
import sys
import time
#serial read
import serial
import io
#graph
import pyqtgraph as pg
import numpy as np
#serial stuff
ser = serial.Serial() #serial class
ser.baudrate = 230400 #set the baudrade

ser.port = 'COM3' #<<<<======== set the port IMPORTANT!!!! CHANGE THIS AS NEEDED!!!!!!!

#ser.setDTR(False) #this line makes the serial data readablle
#ser.setRTS(False) #this line makes the serial data readablle
#ser.timeout = 10 #safety timeout in seconds


#read 1 input line from the serial
#helps make sure everything is in sync
z = b''
def read():
    global z
    rc = 0 #return counter to make sure we do three at a time
    #we're trying to read ~19 bytes from serial
    #at 1024 samples:
    #- read(19) ~1.047
    #- read(1)+parse ~ 1.5 for 1/3; 4.6 for equivalent of 1024
    #- read_until(b'\n') = ~4.6
    #- readline = ~4.5
    '''From the results of these tests we can conclude that the best way forward is going to be read(n) and making sure we are sending the correct # of bytes at once'''
    
    #z = y[:-1].split(",") #[time, raw, env]
    while rc < 3:
        y = ser.read(12)
        if (y == b'\n') or (y ==b','):
            x = z
            z = b''
            #print(x)
            rc = rc + 1
            return x
        else:
            z = z+y
    #return z

#utf-16 should be the correct encoding for how we're sending it from arduino
#however I get random chars when I decode that so I think it's a scyn issue
#since we know we're looking for a message 12 characters long as long as we have a window (w) twice that size we should find the correct orientation by sliding accross it
#this code probabl won't be useful beyond these tests but who knows, here's to hoping!
def testEncoding():
    #printing the array, or segments of it gives a value such as: b'\x01\xf3\xe5\xc8\xf9\xe0\x8f\xd1IV&F\x1d+E\xe4+E\xab/Er1E'
    #printing just an individual byte gives us a value from 0-255
    w = ser.read(24)
    print("messing around with w[n]")
    for i in range(len(w)-8):
        p = []
        j = i+4
        #print(w[i:j].decode('utf-16'))
        p = w[i:j]
        print(p[0])
    print("just print(w): ")
    print(w)

#data storage for our graphs
#might merge this with the buffer eventually, but for now we're keeping it seprate
xs = [] #time
ys = [] #raw values
#y2s = [] #env values
lastcall = 0; #to try to help kep track of when we're calling the code to store stuff in the buffer
#the function which animates things
def roughBuff():
    #make sure we're storing to the right arays
    global xs
    global ys
    global lastcall
    #rouighly one tenth of our tample rate (1024) so swe should call this every 10th of a second
    #for i in range(1024):
    data = read() #read once from serial
    #print(data) #debugging stuff
    if len(z) > 2: #this makes sure we only record valid arrays
        if (z[0] != '') and (z[0] != '') and (z[0] != ''):
            #time = timecheck(int(data[0])) #convert out time to be poper for the graph; MIGHT BE REDUNDANT WITH NEW GRAPH?
            #add data to our axis
            xs.append(z[0]) 
            ys.append(z[1])
            #DO NOT DELETE THIS LINE
            #dump = data[2] #for some reason if you don't have this line it gives and out of bounds error on the previous line
    #print("ran rough buff at: {:f}".format(time.time()))
    lastcall = time.time()

#function we should call to try and make things in sync
#calling it pawshake instead of handshake because it's funny and furry
def pawshake():
    print("Performing pawshake...")
    shake = False #for tracking if we actually shook or not
    ser.write(621) #write some random data to let the esp32 know we're here
    #recoding  how much data is in the input/output buffers for later comparison
    oldout = ser.out_waiting
    oldin = ser.in_waiting
    #since the hsake hasn't been confirmed, keep running this loop to check until we get it confirmed
    while(not shake):
        #wait to see if the bytes has been sent
        '''SOMETHING TO CONSIDER:''' #should we check to see if it's zero or just one less than what it was when we started?
        if(ser.out_waiting < oldout):
            w = ser.readline()#.decode() #not sure if the decode is needed
            print(w[-104:-1]) #needs to be tailored to specific start message, current message is 52 char long w/2 end chars
            ser.write(621)
            #see of the ESP32 send a message back
            #trying this by looking at the previous in vaue instead of 
            if(ser.in_waiting > oldin):
                #clear the buffer so we don't read junk data by accident
                ser.reset_input_buffer()
                #update our shake so that we can do the rest of the things
                shake = True
        #if we did the shake we don't need to wait
        if not shake:
            time.sleep(.1) #sleep for .1 seconds before checking to see if theer was a response again
                
#attempt at making the program read data fast and not have it be weirdly segmented
def smartRead():
    #we know the incoming message should be 8 bytes
    #1 x uint32_t + 2 x uint16_t = 4 + 2*2 = 8
    #[0-3] = time of sample
    #[4-5] = raw value
    #[6-7] = env value
    
    #essentially check to make sure we have completed messages in there
    #need to implement some way of making sure we're always looking for the right amount of bytes
    if(ser.in_waiting % 8 == 0):
        #read one whole output
        m = ser.read(32)
        #need to decide if this is how I actually want to return values
        #does conversion/calculation need to be done elsewhere for speed?
        t = m[0:3]#.decode()
        r = m[4:5]#.decode()
        e = m[6:7]#.decode()
    print("Oops! Not done yet!")
    print(type(m))
    print("m:")
    for i in m:
        print("{j}".format(j=i))
    print("Time: {ti} \nRaw: {ra} \nEnv: {en}".format(ti=t, ra=r, en=e))
    print("Decoded - Time: {ti} \nRaw: {ra} \nEnv: {en}".format(ti=t.decode('utf-32'), ra=r.decode('utf-16'), en=e.decode('utf-16')))

#grab multiple same length samples and check to see if they remain aligned each time
passes = [] #for storing data
def alignCheck(pcnt):
    print("Prefomring Alignment check...")
    #for keeping track of which pass we're on
    #ocnt = pcnt
    while pcnt > 0:
        if ser.in_waiting > 32:
            m = ser.read(32)
            print("Successfully read {b} bytes from in_waiting!".format(b=len(m)))
            passes.append(m)
        pcnt = pcnt-1

    #just to make things look nicer/make the output clearer
    print("{c} passes of length {l}:".format(c=len(passes), l=len(passes[0])))
    #print and compare them all:
    for i in range(len(passes[0])):
        toPrint = ""
        for j in range(len(passes)):
            toPrint += "{b}\t".format(b=passes[j][i])
        print(toPrint)

#variation of align checker for use with SerialSpeedTest-USB2
#in short: it looks for this pattern: [prev entry], time[4 bytes], raw [2 bytes], env [2 bytes], time [4 bytes], [new entry]
#each sample is expected to be 12 bytes, with the 4 at the start and end being thwe time of the sample
#may change the pattern down the line, or for the final version SO BE AWARE
def timeAlignCheck(scnt):
    print("Performing verification via time alignment in samples...")
    rData = []
    #collect data
    while scnt > 0:
        if ser.in_waiting > 24:
            m = ser.read(24)
            print("Successfully read {b} bytes from in_waiting!".format(b=len(m)))
            #add the data from the buffer into our run's data
            rData += m
        rcnt = rcnt-1

    #look for the data we wanna see by running the pattern across it
    step = 0 #used to keep track of alignment, starts from zero
    found = False #as long as we haven't found it keep trying
    #variables to keep track of where we're looking
    fs = 0 #first start
    fe = 3 #first end
    ss = 8 #second start
    se = 11 #second end
    #make sure to check for step of length equal to sample size
    while (found == False) or (step > 11):
        if (rcnt[fs:fe] == rcnt[ss:se]):
            print("Alignment found! Shifting start by {n} bytes...".format(n=step))
                found = True #set found to true to get out of the loop
                return step
        else:
            #if the values don't match the expected pattern, keep going
            step += 1
    #print an error if we didn't find it
    if step > 11:
        print("Test Failed, Expected pattern not found :( :(")
        
#maybe run this on it's own thread?
print("starting!")
ser.open() #open it
pawshake()
#smartRead()
#alignCheck(8)
alignment = timeAlignCheck(8)
ser.close()
