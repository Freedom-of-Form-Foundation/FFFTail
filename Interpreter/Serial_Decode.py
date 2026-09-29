import copy
import sys


#  Decode raw hex bytes into human-readable integers and detect data loss
def fast_decode(record, read_pointer, last_valid_byte, total_bytes_lost, total_errors, total_alignment_errors,
                packet_size=12, verbose=False, sample_per_second=None):
    """
    Reads from the serial record to decode a sample at a time from hex bytes into integers for graphing.

    Data format: 4 bytes of time, 2 bytes of raw data, 2 bytes of envelope data, 4 bytes of time.

    After decoding into integers the data is verified by a number of checks.

    1. The times at the beginning and end of a data sample must be equal.
    2. Raw and envelope data must both be between 0-4096.
    3. Time must be progressing forward (a comparison is made between last valid data packet).
    4. Time must be progressing at the expected rate.
    5. The data packet received is assumed to be close in time to the last data packet. (See line 142)

    :param record: String serial record
    :param read_pointer: Last position of serial record decode
    :param last_valid_byte: [Time, Raw, Env] of the last valid data packet
    :param total_bytes_lost: Number of bytes lost
    :param total_errors: Number of errors detected
    :param total_alignment_errors: Number of samples lost due to time skip
    :param packet_size: Expected packet size of incoming data. (Always 12 per data format)
    :param verbose: Print debug info on number and type of decode total_errors found.
    :param sample_per_second: Sample rate per second, used to calculate time delta.
    :return: A list of decoded values in the format [Time, raw data, envelope data]
    """

    step = 0
    decoded_value = None
    duplicate_serial = copy.deepcopy(record)
    transfer_failure = False

    # only start decoding if there are at least 25 extra bytes to account for error
    if (len(duplicate_serial) - read_pointer) >= 25:

        if verbose:
            print("decoding...")
            print(f"Grabbing from serial record with: packet_size = {packet_size}; ", end='')
            print(f"read_pointer = {read_pointer}; end_point = {read_pointer + packet_size * 5}")
            print(f"window size: {packet_size * 5}")

        # Keep decoding until we have the requested number of samples

        while decoded_value is None:

            # Find the next sample
            sample = duplicate_serial[read_pointer:read_pointer + packet_size]

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
                    time_int > last_valid_byte[0] and
                    time_int % sample_delta_time == 0 and
                    time_int - last_valid_byte[0] <= current_timestep_allowance * sample_delta_time
            ):

                if verbose and not transfer_failure:
                    print(f"\nData transfer error detected at index {read_pointer}. Performing correction")

                    print(f"Bogus sample: [{time_int}, {raw_int}, {env_int}, {time_check_int}]")
                    print(f"Last valid data: {last_valid_byte}")

                    if not time_int == time_check_int:
                        print("TIMES DO NOT ALIGN")
                    if not 0 <= raw_int <= 4096:
                        print("RAW VALUE NOT CORRECT")
                    if not 0 <= env_int <= 4096:
                        print("ENV VALUE NOT CORRECT")
                    if not time_int - last_valid_byte[0] <= current_timestep_allowance * sample_delta_time:
                        print("TIME IS NOT WITHIN", current_timestep_allowance * sample_delta_time,
                              "FROM PREVIOUS VALID TIME")
                    if not time_int > last_valid_byte[0]:
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
                        sys.exit("COULD NOT FIND TIME ALIGNMENT")

                # Move along the serial record and update check variables
                current_offset = read_pointer + step

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
                total_bytes_lost += step + packet_size * (current_timestep_allowance - 1)
                total_errors += 1

                # Factors the individual byte misalignment into the read_pointer increment
                read_pointer += step + packet_size

                if step == 0:
                    total_alignment_errors += 1
                    if verbose:
                        print(f"realigned sample: [{time_int}, {raw_int}, {env_int}, {time_check_int}]")

                        print(f"TIME LOSS ONLY! LOST EXACTLY {12 * (current_timestep_allowance - 1)} BYTES, ", end='')
                        print(f"{current_timestep_allowance - 1} TIME STEPS")

                        print(f"Alignment found! Shifting read point by {step}, new read point is {read_pointer}\n")

                else:
                    total_alignment_errors += 1

                    if verbose:
                        print(f"realigned sample: [{time_int}, {raw_int}, {env_int}, {time_check_int}]")
                        print(f"FOUND CORRECTION WITHIN {current_timestep_allowance} TIME STEPS")
                        print(f"Alignment found! Shifting read point by {step}, new read point is {read_pointer}\n")

                step = 0
            else:
                read_pointer += packet_size

            # Save the valid sample
            decoded_value = [time_int, raw_int, env_int]

            # Update the last known valid sample for error correction purposes
            last_valid_byte = [time_int, raw_int, env_int]

        if verbose:
            if transfer_failure:
                print(total_bytes_lost, "BYTES GARBLED OUT OF", packet_size * 5, "EXTRA ALLOCATED")
                print(f"{total_alignment_errors} ALIGNMENT total_errors FOUND SO FAR")
                print(f"CURRENT READ POINT IS {read_pointer}")
                print("\n\n\n\n\n\n")

        return decoded_value, record, read_pointer, last_valid_byte, total_alignment_errors, total_errors, total_bytes_lost

    # If there's not enough data in record
    sys.exit(
        f"Not enough data in the record yet for that amount of samples :(\nCurrent record size: {len(duplicate_serial) - read_pointer} vs {25}. Actual: {len(duplicate_serial)}")
