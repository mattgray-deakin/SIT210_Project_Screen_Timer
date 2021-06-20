"""
SIT210 - Embedded Systems Development
Screen Time Monitor Project
Matthew Gray

This Python Script is developed for the Raspberry Pi
In this script, the Pi communicates to a Particle Argon (Attachment via Serial Required)

The purpose of the script is to monitor USB device connections and disconnections, and associate them with a Timer.

It is used to monitor device usage for digital health of children
"""

import re
import subprocess
import pandas as pd
import threading
import time
import serial

# Serial Interface Setup (GPIO RX and TX - Must be enabled in Raspberry Pi Setup)
ser = serial.Serial(
    port='/dev/ttyS0',
    baudrate = 9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
    )

# Setup global varables and constants
dev_time = 120  # (5 seconds for testing only)
alerting = False

# Get a list of attached USB devices through the use of 'lsusb'
def get_usbdevices():
    device_re = re.compile("Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$", re.I)    # Regular Expression to parse the lsusb output
    usb_list = subprocess.check_output("lsusb", text=True)                                                              # Run lsusb in the background, monitor output
    devices = []                                                                                                        # Setup a Dict to hold the information
    # For loop to read through the usb_list and match against the regular expression                                                                                              
    for i in usb_list.split('\n'):
        if i:
            info = device_re.match(i)
            if info:
                dinfo = info.groupdict()
                devices.append(dinfo)

    dataset = pd.DataFrame(devices)                                                                                     # Use pandas to change the Dict into a Dataset and return the data
    return dataset

#Setup Dataframes x 4 - One for Monitored Devices, One for Current Device List, One for the Previous Devices, One for Device Timers
device_col = ['bus', 'device', 'id', 'tag']
monitored_device = pd.DataFrame(columns = device_col)
timer_col = ['id', 'tag', 'timer', 'start']
device_timers = pd.DataFrame(columns = timer_col)
current_devices = get_usbdevices()
previous_devices = get_usbdevices()

## Procedure to check for device list changes and action accordingly - It operates in its own continuously running thread
def device_change_detection():
    # Bring in global data that will be used in the procedure
    global previous_devices
    global current_devices
    global monitored_device
    global alerting

    while True:
        # Get the current list of devices, then compare this list to the old list.  If there is a change - act
        current_devices = get_usbdevices()
        curr_size = current_devices.size
        prev_size = previous_devices.size
        
        if curr_size < prev_size:                                                                       # Less Devices - A device has been disconnected and must be monitored
            new_device = pd.concat([previous_devices, current_devices]).drop_duplicates(keep=False)     # Compare list, get the difference, store in new_device
            monitored_device = monitored_device.append(new_device)                                      # Add the new device to the list
            # Gather the new devices id and tag, send it to the add_device procedure for timer monitoring
            dev_id = new_device.iloc[0]['id']                                                               
            dev_name = new_device.iloc[0]['tag']
            add_device(dev_id, dev_name)
        if curr_size > prev_size:                                                                                           # More devices - A device has been connected or reconnected
            # Use the device 'id' to check for what is connected (A device will get re-enumerated on each connection, thus need to use device details for comparison)
            dev_to_remove = pd.concat([previous_devices, current_devices]).drop_duplicates(subset=['id'], keep=False)
            print("DTR:")
            print(dev_to_remove)                                                                        
            # Remove the alerting flag - As the alerting device may have been re-added
            alerting = False
            if monitored_device.size > 0:                                                                                   # Confirm devices are being monitored
                check = pd.concat([monitored_device, dev_to_remove])                                                        # Make a comparison list (check) of monitored devices and devices that are just connected
                print("CHK:")
                print(check)
                if check.size > 0:                                                                                              # Confirm check is more than zero, thus a device (or devices) no longer need monitoring
                    monitored_device = pd.concat([monitored_device, dev_to_remove]).drop_duplicates(subset=['id'], keep=False)  # remove items from the monitored device dataframe
                    # Grab the device id and tag, send to stop_device so that the device timer is stopped
                    dev_id = dev_to_remove.iloc[0]['id']
                    dev_name = dev_to_remove.iloc[0]['tag']
                    print(dev_id)
                    print(dev_name)
                    stop_device(dev_id, dev_name)
                    print("MON_DEV_REM:")
                    print(monitored_device)
        previous_devices = current_devices                                                              # Set the previous device list to the current in prepartation for another check

# Procedure to append a new device, with start time and time allowed to the device_timers DataFrame
def add_device(new_id, new_name):
    global device_timers

    new_data = {'id':new_id, 'tag':new_name,'timer':dev_time, 'start': time.time()}
    device_timers = device_timers.append(new_data, ignore_index=True)
    print(device_timers)

# Procedure to remove a device from the device_timers DataFrame
def stop_device(old_id, old_name):
    global device_timers

    search_term = [old_id, old_name]
    device_timers = device_timers.drop(device_timers[(device_timers['id'] == old_id) & (device_timers['tag'] == old_name)].index)
    print(device_timers)

# Timer Monitor procedure - This Continuously running threaded procedure monitors the device_timers DataFrame and sets an alarm state if a device goes overtime
def timer_monitor():
    global device_timers
    global alerting

    print("Started Timer Monitor") # Debug

    while True:
        if device_timers.size > 0:                                              # Check to see if there is anything to monitor
            for index, row in device_timers.iterrows():                         # Iterate through the DataFrame
                time_check = (row['timer'] + row['start']) - (time.time())      # Check the time against the start time and time allowed
                if (time_check <= 0) & (alerting == False):                     # If overtime, send an alert via Serial, using the [data] protocol
                    alerting = True
                    print("alert sent")
                    ser.write("[2]".encode())
                    ser.write( ("[" + row['tag'][:10] + "]").encode() )

# Serial Communications Procedure - This procedure is continously running, it monitors the Device Timers DataFrame and sends data to the Serial Interface as required.
def ser_communications():
    global device_timers
    global alerting
    # Initiate the 'old_size' integer, which is used to define if there is a change to the data
    old_size = device_timers.size
    # sleep timer - helps with the serial interface
    time.sleep(1)
    ser.write( "[4]".encode() )     # Sends a [4] which clears the LCD Display in preparation for data
    already_clear = 1               # Display cleared flag
    print("started ser_comms")      # Debug

    while True:
        if (device_timers.size > old_size) or (device_timers.size < old_size):          # Comparison of quantity of device timers being monitored.  If there is a change, wipe the display
            ser.write("[4]".encode())
            print("Data Change")                                                        # Debug
        if ((device_timers.size > 0) & (alerting == False)):                            # If there is any data in Device Timers, we need to display it, unless there is an alert in progress
            for index, row in enumerate(device_timers.itertuples(), 0):                 # Iterate using enumerated itertuples
                ser.write("[1]".encode())                                               # Send [1] which communicates that Device Data is being sent
                time_check = (row.timer + row.start) - (time.time())                    # Create a time check to send time remaining in seconds 
                ser.write( ("[" + str(index) + "]").encode() )                          # Encode the index of the dataframe
                ser.write( ("[" + row.tag[:8] + "]").encode() )                         # Send an eight letter version of the device name
                ser.write( ("[" + str(int(time_check)) + "]").encode() )                # Send the time remaining
                already_clear = 0                                                       # Set to 0, as there is now stuff on the LCD
                print("sendingstuff")                                                   # Debug
        if (device_timers.size == 0) and (already_clear == 0):                          # If there is no more device being monitored and the LCD in not clear, send a clear display
            ser.write( "[3]".encode() )
            print("Clearing Display")
            already_clear = 1
        old_size = device_timers.size                                                   # Update the number of devices
        time.sleep(5)                                                                   # A short sleep to provide cleaner serial, and due to the difference in speed of the systems

## Threads used by the script
dev_monitor_thread = threading.Thread(target=device_change_detection)                   # Thread for the Device Change Detection
dev_monitor_thread.start()

timer_check_thread = threading.Thread(target=timer_monitor)                             # Thread for the Timer Monitor
timer_check_thread.start()

ser_comms_normal = threading.Thread(target=ser_communications)                          # Serial Communications Thread
ser_comms_normal.start()