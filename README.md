# FFFTail
Github Repository containing relevant work files for the Freedom of Form Foundation's Enhanced Tail project!

## What's inside:
### B6.1 Hardware Code
- Current Stable release of the code
- Capable of achieving a fairly consistent sample rate in the range of 1024Hz
- structurally very similar to the b6 code
- fixed the overflow bug in the esp32's output of time

### B7 Code
- structurally very different from the b7 code
- attempts to make things more efficient by simplifying them
- unfished/Nonfunctional, more of a preview into future revisions

### Grapher.py
- Designed to read the serial data from the esp32 (or similar hardware) and live graph it in a human readable format

### data_stats_tool.py
- Collection of functions to help analyze serial data provided
  - `prasebt(data)` and `parseusb(data)`: used to turn the sreial input into an array to make data processing easier
  - `comparedata(bluetooth, usb)`: compare two sets of data, the usb and bluetooth data, to make sure there are no discrepencies
  - `extranalyze(data)`: extremely helpful function which returns lots of useful statistics about the data, namely: Average, Maximum, Minimum, and Range
  - `skipCount(data)`: checks for weird time skips in the data, helps make sure sampling is fairly consistent
