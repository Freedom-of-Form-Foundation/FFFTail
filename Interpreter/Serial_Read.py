import time


# Fast Read to get input data as fast as we can
def fast_read(serial_port, record, num_requested_samples, last_read, update_time, verbose=False):
    """
    We set the num_requested_samples to the amount we expect to decode and graph
    before a buffer of that many samples builds up.

    If there are more bytes waiting in the buffer than num_requested_samples,
    then we are receiving more data than we can process in a cycle.

    :param serial_port: Serial port object
    :param record: String serial record
    :param num_requested_samples: Number of samples to pull from serial buffer
    :param last_read: Time since last read in seconds
    :param update_time: Time since last update in ms
    :param verbose: Print debug info
    :return: Serial record and last read
    """

    if verbose:
        current_call = time.time()

        time_diff = round((current_call - last_read) - (update_time / 1000), 4)
        print(time_diff, "seconds", serial_port.in_waiting - (num_requested_samples * 12))

        last_read = current_call

    record += serial_port.read((num_requested_samples + 3) * 12)

    return record, last_read
