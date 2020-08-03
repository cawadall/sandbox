#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys, threading, time, signal
sys.path.append("/opt/jderobot/lib/python2.7")
sys.path.append("/opt/jderobot/lib/python2.7/visualStates_py")
from codegen.python.state import State
from codegen.python.temporaltransition import TemporalTransition
from codegen.python.conditionaltransition import ConditionalTransition
from codegen.python.runtimegui import RunTimeGui
from PyQt5.QtWidgets import QApplication
import config, comm
import random
import time
import math


class State0(State):
	def __init__(self, id, initial, interfaces, cycleDuration, parent=None, gui=None):
		State.__init__(self, id, initial, cycleDuration, parent, gui)
		self.interfaces = interfaces

	def runCode(self):
		pass

class State1(State):
	def __init__(self, id, initial, interfaces, cycleDuration, parent=None, gui=None):
		State.__init__(self, id, initial, cycleDuration, parent, gui)
		self.interfaces = interfaces

	def runCode(self):
		self.interfaces.myMotors.sendV(0.8)
		self.interfaces.myMotors.sendW(0)
		self.interfaces.turned = False
		self.interfaces.randang = 0

class State2(State):
	def __init__(self, id, initial, interfaces, cycleDuration, parent=None, gui=None):
		State.__init__(self, id, initial, cycleDuration, parent, gui)
		self.interfaces = interfaces

	def runCode(self):
		self.interfaces.calculate_random_angle()
		self.interfaces.myMotors.sendV(0)
		self.interfaces.complete_spin()

class State3(State):
	def __init__(self, id, initial, interfaces, cycleDuration, parent=None, gui=None):
		State.__init__(self, id, initial, cycleDuration, parent, gui)
		self.interfaces = interfaces

	def runCode(self):
		self.interfaces.myMotors.sendV(-0.4)
		self.interfaces.myMotors.sendW(0)

class Tran3(ConditionalTransition):
	def __init__(self, id, destinationId, interfaces):
		ConditionalTransition.__init__(self, id, destinationId)
		self.interfaces = interfaces

	def checkCondition(self):
		self.interfaces.calculate_obstacle()
		return self.interfaces.is_obstacle

	def runCode(self):
		pass

class Tran2(ConditionalTransition):
	def __init__(self, id, destinationId, interfaces):
		ConditionalTransition.__init__(self, id, destinationId)
		self.interfaces = interfaces

	def checkCondition(self):
		return self.interfaces.turned

	def runCode(self):
		pass

class Tran4(TemporalTransition):

	def runCode(self):
		pass

class Interfaces():
	def __init__(self):
		self.jdrc = None
		self.myMotors = None
		self.myLaser = None
		self.myPose = None
		self.is_obstacle = False
		self.randang = 0
		self.turned = False

		self.connectProxies()

	def connectProxies(self):
		cfg = config.load(sys.argv[1])
		self.jdrc = comm.init(cfg, "bump_and_go")
		self.myMotors = self.jdrc.getMotorsClient("bump_and_go.myMotors")
		if not self.myMotors:
			raise Exception("could not create client with name:myMotors")
		print("myMotors is connected")
		self.myLaser = self.jdrc.getLaserClient("bump_and_go.myLaser")
		if not self.myLaser:
			raise Exception("could not create client with name:myLaser")
		print("myLaser is connected")
		self.myPose = self.jdrc.getPose3dClient("bump_and_go.myPose")
		if not self.myPose:
			raise Exception("could not create client with name:myPose")
		print("myPose is connected")

	def destroyProxies(self):
		if self.jdrc is not None:
			self.jdrc.destroy()

	def calculate_obstacle(self):
		threshold_value = 0.4
		laserData = self.myLaser.getLaserData()
		for val in laserData.values:
			if val < threshold_value:
				self.is_obstacle = True
				return
		self.is_obstacle = False
		
	def calculate_random_angle(self):
		self.randang = 0.0174533*random.randrange(-180, 180, 1) #degrees to radians
		
	def complete_spin(self):
		rot = self.myPose.getPose3d().yaw
		print(rot)
		new_yaw = rot + self.randang
		print "new yaw = ", new_yaw
		if new_yaw > math.pi:
			new_yaw = (new_yaw-math.pi)-math.pi
		elif new_yaw < -math.pi:
			new_yaw = 2*math.pi + new_yaw
		print "new yaw corrected = ", new_yaw
		time.sleep(1)
		if new_yaw < rot:
			print("turnig right")
			while rot > new_yaw:
				self.myMotors.sendW(-0.2) #rad/seg
				rot = self.myPose.getPose3d().yaw
				print(rot)
		else:
			print("turnig left")
			while rot < new_yaw:
				self.myMotors.sendW(0.2) #rad/seg
				rot = self.myPose.getPose3d().yaw
				print(rot)
		self.turned = True

displayGui = False
guiThread = None
gui = None
state0 = None

def signal_handler(signal, frame):
	global gui
	print("SIGINT is captured. The program exits")
	if gui is not None:
		gui.close()
	global state0
	state0.stop()

def readArgs():
	global displayGui
	for arg in sys.argv:
		splitedArg = arg.split('=')
		if splitedArg[0] == '--displaygui':
			if splitedArg[1] == 'True' or splitedArg[1] == 'true':
				displayGui = True
				print('runtime gui enabled')
			else:
				displayGui = False
				print('runtime gui disabled')

def runGui():
	global gui
	app = QApplication(sys.argv)
	gui = RunTimeGui()
	gui.show()
	app.exec_()

if __name__ == "__main__":
	interfaces = Interfaces()

	readArgs()
	if displayGui:
		guiThread = threading.Thread(target=runGui)
		guiThread.start()


	if displayGui:
		while(gui is None):
			time.sleep(0.1)

		gui.addState(0, "root", True, 0.0, 0.0, None)
		gui.addState(1, "Go Straight", True, 845.0, 970.0, 0)
		gui.addState(2, "Spin", False, 1024.0, 980.0, 0)
		gui.addState(3, "Go Back", False, 948.0, 823.0, 0)

		gui.addTransition(3, "obstacle", 1, 3, 892.0, 904.5)
		gui.addTransition(2, "turned", 2, 1, 927.0, 1056.0)
		gui.addTransition(4, "1 sec", 3, 2, 983.0, 903.0)

	if displayGui:
		gui.emitLoadFromRoot()
		gui.emitActiveStateById(0)

	state0 = State0(0, True, interfaces, 100, None, gui)
	state1 = State1(1, True, interfaces, 100, state0, gui)
	state2 = State2(2, False, interfaces, 100, state0, gui)
	state3 = State3(3, False, interfaces, 100, state0, gui)

	tran3 = Tran3(3, 3, interfaces)
	state1.addTransition(tran3)

	tran2 = Tran2(2, 1, interfaces)
	state2.addTransition(tran2)

	tran4 = Tran4(4, 2, 1000)
	state3.addTransition(tran4)

	try:
		state0.startThread()
		signal.signal(signal.SIGINT, signal_handler)
		signal.pause()
		state0.join()
		if displayGui:
			guiThread.join()

		interfaces.destroyProxies()
	except:
		state0.stop()
		if displayGui:
			gui.close()
			guiThread.join()

		state0.join()
		interfaces.destroyProxies()
		sys.exit(1)
