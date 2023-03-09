#quick grapher for graphing recorded data files taken from the arduino serial monitor
#Made by Mecknhavorz (T&R) for the Freedom of Form Foundationm, March 7th 2023

'''Imports'''
#the stuff we need to make graphs
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
import numpy as np
import math

'''main functions'''
#parse the usb data, since it has a slightly different format
#this assumes arduino serial monitor has been set to have timestamps enabled
#eg format of each line looks roughly like: 14:17:57.637 -> 60733167,1867,549
def parse(data):
    times = [] #times when things happen
    raw = [] #raw values
    env = [] #env values
    dt = [] #changes in time
    #values = [] #actual readings at times

    Lines = data.readlines()
    count = 0
    for line in Lines:
        tvd = line.split() #0 in the array should be the time and the rest should be the data
        #get the times
        readings = tvd[2].split(",") #this tiny lil 2 is the only difference, probably could fit both functions together somehow but ehh
        #add the data we want to the arrays we want
        times.append(int(readings[0]))
        raw.append(int(readings[1]))
        env.append(int(readings[2]))

        #get the delta t values
        if count > 1:
            dt.append(times[count] - times[count-1])
        #print(count + " - t1:" times[count] + "; t2:" + times[count-1])
        count +=1 #iterate the line number
    return [times, raw, env, dt]

#taking this fucntion from the data_stats_tool.py file
#thought it would be nice to also ahve access to this information on the graph
def extranalyze(data):
    avg = 0
    count = 0 #sum of the values in data so far, used for calculating average
    lcount = 0 #the last value of our count
    cdips = 0 #the number of times that our count goes down (it should never do that)
    high = 0
    low = 0
    datarange = 0
    tbp = [] #to be popped, for helping clean up our data
    #to check and make sure our count isn't dropping for some reason
    for i in range(len(data)):
        if data[i] > 0:
            count += data[i] #sum the array
            if(count <= lcount):
                cdips += 1
            lcount = count
        else:
            tbp.append(i)

    #clean up our data some
    #used for removing/tracking negative time differences
    if len(tbp) > 0:
        for n in tbp:
            data.pop(n)
    
    avg = count / len(data)
    #keep track of high and low
    low = min(data)
    high = max(data)
    datarange = high - low
    return [avg, high, low, datarange, cdips, len(tbp)]

#actually graph the info we want
def quickgraph(parsed, extradata):
    #a bit of extra data formatting
    st = parsed[0][0]
    #zero our times for a neater end graph
    for i in range(len(parsed[0])):
        parsed[0][i] = (parsed[0][i] - st) / 1000000
    fig, ax = plt.subplots()
    #add our data to the graph
    ax.plot(parsed[0], parsed[1], label='Raw')
    ax.plot(parsed[0], parsed[2], label='Env')
    
    #formatting stuff:
    #this method of determining time window might break for recordings over 16 minutes or that happen near the overlfow reset
    plt.title("Recorded Values over {s} seconds".format(s=parsed[0][-1]))
    ax.set_xlabel('Time')
    ax.set_ylabel('Raw and Env')
    ax.legend() #to help differentiate the values being graphed
    ax.grid(True)
    #add the other info we want displayed, eg consistency stuff
    extratext = 'Consistency Results:\n Average delay between samples: {a}μs\n Maximum: {h}μs\n Minimum: {l}μs\n Range: {r}μs\n\n Testing Attributes:\n Drops in total before divison for average: {c}\n Negative time differences: {n}'.format(
        a=round(extradata[0], 2), h=extradata[1], l=extradata[2], r=extradata[3], c=extradata[4], n=extradata[5])
    plt.gcf().text(.15, .6, extratext, fontsize = 8, 
         bbox = dict(facecolor = 'gray', alpha = 0.5))
    #plt.subplots_adjust(right=0.8)
    #plt.subplots_adjust(left=1.2)
    #actually show the graph
    print("Graph completed!")
    plt.show()

'''actually do things'''
file = input("Path To Recorded Data File: ") #get our path to the file we wanna graph
data = open(file, "r") #open it so we can parse it

parsed = parse(data) #parse the file to get the data we want:[times, raw, env, dt] with dt being difference it times
extradata = extranalyze(parsed[3]) #get the other interesting statistics
quickgraph(parsed, extradata)
data.close() #close the file once doneb
