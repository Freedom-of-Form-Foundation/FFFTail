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

#attempt at making the program read data fast and not have it be weirdly segmented
def smartRead():
    print("Oops! Not done yet!")

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
    ser.write(621)
    w = ser.readline()#.decode() #not sure if the decode is needed
    #do this last to make sure whatever we get from here is gonna be our code
    reset_input_buffer()

#maybe run this on it's own thread?
print("starting!")
ser.open() #open it
pawshake()
testEncoding()

'''
#animate the graph
count = 0
x = time.time()
#startWait()
while(count < 1024):
    #pg.plot(xs, ys, pen='r')
    #roughBuff()
    read()
    count += 1
    print(count)
y = time.time()
print(y-x)
'''
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
