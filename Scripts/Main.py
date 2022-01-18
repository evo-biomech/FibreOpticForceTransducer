#===========================================================================================================================
# Imports
#===========================================================================================================================
from pipython import GCSDevice, pitools, datarectools, gcscommands

import multiprocessing as mp
from multiprocessing import Process
import collections
import time
import threading
from threading import Thread

import pandas as pd
import numpy as np
import yaml
from yaml import load, dump
try:
	from yaml import CLoader as Loader, CDumper as Dumper
except:
	from yaml import Loader, Dumper

import matplotlib.pyplot as plt
import matplotlib.figure as mplfig
import matplotlib.backends.backend_tkagg as tkagg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.animation as animation
from matplotlib.animation import FuncAnimation
from pylab import show

import serial
import serial.tools.list_ports
import os
from os import system as cmd
import socket
import csv

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter.filedialog import askopenfilename
from tkinter import scrolledtext
from tkinter import messagebox as msg

# Functioos and classes for motor stages and sensor
from MotorStages import deviceSettings, deviceInit, deviceRangeTest, deviceTest, deviceAbsolutePos, deviceMoveAbsolutePos, deviceRelativePos, deviceMoveRelativePos, deviceMoveMinPos, deviceMoveMaxPos, StopStages, background, multi_run_wrapper_Absolute, runInParallel, StopStages1
from Save_Stage_Disp import Method_to_List, StageDisp_To_Dict
import configtab as con
import calib as cal
import measure2 as meas
from sensor import sens
import save
from forceconversion import FC

#---------------------------
#  variables to try out the savealldata method
testmetadata = [["blubb",34],["bla",50,40,2]]
testdata = {"hallo":[1,2,3,4,5,6,7,8,9,0],"world":[0,9,8,7,6,5,4,3,2,1]}
PosRec = []

#===========================================================================================================================
# Get the current directory and define the other directories
#===========================================================================================================================
Cur_Dir = os.path.dirname(os.getcwd()) # Parent directory
Method_Dir = os.path.join(Cur_Dir, "Methods") # Directory containing the method files
Method_Dir_Std = os.path.join(Method_Dir, "Standard_Methods") # Directory containing the standard method files
Method_Dir_Grid = os.path.join(Method_Dir, "Grids") # Directory containing the method files for grids
Output_Dir = os.path.join(Cur_Dir, "OutputFiles") # Directory containing the output files

#===========================================================================================================================
# Define the range of motion and velocity allowed
#===========================================================================================================================
PosminX = 0
PosmaxX = 25
PosminY = 0
PosmaxY = 100
PosminZ = 0
PosmaxZ = 150
VelmaxX = 10
VelmaxY = 1
VelmaxZ = 50

#===========================================================================================================================
# Default variables
#===========================================================================================================================
# Set the default velocity for stage movement (mm/s)
Default_Vel_X = 10
Default_Vel_Y = 1
Default_Vel_Z = 5

# Set the stage position for initialisation (mm)
Initial_Pos_X = 10
Initial_Pos_Y = 90
Initial_Pos_Z = 45

# Number of points and frequency of recording
NUMVALUES = 1000  # number of data sets to record as integer
RECRATE = 20  # number of recordings per second, i.e. in Hz
offset_rec = 0

#===========================================================================================================================
# Motor and stage parameters
#===========================================================================================================================
"""Defining the three motor stages parameters - at this stage, we do not know which controller is connected to which USB port, 
so usb value is empty"""

motorX =	{
	"ctr": 'C-863.11',
	"stg": 'M-403.1PD',
	"usb": (),
	"ref": 'FNL',
	"axMot": 'X',
}
motorY =	{
	"ctr": 'C-663.11',
	"stg": 'M-403.42S',
	"usb": (),
  	"ref": 'FNL',
	"axMot": 'Y',
}
motorZ =	{
	"ctr": 'C-863.11',
	"stg": 'M-404.6PD',
	"usb": (),
	"ref": 'FNL',
	"axMot": 'Z',
}
motors=[motorX, motorY, motorZ]
List_Mot = np.array([motorX["axMot"],motorY["axMot"],motorZ["axMot"]]) #Array of stage axis to read the method

# Baud Rate has to match the pins on each controller
BAUDRATE=38400

# Defining the stages parameters
StageX = collections.OrderedDict([('1', 'M-403.1PD')])
StageY = collections.OrderedDict([('1', 'M-403.42S')]) # or OrderedDict([('1', 'DEFAULT_STAGE')])
StageZ = collections.OrderedDict([('1', 'M-404.6PD')]) # or OrderedDict([('1', 'DEFAULT_STAGE')])
DefaultStage = collections.OrderedDict([('1', 'DEFAULT_STAGE')]) # Can be Y or Z 
Stages = [StageX,StageY,StageZ]

#===========================================================================================================================
# Functions with global inputs
#===========================================================================================================================
""" List of functions:
Stage connection and initialisation
	ConnectStages, InitStage, PopUp_Init, multi_run_wrapper_Init
Functions to stop stages movements and exit
	exit, popUp_PosInit
Functions to get the current position of the stages and update position after movement:
	GetCurPos_x, GetCurPos_y, GetCurPos_zm Move_Update_Pos
Functions to create, import, represent and save method:
	Display_Steps, Start_Method, Add_Step, Remove_Step, Import_Method, Display_Method, callback, PlotMethod, Plot_Graph, GetMethod, SaveMethod
Functions to create a grid and change parameters independently 
	Plot_Grid, Get_Grid, Plot_Grid, SetMethod, Show_Prev_Point, Show_Next_Point, Update_Grid, GetMethod, SaveMethod, SaveGrid
Functions to open, display, and run a method file:
	OpenFile, Show_Method, Method_Grid_Plot, Show_Method_Plot, Read_method
"""

#========================================
# Stage connection and initialisation
#========================================
def ConnectStages():
	""" The function ConnectStages() automatically assigns the correct USB port of each port, connects to the stage, 
	and prints the connexion status
	"""
	global Connect_Status_X
	global Connect_Status_Y
	global Connect_Status_Z

	# Get the list of available USB ports
	print("This is motor-stage USB list", sens.usb) #The programme connects to the sensor and gets the list of all available ports (sens.usb)
	List_USB = [x for x in sens.usb if "USB" in x] # The list sens.ubs contains '/dev/ttyS0', which corresponds the hub port. I created a list
	# containing the actual USB ports

	# Find the device connected to each USB port and connect it
	Try_Connect = 0

	while Try_Connect<4: #It usually takes 3 attempts to find and connect to the stages (query times out a few times...)

		# Once all usb ports are found, it stops 
		if ((motorX['usb'] != ()) and (motorY['usb'] != ()) and (motorZ['usb'] != ())): 
			break

		# Connection to the stages 		
		else:
			print("Trying to connect to the stages...")
			#for usbP in sens.usb:
			for usbP in List_USB:
				try:
					print("try to connect", usbP)
					gcs = GCSDevice()
					gcs.ConnectRS232(usbP, BAUDRATE)
					print("    ",gcs.qIDN()) # Prints the controller ID connected to USB port
					print("    ",gcs.qCST()) # Prints the motor ID connected to USB port
					ctr = gcs.qIDN()
					stg = gcs.qCST()
					if ((stg == StageX) and ("C-863" in ctr)):
						motorX['usb'] = usbP
						print("    motorX", usbP)
					elif (((stg == StageY) or (stg == DefaultStage)) and ("C-663" in ctr)):
						motorY['usb'] = usbP
						print("    motorY", usbP)
					elif (((stg == StageZ) or (stg == DefaultStage)) and ("C-863" in ctr)):
						motorZ['usb'] = usbP
						print("    motorZ", usbP)
					gcs.CloseConnection()
					print("    Try", Try_Connect)	
					#sens.connection_check()
				except:
					print('    Not connected')
					print("    Try", Try_Connect)
					#sens.connection_check()
		Try_Connect = Try_Connect+1

	# Print the connection status
	if "USB" in motorX['usb']:
		Connect_Status_X.set("Connected")
	else:
		Connect_Status_X.set("Not connected")

	if "USB" in motorY['usb']:
		Connect_Status_Y.set("Connected")
	else:
		Connect_Status_Y.set("Not connected")

	if "USB" in motorZ['usb']:
		Connect_Status_Z.set("Connected")
	else:
		Connect_Status_Z.set("Not connected")
	
	Label_Connect_X.config(text=Connect_Status_X.get())
	Label_Connect_Y.config(text=Connect_Status_Y.get())
	Label_Connect_Z.config(text=Connect_Status_Z.get())

	SensConnect = sens.connection_check()
	print(SensConnect)

	# IF all the stages are connected, the function PopUp_Init is called to initialise the stages. If not
	# the user is warned about the connection status
	if ("USB" in motorX['usb'])&("USB" in motorY['usb'])&("USB" in motorZ['usb']):
		PopUp_Init() # Pop up window to ask the user if they want to home the stages 
	else:
		PopUp_Connect() #Pop up window to tell the user that at least one stage is not connected

#--------------------------------------------------------------------------------------------------------

def InitStage(active, BAUDRATE, Initial_Pos, Default_Vel):
	"""The function InitStage initialises the stage and homes the stage to the initial position 
	"""
	global Connect_Status_X
	global Connect_Status_Y
	global Connect_Status_Z

	# Get the connection status of the stages
	Connect_Status = [Connect_Status_X, Connect_Status_Y, Connect_Status_Z]
	Label_Connect = [Label_Connect_X, Label_Connect_Y, Label_Connect_Z]
	index = np.where(np.array(motors)==active)[0][0]

	# initialise the stages
	if (Connect_Status[index].get() != "Not connected"):
		try:
			background(lambda: deviceMoveAbsolutePos(active, BAUDRATE, Initial_Pos, Default_Vel, True, True))
		except:
			Connect_Status[index].set("Not initialised")
			Label_Connect[index].config(text=Connect_Status[index].get())
	else:
		Connect_Status[index].set("Not connected")
		Label_Connect[index].config(text=Connect_Status[index].get())

#--------------------------------------------------------------------------------------------------------
def PopUp_Init():
	"""The function PopUp_Init() displays a pop up window to warn the user about the stage initialising
	If the user presses "yes", initialisation of the stages startsm they go to their home position
	If the user presses "no", the stages stay in their current position
	If user presses "cancel", the programme is closed 
	"""
	answer = msg.askyesnocancel("Stage initialisation","Do you want to home the stages?")
	if answer:		
		background(InitStage(motorX, BAUDRATE, Initial_Pos_X, Default_Vel_X))
		background(InitStage(motorY, BAUDRATE, Initial_Pos_Y, Default_Vel_Y))
		background(InitStage(motorZ, BAUDRATE, Initial_Pos_Z, Default_Vel_Z))
	if answer is None:
		root.destroy()

#--------------------------------------------------------------------------------------------------------
def PopUp_Connect():
	"""The function PopUp_Connect() displays a pop up window if the connection failed
	If the user presses "yes", connection of the stages starts again
	If the user presses "no", it closes all the windows 
	"""
	answer = msg.askyesno("Stage connection","Attempt to connect the stages failed. Do you want to try again?")
	if answer == True:		
		ConnectStages()
	if answer == False:
		root.destroy()
	
#--------------------------------------------------------------------------------------------------------
def multi_run_wrapper_Init(args):
	return InitStage(*args)

#========================================
# Stop and exit
#========================================
def exit():
	""" Function exit() stops all stage movements, asks the user if the stages should be homed to their initial position,
	and closes the programme 
	"""
	# Stop stages movements
	StopStages1(motorX)
	StopStages1(motorY) 
	StopStages1(motorZ)

	# Call popUp_PosInit() to display ampop up window asking the user if stages should be homed, and close the programme
	ans_PosInit = popUp_PosInit()
	if ans_PosInit == True or ans_PosInit == False: #Does not exit if user hits "cancel"
		root.destroy() 

#--------------------------------------------------------------------------------------------------------
def popUp_PosInit():
	""" Function popUp_PosInit() displays a pop upwindow asking the user if the stages should be homed to their home position
	If yes, the stages are moved 
	"""
	answer = msg.askyesnocancel("Exit","Would you like to home the stages before exiting?")
	if answer == True:
		background(InitStage(motorX, BAUDRATE, Initial_Pos_X, Default_Vel_X))
		background(InitStage(motorY, BAUDRATE, Initial_Pos_Y, Default_Vel_Y))
		background(InitStage(motorZ, BAUDRATE, Initial_Pos_Z, Default_Vel_Z))
	return answer

#========================================
# Get the current position of the stages
#========================================
def GetCurPos_x():
	""" Function GetCurPos_x() gets the current position of stage X and update the position in the GUI 
	"""
	global CurPos_x
	device=GCSDevice(motorX["ctr"])
	device.ConnectRS232(motorX["usb"], BAUDRATE)
	for axis in device.axes:
		CurPos_x.set(device.qPOS(axis)[axis])
		label_CurPos_X.config(text=CurPos_x.get())
	# Schedule the GetCurPos_x() function for another 2000 ms from now to update the current position
	# root.after(2000, GetCurPos_x)

#--------------------------------------------------------------------------------------------------------
def GetCurPos_y():
	""" Function GetCurPos_y() gets the current position of stage Y and update the position in the GUI 
	"""
	global CurPos_y
	device=GCSDevice(motorY["ctr"])
	device.ConnectRS232(motorY["usb"], BAUDRATE)
	for axis in device.axes:
		CurPos_y.set(device.qPOS(axis)[axis])
		label_CurPos_Y.config(text=CurPos_y.get())
	# Schedule the GetCurPos_x() function for another 2000 ms from now to update the current position
	# root.after(2000, GetCurPos_y)

#--------------------------------------------------------------------------------------------------------
def GetCurPos_z():
	""" Function GetCurPos_z() gets the current position of stage Z and update the position in the GUI 
	"""
	global CurPos_z
	device=GCSDevice(motorZ["ctr"])
	device.ConnectRS232(motorZ["usb"], BAUDRATE)
	for axis in device.axes:
		CurPos_z.set(device.qPOS(axis)[axis])
		label_CurPos_Z.config(text=CurPos_z.get())
	# Schedule the GetCurPos_x() function for another 2000 ms from now to update the current position
	# root.after(2000, GetCurPos_z)

#--------------------------------------------------------------------------------------------------------
def Move_Update_Pos(Func_Move,arg_func):
	""" Move_Update_Pos() allows stage movement (defined by the function "Func_Move" taking "arg_func" as arguments)
	and updates the current position on the GUI
	Func_Move : Function allowing a movement of the stage
	arg_func : arguments of the function 
	"""
	# Move the stage as defined by function Func_Move and arguments arg_func
	Func_Move(*arg_func)

	# Update position at the end of the movement
	try:		
		GetCurPos_x()
		GetCurPos_y()
		GetCurPos_z()
	except:
		print('unable to print position')	

#=========================================================
# Functions to create, import, represent and save method
#=========================================================

def Display_Steps(Step_number, StartPos=1, del_Method = False, cur_step = [0]*100):
	"""When the number of steps is defined or 'add step' button is pressed, the function Display_Steps creates the widgets to define the different steps.
	It will only display the type of segments. ONce a type of segment is defined, the function "callback" is called and the fields corresponding to the type of segments are displayed
	# Step_number: number of segments defined by the user
	# StartPos: position at which the step is added
	# del_Method: boolean specifying if the current method should be deleted before diplaying the new steps (new method) or not (add segment)
	# cur_step: default value of current segment
	"""
	global Combobox_Type
	global Combobox_Stage
	global entry_Value
	global entry_Velocity
	global entry_Time

	# Delete previous method if new method is created
	if del_Method:
		for label in frame_method_def.grid_slaves():
			if int(label.grid_info()["row"]) > 1:
				label.grid_forget()

	# Add widgets for type of segments (+ segment number)
	for i in range(Step_number):
		label_StepNumber = tk.Label(frame_method_def, text=("Segment {}".format(StartPos+i)))
		label_StepNumber.grid(row=StartPos+i+3, column=0, padx=5, pady=5)
		label_Type = tk.Label(frame_method_def, text="Type")
		label_Type.grid(row=2, column=1, padx=5, pady=5)
		#Combobox_Type[StartPos+i-1] = ttk.Combobox(frame_method_def, state="readonly", values = ('','Move stage','Hold','Preload'))
		Combobox_Type[StartPos+i-1] = ttk.Combobox(frame_method_def, state="readonly", values = values_Combobox_Type)
		Combobox_Type[StartPos+i-1].current(cur_step[i])
		Combobox_Type[StartPos+i-1].grid(row=StartPos+i+3, column=1, padx=5, pady=5)
		Combobox_Type[StartPos+i-1].bind('<<ComboboxSelected>>', lambda event, arg=StartPos+i-1: callback(event, arg))

#--------------------------------------------------------------------------------------------------------
def Start_Method(Step_number):
	""" The function Start_Method allows the user to start a new method containing the number of segments (Step_number) 
	defined by the user
	# Step_number: number of the segments in the method
	"""
	global Combobox_Type	
	global Combobox_Stage	
	global entry_Value	
	global entry_Velocity	
	global entry_Time	

	# Create empty widgets of length the number of segments
	Combobox_Type = [None]*Step_number
	Combobox_Stage = [None]*Step_number
	entry_Value = [None]*Step_number
	entry_Velocity = [None]*Step_number
	entry_Time = [None]*Step_number

	# Clear the previous graph and set the axis labels and titles (by default, stage movement control)
	ax.clear()
	ax.set_xlabel('Time (s)', fontsize=14)
	ax.set_ylabel('Displacement (mm)', fontsize=14)
	ax.set_title('Z stage movement', fontsize=18)
	ax.grid()

	# Display the types of segment for each segment	
	Display_Steps(Step_number, del_Method = True)	

#--------------------------------------------------------------------------------------------------------
def Add_Step():
	"""The function Add_Steps() will add a new segment at the end of the segments already defined
	"""
	global Number_Steps
	global Combobox_Type
	global Combobox_Stage
	global entry_Value
	global entry_Velocity
	global entry_Time

	# Add an empty value in each dictionary
	Combobox_Type.append(None)
	Combobox_Stage.append(None)
	entry_Value.append(None)
	entry_Velocity.append(None)
	entry_Time.append(None)

	# Update the number of segments in the GUI
	Number_Steps.set(Number_Steps.get()+1)

	# Add widgets in the GUI for the addtional segment
	Display_Steps(1, StartPos=Number_Steps.get())

#--------------------------------------------------------------------------------------------------------
def Remove_Step():
	"""The function Remove_Step() removes the last step of the method and calls the function PlotMethod()
	to update the graphical representation of the segments
	"""
	global Number_Steps
	global Combobox_Type
	global Combobox_Stage
	global entry_Value
	global entry_Velocity
	global entry_Time

	# Remove widgets from the GUI
	for label in frame_method_def.grid_slaves():
		if ((int(label.grid_info()["row"]) == 3+Number_Steps.get())):
			label.grid_forget()
	Number_Steps.set(Number_Steps.get()-1)

	# Remove last values from the lists
	Combobox_Type.pop()
	Combobox_Stage.pop()
	entry_Value.pop()
	entry_Velocity.pop()
	entry_Time.pop()

	# Update the graph to remove the last segment
	PlotMethod()

#--------------------------------------------------------------------------------------------------------
def Import_Method():
	"""The function Import_Method() allows the user to import an existing method and update the parameters.   
	The function calls the function Display_Method() to set the initial values of the widgets, and 
	PlotMethod() to display the graphical representation of the segments
	"""
	# Open a method file
	name = askopenfilename(initialdir=Method_Dir_Std, filetypes =(("YAML files", "*.yaml"),("All Files","*.*")), title = "Choose a file.")

	# Read the file and create dictionary List
	with open(name,'r') as UseFile:
		List = yaml.load(UseFile)

	# Display content of the method in GUI
	Display_Method(List)

#--------------------------------------------------------------------------------------------------------
def Display_Method(List):
	"""The function Display_Method(List) displays the method defined by List (called when a method is imported or a list is created)
	# List: dictionnary containing all the steps
	"""
	global Number_Steps
	global Combobox_MethodType
	global Combobox_Type
	global Combobox_Stage
	global entry_Value
	global entry_Velocity
	global entry_Time

	# Create empty widgets depending on the number of segments
	NumberSteps = len(List)
	Combobox_Type = [None]*NumberSteps
	Combobox_Stage = [None]*NumberSteps
	entry_Value = [None]*NumberSteps
	entry_Velocity = [None]*NumberSteps
	entry_Time = [None]*NumberSteps

	Current_Steps = [None]*NumberSteps
	values_Steps = np.array(values_Combobox_Type)
	values_Stages = np.array(['X','Y','Z'])	

	# Display the correct widgets depending on the type of segments
	for item, doc in List.items():
		Current_Steps[item] = np.where(values_Steps == doc.get('Type'))[0][0]
	Display_Steps(NumberSteps, del_Method = True, cur_step = Current_Steps)

	# Add the values of each widget as defined in List
	for item, doc in List.items():	
		if (doc.get('Type') == values_Steps[1]): # If Move stage
			Current_Control = np.where(np.array(Combobox_MethodType['values']) == doc.get('Control'))[0][0]
			Combobox_MethodType.current(Current_Control)

			label_Stage = tk.Label(frame_method_def, text="Stage")
			label_Stage.grid(row=4+item, column=2, padx=5, pady=5)
			Combobox_Stage[item] = ttk.Combobox(frame_method_def, state="readonly", values = ('X','Y','Z'))
			Current_Stage = np.where(values_Stages == doc.get('Stage'))[0][0]
			Combobox_Stage[item].current(Current_Stage)
			Combobox_Stage[item].grid(row=4+item, column=3, padx=5, pady=5)

			Current_Value = values_LabelValue[Current_Control]
			label_Value = tk.Label(frame_method_def, text=Current_Value)
			label_Value.grid(row=4+item, column=4, padx=5, pady=5)
			entry_Value[item] = tk.Entry(frame_method_def)
			entry_Value[item].insert(0,doc.get('Value'))
			entry_Value[item].grid(row=4+item, column=5, padx=5, pady=5)
			entry_Value[item].bind("<Return>", PlotMethod)

			label_Time = tk.Label(frame_method_def, text="Duration (s)")
			label_Time.grid(row=4+item, column=6, padx=5, pady=5)
			entry_Time[item] = tk.Entry(frame_method_def)
			entry_Time[item].insert(0,doc.get('Duration'))
			entry_Time[item].grid(row=4+item, column=7, padx=5, pady=5)
			entry_Time[item].bind("<Return>", PlotMethod)

		if (doc.get('Type') == values_Steps[2]): # If Hold
			label_Time = tk.Label(frame_method_def, text="Duration (s)")
			label_Time.grid(row=4+item, column=2, padx=5, pady=5)
			entry_Time[item] = tk.Entry(frame_method_def)
			entry_Time[item].insert(0,doc.get('Duration'))
			entry_Time[item].grid(row=4+item, column=3, padx=5, pady=5)
			entry_Time[item].bind("<Return>", PlotMethod)

		if (doc.get('Type') == values_Steps[3]): # If Preload
			label_Stage = tk.Label(frame_method_def, text="Stage")
			label_Stage.grid(row=4+item, column=2, padx=5, pady=5)
			Combobox_Stage[item] = ttk.Combobox(frame_method_def, state="readonly", values = ('X','Y','Z'))
			Current_Stage = np.where(values_Stages == doc.get('Stage'))[0][0]
			Combobox_Stage[item].current(Current_Stage)
			Combobox_Stage[item].grid(row=4+item, column=3, padx=5, pady=5)

			label_Force = tk.Label(frame_method_def, text="Force (mN)")
			label_Force.grid(row=4+item, column=4, padx=5, pady=5)
			entry_Value[item] = tk.Entry(frame_method_def)
			entry_Value[item].insert(0,doc.get('Value'))			
			entry_Value[item].grid(row=4+item, column=5, padx=5, pady=5)

			label_Velocity = tk.Label(frame_method_def, text="Velocity (mm/s)")
			label_Velocity.grid(row=4+item, column=6, padx=5, pady=5)
			entry_Velocity[item] = tk.Entry(frame_method_def)
			entry_Velocity[item].insert(0,doc.get('Velocity'))
			entry_Velocity[item].grid(row=4+item, column=7, padx=5, pady=5)

			label_Time = tk.Label(frame_method_def, text="Duration (s)")
			label_Time.grid(row=4+item, column=8, padx=5, pady=5)
			entry_Time[item] = tk.Entry(frame_method_def)
			entry_Time[item].insert(0,doc.get('Duration'))
			entry_Time[item].grid(row=4+item, column=9, padx=5, pady=5)
			entry_Time[item].bind("<Return>", PlotMethod)

		Number_Steps.set(len(List))

	# Plot the method
	PlotMethod(key=None)

#-------------------------------------------------------------------------------------------------------------------------
def callback(event, arg):
	"""When the type of segment is defined (move, hold or preload), the function Display_Steps will call the function callback to display
	the parameters related to the type of segment. Once a segment is defined (and Return key is pressed), it will call the function
	PlotMethod to add a representation of the segment 
	# event: the function is called when the return key is pressed
	# arg: Position on the grid of the frame (integer)
	"""
	global Combobox_MethodType
	global Combobox_Stage
	global Combobox_Control
	global entry_Value
	global entry_Velocity
	global entry_Time

	# Delete previous line when type of segment (move / hold / Preload) is changed
	for label in frame_method_def.grid_slaves():
		if ((int(label.grid_info()["row"]) == 4+arg) and int(label.grid_info()["column"])>1):
			label.grid_forget()
	
	# Define the labels depending on the method (Stage movement, displacement or force)	
	Current_Value_Index = np.where(Combobox_MethodType.get() == np.array(Combobox_MethodType['values']))[0][0]
	Current_Value = values_LabelValue[Current_Value_Index]

	# Types of segments (move stage / hold / preload)
	values_Steps = np.array(values_Combobox_Type) # Type

	# Add widgets according to the type of segment
	if (event.widget.get() ==  values_Steps[1]): # if move stage
		label_Stage = tk.Label(frame_method_def, text="Stage")
		label_Stage.grid(row=4+arg, column=2, padx=5, pady=5)
		Combobox_Stage[arg] = ttk.Combobox(frame_method_def, state="readonly", values = ('X','Y','Z'))
		Combobox_Stage[arg].current(2)
		Combobox_Stage[arg].grid(row=4+arg, column=3, padx=5, pady=5)

		Label_Value = tk.Label(frame_method_def, text=Current_Value)
		Label_Value.grid(row=4+arg, column=4, padx=5, pady=5)
		entry_Value[arg] = tk.Entry(frame_method_def)
		entry_Value[arg].grid(row=4+arg, column=5, padx=5, pady=5)
		entry_Value[arg].bind("<Return>", PlotMethod)

		label_Time = tk.Label(frame_method_def, text="Duration (s)")
		label_Time.grid(row=4+arg, column=6, padx=5, pady=5)
		entry_Time[arg] = tk.Entry(frame_method_def)
		entry_Time[arg].grid(row=4+arg, column=7, padx=5, pady=5)
		entry_Time[arg].bind("<Return>", PlotMethod)

	if (event.widget.get() == values_Steps[2]): # if hold
		label_Time = tk.Label(frame_method_def, text="Duration (s)")
		label_Time.grid(row=4+arg, column=2, padx=5, pady=5)
		entry_Time[arg] = tk.Entry(frame_method_def)
		entry_Time[arg].grid(row=4+arg, column=3, padx=5, pady=5)
		entry_Time[arg].bind("<Return>", PlotMethod)

	if (event.widget.get() ==  values_Steps[3]): # if preload
		label_Stage = tk.Label(frame_method_def, text="Stage")
		label_Stage.grid(row=4+arg, column=2, padx=5, pady=5)
		Combobox_Stage[arg] = ttk.Combobox(frame_method_def, state="readonly", values = ('X','Y','Z'))
		Combobox_Stage[arg].current(2)
		Combobox_Stage[arg].grid(row=4+arg, column=3, padx=5, pady=5)

		label_Force = tk.Label(frame_method_def, text="Force (mN)")
		label_Force.grid(row=4+arg, column=4, padx=5, pady=5)
		entry_Value[arg] = tk.Entry(frame_method_def)
		entry_Value[arg].grid(row=4+arg, column=5, padx=5, pady=5)

		label_Velocity = tk.Label(frame_method_def, text="Velocity (mm/s)")
		label_Velocity.grid(row=4+arg, column=6, padx=5, pady=5)
		entry_Velocity[arg] = tk.Entry(frame_method_def)
		entry_Velocity[arg].grid(row=4+arg, column=7, padx=5, pady=5)
		entry_Velocity[arg].bind("<Return>", PlotMethod)

		label_Time = tk.Label(frame_method_def, text="Duration (s)")
		label_Time.grid(row=4+arg, column=8, padx=5, pady=5)
		entry_Time[arg] = tk.Entry(frame_method_def)
		entry_Time[arg].grid(row=4+arg, column=9, padx=5, pady=5)
		entry_Time[arg].bind("<Return>", PlotMethod)
		
#-------------------------------------------------------------------------------------------------------------------------
def PlotMethod(key=None):
	"""The function PlotMethod gets x_time and y_disp and calls the function Plot_Graph to plot the different segments 
	and have a representation of the method (only stage Z)
	The function does not represent the preload- only the holding of preload
	# key: the function is called when the return key is pressed, or when importing a method
	"""
	global ax
	global canvas
	global List_Types
	global List_Value
	global List_Vel
	global List_Time
	global X_Time
	global Y_Disp

	# Create empty lists with length of number of segments (+1 for X and Y)
	List_Types = [None] * Number_Steps.get()
	List_Value = [None] * Number_Steps.get()
	List_Vel = [None] * Number_Steps.get()
	List_Time = [None] * Number_Steps.get()
	X_time = [None] * (Number_Steps.get()+1)
	X_time[0] = 0
	Y_disp = [None] * (Number_Steps.get()+1)
	Y_disp[0] = 0

	values_Steps = np.array(values_Combobox_Type) # Types of segments (move stage / hold / preload)

	# Add values in the list
	for i in range(Number_Steps.get()):
		try: 
			List_Types[i] = Combobox_Type[i].get()
			if (List_Types[i]==values_Steps[1]): # if move stage
				List_Value[i] = (float(entry_Value[i].get()))
				List_Vel[i] = abs(float(entry_Value[i].get())/float(entry_Time[i].get())) #(float(entry_Velocity[i].get()))
				List_Time[i] = (float(entry_Time[i].get()))
				X_time[i+1] = X_time[i] + List_Time[i]
				if (Combobox_Stage[i].get() == 'Z'):
					Y_disp[i+1] = List_Value[i] + Y_disp[i]
				else:
					Y_disp[i+1] = Y_disp[i]
			else:
				List_Value[i] = 'na'
				List_Vel[i] = 'na'
				List_Time[i] = (float(entry_Time[i].get()))
				X_time[i+1] = X_time[i] + List_Time[i]
				Y_disp[i+1] = Y_disp[i]
		except:
			break

	try:
		index = np.where((np.array(X_time)==None)&(np.array(Y_disp)==None))[0][0]
	except:
		index = len(Y_disp)

	Plot_Graph(X_time, Y_disp, ax, canvas, index)

#-------------------------------------------------------------------------------------------------------------------------
def Plot_Graph(X_time, Y_disp, ax, canvas, index=None): 
	"""The function Plot_Graph plots the different segments to have a representation of the method (only stage Z). Depending on the type
	of method (Stage movement, displacement control, force control)m it plots either W stage movementm displacementm or force
	The function does not represent the preload- only the holding of preload
	# X_Time: array of time
	# Y_disp: array of stage movement / displacement / Force
	# ax, canvas: figure and canvas in which the graph is plotted
	"""
	global Combobox_MethodType

	Type_Method = Combobox_MethodType.get()

	ax.clear()
	line, = ax.plot(X_time, Y_disp, '.-')   #tuple of a single element
	try:
		ax.set_xlim(min(X_time[0:index]), max(X_time[0:index]))
		ax.set_ylim(min(Y_disp[0:index])-1, max(Y_disp[0:index])+1)
	except:
		ax.set_xlim(0, 10)
		ax.set_ylim(-5, 5)
	ax.set_xlabel('Time (s)', fontsize=14)
	if Type_Method == Combobox_MethodType['values'][0]:
		ax.set_ylabel('Displacement (mm)', fontsize=14)
		ax.set_title('Z stage movement', fontsize=16)
	if Type_Method == Combobox_MethodType['values'][1]:
		ax.set_ylabel('Displacement (um)', fontsize=14)
		ax.set_title('Displacement', fontsize=16)
	if Type_Method == Combobox_MethodType['values'][2]:
		ax.set_ylabel('Force (mN)', fontsize=14)
		ax.set_title('Force', fontsize=16)
	ax.grid()
	canvas.draw()	
	canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
	
#-------------------------------------------------------------------------------------------------------------------------
def GetMethod():
	"""The function GetMethod() creates a dictionary containing the method, 
	and the function SaveMethod() saves the different segments in a yaml format
	"""
	global Combobox_MethodType
	global List_Types
	global List_Stages
	global List_Value
	global List_Vel
	global List_Time
	global Dict_Grid
	global Dict_Final
	global Cur_Point

	List_Types = [None] * Number_Steps.get()	
	List_Stages = [None] * Number_Steps.get()
	List_Value = [None] * Number_Steps.get()
	List_Vel = [None] * Number_Steps.get()
	List_Time = [None] * Number_Steps.get()

	Name_method = Combobox_MethodType.get()
	values_Steps = np.array(values_Combobox_Type) # Types of segments (move stage / hold / preload)

	Number_Segments = len(Combobox_Type)

	# Create lists for each widget
	for i in range(Number_Segments):
		List_Types[i] = Combobox_Type[i].get()
		if (List_Types[i]==values_Steps[1]): # if move stage
			List_Stages[i] = Combobox_Stage[i].get()
			List_Value[i] = (float(entry_Value[i].get()))
			List_Vel[i] = abs(float(entry_Value[i].get())/float(entry_Time[i].get())) #(float(entry_Velocity[i].get()))
			List_Time[i] = (float(entry_Time[i].get()))
		elif (List_Types[i]==values_Steps[2]):  # if hold
			List_Stages[i] = 'na'
			List_Value[i] = 'na'
			List_Vel[i] = 'na'
			List_Time[i] = (float(entry_Time[i].get()))
		elif (List_Types[i]==values_Steps[3]): # if preload
			List_Stages[i] = Combobox_Stage[i].get()
			List_Value[i] = (float(entry_Value[i].get()))
			List_Vel[i] = 'na'
			List_Time[i] = (float(entry_Time[i].get()))
			List_Vel[i] = (float(entry_Velocity[i].get()))
		else:
			Number_Segments = i		
			break

	# Create dictionary
	dict_test = {}	
	for i in range(Number_Segments):
		dict_test[i] = {'Control': Name_method, 'Type': List_Types[i], 'Stage': List_Stages[i], 'Value': List_Value[i], 'Velocity': List_Vel[i], 
				  'Duration': List_Time[i]}

	# For a grid - updates the variable Dict_Grid with the new method defined by the user
	try:
		Dict_Grid[Cur_Point.get()-1] = dict_test
	except:
		Dict_Grid = [None]*1
		Dict_Grid[0] = dict_test	
	return dict_test
	
#-------------------------------------------------------------------------------------------------------------------------
def SaveMethod():
	""" The function SaveMethod calls GetMethod to create a dictionary containing the method defined by the user and saves it in a 
	YAML format 
	"""
	dict_test = GetMethod()
	filenameSave =  filedialog.asksaveasfilename(initialdir = Method_Dir_Std, title = "Select file",filetypes = (("yaml","*.yaml"),("all files","*.*")))	
	with open(filenameSave, 'w') as yaml_file:
		yaml.dump(dict_test, yaml_file, default_flow_style=False)

#================================================================
# Functions to create a grid and change parameters independently
#================================================================
def Get_Grid(event=None):
	"""The function Get_Grid() gets the coordinates of each measurement point on the grid and calls the function Plot_Grid() 
	# event: the function is called when the return key is pressed
	"""
	X_grid = []
	Y_grid = []
	n = []
	k = 1
	for i in range(Grid_Number_X.get()):
		for j in range(Grid_Number_Y.get()):
			X_grid.append(i*Grid_dX.get())
			Y_grid.append(j*Grid_dY.get())
			n.append(k)
			k = k+1
	Plot_Grid(X_grid, Y_grid, ax_grid, canvas_grid, n)

#-------------------------------------------------------------------------------------------------------------------------
def Plot_Grid(X_Pos, Y_Pos, ax, canvas, n=[1], index=None): 
	"""The function Plot_Grid plots a representation of the grid, with a label on each point
	# X_Pos, Y_Pos: array of coordinates
	# ax: figure in whih the grid is plotted
	# canvas: canvas in which the figure is plotted
	# n: number of points to label
	# index: used to find the limits of X and Y 
	"""
	ax.clear()
	line, = ax.plot(X_Pos, Y_Pos, '.')   #tuple of a single element

	# Set axis limits
	try:
		ax.set_xlim(min(X_Pos[0:index])-1, max(X_Pos[0:index])+1)
		ax.set_ylim(min(Y_Pos[0:index])-1, max(Y_Pos[0:index])+1)
	except:
		ax.set_xlim(0, 10)
		ax.set_ylim(0, 10)

	# Set axis labels and graph title
	ax.set_xlabel('X position (mm)', fontsize=14)
	ax.set_ylabel('Y position (mm)', fontsize=14)
	ax.set_title('Grid of measurements', fontsize=16)

	# Add the number of each point
	for i, txt in enumerate(n):
		ax.annotate(txt, (X_Pos[i], Y_Pos[i]))
	
	# Add grid and plot the points
	ax.grid()
	canvas.draw()	
	canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

#-------------------------------------------------------------------------------------------------------------------------
def SetMethod():
	"""Function SetMethod() creates a grid method with identical segments on each point, and displays it
	"""
	global Dict_Method
	global Dict_Grid
	global Dict_Final
	global Grid_Number_X
	global Grid_Number_Y
	global ax
	global canvas

	# Get number of points in the grid and create dictionary
	Num_Points_Grid = Grid_Number_X.get()*Grid_Number_Y.get()	
	Dict_Grid = [None]*Num_Points_Grid # Dictionary of the whole method with identical segments in each point
	Dict_Final = {} # Dictionary of the whole method updated in each point

	Dict_Method = GetMethod() # Dictionary of the method in one location

	# Create lists with X and Y coordinates
	X_grid = []
	Y_grid = []
	for i in range(Grid_Number_X.get()):
		for j in range(Grid_Number_Y.get()):
			X_grid.append(i*Grid_dX.get())
			Y_grid.append(j*Grid_dY.get())

	# Create dictionary with X and Y coordinates, and method in each point (same method in each point)
	for i in range(Num_Points_Grid):
		Dict_Grid[i] = Dict_Method
		Num_Segment = len(Dict_Grid[i])
		Dict_Final[(Num_Segment+1)*i] = {'Type': 'Go to', 'Pos X': X_grid[i], 'Pos Y': Y_grid[i], 'Z up': Z_up.get()}
		for j in range(Num_Segment):
			Dict_Final[(Num_Segment+1)*i+j+1] = {**Dict_Grid[i][j]} #Add ** to copy the content of the dictionary and not the dict itself

	# Plot the whole method
	[X_time, Y_disp] = Method_Grid_Plot(Dict_Final)
	try:
		index = np.where((np.array(X_time)==None)&(np.array(Y_disp)==None))[0][0]
	except:
		index = len(Y_disp)
	Plot_Graph(X_time, Y_disp, ax, canvas, index)

#-------------------------------------------------------------------------------------------------------------------------
def Show_Prev_Point():
	"""The function Show_Prev_Point() updates the method of the current point of the grid and 
	displays the method of the previous point of the grid, if this point is in the grid
	""" 
	global Cur_Point
	global Grid_Number_X
	global Grid_Number_Y
	global Dict_Grid

	Update_Grid() # Update_Grid() is called to save the changes that have been made on the current point

	# Set the point number (should be superior to 1)
	if Cur_Point.get()>1:
		Cur_Point.set(Cur_Point.get()-1)
	Label_Cur_Point.config(text=Cur_Point.get())

	# Display the method on the current point and plot the whole method
	Display_Method(Dict_Grid[Cur_Point.get()-1]) # Updates the dictionary on the current point
	Update_Grid() # Update_Grid() is called again to plot the entire method in each point of the grid

#-------------------------------------------------------------------------------------------------------------------------
def Show_Next_Point():
	"""The function Show_Next_Point() updates the method of the current point of the grid and 
	displays the method of the next point of the grid
	"""
	global Cur_Point
	global Grid_Number_X
	global Grid_Number_Y

	Update_Grid() # Update_Grid() is called to save the changes taht have been made on the current point

	# Set the point number (should be inferior or equal to number of points)
	if Cur_Point.get()<Grid_Number_X.get()*Grid_Number_Y.get():
		Cur_Point.set(Cur_Point.get()+1)
	Label_Cur_Point.config(text=Cur_Point.get())

	# Display the method on the current point and plot the whole method
	Display_Method(Dict_Grid[Cur_Point.get()-1]) # Updates the dictionary on the current point
	Update_Grid() # Update_Grid() is called again to plot the entire method in each point of the grid

#-------------------------------------------------------------------------------------------------------------------------
def Update_Grid():
	"""The function Update_Grid() updates the method of the current segment and stores the whole method in Dict_Final
	"""
	global Cur_Point
	global Grid_Number_X
	global Grid_Number_Y
	global Dict_Final
	global Dict_Grid

	# Create a dictionnary (Dict_Grid) from the method defined by the user on the current point
	dict_test = GetMethod() # The variable dict_test is not used- he function GetMethod updates the variable Dict_Grid

	# Get the number of points in the grid and create arrays with X and y coordinates
	Num_Points_Grid = Grid_Number_X.get()*Grid_Number_Y.get()
	X_grid = []
	Y_grid = []
	for i in range(Grid_Number_X.get()):
		for j in range(Grid_Number_Y.get()):
			X_grid.append(i*Grid_dX.get())
			Y_grid.append(j*Grid_dY.get())

	k = 0 # k is the number of segments in the new dictionnary (may differ from the length of the dictionnary if a segment is removed from the method in one point

	# Create the final dictionnary containing the different points and the dictionnary on each point
	for i in range(Num_Points_Grid):
		Num_Segment = len(Dict_Grid[i])
		Dict_Final[k] = {'Type': 'Go to', 'Pos X': X_grid[i], 'Pos Y': Y_grid[i], 'Z up': Z_up.get()}
		k = k+1
		for j in range(Num_Segment):
			Dict_Final[k] = {**Dict_Grid[i][j]} #Add ** to copy the content of the dictionary and not the dict itself
			k = k+1

	#Delete elements of the dictionary if a segment is removed
	for i in range(len(Dict_Final)-k):
		try:
			del Dict_Final[k+i]
		except:
			break

	#Plot the method in each point
	[X_time, Y_disp] = Method_Grid_Plot(Dict_Final)
	try:
		index = np.where((np.array(X_time)==None)&(np.array(Y_disp)==None))[0][0]
	except:
		index = len(Y_disp)
	Plot_Graph(X_time, Y_disp, ax, canvas, index)

#-------------------------------------------------------------------------------------------------------------------------
def SaveGrid():
	"""The function SaveGrid() saves the different segments in each point of the grid in a yaml format
	"""
	global Dict_Final

	Update_Grid()
	dict_test = GetMethod()
	filenameSave =  filedialog.asksaveasfilename(initialdir = Method_Dir_Grid, title = "Select file",filetypes = (("yaml","*.yaml"),("all files","*.*")))
	with open(filenameSave, 'w') as yaml_file:
		yaml.dump(Dict_Final, yaml_file, default_flow_style=False)

#===================================================
# Functions to open, display, and run a method file
#===================================================

def OpenFile():
	"""OpenFile() will open a dialog window to browse the file and will set the name of the file
	It will then call Show_method() to display the method content in a new frame and Show_Method_Plot()
	to add a graphical representation of the successive segments in a new frame
	"""
	global Filename_method

	name = askopenfilename(initialdir=Method_Dir, filetypes =(("YAML files", "*.yaml"),("All Files","*.*")), title = "Choose a file.")
	#Using try in case user types in unknown file or closes without choosing a file.
	try:
		with open(name,'r') as UseFile:
			print(UseFile.read())
			Filename_method.set(UseFile.name)
			Show_Method(UseFile.name)
			Show_Method_Plot(UseFile.name)
	except:
		print("File does not exist")

#-------------------------------------------------------------------------------------------------------------------------
def Show_Method(filename):
	""" The function Show_Method(filename) reads the method contained in the file and displays its content
	"""
	global Method_Content

	# Read the method and update the variable "Method_Content"
	try:
		with open(filename) as file:
			Method_Content.set(file.read()) # Reads the content of the method
		
	except:
		Method_Content.set('No test - File does not exist')

	# Create frame containing the method content 
	frame_Method_Content = ttk.LabelFrame(tab1, text = 'Segments', borderwidth=2, relief='ridge')
	frame_Method_Content.grid(column=0, row=3, columnspan=1, sticky="nsew")
	frame_Method_Content.columnconfigure(1, weight=1)
	frame_Method_Content.rowconfigure(1, weight=1)

	# Create a scrolledtext widget containing the method content 
	scrol_h = 30
	scrol_w = 50
	scr = scrolledtext.ScrolledText(frame_Method_Content, width = scrol_w, height = scrol_h)
	scr.grid(row=0, column=0, padx=5, pady=5, columnspan=1)
	scr.configure(state='normal')
	scr.insert('insert', Method_Content.get())
	scr.configure(state='disabled')	# State is 'disabled' so that the user can change the content

#-------------------------------------------------------------------------------------------------------------------------
def Method_Grid_Plot(List):
	"""The function Method_Grid_Plot() gets the coordinates of X (time) and Y (Z displacement/Force) for a grid
	# List: dictionnary containing the method (one point or grid)
	"""
	# Creates X and Y arays (Y_Disp can be stage movement, displacement or force)
	X_time = [None] * (len(List)+1)
	X_time[0] = 0
	Y_disp = [None] * (len(List)+1)
	Y_disp[0] = 0

	# Add the values or X and Y
	for item, doc in List.items():
		Type = doc.get('Type')
		if (Type == "Preload"):
			t_hold = doc.get("Duration")
			X_time[item+1] = X_time[item] + t_hold
			Y_disp[item+1] = Y_disp[item]
		if (Type == "Move stage"):
			Stg = doc.get('Stage')
			Dis = doc.get('Value')
			Vel = doc.get('Velocity')
			X_time[item+1] = X_time[item] + abs(Dis)/Vel
			if (Stg == 'Z'):
				Y_disp[item+1] = Dis + Y_disp[item]
			else:
				Y_disp[item+1] = Y_disp[item]
		if (Type == "Hold"):
			t_hold = doc.get("Duration")
			X_time[item+1] = X_time[item] + t_hold
			Y_disp[item+1] = Y_disp[item]
		if (Type == "Go to"):
			X_time[item+1] = X_time[item]
			Y_disp[item+1] = Y_disp[item]
	return X_time,Y_disp

#-------------------------------------------------------------------------------------------------------------------------
def Show_Method_Plot(filename):
	"""The function Show_Method_Plot() plots the representation of the method (one point or grid)
	# filename: name of file containing the method
	"""
	# Open the file and call Method_Grid_Plot to get X and y coordinates
	with open(filename) as file:
		List = yaml.load(file)
	[X_time, Y_disp] = Method_Grid_Plot(List)

	#Create frame in which the graph will be displayed
	frame_Method_Plot = ttk.LabelFrame(tab1, text = 'Plot', borderwidth=2, relief='ridge')
	frame_Method_Plot.grid(column=1, row=3, columnspan=1, sticky="nsew")
	frame_Method_Plot.columnconfigure(1, weight=1)
	frame_Method_Plot.rowconfigure(1, weight=1)	

	#Create a figure and plot the graph with a toolbar
	fig = Figure(figsize=(5,3))
	ax1 = fig.add_subplot(111)
	fig.subplots_adjust(top=0.9,bottom=0.20,left=0.15,right=0.9)

	canvas1 = FigureCanvasTkAgg(fig, master=frame_Method_Plot)
	toolbar1 = NavigationToolbar2Tk(canvas1, frame_Method_Plot)

	Plot_Graph(X_time, Y_disp, ax1, canvas1)

#-------------------------------------------------------------------------------------------------------------------------
# Functions to start or stop the measurement when test is started or stopped
#-------------------------------------------------------------------------------------------------------------------------
def start_measuring(tabControl,measuretab): 
	"""starts the data stream the plotted data depends on whether self.plotforce= true or false
	creates a new graphframe on top of the old one"""
	measuretab.switchon()
	tabControl.select(measuretab)

def stop_measuring(measuretab):
	"""stops the datastream and the animation, reads out the buffer and appends its content to sens.emptystreamdict"""	
	measuretab.switchoff()
	savealldata_temp()
	print('data saved')
	

def recorddata1(drec, NUMVALUES=300, RECRATE=100):
	"""Set up data recorder to record 2 tables for first axis after next motion command.
	@type drec : pipython.datarectools.Datarecorder
	"""
	#Start_Record = time.time()
	drec.numvalues = NUMVALUES
	drec.samplefreq = RECRATE
	print('data recorder rate: {:.2f} Hz'.format(drec.samplefreq))
	drec.options = (datarectools.RecordOptions.ACTUAL_POSITION_2, datarectools.RecordOptions.COMMANDED_POSITION_1)
	drec.sources = drec.gcs.axes[0]	
	drec.trigsources = datarectools.TriggerSources.NEXT_COMMAND_WITH_RESET_2

#-------------------------------------------------------------------------------------------------------------------------
stop_event = threading.Event() # when the "stop test" button is pressed, the thread will start and the test loop will stop

def Read_method(filename, List_Mot, BAUDRATE, stop_event,tabControl, measuretab):
	"""The function Read method reads the method file and calls the appropriate function to execute the successive segments
	depending on the type of method (stage movement, displacement control, force control)
	# filename: name of file containing the method
	# List_Mot: List of motors
	# BAUDRATE : baudrate used for the controllers (same for all stages)
	# stop_event : thread started when "stop test" button is pressed
	# tabControl : tab of measurements
	# measuretab : 	
	"""
	global Method_Content
	global NUMVALUES
	global Mot_freq
	global RECRATE
	global testdata
	global testmetadata
	global offset_rec
	global PosRec

	# Make sure the correct beam is selected and distances are entered correctly
	forcedist = FC.forcelength
	measdist = FC.measurelength
	Tare_dist = FC.tare	
	beam_test = sens.current_beam	
	answer = popup_beam(beam_test,forcedist,measdist,Tare_dist)

	if answer == True:

		# Make sure data from previous test is cleared
		print("forcelist: ", sens.make_forcelist())
		print("timelist: ", sens.timelist)
		ans_clear = True
		if sens.make_forcelist(): # Check if force array is not empty
			ans_clear = popup_clear()

		# Read the file and execute the test
		if ans_clear:
			try:
				Current_Segment.set("Reading file")

				with open(filename) as file:
					# Create dictionary of the method
					try:
						List = yaml.load(file, Loader = yaml.FullLoader) #Loader does not work here
					except:
						List = yaml.load(file)
					stop_event.clear()

					# Calculate the duration of the test and frequency of recording + number of recording values read
					RECRATE = Get_Recrate(List,float(entry_freq.get()))
					offset_reading = RECRATE # number of recording values read when recording function is called
								
					# Create frame containing progression of the test
					Frame_Test_Progression = ttk.LabelFrame(tab1, text = 'Progression', borderwidth=2, relief='ridge')
					Frame_Test_Progression.grid(column=0, row=4, sticky="nsew", columnspan=2)
					Frame_Test_Progression.columnconfigure(1, weight=1)
					Frame_Test_Progression.rowconfigure(1, weight=1)
					Label_Test_Progression = tk.Label(Frame_Test_Progression, textvariable=Current_Segment)
					Label_Test_Progression.grid(row=0, column=0, padx=5, pady=5, columnspan=8)

					# Getting the initial position for the grid and update label in GUI
					GetCurPos_x()
					PosX_init = CurPos_x.get()
					GetCurPos_y()
					PosY_init = CurPos_y.get()
					GetCurPos_z()
					PosZ_init = CurPos_z.get()
					Initial_Pos = [PosX_init,PosY_init,PosZ_init]

					# Perform test depending on type of control
					if any(Combobox_MethodType['values'][0] in d.values() for d in List.values()): # if stage movement
						Test_Stage_Movement(List, Initial_Pos, PosZ_init, filename, List_Mot, BAUDRATE, stop_event,tabControl, measuretab)
					elif any(Combobox_MethodType['values'][1] in d.values() for d in List.values()): # if displacement (stage displacement - deflection) control
						print("Displacement control function not written yet")
					elif any(Combobox_MethodType['values'][2] in d.values() for d in List.values()): # if force control
						print("Force control function not written yet")
					
			except:
				Method_Content.set('Unable to run the test')
#-------------------------------------------------------------------------------------------------------------------------
def Test_Stage_Movement(List, Initial_Pos, PosZ_init, filename, List_Mot, BAUDRATE, stop_event,tabControl, measuretab):
	""" Function to perform a test in stage movement control
	# List: Dictionary of the method
	# Initial_Pos: Initial position of all stages when performing the test
	# PosZ_Init: Initial position of Z stage
	# filemame: Name of the method file
	# Lis_Mot: list of motors of the 3 stages
	# BAUDRATE: Baudrate of the controller
	# stop_event: thread that is started when the test is stopped before the end
	# tabControl : tab of measurements
	# measuretab : 
	"""
	global Method_Content
	global NUMVALUES
	global Mot_freq
	global RECRATE
	global testdata
	global testmetadata
	global offset_rec
	global PosRec

	# Check if stage movements in the range of motion and velocity does not exceed maximal velocity
	[minZ, maxZ, max_VelZ] = Check_Range_Motion(List,PosZ_init)
	
	if (minZ>PosminZ)&(maxZ<PosmaxZ)&(max_VelZ<VelmaxZ):

		# Connexion to the stages
		deviceX=GCSDevice(motorX["ctr"])
		deviceX.ConnectRS232(motorX["usb"], BAUDRATE)
		deviceY=GCSDevice(motorY["ctr"])
		deviceY.ConnectRS232(motorY["usb"], BAUDRATE)
		deviceZ=GCSDevice(motorZ["ctr"])
		deviceZ.ConnectRS232(motorZ["usb"], BAUDRATE)
		devices = [deviceX, deviceY, deviceZ]

		# Settings for recording stage position				
		drec = datarectools.Datarecorder(deviceZ)
		recorddata1(drec, NUMVALUES, RECRATE)
		offset_rec = 1
		testdata = []
		PosRec = []
		Current_Segment.set("test starting")

		# Manage the grid
		Grid_Point = 0 #Point in the grid	

		# Start measurements and performing the test					
		start_measuring(tabControl,measuretab)	# Force measurements + record			
		drec.arm() # Record position
		time.sleep(1) # wait for 1s so that force measurements start before the test

		Initial_Time = time.time()
		testmetadata = Method_to_List(filename, Initial_Pos, [1000,1000,1000], Initial_Time, 1000) #temporary metadata in case test is stopped

		# Read dictionary and perform successive segments
		for item, doc in List.items():
			if stop_event.is_set(): #Will stop the test after the end of the current segment
				Current_Segment.set('Test stopped')
				break
			Type = doc.get('Type')
			print("Type", Type)

			if (Type == 'Preload'):
				Stg = doc.get('Stage')
				For = doc.get('Force')
				Vel = doc.get('Velocity')
				t_hold = doc.get("Duration")
				mot = motors[np.where(List_Mot==Stg)[0][0]] # Identify the motor corresponding to the stage
				Current_Segment.set('Point {} - Performing segment: {}, Stage: {}, Velocity: {:.2f}, Hold for: {:.2f} seconds'.format(Grid_Point+1, item, Stg, Vel, t_hold))						
				device = devices[np.where(List_Mot==Stg)[0][0]]				
				Preload(device, For, t_hold)

			if (Type == "Move stage"):
				Stg = doc.get('Stage')
				print("Stage", Stg)
				Dis = doc.get('Value')
				print("Disp", Dis)
				Vel = doc.get('Velocity')
				print("Stage : ", Stg, ", Displacement : ", Dis, ", Velocity : ", Vel)
				mot = motors[np.where(List_Mot==Stg)[0][0]] # Identify the motor corresponding to the stage
				Current_Segment.set('Point {} - Performing segment: {}, Stage: {}, Displacement: {:.2f}, Velocity: {:.2f}'.format(Grid_Point+1, item, Stg, Dis, Vel))						
				device = devices[np.where(List_Mot==Stg)[0][0]]
				background(deviceRelativePosRec(device, Dis, Vel, True,drec,PosRec))

			elif (Type == "Hold"):
				t_init = time.time()
				t_current = time.time()
				t_hold = doc.get("Duration")
				Current_Segment.set('Point {} - Performing segment: {}, Hold for {:.2f} seconds'.format(Grid_Point+1, item, t_hold))
				while t_current-t_init<t_hold:
					t_current = time.time()									
					if t_hold>1:													
						try:
							Data_Pos = drec.read(numvalues=offset_reading,offset=offset_rec)			
							offset_rec = offset_rec+offset_reading
							print(offset_rec)														
							for i in (Data_Pos[1][0]):
								PosRec.append(i)
						except:
							t_current = time.time()	

			elif (Type == "Go to"):
				PosX = doc.get("Pos X") + PosX_init
				PosY = doc.get("Pos Y") + PosY_init
				FC.forcelength = FC.forcelength - doc.get("Pos Y") # update distance to force application
				Z_up = doc.get("Z up")
				Current_Segment.set('Going to point {} - Moving to position X: {:.2f} Y: {:.2f}'.format(Grid_Point+1, PosX, PosY))
				background(deviceRelativePos(deviceZ, -Z_up, Default_Vel_Z, wait_target=True)) #move up by -Z up
				#background(Move_Update_Pos(deviceRelativePos,(deviceZ, -Time = time.time()Z_up, Default_Vel_Z, True))) #move up by -Z up
				pool = mp.Pool(3)
				results = pool.map(multi_run_wrapper_Absolute,[(motorX, BAUDRATE, PosX, Default_Vel_X, False, True),(motorY, BAUDRATE, PosY, Default_Vel_Y, False, True)])
				background(deviceRelativePos(deviceZ, Z_up, Default_Vel_Z, True)) #move down by Z up
				GetCurPos_x() # Update X position
				GetCurPos_y() # Update Y position
				Grid_Point = Grid_Point+1

			Final_Time = time.time()
			GetCurPos_z()
		Current_Segment.set('Test finished')	
		for k in range(100):
			try:
				Data_Pos = drec.read(numvalues=10,offset=offset_rec)									
				for i in (Data_Pos[1][0]):
					PosRec.append(i)
				offset_rec = offset_rec+10
			except:
				break
				
		# Get the final position for the grid and update label in GUI
		Final_Pos = Get_FinalPos()
		
		# Create metadata and data
		Time = list(np.arange(0,(1/RECRATE)*len(PosRec),(1/RECRATE)))
		Disp = PosRec
		testmetadata = Method_to_List(filename, Initial_Pos, Final_Pos, Initial_Time, Final_Time)
		testdata = StageDisp_To_Dict(Time,Disp)
		stop_event.clear()
		print('Stopping test')
		stop_measuring(measuretab)
		
	else:
		if (minZ<PosminZ) or (maxZ>PosmaxZ):
			Current_Segment.set("Unable to run the test, position out of range (0 - 150mm)")
			print("Unable to run the test, position out of range (0 - 150mm)")
		if (max_VelZ>VelmaxZ):
			Current_Segment.set("Unable tu run the test, velocity exceeds the maximal velocity allowed (50mm/s)")
			print("Unable tu run the test, velocity exceeds the maximal velocity allowed (50mm/s)")
		if (max_VelZ>VelmaxZ)&((minZ<PosminZ) or (maxZ>PosmaxZ)):
			Current_Segment.set("Unable to run the test, position out of range (0 - 150mm) and velocity exceeds the maximal velocity allowed (50mm/s)")

#-------------------------------------------------------------------------------------------------------------------------
def Preload(device, Force_Target, Time_Preload, Velocity = 0.5):
	""" Preload function - the stage moves at a constant velocity until a force threshold is reached. 
	# device: stage that needs to be moved
	# Force_Target: value of the preload
	# Time_Preload: Holding time for the preload (as of nowm the stage movement is stopped, which does not garanty that the force will be holded)
	# Velocity: velocity with which thr stage is moved
	"""
	# Get initial force 
	Force_Init = sens.forcelist[-1] 
	Force = Force_Init

	# Move the stage until preload is reached
	for axis in device.axes:
		device.VEL(axis,Velocity)
		background(device.MVR(axis,20)) # the value 20 is arbitrary- the movement will actually stop when the force target is reached
	while (abs(Force-Force_Init)<Force_Target):
		Force = sens.forcelist[-1]

	# Stop stage, update current position and hold the preload
	device.STP(noraise=True)
	GetCurPos_z()
	time.sleep(Time_Preload)

#-------------------------------------------------------------------------------------------------------------------------
def Get_FinalPos():
	""" The function gets the final position of each stage and updates in the GUI 
	"""
	GetCurPos_x()
	PosX_Final = CurPos_x.get()
	GetCurPos_y()
	PosY_Final = CurPos_y.get()
	GetCurPos_z()
	PosZ_Final = CurPos_z.get()
	Final_Pos = [PosX_Final,PosY_Final,PosZ_Final]
	return Final_Pos
#-------------------------------------------------------------------------------------------------------------------------
def Stop_Test():
	""" The function creates the test data for the output file, stops force measurementsm saves data, stops the stages
	and stops the test 
	"""
	global testdata
	global testmetadata
	global PosRec
	global RECRATE

	# Create the data array for the output file (for the stages)
	Time = list(np.arange(0,(1/RECRATE)*len(PosRec),(1/RECRATE)))
	testdata = StageDisp_To_Dict(Time,PosRec)

	# Stop recordings and movements
	stop_measuring(measuretab)	
	StopStages(motors)
	stop_event.set()

#-------------------------------------------------------------------------------------------------------------------------
def deviceRelativePosRec(device, disp, vel, wait_target,drec,PosRec):
	""" This function moves the stage by a relative dispacemenet and records the position
	The way position is recorded could be improved...
	"""
	global offset_rec

	for axis in device.axes:
		# Move stage at the desired velocity
		InitialPos = device.qPOS(axis)[axis]
		print('initial position on axis {} is {:.2f}'.format(axis, InitialPos))
		target = InitialPos+disp
		print('move axis {} to {:.2f}'.format(axis, target))
		device.VEL(axis, vel)
		device.MOV(axis, target)

		# Wait until the target is reached (function to stop stage movements does not work with waitontarget)
		if wait_target:
			ret=device.qONT(axis) # Returns if target is reached
			ret = ret['1']
			while ret == False:
				try:
					# Qurey if position is reached
					ret=device.qONT(axis)[axis]
					position = device.qPOS(axis)[axis]
					# Record position data		
					try:
						Data_Pos = drec.read(numvalues=offset_reading-1,offset=offset_rec)
						offset_rec = offset_rec+offset_reading						
						for i in (Data_Pos[1][0]):
							PosRec.append(i)
						print("PosRec: ", PosRec)
					except:
						offset_rec = offset_rec
				except:
					device.STP(noraise=True) # When the stages are stopped, the current position cannot be obtained
					break		
		FinalPos = device.qPOS(axis)[axis]
		print('current position of axis {} is {:.2f}'.format(axis, FinalPos))
		print("end moving time: ", time.time())

#--------------------------------------------------------------------------------------------------------------------
def Get_Recrate(List, freq):
	"""The function Get_Recrate() calculates the frequency of recording based on the duration of the test 
	The maximal number of points that can be recorded is 1024 
	# List: dictionary containing the method
	# freq: frequency set by the user
	"""	
	global NUMVALUES

	# Calculate duration of the test (does not include the preload...)
	Duration_Test = 0
	for item, doc in List.items():
		Type = doc.get('Type')
		if (Type == "Move stage"):
			Duration_Test = Duration_Test + abs(doc.get('Value'))/doc.get('Velocity')
		elif (Type == "Hold"):
			Duration_Test = Duration_Test + doc.get("Duration")	
	Duration_Test = Duration_Test+2 # Add 2 seconds to make sure the whole test is recorded

	# Calculate the number of values necessary to cover the whole test with the desired frequency
	num_val = freq*Duration_Test

	# Decrease the frequency if the test is too long
	if num_val > NUMVALUES:
		RECRATE = int(NUMVALUES/Duration_Test)
		print("Recrate: ", RECRATE)	
	else:
		RECRATE = freq

	return RECRATE
	
#-------------------------------------------------------------------------------------------------------------------------
def Check_Range_Motion(List,PosZ_init):
	"""The function Check_Range_Motion ensures that the stage movements are in the range of motion and the velocity is lower than
	the maximal velocity of the stage 
	# List: dictionary containing the method
	# PosZ_init: initial position for the test
	"""
	# Initialise min and max values of diaplacement ond velocity
	dispZ = PosZ_init
	minZ = dispZ
	maxZ = dispZ
	max_VelZ = 0

	# REad the method file and find range of displacement and maximal velocity
	for item, doc in List.items():
		Type = doc.get('Type')
		Stg = doc.get('Stage')
		if (Type == "Move stage")&(Stg == "Z"):
			dispZ = dispZ+doc.get('Value')
			VelZ = doc.get('Velocity')
			if VelZ > max_VelZ:
				max_VelZ = VelZ
			if dispZ < minZ:
				minZ = dispZ
			elif dispZ > maxZ:
				maxZ = dispZ

	return minZ, maxZ, max_VelZ
#-------------------------------------------------------------------------------------------------------------------------
def popup_beam(beam_test,forcedist,measdist,Tare_dist):
	"""The function popup_beam() displays a pop up window indicating which beam is selected for the test. Returns yes or no
	#beam_test: selected beam for the test
	#forcedist: distance to force application
	measdist: distance to measurement
	Tare_dist: tare diatance (from sensor to beam) 
	"""
	if Tare_dist>700: # if sensor is too far from the beam, the user is warned
		message = "Selected beam: {} \n \n Distance to force application: {}mm \n Distance to measurement: {}mm \n Tare distance: {}mm \n \n Check sensor position \n \n Do you want to continue?".format(beam_test, forcedist,measdist,Tare_dist)
	else:
		message = "Selected beam: {} \n Distance to force application: {}mm \n Distance to measurement: {}mm \n \n Do you want to continue?".format(beam_test, forcedist,measdist)
	answer = msg.askyesno("selected beam", message)
	return answer

#-------------------------------------------------------------------------------------------------------------------------
def popup_clear():
	"""The function popup_clear() displays a pop up window asking the user if they want to clear the data from previous tests. Returns yes, no, or cancel 
	"""
	answer = msg.askyesno("clear data", "Data from previous measurements have not been cleared. would you like to continue?")
	return answer

#===================================================
# Functions for the fibre optic sensor
#===================================================
def switch_to_calib():
	configtab.running=False
	# self.measuretab.switchoff()
	time.sleep(1)
	calibtab.running=True 
	calibtab.weightcalib.update_distlbl()
	tabControl.tab(3,state='normal')
	tabControl.tab(2,state='disabled')
	tabControl.tab(4,state='disabled')

#-------------------------------------------------------------------------------------------------------------------------
def switch_to_config():
	calibtab.running=False
	# self.measuretab.switchoff()
	time.sleep(1)
	configtab.running = True
	tabControl.tab(2,state='normal')
	tabControl.tab(3,state='disabled')
	tabControl.tab(4,state='disabled')

#-------------------------------------------------------------------------------------------------------------------------
def switch_to_meas():
	calibtab.running=False
	configtab.running=False
	time.sleep(1)
	# self.measuretab.switchon()
	tabControl.tab(4,state='normal')
	tabControl.tab(2,state='disabled')
	tabControl.tab(3,state='disabled')

#-------------------------------------------------------------------------------------------------------------------------
def savealldata():
	""" saves data and metadata of sensor and motorstages to a folder that can be selected via the gui"""
	metadata = sens.make_metadata()
	metadata.append(' ') # makes an emptyline between the sensor and motorstages metadaata
	for i in testmetadata:
		metadata.append(i)    
	data = sens.make_data()   
	for i in range(len(testdata)):
		data[list(testdata)[i]]=list(testdata.values())[i]
	print(metadata)
	print(data)
	save.save_with_metadata(metadata,data, Output_Dir)

#-------------------------------------------------------------------------------------------------------------------------
def savealldata_temp():
	""" saves data and metadata of sensor and motorstages to a folder that can be selected via the gui"""
	metadata = sens.make_metadata()
	metadata.append(' ') # makes an emptyline between the sensor and motorstages metadaata
	for i in testmetadata:
		metadata.append(i)    
	data = sens.make_data()   
	for i in range(len(testdata)):
		data[list(testdata)[i]]=list(testdata.values())[i]
	save.save_with_metadata_temp(metadata,data, Output_Dir)

#-------------------------------------------------------------------------------------------------------------------------
def close_threads(event):
	"""closes all possibly running threads when tabs are switched"""
	configtab.advsetframe.running = False
	calibtab.updatetare = False
	calibtab.weightcalib.running = False
	calibtab.emodulcalib.updatetare = False

#===========================================================================================================================
# Create GUI, add title, and add tabs
#===========================================================================================================================
root = tk.Tk()
root.title("Maria is the best")

# The first tab is to control the stage movements and run a succession of segments
# The second tab is to define a succession of segments
# The third tab is for the sensor configuration
# The fourth tab is for the sensor calibration
# the fifth tab is for the sensors measurements

#initialise the notebook and the tabs
tabControl = ttk.Notebook(root)
tab1 = tk.Frame(tabControl)
tabControl.add(tab1, text = 'Test')
tab2 = tk.Frame(tabControl)
tabControl.add(tab2, text = 'Method Z measurement')

configtab = con.ConfigTab(tabControl)
tabControl.add(configtab, text='Configuration')
calibtab = cal.CalibWindow(tabControl)
tabControl.add(calibtab, text='Calibration')
#tabControl.tab(3,state='disabled')
measuretab = meas.Measure(tabControl)
tabControl.add(measuretab, text='Measurements')
#tabControl.tab(4,state='disabled')

measuretab.savebtn.configure(command = savealldata) # change the save function in measuretab, so that it also saves data from the motorstages

tabControl.bind('<<NotebookTabChanged>>', close_threads)# assigns a function to changing tabs
tabControl.pack(expand=1,fill="both")

#===========================================================================================================================
# Variables for holding current position data
#===========================================================================================================================
CurPos_x = tk.DoubleVar()
CurPos_y = tk.DoubleVar()
CurPos_z = tk.DoubleVar()

#===========================================================================================================================
# Frame for connexion and initialisation of the stages
#===========================================================================================================================
"""In this frame, the stages can be connected to the correct USB port and be homed to their initial position"""

# Create the main container
frame_init = ttk.LabelFrame(tab1, text = 'Stage initialisation', borderwidth=2, relief='ridge')

# Lay out the main container
frame_init.grid(column=0, row=0, sticky="nsew")

# Allow middle cell of grid to grow when window is resized
frame_init.columnconfigure(1, weight=1)
frame_init.rowconfigure(1, weight=1)

#==========================================
# Declare variables
#==========================================
#Variables holding the status of the stages
Connect_Status_X = tk.StringVar()
Connect_Status_Y = tk.StringVar()
Connect_Status_Z = tk.StringVar()

#==========================================
# Create label, entry, and button widgets
#==========================================
button_Init_X = tk.Button(frame_init, text="Stage X", command=lambda: background(InitStage(motorX, BAUDRATE, Initial_Pos_X, Default_Vel_X)))
button_Init_Y = tk.Button(frame_init, text="Stage Y", command=lambda: background(InitStage(motorY, BAUDRATE, Initial_Pos_Y, Default_Vel_Y)))
button_Init_Z = tk.Button(frame_init, text="Stage Z", command=lambda: background(InitStage(motorZ, BAUDRATE, Initial_Pos_Z, Default_Vel_Z)))
button_Init_All = tk.Button(frame_init, text="Initialisation", command=lambda: [background(InitStage(motorX, BAUDRATE, Initial_Pos_X, Default_Vel_X)), background(InitStage(motorY, BAUDRATE, Initial_Pos_Y, Default_Vel_Y)), background(InitStage(motorZ, BAUDRATE, Initial_Pos_Z, Default_Vel_Z))])

Button_Connect = tk.Button(frame_init, text="Connexion", command=lambda: background(ConnectStages()))

Label_Connect_X = tk.Label(frame_init, text=Connect_Status_X.get())
Label_Connect_Y = tk.Label(frame_init, text=Connect_Status_Y.get())
Label_Connect_Z = tk.Label(frame_init, text=Connect_Status_Z.get())

#=====================================
# Lay out the widgets
#=====================================
button_Init_X.grid(row=0, column=0, padx=5, pady=5)
button_Init_Y.grid(row=0, column=1, padx=5, pady=5)
button_Init_Z.grid(row=0, column=2, padx=5, pady=5)

Label_Connect_X.grid(row=1, column=0, padx=5, pady=5)
Label_Connect_Y.grid(row=1, column=1, padx=5, pady=5)
Label_Connect_Z.grid(row=1, column=2, padx=5, pady=5)

Button_Connect.grid(row=0, column=3, padx=5, pady=5)
button_Init_All.grid(row=1, column=3, padx=5, pady=5)

#=====================================
# Stages connexion
#=====================================

ConnectStages()

#===========================================================================================================================
# Frame for stop and exit buttons
#===========================================================================================================================
# The button "STOP THE STAGES" stops all stages moving
# The button "STOP AND EXIT"  stops all stages moving and exit the programme

# Create the main container
frame_Stop = ttk.LabelFrame(tab1, text = 'Stop and exit', borderwidth=2, relief='ridge')

# Lay out the main container
frame_Stop.grid(column=1, row=0, sticky="nsew")

# Allow middle cell of grid to grow when window is resized
frame_Stop.columnconfigure(1, weight=1)
frame_Stop.rowconfigure(1, weight=1)

#==========================================
# Create label, entry, and button widgets
#==========================================
button_Stop = tk.Button(frame_Stop, text="STOP THE STAGES", command=lambda: [StopStages1(motorX), StopStages1(motorY), StopStages1(motorZ)], fg='red')
button_Exit = tk.Button(frame_Stop, text="STOP AND EXIT", command=lambda: exit(), fg='red')

#=====================================
# Lay out the widgets
#=====================================
button_Stop.grid(row=0, column=0, padx=5, pady=5)
button_Exit.grid(row=0, column=1, padx=5, pady=5)

#===========================================================================================================================
# Frame for stage movement
#===========================================================================================================================
"""In this frame, it is possible to:
- display the current position of the stages
- move a stage to its minimum/maximum position
- move a stage to an absolute position defined by the user
- move a stage to a relative position defined by the user
- specify the velocity for all these movements"""

# Create the main container
frame = ttk.LabelFrame(tab1, text = 'Stage movement', borderwidth=2, relief='ridge')

# Lay out the main container
frame.grid(column=0, row=1, columnspan=2, sticky="nsew")

# Allow middle cell of grid to grow when window is resized
frame.columnconfigure(1, weight=1)
frame.rowconfigure(1, weight=1)

#=====================================
# Declare variables
#=====================================
# Variables for holding absolute position data
Pos_x = tk.DoubleVar()
Pos_y = tk.DoubleVar()
Pos_z = tk.DoubleVar()

# Variables for holding relative displacement data
Dis_x = tk.DoubleVar()
Dis_y = tk.DoubleVar()
Dis_z = tk.DoubleVar()

# Variables for holding velocity data
Vel_x = tk.DoubleVar()
Vel_y = tk.DoubleVar()
Vel_z = tk.DoubleVar()

#==========================================
# Create label, entry, and button widgets
#==========================================
Vel_Disp = tk.Label(frame, text="Velocity (mm/s)")
Cur_Pos = tk.Button(frame, text="Current position (mm)", command=lambda: [GetCurPos_x(),GetCurPos_y(),GetCurPos_z()])
Abs_Pos = tk.Label(frame, text="Absolute position (mm)")
Rel_Disp = tk.Label(frame, text="Relative displacement (mm)")

#------------------------------------------------------------------------------------------------------------------
label_Stage_X = tk.Label(frame, text="Stage X")
entry_pos_X = tk.Entry(frame, width=7, textvariable=Pos_x)
entry_dis_X = tk.Entry(frame, width=7, textvariable=Dis_x)
entry_vel_X = tk.Entry(frame, width=7, textvariable=Vel_x)
label_Range_Vel_X = tk.Label(frame,text="(0-10)") # Displays the range of velocity that is allowed
Label_Range_Pos_X = tk.Label(frame,text="(0.1-25)") # Displays the range of motion that is allowed
Vel_x.set(Default_Vel_X) # Set a default value (ideally, it would be the maximal velocity of the stage)
button_Min_X = tk.Button(frame, text="Min", command=lambda: background(lambda: Move_Update_Pos(deviceMoveMinPos,(motorX, BAUDRATE, Vel_x.get(),True)))) 
button_Max_X = tk.Button(frame, text="Max", command=lambda: background(lambda: Move_Update_Pos(deviceMoveMaxPos,(motorX, BAUDRATE, Vel_x.get(),True))))
button_Pos_X = tk.Button(frame, text="Go", command=lambda: background(lambda: Move_Update_Pos(deviceMoveAbsolutePos,(motorX, BAUDRATE, Pos_x.get(), Vel_x.get(), False, True))))
button_dis_X = tk.Button(frame, text="Go", command=lambda: background(lambda: Move_Update_Pos(deviceMoveRelativePos,(motorX, BAUDRATE, Dis_x.get(), Vel_x.get(), True))))
label_CurPos_X = tk.Label(frame, textvariable=CurPos_x)

#------------------------------------------------------------------------------------------------------------------
label_Stage_Y = tk.Label(frame, text="Stage Y")
entry_pos_Y = tk.Entry(frame, width=7, textvariable=Pos_y)
entry_dis_Y = tk.Entry(frame, width=7, textvariable=Dis_y)
entry_vel_Y = tk.Entry(frame, width=7, textvariable=Vel_y)
label_Range_Vel_Y = tk.Label(frame,text="(0-1)") # Displays the range of velocity that is allowed
Label_Range_Pos_Y = tk.Label(frame,text="(0.1-90)") # Displays the range of motion that is allowed
Vel_y.set(Default_Vel_Y) # Set a default value (ideally, it would be the maximal velocity of the stage)
button_Min_Y = tk.Button(frame, text="Min", command=lambda: background(lambda: Move_Update_Pos(deviceMoveMinPos,(motorY, BAUDRATE, Vel_y.get(),True)))) 
button_Max_Y = tk.Button(frame, text="Max", command=lambda: background(lambda: Move_Update_Pos(deviceMoveMaxPos,(motorY, BAUDRATE, Vel_y.get(),True))))
button_Pos_Y = tk.Button(frame, text="Go", command=lambda: background(lambda: Move_Update_Pos(deviceMoveAbsolutePos,(motorY, BAUDRATE, Pos_y.get(), Vel_y.get(), False, True))))
button_dis_Y = tk.Button(frame, text="Go", command=lambda: background(lambda: Move_Update_Pos(deviceMoveRelativePos,(motorY, BAUDRATE, Dis_y.get(), Vel_y.get(), True))))
label_CurPos_Y = tk.Label(frame, textvariable=CurPos_y)

#------------------------------------------------------------------------------------------------------------------
label_Stage_Z = tk.Label(frame, text="Stage Z")
entry_pos_Z = tk.Entry(frame, width=7, textvariable=Pos_z)
entry_dis_Z = tk.Entry(frame, width=7, textvariable=Dis_z)
entry_vel_Z = tk.Entry(frame, width=7, textvariable=Vel_z)
label_Range_Vel_Z = tk.Label(frame,text="(0-50)") # Displays the range of velocity that is allowed
Label_Range_Pos_Z = tk.Label(frame,text="(0.1-150)") # Displays the range of motion that is allowed
Vel_z.set(Default_Vel_Z) # Set a default value (ideally, it would be the maximal velocity of the stage)
button_Min_Z = tk.Button(frame, text="Min", command=lambda: background(lambda: Move_Update_Pos(deviceMoveMinPos,(motorZ, BAUDRATE, Vel_z.get(),True)))) 
button_Max_Z = tk.Button(frame, text="Max", command=lambda: background(lambda: Move_Update_Pos(deviceMoveMaxPos,(motorZ, BAUDRATE, Vel_z.get(),True))))
button_Pos_Z = tk.Button(frame, text="Go", command=lambda: background(lambda: Move_Update_Pos(deviceMoveAbsolutePos,(motorZ, BAUDRATE, Pos_z.get(), Vel_z.get(), False, True))))
button_dis_Z = tk.Button(frame, text="Go", command=lambda: background(lambda: Move_Update_Pos(deviceMoveRelativePos,(motorZ, BAUDRATE, Dis_z.get(), Vel_z.get(), True))))
label_CurPos_Z = tk.Label(frame, textvariable=CurPos_z)

#=====================================
# Lay out the widgets
#=====================================
Vel_Disp.grid(row=0, column=1, padx=5, pady=5)
Cur_Pos.grid(row=0, column=3, padx=5, pady=5)
Abs_Pos.grid(row=0, column=6, padx=5, pady=5)
Rel_Disp.grid(row=0, column=9, padx=5, pady=5)

#---------------------------------------------------
label_Stage_X.grid(row=1, column=0, padx=5, pady=5)
entry_vel_X.grid(row=1, column=1, padx=5, pady=5)
label_Range_Vel_X.grid(row=1, column=2, padx=5, pady=5)
label_CurPos_X.grid(row=1, column=3, padx=5, pady=5)
button_Min_X.grid(row=1, column=4, padx=5, pady=5)
button_Max_X.grid(row=1, column=5, padx=5, pady=5)
entry_pos_X.grid(row=1, column=6, padx=5, pady=5)
Label_Range_Pos_X.grid(row=1, column=7,padx=5, pady=5)
button_Pos_X.grid(row=1, column=8, padx=5, pady=5)
entry_dis_X.grid(row=1, column=9, padx=5, pady=5)
button_dis_X.grid(row=1, column=10, padx=5, pady=5)

#---------------------------------------------------
label_Stage_Y.grid(row=2, column=0, padx=5, pady=5)
entry_vel_Y.grid(row=2, column=1, padx=5, pady=5)
label_Range_Vel_Y.grid(row=2, column=2, padx=5, pady=5)
label_CurPos_Y.grid(row=2, column=3, padx=5, pady=5)
button_Min_Y.grid(row=2, column=4, padx=5, pady=5)
button_Max_Y.grid(row=2, column=5, padx=5, pady=5)
entry_pos_Y.grid(row=2, column=6, padx=5, pady=5)
Label_Range_Pos_Y.grid(row=2, column=7,padx=5, pady=5)
button_Pos_Y.grid(row=2, column=8, padx=5, pady=5)
entry_dis_Y.grid(row=2, column=9, padx=5, pady=5)
button_dis_Y.grid(row=2, column=10, padx=5, pady=5)

#---------------------------------------------------
label_Stage_Z.grid(row=3, column=0, padx=5, pady=5)
entry_vel_Z.grid(row=3, column=1, padx=5, pady=5)
label_Range_Vel_Z.grid(row=3, column=2, padx=5, pady=5)
label_CurPos_Z.grid(row=3, column=3, padx=5, pady=5)
button_Min_Z.grid(row=3, column=4, padx=5, pady=5)
button_Max_Z.grid(row=3, column=5, padx=5, pady=5)
entry_pos_Z.grid(row=3, column=6, padx=5, pady=5)
Label_Range_Pos_Z.grid(row=3, column=7,padx=5, pady=5)
button_Pos_Z.grid(row=3, column=8, padx=5, pady=5)
entry_dis_Z.grid(row=3, column=9, padx=5, pady=5)
button_dis_Z.grid(row=3, column=10, padx=5, pady=5)

#=====================================
# Update current position
#=====================================
# Schedule the GetCurPos() functions to be called periodically to update the value of current position
# root.after(2000, GetCurPos_x)
# root.after(2000, GetCurPos_y)
# root.after(2000, GetCurPos_z)

#===========================================================================================================================
# Frame for running test from method
#===========================================================================================================================
"""In this frame, it is possible to
- Open a file containing a succession of segments (loading/Hold/Unloading)
	- the content of the method (list of steps) will be displayed (linked to function Open_Method)
 	- a graphical representation of the method will be displayed (linked to function Open_Method)
- Run the test based on the successive segments
- Display in a new frame the segment being performed"""

# Create the main container
frame_test = ttk.LabelFrame(tab1, text = 'Test', borderwidth=2, relief='ridge')

# Lay out the main container
frame_test.grid(column=0, row=2, columnspan=2, sticky="nsew")

# Allow middle cell of grid to grow when window is resized
frame_test.columnconfigure(1, weight=1)
frame_test.rowconfigure(1, weight=1)

#=====================================
# Declare variables
#=====================================
# Filename_method: name of the method file
Filename_method = tk.StringVar()
Filename_method.set('.yaml')

# Method content: content of the method file to be displayed
Method_Content = tk.StringVar()
Method_Content.set('')
Current_Segment = tk.StringVar() # Current_Segment: segment being performed

# Freauency of measurements
Mot_freq = tk.IntVar()
Mot_freq.set(20)
RECRATE = Mot_freq.get()

#==========================================
# Create label, entry, and button widgets
#==========================================
label_Method = tk.Label(frame_test, text="Test method")
entry_Method = tk.Entry(frame_test, width=40, textvariable=Filename_method)
button_OpenMethod = tk.Button(frame_test, text="Open file", command=lambda: OpenFile())
button_run_met = tk.Button(frame_test, text="Run test", command=lambda: background(lambda: Read_method(Filename_method.get(), List_Mot, BAUDRATE, stop_event,tabControl, measuretab)))
button_stop_met = tk.Button(frame_test, text="STOP TEST", command=lambda: Stop_Test())
label_freq = tk.Label(frame_test, text="Frequency recording (Hz)")
entry_freq = tk.Entry(frame_test, textvariable=Mot_freq)

#=====================================
# Lay out the widgets
#=====================================
label_Method.grid(row=0, column=0, padx=5, pady=5)
entry_Method.grid(row=0, column=1, padx=5, pady=5)
button_OpenMethod.grid(row=0, column=2, padx=5, pady=5)
button_run_met.grid(row=0, column=3, padx=5, pady=5)
button_stop_met.grid(row=0, column=4, padx=5, pady=5)
label_freq.grid(row=1, column=0, padx=5, pady=5)
entry_freq.grid(row=1, column=1, padx=5, pady=5)

#===========================================================================================================================
# Frames for creating and saving a method
#===========================================================================================================================
"""In these frames, it is possible to:
- Import an existing method
- Define a new method containing a number of segments defined by the user
- Add a segment
- Remove a segment
- For all the above, each parameter can be modified by the user
- Save the method in a YAML file with a name defined by the user"""

frame_method = ttk.LabelFrame(tab2, text = 'Method definition', borderwidth=2, relief='ridge')
frame_method_def = ttk.LabelFrame(tab2, text = 'Segments', borderwidth=2, relief='ridge')

# Lay out the main container
frame_method.grid(column=0, row=0, columnspan=2, sticky="nsew")
frame_method_def.grid(column=0, row=1, columnspan=2, sticky="nsew")

# Allow middle cell of grid to grow when window is resized
frame_method.columnconfigure(1, weight=1)
frame_method.rowconfigure(1, weight=1)
frame_method_def.columnconfigure(1, weight=1)
frame_method_def.rowconfigure(1, weight=1)

#=====================================
# Declare variables
#=====================================
Name_method = []
Number_Steps = tk.IntVar()
Number_Steps.set(0)

# Widgets used to create methods
Combobox_Type = [] #Type can be preload, move stage, or hold
Combobox_Stage = [] # Stage X, Y, or Z
entry_Value = [] # Can be value of displacement, deflection, or force depending on the method
entry_Velocity = [] # Used for preload
entry_Time = [] # Duration of segment or preload

# List containing the widgets variables
List_Types = [] # Type of segment
List_Stages = [] # Stage to be moved
List_Value = [] # Target value for movement (force or displacement)
List_Vel = [] # Velocity for the movement
List_Time = [] # Duration of the segment or duration of the hold for the preload

# Values of the combobox/label for the type of segment/method
values_LabelValue = np.array(['Displacement (mm)','Displacement (um)','Force (mN)'])
values_Combobox_Type = ('','Move stage','Hold','Preload')

#==========================================
# Create and lay out widgets
#==========================================
label_MethodType = tk.Label(frame_method, text="Method type")
label_MethodType.grid(row=0, column=0, padx=5, pady=5)
Label_Step_Number = tk.Label(frame_method, text="Number of segments")
Label_Step_Number.grid(row=1, column=0, padx=5, pady=5)
Entry_StepNumber = tk.Entry(frame_method, textvariable = Number_Steps)
Entry_StepNumber.grid(row=1, column=1, padx=5, pady=5)

Combobox_MethodType = ttk.Combobox(frame_method)
Combobox_MethodType['values'] = ('Stage movement','Displacement control','Force control')
Combobox_MethodType.current(0)
Combobox_MethodType.grid(row=0, column=1, padx=5, pady=5)

Button_ImportMethod = tk.Button(frame_method,text="Import method",command=lambda: Import_Method())
Button_ImportMethod.grid(row=1,column=2, padx=5, pady=5)
Button_DefineMethod = tk.Button(frame_method,text="New method",command=lambda: Start_Method(Number_Steps.get()))
Button_DefineMethod.grid(row=1,column=3, padx=5, pady=5)
Button_AddStep = tk.Button(frame_method,text="Add segment",command=lambda: Add_Step())
Button_AddStep.grid(row=1,column=4, padx=5, pady=5)
Button_RemStep = tk.Button(frame_method,text="Remove segment",command=lambda: Remove_Step())
Button_RemStep.grid(row=1,column=5, padx=5, pady=5)
button_Save_Method=tk.Button(frame_method,text="Save method",command=SaveMethod)
button_Save_Method.grid(row=1,column=6, padx=5, pady=5)

#===========================================================================================================================
# Frame for representation method segments
#===========================================================================================================================
"""In this frame, a graphical representation of the segments is plotted when the enter key is pressed (for Z stage)"""

frame_method_plot = ttk.LabelFrame(tab2, text = 'Representation', borderwidth=2, relief='ridge')
frame_method_plot.grid(column=0, row=2, columnspan=2, sticky="nsew")

frame_method_plot.columnconfigure(1, weight=1)
frame_method_plot.rowconfigure(1, weight=1)

# Each array is initially empty
X_time = []
Y_disp = []

fig = Figure(figsize=(10,3))
ax = fig.add_subplot(111)
fig.subplots_adjust(top=0.9,bottom=0.20,left=0.10,right=0.9)

canvas = FigureCanvasTkAgg(fig, master=frame_method_plot)
toolbar = NavigationToolbar2Tk(canvas, frame_method_plot)

Plot_Graph(X_time, Y_disp, ax, canvas)

#===========================================================================================================================
# Frames for grid definition
#===========================================================================================================================
"""In these frames, a grid of measurements can be defined and represented in a plot
In each point of the grid, the segments can be modified (and segments can be added/removed)"""

# Lay out the main container
frame_method_grid = ttk.LabelFrame(tab2, text = 'Grid', borderwidth=2, relief='ridge')
frame_method_grid.grid(column=0, row=3, sticky="nsew")

frame_plot_grid = ttk.LabelFrame(tab2, borderwidth=2, relief='ridge')
frame_plot_grid.grid(column=1, row=3, sticky="nsew")

# Allow middle cell of grid to grow when window is resized
frame_method_grid.columnconfigure(1, weight=1)
frame_method_grid.rowconfigure(1, weight=1)

frame_plot_grid.columnconfigure(1, weight=1)
frame_plot_grid.rowconfigure(1, weight=1)

#=====================================
# Declare variables
#=====================================
Grid_Number_X = tk.IntVar() # Contains the number of points along X axis
Grid_Number_X.set(1) # Initial value is set to 1
Grid_dX = tk.DoubleVar() # Contains the spacing between each point along X axis
Grid_Number_Y = tk.IntVar() # Contains the number of points along Y axis
Grid_Number_Y.set(1) # Initial value is set to 1
Grid_dY = tk.DoubleVar() # Contains the spacing between each point along Y axis

Dict_Method = [] #Contains method with default parameters
Dict_Grid = [] #Contains method with updated parameters for each segment
Dict_Final = {} #Final dictionary for the grid

Cur_Point = tk.IntVar() # Values of the current point of the grid that is displayed
Cur_Point.set(1)

Z_up = tk.DoubleVar() # Contains Z displacement between each measurement (positive value)
Z_up.set(10)

#==========================================
# Create widgets
#==========================================
Label_dX = tk.Label(frame_method_grid, text="dX (mm)")
Entry_dX = tk.Entry(frame_method_grid, textvariable = Grid_dX)
Entry_dX.bind("<Return>", Get_Grid)
Label_X_Number = tk.Label(frame_method_grid, text="# X")
Entry_X_Number = tk.Entry(frame_method_grid, textvariable = Grid_Number_X)
Entry_X_Number.bind("<Return>", Get_Grid)
Label_dY = tk.Label(frame_method_grid, text="dY (mm)")
Entry_dY = tk.Entry(frame_method_grid, textvariable = Grid_dY)
Entry_dY.bind("<Return>", Get_Grid)
Label_Y_Number = tk.Label(frame_method_grid, text="# Y")
Entry_Y_Number = tk.Entry(frame_method_grid, textvariable = Grid_Number_Y)
Entry_Y_Number.bind("<Return>", Get_Grid)

Label_Z_up = tk.Label(frame_method_grid, text = "Z up (mm)")
Entry_Z_up = tk.Entry(frame_method_grid, textvariable = Z_up)

Label_Cur_Point = tk.Label(frame_method_grid, text=Cur_Point.get())
Button_Prev_Point = tk.Button(frame_method_grid, text="Prev.", command = lambda: Show_Prev_Point())
Button_Next_Point = tk.Button(frame_method_grid, text="Next", command = lambda: Show_Next_Point())

Button_Create_Grid = tk.Button(frame_method_grid,text="Create grid", command = lambda: SetMethod())
Button_Save_Grid = tk.Button(frame_method_grid,text="Save grid", command = lambda: SaveGrid())

#==========================================
# Lay out widgets
#==========================================
Label_X_Number.grid(row=0, column=0, padx=5, pady=5)
Entry_X_Number.grid(row=0, column=1, padx=5, pady=5)
Label_dX.grid(row=0, column=2, padx=5, pady=5)
Entry_dX.grid(row=0, column=3, padx=5, pady=5)
Label_Y_Number.grid(row=1, column=0, padx=5, pady=5)
Entry_Y_Number.grid(row=1, column=1, padx=5, pady=5)
Label_dY.grid(row=1, column=2, padx=5, pady=5)
Entry_dY.grid(row=1, column=3, padx=5, pady=5)

Label_Z_up.grid(row=2, column=0, padx=5, pady=5)
Entry_Z_up.grid(row=2, column=1, padx=5, pady=5)

Label_Cur_Point.grid(row=3,column=1, padx=5, pady=5)
Button_Prev_Point.grid(row=3,column=0, padx=5, pady=5)
Button_Next_Point.grid(row=3,column=2, padx=5, pady=5)

Button_Create_Grid.grid(row=4,column=1, padx=5, pady=5)
Button_Save_Grid.grid(row=4,column=2, padx=5, pady=5)

#==========================================
# Create the plot of the grid
#==========================================
# Each array contains the first location
X_points = [0]
Y_points = [0]

fig_grid = Figure(figsize=(5,3))
ax_grid = fig_grid.add_subplot(111)
fig_grid.subplots_adjust(top=0.9,bottom=0.20,left=0.2,right=0.9)

canvas_grid = FigureCanvasTkAgg(fig_grid, master=frame_plot_grid)

Plot_Grid(X_points, Y_points, ax_grid, canvas_grid)

#===========================================================================================================================
# Start GUI
#===========================================================================================================================
root.mainloop()