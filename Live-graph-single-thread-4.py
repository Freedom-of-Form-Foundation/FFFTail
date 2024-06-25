# @title
# 2024 @Pepper, @Mecknavorz
# made for the FFF enhanced tail project.
# Live grapher

# important stuff
import time
import copy
import pyqtgraph as pyqt
import pyqtgraph.multiprocess as pyqtmp
import math
import serial
import sys


# Fast Read to get input data as fast as we can
def fastRead(num_requested_samples, verbose=False):
    """
    We set the num_requested_samples to the amount we expect to decode and graph
    before a buffer of that many samples builds up.

    If there are more bytes waiting in the buffer than num_requested_samples,
    then we are receiving more data than we can process in a cycle.

    :param num_requested_samples: Number of samples to pull from serial buffer
    :param verbose: Print debug info
    :return: None
    """
    global serial_record
    global read_point

    serial_length_at_request = len(serial_record)

    if ser.in_waiting >= (num_requested_samples * 12):
        print(f"{ser.in_waiting} BYTES WERE WAITING IN THE SERIAL")
        print(f"OUR CODE IS TOO SLOW D: WE ARE {ser.in_waiting - (num_requested_samples * 12)} BYTES BEHIND")
        sys.exit(1)  # Functionality for processing past data has not been implemented yet
    elif verbose:
        print(f"{ser.in_waiting} BYTES WERE WAITING IN THE SERIAL")
        print(f"OUR CODE IS VERY QUICK :D WE ARE {(num_requested_samples * 12) - ser.in_waiting} BYTES AHEAD")

    while len(serial_record) < ((num_requested_samples + 3) * 12) + read_point:
        if ser.in_waiting > 0:
            serial_record += ser.read(ser.in_waiting)

    if verbose:
        print(f"BYTES REQUESTED:\t{(num_requested_samples + 3) * 12}")
        print(f"BYTES RECEIVED:\t{len(serial_record) - serial_length_at_request}")

    return None


# --------------------------- Error correction ---------------------------

#  Decode raw hex bytes into human-readable integers and detect data loss
def fastDecode(samples_to_decode=1, packet_size=12, verbose=False, sample_per_second=None):
    """
    Reads from the serial record to decode a sample at a time from hex bytes into integers for graphing.

    Data format: 4 bytes of time, 2 bytes of raw data, 2 bytes of envelope data, 4 bytes of time.

    After decoding into integers the data is verified by a number of checks.

    1. The times at the beginning and end of a data sample must be equal.
    2. Raw and envelope data must both be between 0-4096.
    3. Time must be progressing forward (a comparison is made between last valid data packet).
    4. Time must be progressing at the expected rate.
    5. The data packet received is assumed to be close in time to the last data packet. (See line 142)

    :param samples_to_decode: Number of samples to decode at a time
    :param packet_size: Expected packet size of incoming data. (Always 12 per data format)
    :param verbose: Print debug info on number and type of decode errors found.
    :param sample_per_second: Sample rate per second, used to calculate time delta.
    :return: A list of decoded values in the format [Time, raw data, envelope data]
    """
    global serial_record
    global read_point
    global last_valid_data
    global time_loss
    global alignment_errors
    global errors
    global no_solution
    global bytes_lost

    step = 0
    decoded_values = []
    duplicate_serial = copy.deepcopy(serial_record)
    transfer_failure = False

    # only start decoding if there are at 25 extra bytes to account for error
    if (len(duplicate_serial) - read_point) >= 25:

        if verbose:
            print("decoding...")
            print(f"Grabbing from serial record with: packet_size = {packet_size}; ", end='')
            print(f"read_point = {read_point}; end_point = {read_point + packet_size * 5}")
            print(f"window size: {packet_size * 5}")

        # Keep decoding until we have the requested number of samples

        while len(decoded_values) < samples_to_decode:

            # Find the next sample
            sample = duplicate_serial[read_point:read_point + packet_size]

            time_bytes = sample[0:4]
            raw_bytes = sample[4:6]
            env_bytes = sample[6:8]
            time_check_bytes = sample[8:12]

            # Convert hex into integers
            time_int = int.from_bytes(time_bytes, 'big')
            raw_int = int.from_bytes(raw_bytes, 'big')
            env_int = int.from_bytes(env_bytes, 'big')
            time_check_int = int.from_bytes(time_check_bytes, 'big')

            # Has a transfer failure occurred in this sample
            transfer_failure = False

            current_timestep_allowance = 1  # allow only a single timestep off to start
            sample_delta_time = int(1 / sample_per_second * 1000000)  # Delta time step

            # Very long list of things to verify if a sample is legit
            # Data format: time, data, time.
            # 1st check is make sure times are equal
            # 2nd and 3rd check if data is within expected range

            # 4th check only accepts corrections within a timescale at a time
            # and also make sure time is flowing forwards

            # 5th and final check is to make sure we're incrementing in exactly
            # the sample rate at a time
            while not (
                    (time_int == time_check_int) and
                    (0 <= raw_int <= 4096) and
                    (0 <= env_int <= 4096) and
                    time_int > last_valid_data[0] and
                    time_int % sample_delta_time == 0 and
                    time_int - last_valid_data[0] <= current_timestep_allowance * sample_delta_time
            ):

                if verbose and not transfer_failure:
                    print(f"\nData transfer error detected at index {read_point}. Performing correction")

                    print(f"Bogus sample: [{time_int}, {raw_int}, {env_int}, {time_check_int}]")
                    print(f"Last valid data: {last_valid_data}")

                    if not time_int == time_check_int:
                        print("TIMES DO NOT ALIGN")
                    if not 0 <= raw_int <= 4096:
                        print("RAW VALUE NOT CORRECT")
                    if not 0 <= env_int <= 4096:
                        print("ENV VALUE NOT CORRECT")
                    if not time_int - last_valid_data[0] <= current_timestep_allowance * sample_delta_time:
                        print("TIME IS NOT WITHIN", current_timestep_allowance * sample_delta_time,
                              "FROM PREVIOUS VALID TIME")
                    if not time_int > last_valid_data[0]:
                        print("TIME IS NOT PROGRESSING")
                    if not time_int % sample_delta_time == 0:
                        print("TIME IS NOT PROGRESSING AT APPROPRIATE SCALE")

                transfer_failure = True

                # Increment byte misalignment by 1.
                # Only checks 25 additional bytes into the future
                step = (step + 1) % 25

                # If we haven't found a suitable solution within a timestep
                # then expand the time loss allowance
                if step % 25 == 0:
                    current_timestep_allowance += 1

                    # Allow consecutive loss of up to 100 time steps/samples before giving up

                    if current_timestep_allowance > 100:
                        print("COULD NOT FIND ALIGNMENT")
                        read_point += packet_size
                        no_solution += 1
                        bytes_lost += packet_size
                        return []

                # Move along the serial record and update check variables
                current_offset = read_point + step

                test_data = duplicate_serial[current_offset:current_offset + 12]

                time_bytes = test_data[0:4]
                raw_bytes = test_data[4:6]
                env_bytes = test_data[6:8]
                time_check_bytes = test_data[8:12]

                time_int = int.from_bytes(time_bytes, 'big')
                raw_int = int.from_bytes(raw_bytes, 'big')
                env_int = int.from_bytes(env_bytes, 'big')
                time_check_int = int.from_bytes(time_check_bytes, 'big')

            if transfer_failure:
                # We lost individual bytes (step) plus a number of whole packets
                bytes_lost += step + packet_size * (current_timestep_allowance - 1)
                errors += 1

                # Factors the individual byte misalignment into the read_point increment
                read_point += step + packet_size

                if step == 0:
                    time_loss += 1
                    if verbose:
                        print(f"realigned sample: [{time_int}, {raw_int}, {env_int}, {time_check_int}]")

                        print(f"TIME LOSS ONLY! LOST EXACTLY {12 * (current_timestep_allowance - 1)} BYTES, ", end='')
                        print(f"{current_timestep_allowance - 1} TIME STEPS")

                        print(f"Alignment found! Shifting read point by {step}, new read point is {read_point}\n")

                else:
                    alignment_errors += 1

                    if verbose:
                        print(f"realigned sample: [{time_int}, {raw_int}, {env_int}, {time_check_int}]")
                        print(f"FOUND CORRECTION WITHIN {current_timestep_allowance} TIME STEPS")
                        print(f"Alignment found! Shifting read point by {step}, new read point is {read_point}\n")

                step = 0
            else:
                read_point += packet_size

            # Save the valid sample
            decoded_values.append([time_int, raw_int, env_int])

            # Update the last known valid sample for error correction purposes
            last_valid_data = [time_int, raw_int, env_int]

        if verbose:
            if transfer_failure:
                print("RETURNING ALL", len(decoded_values), "DATA POINTS REQUESTED!")
                print(bytes_lost, "BYTES GARBLED OUT OF", packet_size * 5, "EXTRA ALLOCATED")
                print(f"{time_loss} PERFECT TIME LOSS ERRORS FOUND SO FAR")
                print(f"{alignment_errors} ALIGNMENT ERRORS FOUND SO FAR")
                print(f"CURRENT READ POINT IS {read_point}")
                print("\n\n\n\n\n\n")

        return decoded_values

    # If there's not enough data in serial_record

    print("Not enough data in the serial_record yet for that amount of samples :(")
    print(f"Current serial_record size: {len(duplicate_serial) - read_point} vs {25}. Actual: {len(duplicate_serial)}")

    return None


# -------------------------
# ACTUALLY RUN EVERYTHING
# -------------------------
if __name__ == "__main__":
    print("starting!")

    # Serial set up
    serial_record = b""
    ser = serial.Serial(baudrate=230400,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS,
                        timeout=None,
                        rtscts=True)
    ser.port = 'COM3'  # set the port
    ser.open()  # open the serial port
    ser.flushInput()  # Flush serial input on first start

    read_point = 0
    block_limit = 500  # Amount of data to queue before graphing, larger = less chance of desync
    serial_length_failsafe = 1000000 * 12  # Number of samples * packet_size
    verbose_fastread = True
    verbose_decode = False
    verbose_graph = False
    time_range = 10  # Graph X-axis limit in seconds

    # Decode function variables
    errors = 0
    time_loss = 0
    alignment_errors = 0
    no_solution = 0
    bytes_lost = 0
    last_valid_data = [0, 0, 0]
    samples_per_second = 100

    # ------------- Graph initialization -------------

    # Create remote process with a plot window
    pyqt.mkQApp()

    proc = pyqtmp.QtProcess()
    rpg = proc._import('pyqtgraph')  # noqa

    # Name window and set background colour to white
    plot_window = rpg.plot(title="Live MyoWare data", background='w')

    # Set Y-axis ticks
    plot_window.getPlotItem().getAxis('left').setTicks([[(i, str(i)) for i in range(0, 4500, 500)]])

    # Set graph Y-axis range
    pyqt.ViewBox.setYRange(plot_window, -100, max=4200)

    # Manually draw the graph lines for the first time_range seconds
    for i in range(1, time_range + 1):
        plot_window.addLine(x=i, pen='k')

    most_recent_second_line = time_range

    for i in range(0, 4500, 500):
        plot_window.addLine(y=i, pen='k')

    # Create graph legend
    plot_window.addLegend(offset=(10, 10), brush=(200, 200, 200), labelTextColor=(0, 0, 0))
    env_curve = plot_window.plot(pen=(0, 0, 255), name="Envelope data")
    raw_curve = plot_window.plot(pen=(255, 165, 0), name="Raw data")

    # Create empty lists in the remote process for each data type

    time_data = proc.transfer([])  # noqa
    raw_data = proc.transfer([])  # noqa
    env_data = proc.transfer([])  # noqa

    # --------------- WARNING: LOOPING BEGINS BEYOND THIS POINT ---------------

    while len(serial_record) < serial_length_failsafe:
        ready_to_graph = []
        total_decode = []

        fastRead(block_limit, verbose=verbose_fastread)

        decode_start_time = time.time()

        while len(ready_to_graph) < block_limit:
            decoded_sample = \
                fastDecode(verbose=verbose_decode, sample_per_second=samples_per_second)[0]

            ready_to_graph.append(decoded_sample)

        if verbose_graph:
            print(f"{block_limit} samples ready to graph!")
            print(ready_to_graph)

        decode_time = round((time.time() - decode_start_time) - ((1 / samples_per_second) * block_limit), 6)

        if decode_time > 0 and verbose_graph:
            print(
                f"DECODING TOOK {decode_time} SECONDS TOO LONG")

            print(f"{time_loss} perfect time loss, {alignment_errors} alignment errors ", end='')
            print(f"{no_solution} sample in a row losses found out of {block_limit} samples ", end='')
            print(f"{bytes_lost} total bytes lost out of {12 * block_limit}, {read_point}")
        elif verbose_graph:
            print(
                f"DECODING IS {decode_time} SECONDS AHEAD")

            print(f"{time_loss} perfect time loss, {alignment_errors} alignment errors", end='')
            print(f"{no_solution} sample in a row losses found out of {block_limit} samples", end='')
            print(f"{bytes_lost} total bytes lost out of {12 * block_limit}, {read_point}")

        times = [datapoint[0] / 1000000 for datapoint in ready_to_graph]
        # print(times)
        raw = [datapoint[1] for datapoint in ready_to_graph]
        env = [datapoint[2] for datapoint in ready_to_graph]

        # _callSync='off' because we do not want to wait for a return value.
        time_data.extend(times, _callSync='off')
        env_data.extend(raw, _callSync='off')
        raw_data.extend(env, _callSync='off')

        raw_curve.setData(x=time_data, y=raw_data, _callSync='off')  # noqa
        env_curve.setData(x=time_data, y=env_data, _callSync='off')  # noqa

        # Move graph view to only show time_range seconds
        if times[0] > time_range:

            pyqt.ViewBox.setXRange(plot_window, times[-1] - time_range, times[-1])

            while most_recent_second_line <= math.ceil(times[-1]):
                # print(f"DRAW NEW SECOND LINE AT {most_recent_second_line}")
                plot_window.addLine(x=most_recent_second_line, z=-1, pen='k')
                most_recent_second_line = most_recent_second_line + 1
