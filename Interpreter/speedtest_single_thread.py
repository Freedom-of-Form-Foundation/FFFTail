# @title
# T&R 2024 (@Mecknavorz, @Pepper)
# made for the FFF enhanced tail project.
# used for testing various aspects around how fast we can send data over serial

# important stuff
import sys
import time
import random
import math
# serial read
import serial
import io
import numpy as np
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
def timeAlignCheck(stepcount, verbose):
    if verbose: print("Performing verification via time alignment in samples...")
    rData = []

    # collect data
    while stepcount > 0:
        if ser.in_waiting > 24:
            m = ser.read(24)
            if verbose: print("Successfully read {b} bytes from in_waiting!".format(b=len(m)))
            # add the data from the buffer into our run's data
            rData.append(m)
            stepcount -= 1

    # look for the data we wanna see by running the pattern across it
    step = 0  # used to keep track of alignment, starts from zero
    found = False  # as long as we haven't found it keep trying

    # make sure to check for step of length equal to sample size
    while (found == False) and (step < 24):
        fs = step  # first start
        fe = step + 4  # first end
        ss = step + 8  # second start
        se = step + 12  # second end

        if (rData[fs:fe] == rData[ss:se] and rData[fs:fe]):
            print("Alignment found! Shifting start by {n} bytes...".format(n=step))
            if verbose:
                print("Timestamp 1: {t1}".format(t1=rData[fs:fe]))
                print("Timestamp 2: {t2}".format(t2=rData[ss:se]))

            # snatch the example raw and env values
            rawbytes = rData[fe:fe + 2]
            envbytes = rData[fe + 2:fe + 4]
            rawact = int.from_bytes(rawbytes, 'big')
            envact = int.from_bytes(envbytes, 'big')

            if verbose:
                print("which means raw and env should be:")
                print("Raw bytes: {rb}\t Raw actual: {ra}".format(rb=rawbytes, ra=rawact))
                print("Env bytes: {eb}\t Env actual: {ea}".format(eb=envbytes, ea=envact))
            # print("Raw: {r}".format(r=
            found = True  # set found to true to get out of the loop

            # return the alignment if we find it
            return step

        else:
            # if the values don't match the expected pattern, keep going
            if verbose:
                print("Alignment not {n}".format(n=step))
                print("- Timestamp 1: {t1}".format(t1=rData[fs:fe]))
                print("- Timestamp 2: {t2}".format(t2=rData[ss:se]))
            step += 1

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
            '''if len(serial_record) >= 4096*packsize:
                print("WRITING TEXT FILE")
                with open("serial-exerpt.txt", 'w') as txt:
                    txt.write(str(serial_record))
                sys.exit(0)'''

        time.sleep(0.01)  # wait for about 10ms or so to give the buffer time to fill up a bit more then add it to our record
        # print("SERIAL RECORD:", serial_record)


# used to decode data and error correct in tandem with fastRead and the serial_record system
def fastDecode(alignment, packsize, grabs, lock):
    global read_point
    global serial_record
    decoded_values = []
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
            end_point = read_point + packsize * grabs

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

        for windowstart in range(0, window_size - packsize, packsize):
            windowstart += step
            # todecode = serial_record[read_point:end_point]
            # for i in range(read_point, (len(todecode) - packsize), packsize):
            windowend = windowstart + packsize

            # slice up our sample into the values we want
            sample = decode_window[windowstart:windowend]

            # maybe redo these to be sample size independent when you get the chance
            # DOUBLE CHECK THIS!!!!!!!!!!!! could be slicing wrong if we get the wrong values
            timebytes = sample[0:4]
            rawbytes = sample[4:6]
            envbytes = sample[6:8]

            # print(sample, timebytes, rawbytes, envbytes, windowstart, windowend, window_size, step)

            # do the math and get our data
            # print("sample", sample, "\ntime:", timebytes)
            timeact = int.from_bytes(timebytes, 'big')
            rawact = int.from_bytes(rawbytes, 'big')
            envact = int.from_bytes(envbytes, 'big')  # this line breaks sporadically, unsure why; Gives an index out of range error
            # print(f"example from sample: [{timeact}, {rawact}, {envact}]")

            if windowstart == 0:
                print(f"example from sample: [{timeact}, {rawact}, {envact}]")

            '''
            alignment correction code
            make sure that this either locks or otherwise doesn't mess up fastRead
            the reason why we use this code instead of time alignment check is because that always starts at zero in the buffer
            we need a dynamic system which remembers where it is in the serial_record, as that is a complete set of data

            if our raw and env values are wayyy out of the expected range then it's likely to be a misalignment
            '''

            realigned = False  # to keep track of if we've actually realigned things yet

            if not (0 <= rawact <= 4096) or not (0 <= envact <= 4096):
                # print(f"Misalignment detected at {windowstart}th place in window, performing alignment correction")
                # print(f"Bogus sample sample: [{timeact}, {rawact}, {envact}]")

                step = windowstart  # to keep track of how long we've been checking alignment

                with lock:  # this makes sure we won't mess up the shared data

                    # make sure the read point isn't broken
                    if not (0 <= read_point <= (len(serial_record) - packsize - 1)):
                        print("Whoops, bogus read_point {r}... attempting fix".format(r=read_point))
                        read_point = (len(serial_record) - packsize - 1)
                        time.sleep(0.05)  # wait a lil bit for the serial_record to fill up more

                # similar checking code from timeAlignmentCheck
                while not realigned:
                    # variables to keep track of where we're looking
                    fs = step  # first start
                    fe = step + 4  # first end
                    ss = step + 8  # second start
                    se = step + 12  # second end

                    if decode_window[fs:fe] == decode_window[ss:se] and decode_window[fs:fe]:
                        # print(f"Alignment found! Shifting read point by {step}")
                        realigned = True
                        # update the decode window
                        sample = decode_window[fs:se]
                        # realign the iterator we're using to jump through the window with
                        windowstart += step
                        # if we found the alignment update it
                        # read_point += step
                        # do stuff here to re-decode data we would've missed or interpreted as gibberish
                        # decodeReverse([fs,fe,se,ss])
                        # make sure we store the right values of things
                        # print(sample)
                        timebytes = sample[0:4]
                        rawbytes = sample[4:6]
                        envbytes = sample[6:8]
                        # do the math and get our data
                        timeact = int.from_bytes(timebytes, 'big')
                        rawact = int.from_bytes(rawbytes, 'big')
                        envact = int.from_bytes(envbytes, 'big')
                        # print(f"realigned sample: [{timeact}, {rawact}, {envact}]")
                        # append the value we want to add
                        decoded_values.append([timeact, rawact, envact])
                    else:
                        # print(f"Alignment not {step}")
                        # since we didn't find the alignment keep looking
                        step += 1
                        step = step % 25

            if not realigned:
                # print("data good, appending!")
                # add our sample to what we want to return
                # MIGHT NEED TO MAKE SURE THIS DOESN'T ACCIDENTALLY APPEND JUNK
                decoded_values.append([timeact, rawact, envact])

        # increment read point by packsize so we remember where we are in serial_record
        # print("updating read_point")

        read_point += window_size

        # only return the values when they're good
        # print("RETURNING ALL", len(tbr), "DATA POINTS OUT OF", grabs, "REQUESTED!")
        return decoded_values

    # if there's not enough data in serial_record for whatever reason
    else:
        print("Not enough data in the serial_record yet for that amount of samples :( :(")
        print(f"Current serial_record size: {len(serial_record)} vs {packsize * grabs}(requested data size)")
        # don't return anything

# graph stuff
def pepper_live_graph(data=None, start=False):
    print("DATA", data, "START", start)

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
        times = [(datapoint[0] - st)/ 100000 for datapoint in data]
        print(times)
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

        # sys.exit(0)
        pepper_live_graph(data=fastDecode(alignment, 12, block_limit, lock), start=False)

# -------------------------
# ACTUALLY RUN EVERYTHING
# -------------------------
if __name__ == "__main__":
    print("starting!")
    ser.open()  # open the serial port
    pawshake()  # verify communications
    # smartRead()
    # alignCheck(8)
    alignment = 0 # timeAlignCheck(8, True)
    # etime = time.time() + 30

    # attempt at multiprocessing
    queue = mp.Queue()
    stopped = threading.Event()

    print("Creating fastRead thread...")
    fr = threading.Thread(target=fastRead, args=(64, lock,))
    print("Starting threads...")
    fr.start()
    print("Thread Started")
    print("Creating Graph...")

    time.sleep(1)
    # pepper graphing code
    pepper_live_graph(data=fastDecode(alignment, 12, 2, lock), start=True)

    pepper_live_graph(data=fastDecode(alignment, 12, 100, lock), start=False)

    # close the fast read thread
    fr.join()

    ser.close()
    print("Closed serial port!")
    if fr.is_alive():
        print("Closed fastRead thread!")
