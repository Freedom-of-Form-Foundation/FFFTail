# FFFTail
Github Repository containing relevant work files for the Freedom of Form Foundation's Enhanced Tail project!

## What's inside:
### B7 Hardware Code
- Current Stable release of the code
- Structurally very different from the b6 lineage of code; Much more simplified, both for readability and functionality
- Capable of achieving a consistent sample rate of 1024Hz
- Fixed the overflow bug in the esp32's output of time
- bluetooth planned for future versions

### Serial Speed Test USB1
- Testing code for measuring serial speed and help with debugging
- contains essentially the most basic version of the code possible
- no bluetooth integration, all data is sent over USB serial
- very simple and easy to follow

### Grapher.py
- Designed to read the serial data from the esp32 (or similar hardware) and live graph it in a human readable format

### data_stats_tool.py
- Collection of functions to help analyze serial data provided
  - `prasebt(data)` and `parseusb(data)`: used to turn the sreial input into an array to make data processing easier
  - `comparedata(bluetooth, usb)`: compare two sets of data, the usb and bluetooth data, to make sure there are no discrepencies
  - `extranalyze(data)`: extremely helpful function which returns lots of useful statistics about the data, namely: Average, Maximum, Minimum, and Range
  - `skipCount(data)`: checks for weird time skips in the data, helps make sure sampling is fairly consistent
