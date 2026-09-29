# @title
# 2026 @Pepper, @Mecknavorz
# made for the FFF enhanced tail project.
# Live grapher

import datetime

import numpy as np
import pyqtgraph as pg
import serial
from PyQt6.QtWidgets import QFileDialog
from pyqtgraph.Qt import QtWidgets, QtCore

from Serial_Decode import fast_decode
from Serial_Read import fast_read


class CustomViewBox(pg.ViewBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_save = 0

        # Enable scroll-wheel zoom + panning
        self.setMouseEnabled(x=True, y=True)

        # Enforce zoom limits
        self.setLimits(
            yMin=0,
            yMax=4500,
            minYRange=1,  # Prevents collapsing to zero-height
            maxYRange=4500  # Prevents zooming out beyond full range
        )

    def mouseClickEvent(self, ev):
        # noinspection PyUnresolvedReferences
        if ev.button() == QtCore.Qt.MouseButton.RightButton:
            self.show_context_menu(ev)
        else:
            super().mouseClickEvent(ev)

    def show_context_menu(self, ev):
        # noinspection PyUnresolvedReferences
        menu = QtWidgets.QMenu()

        menu.addAction("Export All Data", self.export_data)
        menu.addAction("Toggle Follow Mode", self.toggle_follow)
        menu.addAction("Load replay", self.load_replay)
        menu.exec(ev.screenPos().toPoint())

    @staticmethod
    def toggle_follow():
        global follow_mode
        follow_mode = not follow_mode
        print("Follow mode:", "ON" if follow_mode else "OFF")

    def export_data(self):
        print("Exporting graph data.")

        t = graph.time_data
        r = graph.raw_data
        e = graph.env_data

        # Only export new rows
        lines = "\n".join(f"{t[i]},{r[i]},{e[i]}" for i in range(self.last_save, len(t)))

        with open(save_name + ".csv", "a") as data_file:
            data_file.write(lines + ("\n" if lines else ""))

        self.last_save = len(t)

    @staticmethod
    def load_replay():
        global replay_mode, replay_time
        replay_mode = True
        replay_time = 0

        # Ask user for a file
        file_name, _ = QFileDialog.getOpenFileName(
            None,
            "Load Replay Data",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )

        if not file_name:
            print("Replay load cancelled.")
            return None

        print(f"Loading replay from: {file_name}")

        global graph
        graph.time_data.clear()
        graph.raw_data.clear()
        graph.env_data.clear()

        try:
            with open(file_name, "r") as f:
                for line in f:
                    line = line.strip()

                    if not line:
                        continue

                    t_str, r_str, e_str = line.split(",")
                    graph.time_data.append(float(t_str))
                    graph.raw_data.append(float(r_str))
                    graph.env_data.append(float(e_str))

            print(f"Loaded {len(graph.time_data)} samples for replay.")

            # Update scrubber range
            graph.scrubber.setMaximum(len(graph.time_data) - 1)
            graph.scrubber.setValue(0)

        except Exception as e:
            print(f"Error loading replay file: {e}")
            return None


# Main Graphing Class
# noinspection PyUnresolvedReferences,PyTypeChecker
class LiveGraph(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.time_data = []
        self.raw_data = []
        self.env_data = []
        self.init_graph()
        self.grab_data()
        self.graph_timer = QtCore.QTimer()
        self.graph_timer.timeout.connect(self.update_graph)

        self.graph_timer.start(update_graph_time)  # Update graph in sync with block limit

    # noinspection PyAttributeOutsideInit
    def init_graph(self):
        # Initialize PyQtGraph application and data
        self.app = pg.mkQApp()

        # Create a custom view box and main plot window
        self.custom_viewbox = CustomViewBox()
        self.plot_item = pg.PlotItem(viewBox=self.custom_viewbox)
        self.window = pg.GraphicsLayoutWidget()
        self.window.addItem(self.plot_item)
        self.window.setWindowTitle("Live MyoWare Data")
        self.replay_speed = 7

        # Configure plot
        self.plot_item.setTitle("Live MyoWare Data")
        self.window.setBackground('k')
        self.custom_viewbox.setYRange(-100, 4200)
        self.custom_viewbox.setXRange(0, 10)

        # Enable dynamic grid
        self.plot_item.showGrid(x=True, y=True, alpha=0.5)

        # Add legend and plot curves
        self.plot_item.addLegend(offset=(10, 10), brush=(200, 200, 200), labelTextColor=(0, 0, 0))
        self.raw_curve = self.plot_item.plot(pen=(0, 0, 255), name="Raw Data")
        self.env_curve = self.plot_item.plot(pen=(255, 165, 0), name="Envelope Data")

        # --- Scrubber Slider ---
        self.scrubber = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.scrubber.setMinimum(0)
        self.scrubber.setMaximum(0)
        self.scrubber.setValue(0)
        self.scrubber.valueChanged.connect(self.scrubber_moved)

        # --- Play/Pause Button ---
        self.replay_button = QtWidgets.QPushButton("Pause")
        self.replay_button.setCheckable(True)
        self.replay_button.toggled.connect(self.toggle_replay_pause)

        # --- Faster/Slower Buttons ---
        self.faster_button = QtWidgets.QPushButton("Faster")
        self.slower_button = QtWidgets.QPushButton("Slower")
        self.faster_button.clicked.connect(self.quicken_replay)
        self.slower_button.clicked.connect(self.slowen_replay)

        # --- Horizontal layout for slider + button ---
        controls_layout = QtWidgets.QHBoxLayout()
        controls_layout.addWidget(self.scrubber)
        controls_layout.addWidget(self.replay_button)
        controls_layout.addWidget(self.slower_button)
        controls_layout.addWidget(self.faster_button)

        # --- Main vertical layout: graph on top, controls below ---
        layout = QtWidgets.QVBoxLayout()
        container = QtWidgets.QWidget()
        container.setLayout(layout)

        layout.addWidget(self.window)  # graph
        layout.addLayout(controls_layout)  # slider + button row

        # Wrap in a QMainWindow
        self.main_window = QtWidgets.QMainWindow()
        self.main_window.setCentralWidget(container)
        self.main_window.setWindowTitle("Live MyoWare Data")
        self.main_window.show()

    @staticmethod
    def grab_data():
        global ready_to_graph
        global serial_record
        global last_call
        global read_point
        global last_valid_data
        global time_loss
        global alignment_errors
        global errors
        global bytes_lost

        ready_to_graph = []

        # If serial is unavailable, do nothing (replay mode will handle rendering)
        if ser is None:
            return

        # We keep reading and decoding data while paused in order to stay in sync.
        serial_record, last_call = fast_read(serial_port=ser, record=serial_record,
                                             num_requested_samples=block_limit, last_read=last_call,
                                             update_time=update_graph_time, verbose=verbose_fast_read)

        while len(ready_to_graph) < block_limit:
            decoded_sample, serial_record, read_point, last_valid_data, alignment_errors, errors, bytes_lost = \
                fast_decode(record=serial_record, read_pointer=read_point, last_valid_byte=last_valid_data,
                            total_bytes_lost=bytes_lost, total_errors=errors,
                            total_alignment_errors=alignment_errors,
                            verbose=verbose_decode, sample_per_second=samples_per_second)

            ready_to_graph.append(decoded_sample)

    def update_graph(self):
        if not replay_mode:
            times = [data[0] / 1_000_000 for data in ready_to_graph]
            raw = [data[1] for data in ready_to_graph]
            env = [data[2] for data in ready_to_graph]

            self.time_data.extend(times)
            self.raw_data.extend(raw)
            self.env_data.extend(env)

            self.raw_curve.setData(x=self.time_data, y=self.raw_data)
            self.env_curve.setData(x=self.time_data, y=self.env_data)

            # Only scroll the view if follow mode is enabled
            if follow_mode:
                newest = times[-1]

                left = newest - 8  # 8 seconds of history
                right = newest + 2  # 2 seconds of future space

                self.custom_viewbox.setXRange(left, right, padding=0)

            self.grab_data()
            return None
        else:
            global replay_time
            if not hasattr(self, "np_time"):
                CustomViewBox.load_replay()
                self.np_time = np.array(graph.time_data)

            if not graph_paused:
                replay_time += self.replay_speed

                # Sync slider with playback
                graph.scrubber.blockSignals(True)
                graph.scrubber.setValue(replay_time)
                graph.scrubber.blockSignals(False)

                t_slice = graph.time_data[:replay_time]
                r_slice = graph.raw_data[:replay_time]
                e_slice = graph.env_data[:replay_time]

                graph.raw_curve.setData(x=t_slice, y=r_slice)
                graph.env_curve.setData(x=t_slice, y=e_slice)

                if follow_mode:
                    newest = t_slice[-1]

                    left = max(0, newest - 8)  # 8 seconds of history
                    right = max(10, newest + 2)  # 2 seconds of future space

                    self.custom_viewbox.setXRange(left, right, padding=0)

                return None
            return None

    def scrubber_moved(self, value):
        global replay_time

        replay_time = int(value)

        t_slice = graph.time_data[:replay_time]
        r_slice = graph.raw_data[:replay_time]
        e_slice = graph.env_data[:replay_time]

        if replay_time > 0:
            graph.raw_curve.setData(x=t_slice, y=r_slice)
            graph.env_curve.setData(x=t_slice, y=e_slice)

            if follow_mode:
                newest = t_slice[-1]
                left = max(0, newest - 8)
                right = max(10, newest + 2)
                self.custom_viewbox.setXRange(left, right, padding=0)

    def toggle_replay_pause(self, checked):
        global graph_paused

        graph_paused = not checked  # checked=True means "playing"
        self.replay_button.setText("Pause" if checked else "Play")

    def quicken_replay(self):
        self.replay_speed += 2

    # noinspection SpellCheckingInspection
    def slowen_replay(self):
        self.replay_speed -= 2


# -------------------------
# ACTUALLY RUN EVERYTHING
# -------------------------
if __name__ == "__main__":
    # Serial set up
    serial_record = b""

    ser = None

    read_point = 0
    last_call = 0
    block_limit = 50  # Amount of data to queue before graphing, larger = less chance of desync
    serial_length_failsafe = 1000000 * 12  # Number of samples * packet_size
    verbose_fast_read = True
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
    samples_per_second = 2048
    follow_mode = True

    save_name = "./" + datetime.datetime.now().strftime("%Y_%B_%d_%H_%M")
    graph_paused = False
    ready_to_graph = []

    update_graph_time = 10  # int((block_limit / samples_per_second) * 1000) - 10
    print("Updating graph every", update_graph_time, "ms")

    try:
        ser = serial.Serial(
            port='COM3',
            baudrate=230400,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=None,
            rtscts=False
        )
        # noinspection PyUnresolvedReferences
        ser.flushInput()
        print("Serial connection established.")
        replay_mode = False
    except Exception as exception:
        print("WARNING: Could not open serial port.")
        print("Reason:", exception)
        print("Starting in replay-only mode.")
        replay_mode = True
        replay_time = 0

    graph = LiveGraph()

    # noinspection PyUnresolvedReferences
    QtWidgets.QApplication.instance().exec()
