# T&R 2023 (@Mecknavorz)
# made for the FFF enhanced tail project.
# used for testing varius aspects around how fast we can send data over serial

# important stuff
import sys
import time
import random
import math
# serial read
import serial
import io
# graph
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
# stuff for byte conversion
import struct
# multiprocessing stuff
import multiprocessing as mp
import threading

# pepper grapher imports
import pyqtgraph as pg
import pyqtgraph.multiprocess as pymp

# serial stuff
ser = serial.Serial(baudrate=230400, timeout=None)  # serial class
# ser.set_buffer_size(rx_size = 256, tx_size = 256) # default buffer size is 2^16 =65536 #doesn't seem to do anything
ser.port = 'COM3'  # <<<<======== set the port IMPORTANT!!!! CHANGE THIS AS NEEDED!!!!!!!
# ser.setDTR(False) # this line makes the serial data readable
# ser.setRTS(False) # this line makes the serial data readable

# multiprocessing stuff
lock = mp.Lock()
# the string where we're gonna store our serial output
serial_record = b''
# variable to keep track of where we were reading from the serial record lst
read_point = 0


# function we should call to try and make things in sync
# calling it pawshake instead of handshake because it's funny and furry
def pawshake():
    print("Performing pawshake...")
    shake = False  # for tracking if we actually shook or not
    ser.write(621)  # write some random data to let the esp32 know we're here
    # recoding  how much data is in the input/output buffers for later comparison
    oldout = ser.out_waiting
    oldin = ser.in_waiting
    # since the shake hasn't been confirmed, keep running this loop to check until we get it confirmed
    while (not shake):
        # wait to see if the bytes has been sent
        '''SOMETHING TO CONSIDER:'''  # should we check to see if it's zero or just one less than what it was when we started?
        if (ser.out_waiting < oldout):
            w = ser.readline()  # .decode() # not sure if the decode is needed
            print(w[
                  -104:-1])  # needs to be tailored to specific start message, current message is 52 char long w/2 end chars
            ser.write(621)
            # see of the ESP32 send a message back
            # trying this by looking at the previous in value instead of
            if (ser.in_waiting > oldin):
                # clear the buffer so we don't read junk data by accident
                ser.reset_input_buffer()
                # update our shake so that we can do the rest of the things
                shake = True
        # if we did the shake we don't need to wait
        if not shake:
            time.sleep(.1)  # sleep for .1 seconds before checking to see if there was a response again


# variation of align checker for use with SerialSpeedTest-USB2
# in short: it looks for this pattern: [prev entry], time[4 bytes], raw [2 bytes], env [2 bytes], time [4 bytes], [new entry]
# each sample is expected to be 12 bytes, with the 4 at the start and end being the time of the sample
# may change the pattern down the line, or for the final version SO BE AWARE
def timeAlignCheck(scnt, v):
    if v: print("Performing verification via time alignment in samples...")
    rData = []

    # collect data
    while scnt > 0:
        if ser.in_waiting > 24:
            m = ser.read(24)
            if v: print("Successfully read {b} bytes from in_waiting!".format(b=len(m)))
            # add the data from the buffer into our run's data
            rData += m
            scnt = scnt - 1

    # look for the data we wanna see by running the pattern across it
    step = 0  # used to keep track of alignment, starts from zero
    found = False  # as long as we haven't found it keep trying

    # variables to keep track of where we're looking
    fs = 0  # first start
    fe = fs + 4  # first end
    se = 12  # second end
    ss = se - 4  # second start

    # make sure to check for step of length equal to sample size
    while (found == False) and (step < 24):
        if (rData[fs:fe] == rData[ss:se] and rData[fs:fe]):
            print("Alignment found! Shifting start by {n} bytes...".format(n=step))
            if v:
                print("Timestamp 1: {t1}".format(t1=rData[fs:fe]))
                print("Timestamp 2: {t2}".format(t2=rData[ss:se]))

            # snatch the example raw and env values
            rawbytes = rData[fe:fe + 2]
            envbytes = rData[fe + 2:fe + 4]
            rawact = fixVals2(rawbytes)
            envact = fixVals2(envbytes)

            if v:
                print("which means raw and env should be:")
                print("Raw bytes: {rb}\t Raw actual: {ra}".format(rb=rawbytes, ra=rawact))
                print("Env bytes: {eb}\t Env actual: {ea}".format(eb=envbytes, ea=envact))
            # print("Raw: {r}".format(r=
            found = True  # set found to true to get out of the loop

            # return the alignment if we find it
            return step

        else:
            # if the values don't match the expected pattern, keep going
            if v:
                print("Alignment not {n}".format(n=step))
                print("- Timestamp 1: {t1}".format(t1=rData[fs:fe]))
                print("- Timestamp 2: {t2}".format(t2=rData[ss:se]))
            step += 1
            fs += 1
            fe += 1
            ss += 1
            se += 1

    # print an error if we didn't find it
    if step > 24:
        print("Test Failed, Expected pattern not found :( :(")
        # return the step so we can use it to measure alignment


def fastRead(packsize, lock):
    # print("doing something")
    while ser.in_waiting:
        # print("serial in waiting {n}".format(n=ser.in_waiting))
        if ser.in_waiting > 12:
            # print("received enough to pass!")
            # lock.acquire() # make sure that decode isn't blocking the serial record so that we don't goof stuff up
            global serial_record
            serial_record += ser.read(ser.in_waiting)
            # print("Length of serial record according to fastRead: {l}".format(l=len(serial_record)))
            # delay for a lil bit
            ser.reset_input_buffer()  # 50% sure this command doesn't work and we need to do like ser.buffer = "" or some such
            # lock.release() # give up control of the lock
        time.sleep(
            0.01)  # wait for about 10ms or so to give the buffer time to fill up a bit more then add it to our record


# used to decode data and error correct in tandem with fastRead and the serial_record system
def fastDecode(alignment, packsize, grabs, lock):
    global read_point
    global serial_record
    tbr = []
    #end_point = 0
    # print("running fastDecode: serial_record length according to fastDecode: {l}".format(l=len(serial_record)))
    '''
    only start decoding if there is 10 samples at least, this will help with checking error correction
    additionally 10 packets should be sent in ~ .00978 seconds which is a very small delay for graphing
    
    redoing this; Instead of directly referencing serial record every time, and thus locking it,
    we copy what we want from the serial record into a window to decode
    '''
    if (len(serial_record) - read_point) > packsize * grabs:
        print("decoding...")

        lock.acquire()  # make sure we have access to serial_record

        if grabs == 1:
            end_point = packsize - 1
        else:
            end_point = read_point + packsize * (grabs - 1)
        
        print("Grabbing from serial record with:",
              f"packsize = {packsize}; read_point = {read_point}; end_point = {end_point}")

        decode_window = serial_record[read_point:end_point]

        # print("decode_window: {d}".format(d=decode_window)) # decode window is empty for some reason
        # print("serial_record: {csr}".format(csr=serial_record))

        lock.release()
        window_size = len(decode_window)

        print(f"window size: {window_size}")

        # read from the beginning of the window to 1 packsize before the end
        step = 0

        for i in range(0, window_size, packsize):
            i += step
            # todecode = serial_record[read_point:end_point]
            # for i in range(read_point, (len(todecode) - packsize), packsize):
            e = i + packsize

            # slice up our sample into the values we want
            sample = decode_window[i:e]

            # maybe redo these to be sample size independent when you get the chance
            # DOUBLE CHECK THIS!!!!!!!!!!!! could be slicing wrong if we get the wrong values
            timebytes = sample[0:4]
            rawbytes = sample[4:6]
            envbytes = sample[6:8]

            # do the math and get our data
            timeact = fixVals4(timebytes)
            rawact = fixVals2(rawbytes)
            envact = fixVals2(envbytes)  # this line breaks sporadically, unsure why; Gives an index out of range error

            if i == 0:
                print(f"example from sample: [{timeact}, {rawact}, {envact}]")

            '''
            alignment correction code
            make sure that this either locks or otherwise doesn't mess up fastRead
            the reason why we use this code instead of time alignment check is because that always starts at zero in the buffer
            we need a dynamic system which remembers where it is in the serial_record, as that is a complete set of data

            if our raw and env values are wayyy out of the expected range then it's likely to be a misalignment
            '''

            if not (0 <= rawact <= 4096) or not (0 <= envact <= 4096):
                print(f"Misalignment detected at {i}th place in window, performing alignment correction")
                print(f"Bogus sample sample: [{timeact}, {rawact}, {envact}]")

                step = i  # to keep track of how long we've been checking alignment
                realigned = False  # to keep track of if we've actually realigned things yet

                with lock:  # this makes sure we won't mess up the shared data

                    # make sure the read point isn't broken
                    if not (0 <= read_point <= (len(serial_record) - packsize - 1)):
                        print("Whoops, bogus read_point {r}... attempting fix".format(r=read_point))
                        read_point = (len(serial_record) - packsize - 1)
                        time.sleep(0.05)  # wait a lil bit for the serial_record to fill up more

                # similar checking code from timeAlignmentCheck
                while not realigned and (step < (i + 24)):
                    # variables to keep track of where we're looking
                    fs = step  # first start
                    fe = fs + 4  # first end
                    se = step + 12  # second end
                    ss = se - 4  # second start

                    if decode_window[fs:fe] == decode_window[ss:se] and decode_window[fs:fe]:
                        print("Alignment found! Shifting read point by {s}".format(s=step - i))
                        realigned = True
                        # update the decode window
                        sample = decode_window[fs:se]
                        # realign the iterator we're using to jump through the window with
                        i += step
                        # if we found the alignment update it
                        # read_point += step
                        # do stuff here to re-decode data we would've missed or interpreted as gibberish
                        # decodeReverse([fs,fe,se,ss])
                        # make sure we store the right values of things
                        timebytes = sample[0:4]
                        rawbytes = sample[4:6]
                        envbytes = sample[6:8]
                        # do the math and get our data
                        timeact = fixVals4(timebytes)
                        rawact = fixVals2(rawbytes)
                        envact = fixVals2(envbytes)
                        print(f"realigned sample: [{timeact}, {rawact}, {envact}]")
                        # append the value we want to add
                        tbr.append([timeact, rawact, envact])
                    else:
                        print(f"Alignment not {step}")
                        # since we didn't find the alignment keep looking
                        step += 1

            # add our sample to what we want to return
            # MIGHT NEED TO MAKE SURE THIS DOESN'T ACCIDENTALLY APPEND JUNK
            tbr.append([timeact, rawact, envact])

        # increment read point by packsize so we remember where we are in serial_record
        print("updating read_point")

        read_point += window_size

        # only return the values when they're good
        return tbr

    # if there's not enough data in serial_record for whatever reason
    else:
        print("Not enough data in the serial_record yet for that amount of samples :( :(")
        print("Current serial_record size: %r vs %g(requested data size)".format(r=len(serial_record),
                                                                                 g=(packsize * grabs)))
        # don't return anything


# might not be necessary
# function to read over serial_record backwards to make sure we're not missing data points in case of a skip
def decodeReverse(window):
    print("Oops! Function still under construction")


'''
#likely has to do with the passes code calling it
def grabData(passes, packsize):
    buff = [] #for just storing a bunch of bytes before we turn it back into data we can use
    while(passes > 0):
        m = []
        #see if we have enough bytes in waiting
        if ser.in_waiting > packsize:
            m = ser.read(packsize) #grab our bytes
            #print("beepis... {n}".format(n=m))
            buff += m #add it to our temp buffer
            passes = passes - 1
        #elif ser.in_waiting == 65536:
            #ser.reset_input_buffer()
    #print("Completed passes... Decoding")
    #buff = buff[-60:] #limit the size of the buffer
    return buff

#used to decode bytes
def grabDecode(todecode, alignment, packsize):
    tbr = []
    #since we want to iterate from the start of our alignment to the end our our decode buffer where i should be multiples of the size of our packets
    'keep getting an error about range arg 3 being 0 here'
    for i in range(alignment, (len(todecode) - packsize), packsize): 
        #s = i+alignment #get the start of a data packet
        e = i + packsize
        #slice up our sample into the values we want
        sample = todecode[i:e]
        #maybe redo these to be sample size independent when you get the chance
        #DOUBLE CHECK THIS!!!!!!!!!!!! could be slicing wrong if we get the wrong values
        timebytes = sample[0:4]
        rawbytes = sample[4:6] 
        envbytes = sample[6:8]
        #do the math and get our data
        timeact = fixVals4(timebytes)
        rawact = fixVals2(rawbytes)
        envact = fixVals2(envbytes)

        if(rawact)
        #add our sample to what we want to return
        tbr.append([timeact, rawact, envact])
        
    #return our values
    return tbr
'''


# used for 2 byte values
def fixVals2(bvals):
    return (bvals[0] << 8 | bvals[1])


# used for 4 byte values
def fixVals4(bvals):
    return (bvals[0] << 24 | bvals[1] << 16 | bvals[2] << 8 | bvals[3])


# graph stuff
'''
style.use('bmh')
fig, ax1 = plt.subplots()
ax1.set_xlim(0, 5120,
             auto=False)  # This should limit the size of our graph to be ~5 seconds of samples, or maybe 2.5 seconds since of the time bug
# ax1.set_xticks(ticks, labels=None, *, minor=False, **kwargs) #used for determining spacing of the labels on the x axis

# data storage for our graphs
# might merge this with the buffer eventually, but for now we're keeping it separate
xs = []  # time
ys = []  # raw values
ys2 = []  # env values


# sample = how many samples we want to grab
# alignment = how we need to adjust the incoming bytes
# samplesize = size of samples in bytes
'''


def pepper_live_graph(data=None, start=False):
    if data is None:
        data = [[], [], []]

    if start:
        global time_range
        global block_limit
        global raw_curve
        global env_curve
        global time_data
        global raw_data
        global env_data
        global data_block
        global st
        global plotwin
        global most_recent_second_line
        time_range = 10  # X-axis limit in seconds
        block_limit = 100  # Amount of data to queue before graphing, larger = less chance of desync
        time_value = data[0][0]

        # Create remote process with a plot window
        pg.mkQApp()

        proc = pymp.QtProcess()
        rpg = proc._import('pyqtgraph')

        plotwin = rpg.plot(title="Live MyoWare data", background='w') # Name window and set bg to white
        plotwin.getPlotItem().getAxis('left').setTicks([[(i, str(i)) for i in range(0, 4500, 500)]])  # Set Y-axis ticks
        pg.ViewBox.setYRange(plotwin, -100, max=4200)  # Set graph range

        # Manually draw the graph lines for the first time_range seconds
        for i in range(1, time_range + 1):
            plotwin.addLine(x=i, pen='k')

        most_recent_second_line = time_range

        for i in range(0, 4500, 500):
            plotwin.addLine(y=i, pen='k')

        # I am legend
        plotwin.addLegend(offset=(10, 10), brush=(200, 200, 200), labelTextColor=(0, 0, 0))
        raw_curve = plotwin.plot(pen=(0, 0, 255), name="Raw data")
        env_curve = plotwin.plot(pen=(255, 165, 0), name="Envelope data")

        # create empty lists in the remote process for each data type
        time_data = proc.transfer([])
        raw_data = proc.transfer([])
        env_data = proc.transfer([])

        st = time_value
    else:
        times = [(datapoint[0] - st) / 1000 for datapoint in data]
        raw = [datapoint[1] for datapoint in data]
        env = [datapoint[2] for datapoint in data]

        # _callSync='off' because we do not want to wait for a return value.
        time_data.extend(times, _callSync='off')
        env_data.extend(raw, _callSync='off')
        raw_data.extend(env, _callSync='off')

        raw_curve.setData(x=time_data, y=raw_data, _callSync='off')
        env_curve.setData(x=time_data, y=env_data, _callSync='off')

        # Move graph view to only show time_range seconds
        if times[0] > time_range:
            pg.ViewBox.setXRange(plotwin, times[-1] - time_range, times[-1])

            if (math.floor(times[0]) + 1) != most_recent_second_line:
                print("DRAW NEW SECOND LINE")
                plotwin.addLine(x=math.floor(times[0]) + 1, z=-1, pen='k')
                most_recent_second_line = math.floor(times[0]) + 1

        data_block = [[], [], []]

        pepper_live_graph(data=fastDecode(alignment, 12, 100, lock), start=False)


def graphTest(i, samples, alignment, samplesize):
    # bytedata = fastDecode(samples, samplesize)
    # print("data grabbed: {d}".format(d=bytedata))
    '''please verify how many of these steps I should actually do, I think this is quickest but needs testing'''
    # convert to numpy array and trans pose it so that instead of a list containing our samples w/each data point in it
    # we instead get an output of an array with three lists containing all the data from that pass
    # this makes the code to actually put the data to our graph simpler
    # data = np.transpose(np.array(grabDecode(bytedata, alignment, samplesize)))
    # then convert it back to a list and add it to the lists
    # xs.append(np.ndarray.tolist(data[0])) #our time data
    # ys.append(np.ndarray.tolist(data[1])) #our raw data
    # add a env
    '''a bit sloppy but should work for testing purposes'''
    # alignment, packsize, grabs, lock
    data = fastDecode(alignment, 12, samples,
                      lock)  # hard coded the 12 here because of an error where it was zero for some reason
    if (data):
        lastadd = len(data)

        for sample in data:
            global xs, ys, ys2
            xs.append(sample[0])
            ys.append(sample[1])
            ys2.append(sample[2])

        # limit the arrays size
        xs = xs[-5120:]
        ys = ys[-5120:]
        ys2 = ys2[-5120:]

        # draw the graph
        ax1.clear()
        ax1.plot(xs, ys, label='Raw')
        ax1.plot(xs, ys2, label='Env')

        # formatting stuff
        plt.title("Live graphing from ESP32")
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Raw and Raw')
        ax1.legend()  # to help differentiate the values being graphed
        ax1.grid(True)

        # space out the labels on the x data
        # get the positions we need for spacing ticks evently

        tickvals, labels = niceTicks(xs)
        # tickvals = nticks[0]
        # labels = nticks[1]

        ax1.set(yticklabels=[])
        ax1.set_xticks(tickvals)  # where to place tick marks
        ax1.set_xticklabels(labels)  # labels
        # print("graph Complete!")

        '''
        #had to use the old function, need to double check why niceTicks doesn't work
        #want to get rest of set up working first
        x_length = len(xs)

        if(x_length > 8):
            ax1.set(yticklabels=[])
            ax1.set(yticklabels=[])
            #get the positions we need for spacing ticks evently
            ax1.set_xticks([xs[0], xs[int(len(xs)/2)], xs[-1]])                     # where to place tick marks
            ax1.set_xticklabels([str(xs[0]), str(xs[int(len(xs)/2)]), str(xs[-1])]) # labels
            ax1.set_xticks([xs[0], xs[int(len(xs)/2)], xs[-1]])                     # where to place tick marks
            ax1.set_xticklabels([str(xs[0]), str(xs[int(len(xs)/2)]), str(xs[-1])]) # labels
        
        # test to make sure that there aren't non-distinct x values which will mess up the graph
        if len(xs) != len(set(xs)):
            print("Uh oh! there are duplicates!")
            print("ser.in_waiting: {s}".format(s=ser.in_waiting))
            #print(xs)
            # reset the buffer; this should help make sure it is the same amount of base time before we get the bug
            ser.read_all() # by reading everything we can clear the buffer; Flush nor the others seemed to work
            
            # things to try:
            # - CHECK ALIGNMENT!!!!!!
            # try parsing some samples at random to see if they're being red in correctly; if not then the Raw or env values won't be between 0-4095
            # if the alignment has changed; Update it so we won't get weird errors
            alignment = timeAlignCheck(samplesize, False)
            # changing the time array crashes the graphing
            # remove the last [samples] entries from the array) - need to test what value to remove works best
            nXsLen = len(xs) - lastadd - 1 #(2*(samples*samplesize))
            print("Removing: {n} entries".format(n=lastadd))
            xs = xs[0:nXsLen]
            ys = ys[0:nXsLen]
            ys2 = ys2[0:nXsLen]

            # try clearing the figure
            # DON'T DO THIS! DOESN'T WORK!
            # NEED TO either create system to remove duplicate x values from the end without changing the length of the arrays maybe?
            #ax1.cla()
        '''


def niceTicks(data):
    datalen = len(data)  # get the length of our data for easy math
    tickvals = []
    labels = []
    if (datalen > 8):
        ax1.set(yticklabels=[])
        # get the positions we need for spacing ticks evently
        tickvals = [data[0], xs[int(datalen / 2)], data[-1]]  # where to place tick marks
        # add labels we want to use instead of just the numerical values
        for v in tickvals:
            # divide by 1000000 to convert from microseconds to seconds for ease of reading
            # since the time is running 2x speed for ??? reasons rn, switched to 500000
            labels.append(str(v / 500000))
    return tickvals, labels


# -------------------------
# ACTUALLY RUN EVERYTHING
# -------------------------
if __name__ == "__main__":
    print("starting!")
    ser.open()  # open the serial port
    pawshake()  # verify communications
    # smartRead()
    # alignCheck(8)
    alignment = timeAlignCheck(8, True)
    # etime = time.time() + 30

    # attempt at multiprocessing
    queue = mp.Queue()
    stopped = threading.Event()

    print("Creating fastRead thread...")
    fr = threading.Thread(target=fastRead, args=(12, lock,))
    print("Starting threads...")
    fr.start()
    print("Thread Started")
    print("Creating Graph...")
    
    # pepper graphing code
    pepper_live_graph(data=fastDecode(alignment, 12, 1, lock), start=True)
    pepper_live_graph(data=fastDecode(alignment, 12, 100, lock), start=False)

    # old attempt at threading matplotlib graphing
    # fg = threading.Thread(target=fastGraph, args=(alignment, ))
    # test_graph = animation.FuncAnimation(fig, graphTest, fargs=(102, alignment, 12), interval=30)
    # plt.ion() # this and the pause seem to prevent the graph from closing but nothing displays and the program seems to stop
    # plt.show()
    # plt.pause(0.001) # see comment on plt.ion()

    fr.join()

    '''
    # non-live graphing
    graphTest(2048, alignment, 12)
    plt.show()

    print("about to grab!")
    start = time.time()
    bytedata = grabData(2048, 12)
    end = time.time()
    total = end - start
    data = grabDecode(bytedata, alignment, 12)
    expected = (data[-1][0] - data[0][0]) / (10**6) # need to do a microsecond to second conversion
    print("Here's the data: {c} samples grabbed in {s} seconds".format(c=len(data), s=total))
    print("python time vs sample time: ")
    print("p: {t1}".format(t1=total))
    print("s: {t2}".format(t2=expected))
    print("data can be accessed as 'data'")
    '''
    ser.close()
    print("Closed serial port!")
    if fr.is_alive():
        print("Closed fastRead thread!")

# old code that I will delete later
'''
# read 1 input line from the serial
# helps make sure everything is in sync
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
    #From the results of these tests we can conclude that the best way forward is going to be read(n) and making sure we are sending the correct # of bytes at once
    
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
    #we know the incoming message should be 8 bytes
    #1 x uint32_t + 2 x uint16_t = 4 + 2*2 = 8
    #[0-3] = time of sample
    #[4-5] = raw value
    #[6-7] = env value
    
    #essentially check to make sure we have completed messages in there
    #need to implement some way of making sure we're always looking for the right amount of bytes
    if(ser.in_waiting % 12 == 0):
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

#utf-16 should be the correct encoding for how we're sending it from arduino
#however I get random chars when I decode that so I think it's a scyn issue
#since we know we're looking for a message 12 characters long as long as we have a window (w) twice that size we should find the correct orientation by sliding across it
#this code probably won't be useful beyond these tests but who knows, here's to hoping!
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
#might merge this with the buffer eventually, but for now we're keeping it separate
xs = [] #time
ys = [] #raw values
#y2s = [] #env values
lastcall = 0; #to try to help kep track of when we're calling the code to store stuff in the buffer
#the function which animates things
def roughBuff():
    #make sure we're storing to the right arrays
    global xs
    global ys
    global lastcall
    #rouighly one tenth of our sample rate (1024) so swe should call this every 10th of a second
    #for i in range(1024):
    data = read() #read once from serial
    #print(data) #debugging stuff
    if len(z) > 2: #this makes sure we only record valid arrays
        if (z[0] != '') and (z[0] != '') and (z[0] != ''):
            #time = timecheck(int(data[0])) #convert out time to be proper for the graph; MIGHT BE REDUNDANT WITH NEW GRAPH?
            #add data to our axis
            xs.append(z[0]) 
            ys.append(z[1])
            #DO NOT DELETE THIS LINE
            #dump = data[2] #for some reason if you don't have this line it gives and out of bounds error on the previous line
    #print("ran rough buff at: {:f}".format(time.time()))
    lastcall = time.time()

#grab multiple same length samples and check to see if they remain aligned each time
passes = [] #for storing data
def alignCheck(pcnt):
    print("Performing Alignment check...")
    #for keeping track of which pass we're on
    #ocnt = pcnt
    while pcnt > 0:
        if ser.in_waiting > 24:
            m = ser.read(24)
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
'''
