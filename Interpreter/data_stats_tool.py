#usb vs bluetooth graph data
#T&R, 2022/2/16

#the stuff we need to make graphs
import plotly.graph_objects as go #used to make the skew graphs
import numpy as np

#parse the bt data
def parsebt(data):
    times = [] #times when things happen
    dt = [] #changes in time
    #values = [] #actual readings at times

    Lines = data.readlines()
    count = 0
    for line in Lines:
        tvd = line.split() #0 in the array should be the time and the rest should be the data
        #get the times
        microtime = tvd[1].split(",")
        times.append(float(microtime[0]))

        #get the delta t values
        if count > 1:
            dt.append(times[count] - times[count-1])

        count +=1 #iterate the line number
    return dt

#parse the usb data, since it has a slightly different format
def praseusb(data):
    times = [] #times when things happen
    dt = [] #changes in time
    #values = [] #actual readings at times

    Lines = data.readlines()
    count = 0
    for line in Lines:
        tvd = line.split() #0 in the array should be the time and the rest should be the data
        #get the times
        microtime = tvd[2].split(",") #this tiny lil 2 is the only difference, probably could fit both functions together somehow but ehh
        #clean the data a bit
        times.append(int(microtime[0]))

        #get the delta t values
        if count > 1:
            dt.append(times[count] - times[count-1])
        #print(count + " - t1:" times[count] + "; t2:" + times[count-1])
        count +=1 #iterate the line number
    skipCount(times)
    return dt

def comparedata(bluetooth, usb):
    different = 0
    same = 0
    for i in range(len(bluetooth)):
        #print("bt: " + str(bluetooth[i]) + ", usb: " + str(usb[i]))
        if bluetooth[i] == usb[i]:
            same += 1
        else:
            different += 1
    print("Same: %d" % same)
    print("Different: %d" % different)

def extranalyze(data):
    avg = 0
    count = 0
    high = 0
    low = 999999999999
    datarange = 0
    for i in range(len(data)):
        if data[i] > 0:
            count += data[i] #sum the array
        #keep track of high and low
        if 0 < data[i] < low:
            low = data[i]
        elif i > high:
            high = data[i]
    
    avg = count / len(data)
    datarange = high - low
    print("average: %d" % avg)
    print("maximum: %d" % high)
    print("minimum: %d" % low)
    print("range:   %d" % datarange)

#def nullCount(data):
    #for i in range

def skipCount(data):
    skips = 0
    for i in range(len(data) - 1):
        if data[i] > data[i + 1]:
            skips += 1 #count a skip
            print("t1: %d t2: %d" % (data[i], data[i+1]))
    print("Skips: %d" % skips)

#code that does stuff
#file1 = input("Bluetooth Path: ")
file2 = input("USB path: ")
#btdata = open(file1, "r")
usbdata = open(file2, "r")

#comapre deltas
#comparedata(parsebt(btdata), praseusb(usbdata))

#print(parsebt(btdata))
#print(praseusb(usbdata))
extranalyze(praseusb(usbdata))

#close the files once we're done
#btdata.close()
usbdata.close()

