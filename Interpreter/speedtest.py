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
        y = ser.read(8)
        if (y == b'\n') or (y ==b','):
            x = z
            z = b''
            #print(x)
            rc = rc + 1
            return x
        else:
            z = z+y
    #return z




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

#maybe run this on it's own thread?
ser.open() #open it
#animate the graph
count = 0
x = time.time()
#startWait()
while(count < 3072):
    #pg.plot(xs, ys, pen='r')
    #roughBuff()
    read()
    count += 1
y = time.time()
print(y-x)

'''
#the function which animates things
def roughBuff():
    #make sure we're storing to the right arays
    global xs
    global ys
    global lastcall
    #rouighly one tenth of our tample rate (1024) so swe should call this every 10th of a second
    #for i in range(1024):
    data = read() #read once from serial
    z = data[:-1].split(",") #[time, raw, env]
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

#function for trying to sync up reading from serial with the esp32's output
def startWait():
    started = 0
    while not started:
        y = ser.read(1)
        #print(y)
        if y == b'\n':
            started += 1
            print('go')
'''
