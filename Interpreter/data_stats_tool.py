# usb vs bluetooth graph data
# T&R, 2022/2/16

# the stuff we need to make graphs
import numpy as np


# parse the data
# this assumes arduino serial monitor has been set to have timestamps enabled
# eg format of each line looks roughly like: 14:17:57.637 -> 60733167,1867,549

def parse_data(data):
    times = []  # times when things happen
    raw = []  # raw values
    env = []  # env values
    dt = []  # changes in time

    for line in data.readlines():
        readings = line.split(' ')[-1].strip().split(",")
        # print(readings)

        if len(times) >= 1:
            dt.append(float(readings[0]) - times[-1])

        times.append(float(readings[0]))
        raw.append(float(readings[1]))
        env.append(float(readings[2]))

    print("Time skips:", sum(1 for delta in dt if delta < 0))

    return [times, raw, env, dt]


def extra_analyze(data):
    avg = np.average(data)
    low = min(dt for dt in data if dt >= 0)
    high = max(data)
    datarange = high - low
    neg_time = sum(1 for delta in data if delta < 0)

    print("Results: ")
    print(f"Average: {avg}μs")
    print(f"Maximum: {high}μs")
    print(f"Minimum: {low}μs")
    print(f"Range:   {datarange}μs\n")
    print("Testing attributes: ")
    print(f"Negative time differences: {neg_time}")
    return [avg, high, low, datarange, neg_time]


# code that does stuff

if __name__ == '__main__': # execute only if run as a script main
    # btfile = input("Bluetooth Path: ")
    usbfile = input("Path To Data: ")
    # btdata = open(file1, "r")
    usbdata = open(usbfile, "r")

    parsed = parse_data(usbdata)[-1]
    # print(parsed)
    # print(parsedata(btdata)[-1])

    extra_analyze(parsed)

    # close the files once we're done
    # btdata.close()
    usbdata.close()
