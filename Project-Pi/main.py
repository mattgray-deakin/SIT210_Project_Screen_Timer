from tkinter import *
import tkinter.font
import re
import subprocess
import pandas as pd
# from pandastable import Table, TableModel
import threading
import time
import serial

ser = serial.Serial(
    port='/dev/ttyS0',
    baudrate = 9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
    )

dev_time = 120  # (5 seconds for testing only)
alerting = False

def get_usbdevices():
    device_re = re.compile("Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$", re.I)
    usb_list = subprocess.check_output("lsusb", text=True)
    devices = []
    for i in usb_list.split('\n'):
        if i:
            info = device_re.match(i)
            if info:
                dinfo = info.groupdict()
                devices.append(dinfo)

    dataset = pd.DataFrame(devices)
    return dataset



#Setup Dataframes x 4 - One for Monitored Devices, One for Current Device List, One for the Previous Devices, One for Device Timers
device_col = ['bus', 'device', 'id', 'tag']
monitored_device = pd.DataFrame(columns = device_col)
current_devices = get_usbdevices()
previous_devices = get_usbdevices()
timer_col = ['id', 'tag', 'timer', 'start']
device_timers = pd.DataFrame(columns = timer_col)


def device_change_detection():
    global previous_devices
    global current_devices
    global monitored_device
    global alerting

    while True:
        current_devices = get_usbdevices()
        curr_size = current_devices.size
        prev_size = previous_devices.size
        if curr_size < prev_size:
            new_device = pd.concat([previous_devices, current_devices]).drop_duplicates(keep=False)
            monitored_device = monitored_device.append(new_device)
            dev_id = new_device.iloc[0]['id']
            dev_name = new_device.iloc[0]['tag']
            add_device(dev_id, dev_name)
            alerting = False
        if curr_size > prev_size:
            dev_to_remove = pd.concat([previous_devices, current_devices]).drop_duplicates(subset=['id'], keep=False)
            print("DTR:")
            print(dev_to_remove)
            if monitored_device.size > 0:
                check = pd.concat([monitored_device, dev_to_remove])
                print("CHK:")
                print(check)
                if check.size > 0:
                    monitored_device = pd.concat([monitored_device, dev_to_remove]).drop_duplicates(subset=['id'], keep=False)
                    dev_id = dev_to_remove.iloc[0]['id']
                    dev_name = dev_to_remove.iloc[0]['tag']
                    print(dev_id)
                    print(dev_name)
                    stop_device(dev_id, dev_name)
                    print("MON_DEV_REM:")
                    print(monitored_device)
        previous_devices = current_devices


def add_device(new_id, new_name):
    global device_timers

    new_data = {'id':new_id, 'tag':new_name,'timer':dev_time, 'start': time.time()}
    device_timers = device_timers.append(new_data, ignore_index=True)
    print(device_timers)

def stop_device(old_id, old_name):
    global device_timers

    search_term = [old_id, old_name]
    device_timers = device_timers.drop(device_timers[(device_timers['id'] == old_id) & (device_timers['tag'] == old_name)].index)
    print(device_timers)

def timer_monitor():
    global device_timers
    global alerting

    print("Started Timer Monitor")

    while True:
        if device_timers.size > 0:
            for index, row in device_timers.iterrows():
                time_check = (row['timer'] + row['start']) - (time.time())
                if (time_check <= 0) & (alerting == False):
                    alerting = True
                    print("alert sent")
                    ser.write("[2]".encode())
                    ser.write( ("[" + row['tag'][:10] + "]").encode() )

def ser_communications():
    global device_timers
    global alerting
    old_size = device_timers.size
    time.sleep(1)
    ser.write( "[4]".encode() )
    already_clear = 1
    print("started ser_comms")

    while True:
        if (device_timers.size > old_size) or (device_timers.size < old_size):
            ser.write("[4]".encode())
            print("Data Change")
        if ((device_timers.size > 0) & (alerting == False)):
            for index, row in enumerate(device_timers.itertuples(), 0):
                ser.write("[1]".encode())
                time_check = (row.timer+ row.start) - (time.time())
                ser.write( ("[" + str(index) + "]").encode() )
                ser.write( ("[" + row.tag[:8] + "]").encode() )
                ser.write( ("[" + str(int(time_check)) + "]").encode() )
                already_clear = 0
                print("sendingstuff")
        if (device_timers.size == 0) and (already_clear == 0):
            ser.write( "[3]".encode() )
            print("Clearing Display")
            already_clear = 1
        old_size = device_timers.size
        #md_table.redraw()
        time.sleep(5)

"""def serial_rcv():
    while True:
        ser_data = ser.readline()
        if (ser_data != b''):
            print(ser_data)
"""

"""# GUI Setup
window = Tk()
window.title("USB Device Timer")
window.geometry("800x600")
the_font = tkinter.font.Font(family='Gentium', size=12, weight="bold")

#top label frame setup
top_label = Frame(window, width= 800, height=50, background= "AntiqueWhite3")
label_text = Label(top_label, text="Currently Monitored Devices")
top_label.pack ()
top_label.pack_propagate(0)

#bottom frame setup
body = Frame(window, width=800, height=550, background= "antique white")
body.pack (expand = 1)
body.pack_propagate(0)

md_table = Table(body, dataframe=device_timers)
md_table.show()
"""

dev_monitor_thread = threading.Thread(target=device_change_detection)
dev_monitor_thread.start()

timer_check_thread = threading.Thread(target=timer_monitor)
timer_check_thread.start()

ser_comms_normal = threading.Thread(target=ser_communications)
ser_comms_normal.start()




# Close Program
#def close_program():
#    window.destroy()

# Closing the Window
#window.protocol("WM_DELETE_WINDOW", close_program)

#window.mainloop()