# @title
# T&R 2024 (@Mecknavorz, @Pepper)
# made for the FFF enhanced tail project.
# used for testing various aspects around how fast we can send data over serial

# important stuff
import sys
import time
import math

# multiprocessing stuff
import multiprocessing as mp
import threading

# serial read
import serial

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
    while not shake:
        # wait to see if the bytes has been sent
        '''SOMETHING TO CONSIDER:'''  # should we check to see if it's zero or just one less than what it was when we started?
        if ser.out_waiting < oldout:
            w = ser.readline()  # .decode() # not sure if the decode is needed
            print(w[-104:-1])  # needs to be tailored to specific start message, current message is 52 char long w/2 end chars
            ser.write(621)
            # see of the ESP32 send a message back
            # trying this by looking at the previous in value instead of
            if ser.in_waiting > oldin:
                # clear the buffer so we don't read junk data by accident
                ser.reset_input_buffer()
                # update our shake so that we can do the rest of the things
                shake = True
        # if we did the shake we don't need to wait
        if not shake:
            time.sleep(.1)  # sleep for .1 seconds before checking to see if there was a response again

def fastRead():
    global serial_record
    #print(f"serial in waiting {ser.in_waiting}")
    #print(f"serial record {serial_record}")
    while len(serial_record) < 24 or (ser.in_waiting and len(serial_record) > 24):
        if ser.in_waiting > 12:
            # print("received enough to pass!")
            serial_record += ser.read(ser.in_waiting)
            # print("Length of serial record according to fastRead: {l}".format(l=len(serial_record)))
            # delay for a lil bit
            ser.reset_input_buffer()  # 50% sure this command doesn't work and we need to do like ser.buffer = "" or some such

        # DOUBLE CHECK THIS TIME SLEEP
        time.sleep(0.01)  # wait for about 10ms or so to give the buffer time to fill up a bit more then add it to our record
        # print("SERIAL RECORD:", serial_record)

# variation of align checker for use with SerialSpeedTest-USB2
# in short: it looks for this pattern: [prev entry], time[4 bytes], raw [2 bytes], env [2 bytes], time [4 bytes], [new entry]
# each sample is expected to be 12 bytes, with the 4 at the start and end being the time of the sample
# may change the pattern down the line, or for the final version SO BE AWARE
# used to decode data and error correct in tandem with fastRead and the serial_record system
def fastDecode(grabs=1,  packsize=12):
    global serial_record
    global read_point
    global lock
    global last_valid_time
    global data_pull
    decoded_values = []
    # print("running fastDecode: serial_record length according to fastDecode: {l}".format(l=len(serial_record)))

    '''
    only start decoding if there are at least 10% extra samples, this will help with checking error correction
    '''

    data_requested = packsize * grabs
    error_account =  packsize * (grabs // 10)

    if (len(serial_record) - read_point) >= data_requested + error_account:
        data_pull = 1
        print("decoding...")

        lock.acquire()  # make sure we have access to serial_record

        end_point = read_point + data_requested + error_account

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
        decoded_values = []
        windowstart = 0
        bytes_lost = 0

        while len(decoded_values) < grabs:

            windowend = windowstart + packsize

            # slice up our sample into the values we want
            sample = decode_window[windowstart:windowend]

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
                last_valid_time = timeact

            '''
            alignment correction code
            make sure that this either locks or otherwise doesn't mess up fastRead
            the reason why we use this code instead of time alignment check is because that always starts at zero in the buffer
            we need a dynamic system which remembers where it is in the serial_record, as that is a complete set of data

            if our raw and env values are wayyy out of the expected range then it's likely to be a misalignment
            '''

            realigned = False  # to keep track of if we've actually realigned things yet
            current_error_allowance = 30_000  # allow only a single timestep off to start

            # print(windowstart, windowend)

            if not (0 <= rawact <= 4096) or not (0 <= envact <= 4096) or not (timeact - last_valid_time < current_error_allowance):
                print(f"Misalignment detected at {windowstart}th place in window, performing alignment correction")
                print(f"Bogus sample sample: [{timeact}, {rawact}, {envact}]")

                with lock:  # this makes sure we won't mess up the shared data

                    # make sure the read point isn't broken
                    if not (0 <= read_point <= (len(serial_record) - packsize - 1)):
                        print(f"Whoops, bogus read_point {read_point}... attempting fix")
                        read_point = len(serial_record) - packsize - 1
                        time.sleep(0.05)  # wait a lil bit for the serial_record to fill up more

                # similar checking code from timeAlignmentCheck
                while not realigned:
                    # variables to keep track of where we're looking
                    fs = windowstart + step  # first start
                    fe = windowstart + step + 4  # first end
                    ss = windowstart + step + 8  # second start
                    se = windowstart + step + 12  # second end

                    time1 = int.from_bytes(decode_window[fs:fe], 'big')
                    time2 = int.from_bytes(decode_window[ss:se], 'big')

                    if (time1 == time2) and (time1 - last_valid_time < current_error_allowance):
                        realigned = True
                        # update the decode window
                        sample = decode_window[fs:se]
                        # realign the iterator we're using to jump through the window with
                        windowstart += step
                        # if we found the alignment update it
                        # read_point += step
                        timebytes = sample[0:4]
                        rawbytes = sample[4:6]
                        envbytes = sample[6:8]
                        # do the math and get our data
                        timeact = int.from_bytes(timebytes, 'big')
                        rawact = int.from_bytes(rawbytes, 'big')
                        envact = int.from_bytes(envbytes, 'big')
                        print(f"FOUND ALIGNMENT WITHIN {current_error_allowance} TIMESTEPS")
                        print(f"realigned sample: [{timeact}, {rawact}, {envact}]")
                        print(f"Alignment found! Shifting window start by {step}, new readpoint is {windowstart}")
                        last_valid_time = timeact
                        # append the value we want to add
                        # decoded_values.append("SHIFT!")
                        bytes_lost += step
                        step = 0
                    else:
                        # since we didn't find the alignment keep looking
                        step = (step + 1) % 25
                        # print(step)
                        if step % 25 == 0:
                            current_error_allowance += 1024

                            if current_error_allowance > 100_000_000:
                                print("COULD NOT FIND ALIGNMENT")
                                sys.exit(0)

            if not realigned:
                # print("data good, appending!")
                # add our sample to what we want to return
                # MIGHT NEED TO MAKE SURE THIS DOESN'T ACCIDENTALLY APPEND JUNK
                decoded_values.append([timeact, rawact, envact])
                last_valid_time = timeact
                windowstart += packsize

        # increment read point by packsize so we remember where we are in serial_record
        # print("updating read_point")

        read_point = read_point + windowstart  # + packsize

        # only return the values when they're good
        print("RETURNING ALL", len(decoded_values), "DATA POINTS REQUESTED!")
        print(bytes_lost, "BYTES LOST OUT OF", error_account, "EXTRA ALLOCATED")
        print("CURRENT READPOINT IS", read_point)
        return decoded_values

    # if there's not enough data in serial_record for whatever reason

    print("Not enough data in the serial_record yet for that amount of samples :( :(")
    print(f"Current serial_record size: {len(serial_record)} vs {packsize * grabs}(requested data size)")

    return None


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

        time.sleep(3)
        pepper_live_graph(data=fastDecode(grabs=block_limit))
    else:
        times = [(datapoint[0] - st)/ 100000 for datapoint in data]
        # print(times)
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

        '''if most_recent_second_line == 2:
                    time.sleep(120)'''

        time.sleep(3)
        pepper_live_graph(data=fastDecode(grabs=block_limit))

# -------------------------
# ACTUALLY RUN EVERYTHING
# -------------------------
if __name__ == "__main__":
    #global serial_record
    print("starting!")
    ser.open()  # open the serial port
    pawshake()  # verify communications

    # attempt at multiprocessing
    queue = mp.Queue()
    stopped = threading.Event()

    print("Creating fastRead thread...")
    fr = threading.Thread(target=fastRead)
    print("Starting threads...")
    fr.start()
    start_time = time.time()
    print(f"start time: {start_time}")
    print("Thread Started")
    #print("Creating Graph...\n")

    time.sleep(1)
    # pepper graphing code
    
    data_pull = 1
    pepper_live_graph(data=fastDecode(), start=True)
    
    
        
    # close the fast read thread
    fr.join()

    ser.close()
    print("Closed serial port!")
    if fr.is_alive():
        print("Closed fastRead thread!")
