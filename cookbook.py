# -*- coding: utf-8 -*-
"""
Created on Tue Jun 14 18:51:11 2022

@author: Ashraf
"""

from pressure_control import *
import time
import pandas as pd


#valve are 8 to 11 and 20 to 23

# auto find and init serial port
init_serial_port()

# If port is known or if other serial devices interfere with autofind:
init_serial_port('COM4')


mBarRange = 2000

# enable Regulator 0 in Constant Pressure Mode
mBarTarget = 200
regulatorTarget = int((mBarTarget/mBarRange)*16384)
set_params_and_start_single(0,DC_MODE,regulatorTarget)

time.sleep(1)
# Turn on Valve 8:
set_params_and_start_single(8,DC_MODE,1)
time.sleep(5)

# shutdown pressure:
set_params_and_start_single(8,DC_MODE,0)
set_params_and_start_single(0,DC_MODE,0)

# enable Regulator 1 in square mode:
mBarTarget1 = 300
regulatorTarget1 = int((mBarTarget/mBarRange)*16384)
mBarTarget2 = 100
regulatorTarget2 = int((mBarTarget/mBarRange)*16384)
timeBase = 10
msPeriod1 = int(1000/timeBase)
msPeriod2 = int(500/timeBase)
msOffset=int(0/timeBase)
# Maintain Presure Target1 for msPeriod1 then switches to Pressure target2 for msPeriod2. msOffset is used if another
# regulator or valve is using the same timebase and needs a phase offset
set_params_and_start_single(1,SQUARE_MODE,mBarTarget1,mBarTarget2,msPeriod1,msPeriod2,msOffset)

# Read out DACs
for i in range(100):
    print(get_last_sample())
    # returns a tuple:
    # (511580, [456, 262, 4274, 4574, 4269, 1258, 29534, 4372], {8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23})
    # (511580, --> timestamp (units are intervals 10ms each
    # [456, 262, 4274, 4574, 4269, 1258, 29534, 4372], --> ADC readout: Not all valid depends on how many regulators on device
    # {8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23}  --> list of enabled Valves
    # )
    time.sleep(0.2)


# shutdown Regulator 1:
set_params_and_start_single(1,DC_MODE,0)

# enable Regulator 1 in triagle mode:
mBarTarget1 = 0
regulatorTarget1 = int((mBarTarget/mBarRange)*16384)
mBarTarget2 = 200
regulatorTarget2 = int((mBarTarget/mBarRange)*16384)
timeBase = 10
msPeriod1 = int(1000/timeBase)
msPeriod2 = int(500/timeBase)
msOffset=int(0/timeBase)
# linear ramp from Presure Target1 to Pressure target2 over  msPeriod1. Then ramps from Pressure2 to pressure1 over
# Period2. msOffset is used if another
# regulator or valve is using the same timebase and needs a phase offset
# if Period 1 or Period 2 is 1 it approaches a saw tooth
set_params_and_start_single(1,TRIANGLE_MODE,mBarTarget1,mBarTarget2,msPeriod1,msPeriod2,msOffset)
time.sleep(5)

# shutdown Regulator 1:
set_params_and_start_single(1,DC_MODE,0)

# enable Regulator 0 in DC mode and toggle 4 valves in square mode with 4 offsets:
msPeriod1 = int(500/timeBase)
msPeriod2 = int(500/timeBase)
msOffset1 = 250
msOffset2 = 500
msOffset3 = 750
mBarTarget =200
set_params_and_start_single(0,DC_MODE,mBarTarget)

# enable valves:
set_params_and_start_single(8,SQUARE_MODE,1,0,msPeriod1,msPeriod2,0)
set_params_and_start_single(9,SQUARE_MODE,1,0,msPeriod1,msPeriod2,msOffset1)
set_params_and_start_single(10,SQUARE_MODE,1,0,msPeriod1,msPeriod2,msOffset2)
set_params_and_start_single(11,SQUARE_MODE,1,0,msPeriod1,msPeriod2,msOffset3)

time.sleep(5)

# shutdown:
set_params_and_start_single(8,DC_MODE,0)
set_params_and_start_single(9,DC_MODE,0)
set_params_and_start_single(10,DC_MODE,0)
set_params_and_start_single(11,DC_MODE,0)
set_params_and_start_single(0,DC_MODE,0)



# shutdown all (good to have at end of all scripts):
for r in range(8):
    set_params_and_start_single(r, DC_MODE, 0)
for v in range(0,24):
    set_params_and_start_single(v,DC_MODE,0)
    time.sleep(0.1)


# Custom names for Regulators and valve for easier scripting
# Modify the configuration.csv file in the folder containing pressure_control.py to
# facilitate scripting and improve readability. You can then use the getDeviceID
# function as a lookup for the device number. In this example, device #8 is a valve that we named "valve1"
# and "Regulator3" is device #2
# Note: Name is case-sensitive.No spaces or special characters!

set_params_and_start_single(getDeviceID('Regulator3'),DC_MODE,mBarTarget)
time.sleep(1)
set_params_and_start_single(getDeviceID('valve1'),DC_MODE,1)
time.sleep(5)
set_params_and_start_single(getDeviceID('valve1'),DC_MODE,0)
time.sleep(1)
set_params_and_start_single(getDeviceID('Regulator3'),DC_MODE,0)

