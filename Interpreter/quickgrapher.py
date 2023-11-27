# quick grapher for graphing recorded data files taken from the arduino serial monitor
# Made by Mecknhavorz (T&R) for the Freedom of Form Foundationm, March 7th 2023

'''Imports'''
# the stuff we need to make graphs
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
import numpy as np
import math
from data_stats_tool import extranalyze, parsedata

'''main functions'''

# actually graph the info we want


def quickgraph(parsed, extradata):
    # a bit of extra data formatting
    st = parsed[0][0]
    # zero our times for a neater end graph
    for i in range(len(parsed[0])):
        parsed[0][i] = (parsed[0][i] - st) / 1000000
    fig, ax = plt.subplots()
    # add our data to the graph
    ax.plot(parsed[0], parsed[1], label='Raw')
    ax.plot(parsed[0], parsed[2], label='Env')

    # formatting stuff:
    # this method of determining time window might break for recordings over 16 minutes or that happen near the overlfow reset
    plt.title("Recorded Values over {s} seconds".format(s=parsed[0][-1]))
    ax.set_xlabel('Time')
    ax.set_ylabel('Raw and Env')
    ax.legend()  # to help differentiate the values being graphed
    ax.grid(True)
    # add the other info we want displayed, eg consistency stuff
    extratext = 'Consistency Results:\n Average delay between samples: {a}μs\n Maximum: {h}μs\n Minimum: {l}μs\n Range: {r}μs\n\n Testing Attributes:\n Drops in total before divison for average: {c}\n Negative time differences: {n}'.format(
        a=round(extradata[0], 2), h=extradata[1], l=extradata[2], r=extradata[3], c=extradata[4], n=extradata[5])
    plt.gcf().text(.15, .6, extratext, fontsize=8,
                   bbox=dict(facecolor='gray', alpha=0.5))
    # plt.subplots_adjust(right=0.8)
    # plt.subplots_adjust(left=1.2)
    # actually show the graph
    print("Graph completed!")
    plt.show()


'''actually do things'''
file = input("Path To Recorded Data File: ")  # get our path to the file we wanna graph
data = open(file, "r")  # open it so we can parse it

parsed = parsedata(data)  # parse the file to get the data we want:[times, raw, env, dt]
extradata = extranalyze(parsed[3], False)  # get the other interesting statistics
quickgraph(parsed, extradata)
data.close()  # close the file once done
