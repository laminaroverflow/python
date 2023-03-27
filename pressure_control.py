import serial as sr
from time import sleep
from struct import pack
import glob, sys
import pandas as pd
#import numpy as np

MAX_NUM_DEVICES = 40 # for now, should be updated.

#Command Codes
START_UPDATE         = 0x1
STOP_UPDATE          = 0x2
GET_ACTIVE           = 0x4
SET_PARAMS           = 0x8
GET_PARAMS           = 0x10
SET_PARAMS_AND_START = 0x20
GET_LAST_SAMPLE      = 0x40
START_STREAMING      = 0x80
STOP_STREAMING       = 0x100

#Function Generation Mode
DC_MODE       = 0
SQUARE_MODE   = 1
TRIANGLE_MODE = 2
SINE_MODE     = 3

PARAM_LIST_SIZE = 5


def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = sr.Serial(port)
            s.close()
            result.append(port)
        except (OSError, sr.SerialException):
            pass
    return result



def findCOM(splist):
    com = 'NOTFOUND'
    global sp

    for prt in splist:

        with sr.Serial(port= prt, baudrate=1000000, timeout=1,) as sp:
            sp.flush()
            rxbuffer = set_params_and_start_single(0, DC_MODE, 0)
            try:
                if 0x55 ==  rxbuffer:
                    com = prt
                    print ("Instrument port is:")
                    print (prt)
                    break
            except:
                com = 'NOTFOUND'

    return com

def init_serial_port(portName = '/dev/ttyACM1'):
    global sp
    comlist = serial_ports()
    instrumentSP = findCOM(comlist)
    if instrumentSP != 'NOTFOUND':
        sp = sr.Serial(port=instrumentSP, baudrate=1000000)
    else:
        print("Unable to Find Instrument. Check Connection")

def transmit_msg(packed_msg=''):
    global sp
    sp.write(packed_msg)
    rsp = int.from_bytes(sp.read(), 'little')
    #print (hex(rsp))
    return rsp

#message is a list of uint32_t
def prepare_message(message):
    checksum = sum(message)
    message_with_checksum = message + [checksum]
    return pack("I"*len(message_with_checksum), *message_with_checksum)

def form_update_command(device_set = {}, active=True): # True for start update, FALSE for stop update
    mask0 = 0
    mask1 = 0
    for d in device_set:
        if d < 32:
            mask0 |= (1 << (d % 32))
        elif d < MAX_NUM_DEVICES:
            mask1 |= (1 << (d % 32))
        else:
            return []

    if active:
        cmd = START_UPDATE
    else:
        cmd = STOP_UPDATE

    message = [cmd, 2, mask0, mask1]
    return (message)

def form_set_params_cmd(device_set = {}, params_list = []):
    # make sure that the device list matches the elements
    # in the param list.
    if PARAM_LIST_SIZE * len(device_set) != len(params_list):
        return []

    mask0 = 0
    mask1 = 0
    for d in device_set:
        if d < 32:
            mask0 |= (1 << (d % 32))
        elif d < MAX_NUM_DEVICES:
            mask1 |= (1 << (d % 32))
        else:
            return []

    return [SET_PARAMS, len(params_list) + 2, mask0, mask1] + params_list

# Forms a list of update params to be sent at once
# later
def append_params_to_list (mode = DC_MODE, \
                           v_1 = 0, \
                           v_2 = 0, \
                           t_1 = 0, \
                           t_2 = 0, \
                           t_offset = 0, \
                           params_list = []):
    return params_list + [mode, (v_2 << 16) | v_1, t_1, t_2, t_offset]

# A helper API to send the command right away
def set_params(device_set = {}, params_list_of_lists = []):
    params_list = []
    for l in params_list_of_lists:
        assert(len(l) == PARAM_LIST_SIZE + 1)
        params_list = append_params_to_list(l[0], l[1], l[2], l[3], l[4], l[5], params_list)

    cmd = form_set_params_cmd(device_set, params_list)
    res = 0
    if len(cmd) != 0:
        msg = prepare_message(cmd)
        res = transmit_msg(msg)
    else:
        print("Returned Command Length is Zero. Device index not supported or parm-list incorrectly formatted.")

    return res

def rcvResponse():
    # Now receive the message
    # Read header first
    cmd = int.from_bytes(sp.read(4), 'little')
    length  = int.from_bytes(sp.read(4), 'little')

    body = []
    for x in range(0, length):
        body.append(int.from_bytes(sp.read(4), 'little'))

    checksum = int.from_bytes(sp.read(4), 'little')

    # print(cmd, length, body, hex(checksum))

    if checksum == (0xFFFFFFFF & sum([cmd, length] + body)):
        # print ("checksum success!")
        return body
    else:
        print('checksum failed!')
        return body

# A helper API to return the device ID based on a custom name in a configuration file
def getDeviceID(customName):
    hwConfig = pd.read_csv('configuration.csv')
    try:
        deviceID = hwConfig.loc[hwConfig['name'] == customName]['ID'].tolist()[0]
    except:
        print("Cannot Device ID. Check configuration File")
        deviceID = -1


# A helper API to set params of a single device
def set_params_single(device_index = 0, \
                      mode = DC_MODE, \
                      v_1 = 0, v_2 = 0, \
                      t_1 = 0, t_2 = 0, t_offset = 0):
    params_list = [mode, v_1, v_2, t_1, t_2, t_offset]
    return set_params({device_index}, [params_list])

# A helper API to send start_update
def start_update(device_set = {}):
    cmd = form_update_command(device_set)
    res = 0
    if len(cmd) != 0:
        msg = prepare_message(cmd)
        res = transmit_msg(msg)
    else:
        print("Returned Command Length is Zero.")

    return res

# A helper API to send stop_update
def stop_update(device_set = {}):
    cmd = form_update_command(device_set, False)
    res = 0
    if len(cmd) != 0:
        msg = prepare_message(cmd)
        res = transmit_msg(msg)
    else:
        print("Returned Command Length is Zero.")

    return res

# A helper API to send set_params and start
def set_params_and_start(device_set = {}, params_list_of_lists = []):
    params_list = []
    for l in params_list_of_lists:
        assert(len(l) == PARAM_LIST_SIZE + 1)
        params_list = append_params_to_list(l[0], l[1], l[2], l[3], l[4], l[5], params_list)

    res = 0
    cmd = form_set_params_cmd(device_set, params_list)
    if len(cmd) != 0:
        cmd[0] = SET_PARAMS_AND_START
        msg = prepare_message(cmd)
        res = transmit_msg(msg)
    else:
        print("Returned Command Length is Zero.")

    return res

# A helper API to set params of a single device
def set_params_and_start_single(device_index = 0, \
                                mode = DC_MODE, \
                                v_1 = 0, v_2 = 0, \
                                t_1 = 0, t_2 = 0, t_offset = 0):
    params_list = [mode, v_1, v_2, t_1, t_2, t_offset]
    return set_params_and_start({device_index}, [params_list])

# A helper to get the active commands.
def get_active_devices():
    # Flush the Serial Port.
    sp.reset_input_buffer()

    cmdMsg = [GET_ACTIVE, 0]

    ack = transmit_msg(prepare_message(cmdMsg))
    activeDevices = {}
    activeDeviceList = []

    if ack == 0x55:
        rsp = rcvResponse()
        mask = 1
        for i in range(0, 32):
            if (mask & rsp[0]):
                activeDeviceList.append(i)
            mask <<= 1

        mask = 1
        for i in range (0, 32):
            if (mask & rsp[1]):
                activeDeviceList.append(i + 32)
            mask <<= 1

        if len(activeDeviceList) > 0:
            activeDevices = set(activeDeviceList)
    else:
        print ("Received NACK!")

    return activeDevices

def get_last_sample():
    sp.reset_input_buffer()

    cmdMsg = [GET_LAST_SAMPLE, 0]

    msg = prepare_message(cmdMsg)

    ack = transmit_msg(msg)

    returnValue = (0, [], 0)
    regValues = []
    openValves = {}
    valveValues = 0

    if ack == 0x55:
        rsp = rcvResponse()

        if len(rsp) == 6:
            timestamp = rsp.pop(0)
            # parse response as 8 16 bit integers
            for index in range(0, 4):
                res = rsp.pop(0)
                regValues.append(res & 0xFFFF)
                regValues.append(res >> 16)
            valveValues = rsp.pop(0)

            ## Create a set of open valves only.
            mask = 1
            valveList = []
            for i in range (0, 32):
                if (mask & valveValues):
                    valveList.append(i + 8)
                mask <<= 1

            if (len(valveList) > 0):
                openValves = set(valveList)

            returnValue = (timestamp, regValues, openValves)
        else:
            print ("Incorrect sample length")
    else:
        print ("Received NACK!")

    return returnValue

# Get Params
def get_params(deviceSet):
    mask0 = 0
    mask1 = 0
    for d in deviceSet:
        if d < 32:
            mask0 |= 1 << (d % 32)
        elif d < MAX_NUM_DEVICES:
            mask1 |= 1 << (d % 32)
        else:
            print("Unsupported Device Index!")
            return []

    cmdMsg = [GET_PARAMS, 2, mask0, mask1]

    ack = transmit_msg(prepare_message(cmdMsg))


    if ack == 0x55:
        rsp = rcvResponse()
    else:
        print ("Received NACK!")

    return rsp

# Start Stream
def start_stream(periodInTicks):
    cmdMsg = [START_STREAMING, 1, periodInTicks]

    msg = prepare_message(cmdMsg)
    return transmit_msg(msg)

# Stop Stream
def stop_stream():
    cmdMsg = [STOP_STREAMING, 0]

    msg = prepare_message(cmdMsg)
    return transmit_msg(msg)
