# Graph recorded data files taken from the arduino serial monitor
# Made by Mecknhavorz (T&R) for the Freedom of Form Foundationm, March 7th 2023

'''Imports'''
# the stuff we need to make graphs
import matplotlib.pyplot as plt
from data_stats_tool import extra_analyze, parse_data


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
    # this method of determining time window might break for recordings
    # over 16 minutes or that happen near the overlfow reset
    plt.title(f"Recorded Values over {round(parsed[0][-1], 3)} seconds")
    ax.set_xlabel('Time')
    ax.set_ylabel('Raw and Env')
    ax.legend()  # to help differentiate the values being graphed
    ax.grid(True)

    # add the other info we want displayed, eg consistency stuff
    extratext = f"Consistency Results:\n\
        Average delay between samples: {round(extradata[0], 2)}μs\n\
        Maximum: {extradata[1]}μs\n\
        Minimum: {extradata[2]}μs\n\
        Range: {extradata[3]}μs\n\n\
        Testing Attributes:\n\
        Negative time differences: {extradata[4]}"

    plt.gcf().text(.15, .6, extratext, fontsize=8,
                   bbox={"facecolor":"gray", "alpha":0.5})

    # plt.subplots_adjust(right=0.8)
    # plt.subplots_adjust(left=1.2)

    print("Graph completed!")
    plt.show()


# Import and parse data
file = input("Path To Recorded Data File: ")
data = open(file, "r")

parsed_data = parse_data(data)  # [times, raw, env, dt]
extra_data = extra_analyze(parsed_data[-1])
quickgraph(parsed_data, extra_data)
data.close()  # close the file once done
