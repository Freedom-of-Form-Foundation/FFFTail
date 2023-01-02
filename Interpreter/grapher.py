#Grapher v1 - made to read serial data from the ESP32 EMG set up
#Freedom of Form Foundationh
#T&R, 2022/8/25


'''Imports'''
#the stuff we need to make graphs
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
import numpy as np
import random
#serial read
import serial
import io
#threading
import threading


'''Global Vairables and Setup'''
#serial stuff
ser = serial.Serial() #serial class
ser.baudrate = 115200 #set the baudrade

ser.port = 'COM3' #<<<<======== set the port IMPORTANT!!!! CHANGE THIS AS NEEDED!!!!!!!

ser.setDTR(False) #this line makes the serial data readablle
ser.setRTS(False) #this line makes the serial data readablle
ser.timeout = 10 #safety timeout in seconds
#maybe run this on it's own thread?
ser.open() #open it

#graph stuff
style.use('bmh')
fig = plt.figure()
ax1 = fig.add_subplot(1,1,1)
ax1.set_xlim(0, 5000000, auto=False) #This should limit the size of our graph to be ~5 seconds of samples
#ax1.set_xticks(ticks, labels=None, *, minor=False, **kwargs) #used for determining spacing of the labels on the x axis

#our buffers for storing recorded data
#giving all the buffers a default length of our target frequency
#so the buffer should fill up after (ideally) one second of recording
raw_buff = [0] * 1024
env_buff = [0] * 1024
time_buff = [0] * 1024

#arrays for recorded data
raw_rec = []
env_rec = []
time_rec = []

'''Functions'''
#parse the usb data
#this version is designed to read from a saved buffer on the python machine
#Doing this because I'm not confident in it running fast enough to keep up with the ESP32 without a buffer
#and syncing to make sure we're drawing data fast enough might me difficult
'''this function might be redundant leaving here just in case
def praseusb(buff_data):
    times = [] #times when things happen
    raw = [] #raw values of the emg
    env = [] 

    #instead of reading from a file this should either read straight from serial (less ideal?)
    #or read from a buffer array where all the data is stored in order to make sure we read fast enoguh
    for data in buff_data:
        prep = data.decode() #decode the byte into a string
        #we go from 0 to -1 in order to remove the \n
        parsed = prep[:-1].split(",") #0 = microsecond time, 1 = raw, 2, env
        #append all the data to what we're gonna output and convert it to the right type
        times.append(int(parsed[0]))
        raw.append(int(parsed[1]))
        env.append(int(parsed[2]))
    
    return [times, raw, env]
'''

#read 1 input line from the serial
#helps make sure everything is in sync
def read():
    y = ser.readline().decode()
    z = y[:-1].split(",") #[time, raw, env]
    #print(z)
    return z

#our handy dandy little function to convert the time in us to value within an ideally 5 second sample range
#the number 5000000 comes up a lot because we want to contrast our measurements vs an objective 5 seconds in us (eg, 5 Million microseconds)
stime = 0
def timecheck(us):
    global stime #make sure we are using the right stime
    #if the program is just starting, our start time is gonna be whatever the board's first output is
    if stime == 0:
        stime = us
        return stime
    #calculate our new time to graph, simple difference between out start time and our current time
    ntime = us-stime
    #if we are over fivve seconds then crop the difference to be in our window and move our starting time 
    if ntime > 5000000:
        stime =  us + 5000000 #move our start time window to be an exact five seconds after our previous time
        return ntime - 5000000
    #if we are neither at zero nor over 5 seconds, just return our graph time
    else:
        return ntime 

#record t seconds and then send it to a file, clear storage    
def record(t):
    st = time_buff[0] #get our start time from the beginning of the buffer, might change this as needed
    et = st + (t * 1000000) #convert seconds to miliseconds and add it to our start to get the desired end time
    #while st < et:

#data storage for our graphs
#might merge this with the buffer eventually, but for now we're keeping it seprate
xs = [] #time
ys = [] #raw values
#y2s = [] #env values
#the function which animates things 
def animate(i):
    global xs
    global ys
    #https://matplotlib.org/3.5.1/gallery/animation/simple_anim.html <=try stuff from here? UNUSED COMMENT
    #gonna try to premtively load some samples into the array before adding them to the graph
    #not sure if this will help with speed
    for i in range(102):
        data = read()
        if len(data) > 2: #this makes sure we only record valid arrays
            print(data)
            if (data[0] != '') and (data[0] != '') and (data[0] != ''):
                time = timecheck(int(data[0])) #convert out time to be poper for the graph
                #add data to our axis
                xs.append(time) 
                ys.append(data[1])
                '''DO NOT DELETE THIS LINE'''
                #dump = data[2] #for some reason if you don't have this line it gives and out of bounds error on the previous line

    
    #this function should reset the graphs when there's a time reset
    #when that happens the most recent thing appended to the list would be smaller than the penultimate
    #check if the list has more than two items,
    #And if the most recent item added is smaller than our penultimate item
    #clear the list
    #*assumes data input is not abnormal, time should only flow forward
    if (len(xs) > 2) and (xs[-1] < xs[-2]):
        ys.clear()
        xs.clear()

    #draw the graphs
    ax1.clear()
    ax1.plot(xs, ys, label="Raw Vales") #to plot env as well we can just past this again but with env_buff instead of raw
    
    #formatting
    plt.xticks(rotation=45, ha="right")
    plt.subplots_adjust(bottom=0.30)
    #plt.axis([None, None, 0, 1.1]) #Limits the size of the plot
    #labels and the like
    plt.title("Myowear serial Feed")
    plt.ylabel("Raw")
    plt.xlabel("Time")
    plt.legend()


#while the port is open we want to read from it
#might change this as needed to be different conditions
#actually animate the graph

live = animation.FuncAnimation(fig, animate, interval=100) #i don't know if the function will be able to animate this fast if not the buffers should help
plt.show()
#ser.close() #don't wanna leave this open ofc

''' test working code for reading and printing from serial in parsed format, given the above poening <- wtf kinda typo is that
DELETE THIS AND FACE THE WRATH OF THE MIGHTY HYDRA
#format is [time, raw, env]
while i >0:
    y = ser.readline().decode()
    z = y[:-1].split(",")
    print(z)
    i = i-1
'''

''' Bogus array removal; makes sure only valid data arrays are accepted
Unsure of what error rate is but seems to print out # in range at least
for i in range(102):
    data = read()
    if len(data) > 2:
        print(data)
        time = timecheck(int(data[0])) #convert out time to be poper for the graph
        #add data to our axis
        xs.append(time) 
        ys.append(data[1])
'''
