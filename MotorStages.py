#========================================
# Imports
#========================================

from __future__ import print_function

try:
    from matplotlib import pyplot
except ImportError:
    pyplot = None

from pipython import GCSDevice, pitools, datarectools
import multiprocessing as mp
import collections
from multiprocessing import Process
import threading
from threading import Thread
import time
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import csv

import os.path

"""
List of functions used in Main.py 
Test functions:
	deviceInit, deviceRangeTest, deviceTest
Initialisation function:
	deviceSettings
Functions to move the stages:
	deviceMoveMinPos, deviceMoveMaxPos, deviceAbsolutePos, deviceMoveAbsolutePos, deviceRelativePos, deviceMoveRelativePos
Function to stop the stages:
	StopStages
Function to run task in the background:
	background
Functions for multiprocessing:
	multi_run_wrapper_Absolute, runInParallel
Functions to record data:
	recorddata, processdata
"""

#========================================
# Test functions
#========================================

def deviceInit(active):
	""" Takes an active stage as an input, initiates it, moves to position 0.0 and returns
	the min and max movement range 
	active: motor
	"""
	# Connection
	print ('Initialisation')
	device=GCSDevice(active["ctr"])
	device.ConnectRS232(active["usb"], BAUDRATE)
	print (device.qIDN())
	axis=device.axes
	pitools.startup(device, stages=active["stg"], refmodes=active["ref"])

	# Parameters query
	rangemin = device.qTMN()
	rangemax = device.qTMX()
	#velmax = device.qVLS() # This velocity query times out, not clear why.
	velmax=0 # Just give it an aribtrary value for now

	# Home position
	device.MOV(axis, 1.0) # Move to 1.00 
	ret=device.qONT(axis)
	ret = ret['1']
	while ret == False:
		try:
			ret=device.qONT(axis)[axis]
			position = device.qPOS(axis)[axis]
		except:
			device.STP(noraise=True)
			break
	#pitools.waitontarget(device, axes=axis)
	curpos = device.qPOS()
	return device, axis, rangemin, rangemax, curpos, velmax

#--------------------------------------------------------------------------------------------------------
def deviceRangeTest(device, axes, rangemin, rangemax, curpos, velmax):
	""" Moves the stages from the minimum to the maximum range. 
	# device: device corresponding to the stage
	# axes: axis of the stage
	# rangemin: min position
	# rangemax: max position
	# curpos: current position
	# velmax: max velocity of the stage
	"""
	for axis in device.axes: # There only is one axis here
		for target in (rangemin[axis], rangemax[axis], curpos): # Go from min, to max, to current,
			print('move axis {} to {:.2f}'.format(axis, target))
			device.MOV(axis, target)
			pitools.waitontarget(device, axes=axis)
			position = device.qPOS(axis)[axis]
			print('current position of axis {} is {:.2f}'.format(axis, position))
	device.CloseConnection()

#--------------------------------------------------------------------------------------------------------
def deviceTest(active):
	""" Packs together the initialisation and movement function for multi-processing purposes 
	# active: motor
	"""	
	device, axis, rangemin, rangemax, curpos, velmax = deviceInit(active)
	deviceRangeTest(device, axis, rangemin, rangemax, curpos, velmax)

#========================================
# Initialisation function
#========================================

def deviceSettings(active, BAUDRATE, init = False):
	""" Takes an active stage as an input, initiates it, and returns device, axis, rangemin, and rangemax 
	# active: motor
	# BAUDRATE: baudrate of the controller
	# init: boolean, True if stage needs to be initialised, False otherwise
	"""
    # Connection
	print ('Initialisation')
	device=GCSDevice(active["ctr"])
	device.ConnectRS232(active["usb"], BAUDRATE)
	# Initialise stage
	axis=device.axes
	if init:
		pitools.startup(device, stages=active["stg"], refmodes=active["ref"])
	rangemin = device.qTMN()
	rangemax = device.qTMX()
	#velmax = device.qVLS() # This velocity query times out, not clear why.
	velmax=0 # Just give it an aribtrary value for now
	return device, axis, rangemin, rangemax

#========================================
# Functions to move the stages
#========================================

def deviceMoveMinPos(active, BAUDRATE, vel=10, wait_target=False):
	""" Moves the stage to min position
	# active: motor
	# BAUDRATE: Baudrate of the controller
	# vel: velocity for the movement
	# wait_target: boolean, True if wait to reach the target before doing something else, False otherwise
	"""
	# Connection
	device=GCSDevice(active["ctr"])
	device.ConnectRS232(active["usb"], BAUDRATE)
	# Move stage
	for axis in device.axes:
		# Parameters query
		rangemin = device.qTMN()
		device.VEL(axis, vel)
		#device.MOV(axis, rangemin[axis]) # Move to min pos
		device.MOV(axis, 1.0) # Move to min posm set at 1.0 to avoid 0
		if wait_target:
			ret=device.qONT(axis) # Query if taget is reached
			ret = ret['1']
			while ret == False:
				try:
					ret=device.qONT(axis)[axis]
					position = device.qPOS(axis)[axis]
				except:
					device.STP(noraise=True)
					break

#--------------------------------------------------------------------------------------------------------
def deviceMoveMaxPos(active, BAUDRATE, vel=10, wait_target=False):
	""" Moves the stage to max position
	# active: motor
	# BAUDRATE: Baudrate of the controller
	# vel: velocity for the movement
	# wait_target: boolean, True if wait to reach the target before doing something else, False otherwise
	"""
	# Connection
	device=GCSDevice(active["ctr"])
	device.ConnectRS232(active["usb"], BAUDRATE)
	# Move stage
	for axis in device.axes:
		# Parameters query
		rangemax = device.qTMX()
		# Max position
		device.VEL(axis, vel)
		device.MOV(axis, rangemax[axis]) # Move to max pos
		if wait_target:
			ret=device.qONT(axis) # Query if target is reached
			ret = ret['1']
			while ret == False:
				try:
					ret=device.qONT(axis)[axis]
					position = device.qPOS(axis)[axis]
				except:
					device.STP(noraise=True)
					break

#--------------------------------------------------------------------------------------------------------   
def deviceAbsolutePos(device, target, vel, wait_target):
	""" Moves the stage to absolute position target with velocity vel
	# device: device of the stage
	# target: target position to reach
	# vel: velocity for the movement
	# wait_target: boolean, True if wait to reach the target before doing something else, False otherwise
	"""
	for axis in device.axes: # There only is one axis here
		print('move axis {} to {:.2f}'.format(axis, target))
		device.VEL(axis, vel)
		rangemin = device.qTMN()
		rangemax = device.qTMX()
		time_init = time.time()
		print(time_init)
		if (target>rangemin[axis] and target<rangemax[axis]):
			device.MOV(axis, target)
			if wait_target:
				ret=device.qONT(axis) # Query if taget is reached
				ret = ret['1']
				while ret == False:
					try:
						ret=device.qONT(axis)[axis]
						position = device.qPOS(axis)[axis]
					except:
						device.STP(noraise=True)
						break
			position = device.qPOS(axis)[axis]
			print('current position of axis {} is {:.2f}'.format(axis, position))			
		else:
			print('Position out of limits')

#--------------------------------------------------------------------------------------------------------        
def deviceMoveAbsolutePos(active, BAUDRATE, target, vel=4.0, init = False, wait_target=False):
	""" Moves the stage to absolute position target with velocity vel
	# active: motor
	# BAUDRATE: Baudrate of the controller
	# target: target position to reach
	# vel: velocity for the movement
	# init: boolean, True if stage needs to be initialised, False otherwise 
	# wait_target: boolean, True if wait to reach the target before doing something else, False otherwise
	"""
	device, axis, rangemin, rangemax = deviceSettings(active, BAUDRATE, init)
	deviceAbsolutePos(device, target, vel, wait_target)

#--------------------------------------------------------------------------------------------------------    
# Moves the stage to relative position disp with velocity vel
def deviceRelativePos(device, disp, vel, wait_target):
	""" Moves the stage to relative position disp with velocity vel
	# device: device of the stage
	# disp: displacement reuested for the stage
	# vel: velocity for the movement
	# wait_target: boolean, True if wait to reach the target before doing something else, False otherwise
	"""
	for axis in device.axes:
		print(time_init)
		InitialPos = device.qPOS(axis)[axis]
		print('initial position on axis {} is {:.2f}'.format(axis, InitialPos))
		target = InitialPos+disp
		rangemin = device.qTMN()
		rangemax = device.qTMX()
		# Make sure movement is within the range 
		if (target>rangemin[axis] and target<rangemax[axis]):
			print('move axis {} to {:.2f}'.format(axis, target))
			device.SVO(axis,True)
			device.VEL(axis, vel)
			device.STE(axis, disp)
			# Wait on target
			if wait_target:
				ret=device.qONT(axis) # Query if taget is reached
				ret = ret['1']
				while ret == False:
					try:
						ret=device.qONT(axis)[axis]
						position = device.qPOS(axis)[axis]
					except:
						device.STP(noraise=True)
						break
			print("stop moving time: ",time.time())
			FinalPos = device.qPOS(axis)[axis]
			print('current position of axis {} is {:.2f}'.format(axis, FinalPos))
			time_init = time.time()
		else:
			print('Position out of limits')

#--------------------------------------------------------------------------------------------------------        
def deviceMoveRelativePos(active, BAUDRATE, disp, vel=4.0, wait_target=False):
	""" Moves the stage to relative position target with velocity vel
	# active: motor
	# BAUDRATE: Baudrate of the controller
	# disp: displacement requested for the stage
	# vel: velocity for the movement
	# wait_target: boolean, True if wait to reach the target before doing something else, False otherwise
	"""
	device, axis, rangemin, rangemax = deviceSettings(active, BAUDRATE)
	deviceRelativePos(device, disp, vel, wait_target)   

#=====================================
# Function to stop the stages
#=====================================
def StopStages1(active, BAUDRATE=38400):
	""" Stops one stage
	active: motor of the stage to stop
	BAUDRATE: Baudrate of the controller
	"""
	device=GCSDevice(active["ctr"])
	device.ConnectRS232(active["usb"], BAUDRATE)
	device.STP(noraise=True) #No raise=False will result in an error after the stages are stopped

#--------------------------------------------------------------------------------------------------------
def StopStages(active, BAUDRATE=38400):
	""" Stops a list of stages
	active: list of motors of the stages to stop
	BAUDRATE: Baudrate of the controller
	"""
	mppool = mp.Pool(processes=3)
	results = [mppool.map(StopStages1, active)]

#========================================
# Function to run task in the background
#========================================

def background(func):
	"""  allows the function 'func' to be run in the background so that another function can be called. If this function is not usedm
	nothing can be done from the GUI while the stages are moving
	# func: name of the function that is run
	"""
	t = threading.Thread(target=func)
	t.start()

#========================================
# Functions for multiprocessing
#========================================

def multi_run_wrapper_Absolute(args):
	""" Function used when running several functions in parallel with different arguments
	"""
	return deviceMoveAbsolutePos(*args)

def runInParallel(*fns):
	""" Function used to run several functions in parallel 
	"""
	proc = []
	for fn in fns:
		p = Process(target=fn)
		p.start()
		proc.append(p)
	for p in proc:
		p.join()

## The following session includes some tests ###########################################################
if __name__ == "__main__":
	BAUDRATE = 38400

	motorZ =	{
	"ctr": 'C-863.11',
	"stg": 'M-404.6PD',
	"usb": '/dev/ttyUSB0',
	"ref": 'FNL',
	"axMot": 'Z',
	}

	motorX =	{
	"ctr": 'C-863.11',
	"stg": 'M-404.1PD',
	"usb": '/dev/ttyUSB2',
	"ref": 'FNL',
	"axMot": 'X',
	}

	deviceZ=GCSDevice(motorZ["ctr"])
	deviceZ.ConnectRS232(motorZ["usb"], BAUDRATE)
	deviceX=GCSDevice(motorX["ctr"])
	deviceX.ConnectRS232(motorX["usb"], BAUDRATE)

	#deviceMoveAbsolutePos(motorX, BAUDRATE, 20, vel=4.0, init = False, wait_target=False)
	#deviceMoveAbsolutePos(motorZ, BAUDRATE, 55, vel=4.0, init = False, wait_target=False)
	## Multiprocessing: move stages X and Z simultaneously, wait for 5 seconds, move X and Z
	pool = mp.Pool(3)
	time_init = time.time()
	pool.map(multi_run_wrapper_Absolute,[(motorX, BAUDRATE, 20, time_init, 5, False, True),(motorZ, BAUDRATE, 100, time_init, 10, False, True)])
	time.sleep(5)
	pool.map(multi_run_wrapper_Absolute,[(motorX, BAUDRATE, 1, time_init, 5, False, True),(motorZ, BAUDRATE, 45, time_init, 10, False, True)])