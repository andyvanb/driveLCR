import time
import serial
from matplotlib import pyplot as plt
from numpy import average
import argparse

parser = argparse.ArgumentParser(description='Sets up and utilizes an East Tester ET4401 LCR meter to measure '
                                             'Capacitance and ESR of a DUT (Device Under Test)')
# COM Port must be discovered by the user and added here as default or specified on the command line
parser.add_argument('inst_port', metavar='port', default='COM11', type=str, nargs='?',
                    help='Serial port for instrument communication. Examples: COM11 in Windows, /dev/tty11 in Linux.'
                         ' Default COM11')
parser.add_argument('inst_meas_a', metavar='a', choices=['AUTO', 'Z', 'R', 'C', 'L', 'DCR', 'ECAP'], default='AUTO',
                    type=str, nargs='?',
                    help='First impedance value of the measured pair. Choices: AUTO, Z, R, C, L, DCR, ECAP'
                         ' Default: AUTO')
parser.add_argument('inst_meas_b', metavar='b', choices=['X', 'D', 'Q', 'THR', 'ESR'], default='X',
                    type=str, nargs='?',
                    help='Second impedance value of the measured pair. Choices: X, D, Q, THR, ESR'
                         ' Default: X')
# Instrument appears to only allow a specific set of frequencies and not any values in between. 0 means the entire list
f_list = [0, 100, 120, 200, 400, 800, 1000, 2000, 4000, 8000, 10000]
f_set = tuple(f_list.copy() + [None])  # appending None in argparse will modify so we make a copy
parser.add_argument('freq_points', metavar='freq', choices=f_list, default=0,
                    type=int, nargs='*', help='Frequencies to use for measurement, example: 100 200'
                                              ' Must be a subset of the allowed default set of values: 100, '
                                              '120, 200, 400, 800, 1000, 2000, 4000, 8000, 10000. Providing just a 0 '
                                              'will utilize the entire default set of values.')
# Time to wait for the instrument before read and write operations, in seconds. This is a key number. At 10ms the
# capacitance measurement variability at 100nF obscures the trend of capacitance over frequency. This is using the
# SLOW instrument setting. With a 100ms delay, the trend is often clear. Reason for this sensitivity is not certain.
# An instrument design issue is suspected, as there does not appear to be no flow control, i.e. the instrument will
# not wait until acquisition is complete to send a result.
parser.add_argument('delay_time', metavar='delay', default=0.250,
                    type=float, nargs='?', help='Time to wait for the instrument before read and write operations, '
                                                'in seconds. Default 0.250')
parser.add_argument('--exitonerr', default=False, action='store_true', help="Exit when an instrument error is detected")
args = parser.parse_args()
inst_port = args.inst_port
freq_pts = args.freq_points
a = args.inst_meas_a
b = args.inst_meas_b
if type(freq_pts) is list:
    if freq_pts[0] is 0:
        freq_pts = f_list[1:len(f_list)]  # If no argument(s), we provide the entire list
else:
    if freq_pts is 0:
        freq_pts = f_list[1:len(f_list)]  # If no argument(s), we provide the entire list

freq_pts.sort()  # Sort in case the args were not in ascending order. Done for graceful plotting
delay_t = args.delay_time
break_on_err = args.exitonerr
print("Break on error= %s" % (break_on_err))
print("freq_pts= %s" % (freq_pts))
print("First and Second Measurement Values are: %s and %s" % (a, b))
inst = "ET4401"  # East Tester brand LCR Meter by Hangzhou Zhongchuang Electron Co.,Ltd., with USB connection. Tested
# with this code on Windows 10.  Commands used here are specific to this instrument. This code may work well or not
# with similar instruments.
exit()


def rd_inst(qcmd=None):
    """write the provided string argument if present.
    Then read the resulting output from the instrument and return.
    Returned object is a list of char. May be one or multiple objects in list.
    Multiple objects are found when the instrument provides comma separators."""
    if qcmd is not None:
        wr_inst(qcmd)
    time.sleep(delay_t)
    read_val = ser.readline().decode('utf-8').split(',')  # read a '\r\n' terminated line as bytes
    err_found = 'err' in read_val[0]
    if err_found and break_on_err:
        print("Instrument error occurred, exiting")
        exit()
    return read_val
    # Note that 'cmd err' will be returned by the instrument if there is a problem and '' if not.
    # It is often useful to allow multiple errors to occur for command debugging. Hence the option to
    # not break on error


def wr_inst(messg=''):
    """Writes string argument to the instrument."""
    time.sleep(delay_t)
    lineout = messg + '\n'
    return ser.write(lineout.encode('utf-8'))


def set_inst(cmd):
    """Writes string argument to the instrument and then prints out the sent and returned values.
    Print is used to verify that the instrument is working correctly."""
    wr_inst(cmd)
    print("Sent: %s, Received: %s" % (cmd, str(rd_inst())))


def set_up_cap_esr():
    """Set up the instrument for measuring capacitance with ESR using AUTO ranging."""
    set_inst("FUNCtion:IMPedance:RANGe:AUTO ON ")  # This makes sure the range is not fixed
    set_inst("VOLTage:LEVel 1500")  # stimulus in mV. There is a limited set of values allowed, 100, 200, etc.
    set_inst("BIAS:VOLTage:LEVel 0")  # bias DC voltage in mV
    set_inst("APERture SLOW")  # Accuracy
    set_inst("FUNCtion:IMPedance:A %s" % a)  # First parameter "A" is set from cmd line or default AUTO
    if a not in 'AUTO':
        set_inst("FUNCtion:IMPedance:B %s" % b)  # Second parameter "B" is set from cmd line or default X


# Serial port does not appear to care about baud rate setting for this instrument type, so we use 115200 baud.
with serial.Serial(inst_port, 115200, timeout=1) as ser:
    inst_found = False
    while not inst_found:
        wr_inst('*IDN?')
        print('Looking for ' + inst + ' on port ' + inst_port)
        line = rd_inst()
        inst_found = (line[1].strip() == inst)
    print('Found the ' + inst + ' device, Firmware ' + line[2])
    set_up_cap_esr()  # Set up the instrument for capacitance and ESR measurement
    xpoints = []
    ypoints_A = []
    ypoints_B = []
    rd_inst("FETCh?")  # The first reading of the sequence is often incorrect, so we make a dummy reading. Reason is
    # unknown. An instrument design issue is suspected.
    for freq in freq_pts:
        set_inst("FREQ %2.0f" % freq)  # ET4401 requires integer type format here
        a, b = rd_inst("FETCh?")  # a and b are the reading of the FUNCtion:IMPedance:A and B values
        print("Measured: A = %.2e, B = %.2e" % (float(a), float(b)))
        xpoints = xpoints + [freq]
        ypoints_A = ypoints_A + [float(a)]
        ypoints_B = ypoints_B + [float(b)]
    # The units of A and B can multiple types, perhaps determined by the instrument in AUTO mode. Ask it what they are.
    # Update, the instrument does not seem to respond with the automatically determined values, C or R, just what has
    # been written, such as "AUTO"
    type_A = rd_inst('FUNCtion:IMPedance:A?')
    type_A_str = type_A[0].strip("\r\n")
    type_B = rd_inst('FUNCtion:IMPedance:B?')
    type_B_str = type_B[0].strip("\r\n")
    print("A, B = ", type_A_str, type_B_str)
# Dictionary for A, B descriptors to graph labels
descript2label = {'AUTO': 'Unknown',
                  'Z': 'Real (Ohms)',
                  'R': 'Resistance (Ohms)',
                  'C': 'Capacitance (F)',
                  'L': 'Inductance, (H)',
                  'DCR': 'DC Resistance (Ohms)',
                  'ECAP': 'ECAP Capacitance (F)',
                  'X': 'Imaginary (Ohms)',
                  'D': 'Dissipation Factor ',
                  'Q': 'Q-factor (Ratio)',
                  'THR': '',    # Unsure what this signifies. Could not find this in documentation.
                  'ESR': 'ESR Resistance (Ohms)'}

# Find the average value of the first and second parameters for comparison purposes
print("Average %s = %.2e" % (descript2label[type_A_str], average(ypoints_A)))
print("Average %s = %.2e" % (descript2label[type_B_str], average(ypoints_B)))

if len(xpoints) > 1:  # Only graph if we have more than one pair of points
    # Configure and create plot with 2 axes. Attempt log-log is possible. X is always log.
    # To specify the number of ticks on both or any single axes
    fig, ax1 = plt.subplots()
    # First trace is "A" parameter. Configured as capacitance using the instrument settings
    color = 'tab:red'
    ax1.set_xlabel('Frequency (Hz)')
    ax1.set_ylabel(descript2label[type_A_str], color=color)
    if min(ypoints_A) > 0:
        ax1.loglog()    # Want frequency and A both as log axes if possible
    else:
        ax1.semilogx()   # Want X axis, the frequency, as log axis if possible
    ax1.plot(xpoints, ypoints_A, color=color)
    ax1.tick_params(axis='y', labelcolor=color)

    # Second trace is "B" parameter. Configured as ESR above using the instrument settings
    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    color = 'tab:blue'
    if min(ypoints_B) > 0:
        ax2.set_yscale("log")    # Want B as log axis if possible
    ax2.loglog()  # Have resistance on a log axis
    ax2.set_ylabel(descript2label[type_B_str], color=color)  # we already handled the x-label with ax1
    ax2.plot(xpoints, ypoints_B, color=color)
    ax2.tick_params(axis='y', labelcolor=color)

    # To specify the number of ticks on both or any single axes
    # Create the plot
    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    plt.show()
