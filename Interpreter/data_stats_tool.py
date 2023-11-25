# usb vs bluetooth graph data
# T&R, 2022/2/16

# the stuff we need to make graphs
import plotly.graph_objects as go  # used to make the skew graphs
import numpy as np


# parse the data
# this assumes arduino serial monitor has been set to have timestamps enabled
# eg format of each line looks roughly like: 14:17:57.637 -> 60733167,1867,549

def parsedata(data):
    times = []  # times when things happen
    raw = []  # raw values
    env = []  # env values
    dt = []  # changes in time
    # values = [] #actual readings at times
    Lines = data.readlines()
    count = 0
    usb = False
    
    for line in Lines:
        if ' ' in line:  # Dealing with USB data
            usb = True
            tvd = line.split()  # 0 in the array should be the time and the rest should be the data
            readings = tvd[2].split(",")
            times.append(int(readings[0]))
            raw.append(int(readings[1]))
            env.append(int(readings[2]))
        else:
            readings = line.split(",")  # microtime looks like ['100532254', '1802', '0\n'] eg, [time, raw, env\n]
            # print(microtime)
            times.append(float(readings[0]))

        # get the delta t values
        if count > 1:
            dt.append(times[count] - times[count - 1])
        # print(count + " - t1:" times[count] + "; t2:" + times[count-1])
        count += 1  # iterate the line number

    if usb: skipCount(times)
    return [times, raw, env, dt]


def comparedata(bluetooth, usb):
    different = 0
    same = 0
    for i in range(len(bluetooth)):
        # print("bt: " + str(bluetooth[i]) + ", usb: " + str(usb[i]))
        if bluetooth[i] == usb[i]:
            same += 1
        else:
            different += 1
    print("Same: %d" % same)
    print("Different: %d" % different)


def extranalyze(data, print_results):
    avg = 0
    count = 0  # sum of the values in data so far, used for calculating average
    lcount = 0  # the last value of our count
    cdips = 0  # the number of times that our count goes down (it should never do that)
    high = 0
    low = 0
    datarange = 0
    tbp = []  # to be popped, for helping clean up our data
    for i in range(len(data)):
        if data[i] > 0:
            count += data[i]  # sum the array
            if (count <= lcount):
                cdips += 1
            lcount = count
        else:
            tbp.append(i)

    # clean up our data some
    # used for removing/tracking negative time differences
    if len(tbp) > 0:
        for n in tbp:
            data.pop(n)

    avg = count / len(data)
    print("Sanity check average", avg == np.average(data))
    # keep track of high and low
    low = min(data)
    high = max(data)
    datarange = high - low

    if print_results:
        print("Results: ")
        print("average: {}μs".format(avg))
        print("maximum: {}μs".format(high))
        print("minimum: {}μs".format(low))
        print("range:   {}μs\n".format(datarange))
        print("Testing attributes: ")
        print("Drops in total before division for average: {}".format(cdips))
        print("Negative time differences: {}".format(len(tbp)))
    else:
        return [avg, high, low, datarange, cdips, len(tbp)]

# def nullCount(data):
# for i in range

def skipCount(data):
    skips = 0
    for i in range(len(data) - 1):
        if data[i] > data[i + 1]:
            skips += 1  # count a skip
            # print("t1: %d t2: %d" % (data[i], data[i+1]))
    print("Skips: %d" % skips)


# code that does stuff
# file1 = input("Bluetooth Path: ")
file2 = input("Path To Data: ")
# btdata = open(file1, "r")
data = open(file2, "r")

# compare deltas
# comparedata(parsebt(btdata), parseusb(usbdata))

# print(parsebt(btdata))
# print(parseusb(usbdata))
parsed = parsedata(data)[3]
# print(parsed)
extranalyze(parsed, True)
# skipCount(parsed) # this doesn't work because you're talking the difference in time not the actual times
# close the files once we're done
# btdata.close()
data.close()
