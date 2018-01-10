# -*- coding: utf-8 -*-
"""
Created on Fri Oct 06 01:16:20 2017

@author: Srinivas N

Description: Sorensen Power Supply Remote Control GUI Interface

You need to have two separate Labeled frames 1 for each channel,
it should have input boxes to set voltage and current for each channel,
it should have labels to display voltage and current on each channel,
it should display if channel is ON or OFF,
it should have input box where will we will enter the IP,
it should have input box where we will enter display update rate,

it should have a small section to scan for all Sorensen PSU via LXI

Found that using NIVISA query and ask commands are working where as with pyvisa-py it is getting stuck

"""
"""
import visa
rm = visa.ResourceManager('@py')
sp = rm.open_resource('TCPIP::10.236.76.92::9221::SOCKET')
sp.query('OP1?')
#sp.write('OP1 0')
"""


SORENSEN_IP = '10.236.76.92'

APPLICATION_TITLE = 'Sorensen XPF Series PSU Remote Control Panel'

CONNECTION_ACTIVE = False

DEBUG = 1

import sorensen_psu_socket_based_driver

import Tkinter as tk  # for python 2
import tkFileDialog
import pygubu
import threading

import vxi11
import time


discoverTimeout = 5#seconds
queryTimeout = 3#seconds

queryTimeout = 3#seconds

APP_REFRESH_INTERVAL = 1#seconds

def queryInstr(Ip):
    try:
        vxi11.socket_timeout(queryTimeout)#uses customised vxi11 lib
        instr = vxi11.Instrument('TCPIP::'+Ip+'::INSTR')
        instr.timeout = queryTimeout-1 #this is required for some equipments, the vxi11 lib does +1 internally, and this is required for some instruments, need to find why
        instr.lock_timeout = queryTimeout-1
        queryString = str(instr.ask('*IDN?'))
        if DEBUG == 1:        
            print queryString
        instr.close()
        return queryString
    except vxi11.rpc.socket.timeout as timeout:
        if DEBUG == 1:                
            print str(timeout)
        return "Device not responding"
    except Exception as e:
        if DEBUG == 1:                
            print str(e)
        return queryString

def findLxiDevices():
    intrumentlist = vxi11.list_devices(timeout=discoverTimeout)

    devList = []

    for ip in intrumentlist:
        devList.append(ip+' : '+queryInstr(ip))
        time.sleep(0.1)
        
    if len(devList) == 0:
        devList.append("No Devices Found Please check make sure, ")
        devList.append("you are in the same network subnet as your device.")
    
    if DEBUG == 1:        
        print str(devList)
    return devList



keepPolling_channel_1 = 0
keepPolling_channel_2 = 0

state_of_channel_1 = 0
state_of_channel_2 = 0

class Application:
    def __init__(self, master):

        #1: Create a builder
        self.builder = builder = pygubu.Builder()

        #2: Load an ui file
        builder.add_from_file('./SorenSen_PSU_Remote_Control_Panel.ui')

        #3: Create the widget using a master as parent
        self.mainwindow = builder.get_object('Frame_1', master)
        
        master.title(APPLICATION_TITLE)
        
        self.Channel_1_Enable_CheckBox = builder.get_object('Checkbutton_1', master)
        self.Channel_2_Enable_CheckBox = builder.get_object('Checkbutton_3', master)
        
        global keepPolling_channel_1
        global keepPolling_channel_2
        keepPolling_channel_1 = tk.BooleanVar(master)
        keepPolling_channel_2 = tk.BooleanVar(master)        
        
        self.Channel_1_Set_Voltage_Btn = builder.get_object('Button_3', master)
        self.Channel_2_Set_Voltage_Btn = builder.get_object('Button_9', master)
        
        self.Channel_1_Set_Current_Btn = builder.get_object('Button_8', master)
        self.Channel_2_Set_Current_Btn = builder.get_object('Button_12', master)
        
        self.Channel_1_On_Btn = builder.get_object('Button_4', master)        
        self.Channel_2_On_Btn = builder.get_object('Button_10', master)
        
        self.Channel_1_Off_Btn = builder.get_object('Button_5', master)
        self.Channel_2_Off_Btn = builder.get_object('Button_11', master)
        
        self.Channel_1_State_RadioBtn = builder.get_object('Radiobutton_1', master)
        self.Channel_2_State_RadioBtn = builder.get_object('Radiobutton_3', master)
        
        global state_of_channel_1
        global state_of_channel_2 
        state_of_channel_1 = tk.IntVar(master)
        state_of_channel_1 = tk.IntVar(master)
        
        self.Channel_1_Voltage_Set_EntryBox = builder.get_object('Entry_1', master)
        self.Channel_2_Voltage_Set_EntryBox = builder.get_object('Entry_5', master)
        
        self.Channel_1_Current_Set_EntryBox = builder.get_object('Entry_2', master)
        self.Channel_2_Current_Set_EntryBox = builder.get_object('Entry_6', master)
        
        self.Channel_1_Voltage_Label = builder.get_object('Label_1', master)
        self.Channel_2_Voltage_Label = builder.get_object('Label_5', master)
        
        self.Channel_1_Current_Label = builder.get_object('Label_2', master)
        self.Channel_2_Current_Label = builder.get_object('Label_6', master)
        
        
        self.TextBox = builder.get_object('Text_1', master)
        self.Psu_Ip_Entry_Box = builder.get_object('Entry_9', master)
        self.Psu_Detect_Btn = builder.get_object('Button_16', master)
        self.SorensenPsuFindBtn = builder.get_object('Button_1',master)
        self.Psu_Set_Screen_Update_Interval_Btn = builder.get_object('Button_13', master)
        self.Psu_Connect_Btn = builder.get_object('Button_15', master)
        self.Psu_Warning_Voltage_Set_Btn = builder.get_object('Button_14', master)
        self.Psu_Screen_Update_Interval_TextBox = builder.get_object('Entry_7', master)
        self.Psu_Warning_Voltage_TextBox = builder.get_object('Entry_8', master)
        

 
def findAndPrintLxiDevices():
    global app
    #write method to clear the textbox first
    app.TextBox.delete(1.0,tk.END)
    app.TextBox.insert(tk.END,'Please wait Scanning for LXI based devices on Current Network...\n')
    try:
        devList = findLxiDevices()
        for i in devList:
            app.TextBox.insert(tk.END,i)
            app.TextBox.insert(tk.END,'\n')
        app.TextBox.insert(tk.END,'\nScanning Complete.')
    except Exception as e:
        app.TextBox.insert(tk.END,'There has been exception, Please check the details below'+str(e))

def findSorensenPsu():
    """    
    #global app
    print 'Please wait '+str(discoverTimeout)+' seconds, Discovering Instruments....\n'
    #app.insert(tk.END,'Please wait '+str(discoverTimeout)+' seconds, Discovering Instruments....\n')
    
    intrumentlist = vxi11.list_devices(timeout=discoverTimeout)
    Sorensen_PSU_List = []    
    for i in intrumentlist:
        if queryInstr(i).find("Sorensen") != -1:
            Sorensen_PSU_List.append(i)
        time.sleep(0.1)
    #return Sorensen_PSU_List
    for i in Sorensen_PSU_List:
        app.insert(tk.END,i)
    """
    thread1 = threading.Thread(target = findAndPrintLxiDevices)
    thread1.start()
    
    
def identifySorensenPsu():
    global app    
    """    
    r = requests.post("http://"+str(app.Psu_Ip_Entry_Box.get()).strip(' ')+"/home.cgi",data={'id':'pg','set':'Identify Instrument'})
    if DEBUG == 1:    
        print r.text
    """
    psu_object = sorensen_psu_socket_based_driver.SorensenWebInterfaceDriver(str(app.Psu_Ip_Entry_Box.get()).strip(' '))
    psu_object.InstrumentHighlight()

    
def guiInit(mainApp):
    global keepPolling_channel_1
    global keepPolling_channel_2
    #mainApp.TextBox.config(state=tk.DISABLED) #change state of TextBox to read-only, but when made read-only even from the program you can insert anything.
    mainApp.Psu_Detect_Btn.config(command=identifySorensenPsu)
    mainApp.SorensenPsuFindBtn.config(command=findSorensenPsu)
    mainApp.Psu_Connect_Btn.config(command=createPsuConnection)
    mainApp.Channel_1_Enable_CheckBox.config(command = chkb1,variable = keepPolling_channel_1,onvalue=True,offvalue=False)
    mainApp.Channel_2_Enable_CheckBox.config(command = chkb2,variable = keepPolling_channel_2,onvalue=True,offvalue=False)

    global state_of_channel_1
    global state_of_channel_2 
    #for the user Radio  button is read-only, it will indicate state of channel    
    mainApp.Channel_1_State_RadioBtn.config(variable=state_of_channel_1)
    mainApp.Channel_2_State_RadioBtn.config(variable=state_of_channel_2)
    
    mainApp.Channel_1_On_Btn.config(command=channel_1_On)
    mainApp.Channel_2_On_Btn.config(command=channel_2_On)
    mainApp.Channel_1_Off_Btn.config(command=channel_1_Off)
    mainApp.Channel_2_Off_Btn.config(command=channel_2_Off)
    
    mainApp.Channel_1_Set_Current_Btn.config(command=channel_1_set_current)
    mainApp.Channel_1_Set_Voltage_Btn.config(command=channel_1_set_voltage)
    mainApp.Channel_2_Set_Current_Btn.config(command=channel_2_set_current)
    mainApp.Channel_2_Set_Voltage_Btn.config(command=channel_2_set_voltage)
    
    mainApp.Psu_Set_Screen_Update_Interval_Btn.config()

def setUpdateInterval():
    global app
    global APP_REFRESH_INTERVAL
    APP_REFRESH_INTERVAL = int(app.Psu_Screen_Update_Interval_TextBox.get())/1000
        
    
def channel_1_set_current():
    global app
    global PSU_Data
    
    if CONNECTION_ACTIVE is True:
        if str(app.Channel_1_Current_Set_EntryBox.get()).isdigit() is True:
            PSU_Data.channel_1.current_set = int(app.Channel_1_Current_Set_EntryBox.get())
            PSU_Data.channel_1.set_current_flag = True

def channel_2_set_current():
    global app
    global PSU_Data
    
    if CONNECTION_ACTIVE is True:
        if str(app.Channel_2_Current_Set_EntryBox.get()).isdigit() is True:
            PSU_Data.channel_2.current_set = int(app.Channel_2_Current_Set_EntryBox.get())
            PSU_Data.channel_2.set_current_flag = True

def channel_1_set_voltage():
    global app
    global PSU_Data
    
    if CONNECTION_ACTIVE is True:
        if str(app.Channel_1_Voltage_Set_EntryBox.get()).isdigit() is True:
            PSU_Data.channel_1.voltage_set = int(app.Channel_1_Voltage_Set_EntryBox.get())
            PSU_Data.channel_1.set_voltage_flag = True
            
def channel_2_set_voltage():
    global app
    global PSU_Data
    
    if CONNECTION_ACTIVE is True:
        if str(app.Channel_2_Voltage_Set_EntryBox.get()).isdigit() is True:
            PSU_Data.channel_2.voltage_set = int(app.Channel_2_Voltage_Set_EntryBox.get())
            PSU_Data.channel_2.set_voltage_flag = True

def channel_1_On():
    global PSU_Data
    if CONNECTION_ACTIVE is True:
        PSU_Data.channel_1.TurnOn_flag = True
    
def channel_2_On():
    global PSU_Data
    if CONNECTION_ACTIVE is True:
        PSU_Data.channel_2.TurnOn_flag = True
        
def channel_1_Off():
    global PSU_Data
    if CONNECTION_ACTIVE is True:
        PSU_Data.channel_1.TurnOff_flag = True
        
def channel_2_Off():
    global PSU_Data
    if CONNECTION_ACTIVE is True:
        PSU_Data.channel_2.TurnOff_flag = True
        
def chkb1():
    
    print 'Selected CHKB 1'
    print keepPolling_channel_1.get()
    #thread3 = threading.Thread(target = pollDataFromPSU)
    #thread3.start()


def chkb2():
    print 'Selected CHKB 2'
    print keepPolling_channel_2.get()
    print 'Connection Active is',
    print CONNECTION_ACTIVE


CONNECT_BTN_TEXT_FOR_STATE = ['Connect','Disconnect']

def createPsuConnection():
    global app
    global PSU
    global CONNECTION_ACTIVE
    if app.Psu_Connect_Btn['text'] == CONNECT_BTN_TEXT_FOR_STATE[0]:
        PSU = sorensen_psu_socket_based_driver.SorensenPSUviaEth(str(app.Psu_Ip_Entry_Box.get()).strip(' '),sorensen_psu_socket_based_driver.SorensenSocketInterfaceDriver)
        app.Psu_Connect_Btn.config(text = CONNECT_BTN_TEXT_FOR_STATE[1])
        #write method to verify if connection was successful and set a flag
        CONNECTION_ACTIVE = True        
        #PSU.toggle_ID_Flashing()
        thread5 = threading.Thread(target=communicationModule)
        thread5.start()
        thread2 = threading.Thread(target = updatePsuDataOnScreen)
        thread2.start()
    elif app.Psu_Connect_Btn['text'] == CONNECT_BTN_TEXT_FOR_STATE[1]:
        app.Psu_Connect_Btn.config(text = CONNECT_BTN_TEXT_FOR_STATE[0])
        PSU.__del__()
        CONNECTION_ACTIVE = False

class PSU_channel_attributes:
    def __init__(self,channel):    
        self.channel = channel 
        self.voltage_measured = 0
        self.current_measured = 0
        self.voltage_set = 0
        self.current_set = 0
        self.ocp = 0
        self.ovp = 0
        self.channel_state = 0
        self.set_voltage_flag = 0
        self.set_current_flag = 0
        self.TurnOn_flag = 0
        self.TurnOff_flag = 0

    
class PSU_data_structure:
    def __init__(self):
        self.channel_1 = PSU_channel_attributes(1)
        self.channel_2 = PSU_channel_attributes(2)
        
    

PSU_Data = PSU_data_structure()

#later I would like to make a separate method for polling data and
#one method to update the Screen.
def pollDataFromPSU():
    global app
    global PSU
    global keepPolling_channel_1
    global keepPolling_channel_2
    global CONNECTION_ACTIVE    
    
    while CONNECTION_ACTIVE is True:
        if keepPolling_channel_1.get() is True:
            print PSU.getCurrent_Measured(1)            
            print PSU.getVoltage_Measured(1)
            
        if keepPolling_channel_2.get() is True:
            pass
        delay = int(app.Psu_Screen_Update_Interval_TextBox.get())
        time.sleep(delay/1000)    #since the above text is in milliseconds
    
def communicationModule():    
    global app
    global PSU
    global keepPolling_channel_1
    global keepPolling_channel_2
    global CONNECTION_ACTIVE
    global state_of_channel_1
    global state_of_channel_2 
    global APP_REFRESH_INTERVAL
    global PSU_Data
    
    while CONNECTION_ACTIVE is True:
        if keepPolling_channel_1.get() is True:
            PSU_Data.channel_1.voltage_measured = PSU.getVoltage_Measured(1)
            PSU_Data.channel_1.current_measured = PSU.getCurrent_Measured(1)
            PSU_Data.channel_1.channel_state = PSU.getChannelState(1)
        if keepPolling_channel_2.get() is True:
            PSU_Data.channel_2.voltage_measured = PSU.getVoltage_Measured(2)
            PSU_Data.channel_2.current_measured = PSU.getCurrent_Measured(2)
            PSU_Data.channel_2.channel_state = PSU.getChannelState(2)
            
        if PSU_Data.channel_1.TurnOff_flag is True:
            PSU.channelOff(1)
            PSU_Data.channel_1.TurnOff_flag = False

        if PSU_Data.channel_2.TurnOff_flag is True:
            PSU.channelOff(2)
            PSU_Data.channel_2.TurnOff_flag = False
            
        if PSU_Data.channel_1.TurnOn_flag is True:
            PSU.channelOn(1)
            PSU_Data.channel_1.TurnOn_flag = False
        
        if PSU_Data.channel_2.TurnOn_flag is True:
            PSU.channelOn(2)
            PSU_Data.channel_2.TurnOn_flag = False

        if PSU_Data.channel_1.set_current_flag is True:
            PSU.setCurrent(1,PSU_Data.channel_1.current_set)
            PSU_Data.channel_1.set_current_flag = False
            
        if PSU_Data.channel_2.set_current_flag is True:
            PSU.setCurrent(2,PSU_Data.channel_2.current_set)
            PSU_Data.channel_2.set_current_flag = False
        
        if PSU_Data.channel_1.set_voltage_flag is True:
            PSU.setVoltage(1,PSU_Data.channel_1.voltage_set)
            PSU_Data.channel_1.set_voltage_flag = False
        
        #we need to make only the polling parts to refresh after certain delay rest should be continuous
        time.sleep(APP_REFRESH_INTERVAL)
    
#for now let us just directly read data from PSU and display on Screen.
def updatePsuDataOnScreen():
    global app
    global PSU
    global keepPolling_channel_1
    global keepPolling_channel_2
    global CONNECTION_ACTIVE
    global state_of_channel_1
    global state_of_channel_2 
    global APP_REFRESH_INTERVAL
    #verify first if connection is active
    while CONNECTION_ACTIVE is True:
        if keepPolling_channel_1.get() is True:
            app.Channel_1_Current_Label.config(text=str(PSU_Data.channel_1.current_measured)+'A')
            app.Channel_1_Voltage_Label.config(text=str(PSU_Data.channel_1.voltage_measured)+'V')
            state_of_channel_1.set(int(PSU_Data.channel_1.channel_state))
        if keepPolling_channel_2.get() is True:
            app.Channel_2_Current_Label.config(text=str(PSU_Data.channel_2.current_measured)+'A')
            app.Channel_2_Voltage_Label.config(text=str(PSU_Data.channel_2.voltage_measured)+'V')
            state_of_channel_2.set(int(PSU_Data.channel_2.channel_state))
        
        time.sleep(APP_REFRESH_INTERVAL) #since we have delay in communication module we don't need this here anymore
        
if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = Application(root)
        guiInit(app)

        #if DEBUG == 1:        
        #    print str(app.selectPortComboBox.get())
        root.mainloop()
        
    except Exception as e:
        print "There has been an Exception, find details below:"        
        print str(e)      
