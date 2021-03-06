#!/usr/bin/python
# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------#
#                                                                       #
# This file is part of the web2board project                            #
#                                                                       #
# Copyright (C) 2015 Mundo Reader S.L.                                  #
#                                                                       #
# Date: April - May 2015                                                #
# Author: Irene Sanz Nieto <irene.sanz@bq.com>                          #
#                                                                       #
#-----------------------------------------------------------------------#

import serial
import os
from subprocess import call
import platform
import glob
import time
import binascii
import math
import sys
from collections import defaultdict
import subprocess
import wx._core
import threading
from Queue import Queue
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
import unicodedata

qBoard = Queue(maxsize=1)
qMonitor = Queue()
qBaudRate = Queue()


class SerialMonitor:
	def __init__(self, port, baudRate = 9600):
		self.port = port
		self.baudRate = baudRate
		self.serial = serial.Serial(
			port=self.port,
			baudrate=self.baudRate,
			parity=serial.PARITY_ODD,
			stopbits=serial.STOPBITS_TWO,
			bytesize=serial.SEVENBITS
		)
		self.pause = False

		self.t2 = threading.Thread(target=self.ui)
		self.t2.start()

		self.t1 = threading.Thread(target=self.readQmonitor)
		self.t1.start()

		self.t3 = threading.Thread(target=self.readBoard)
		self.t3.start()

		self.t4 = threading.Thread(target=self.readBaudRate)
		self.t4.start()


	def readQmonitor(self):
		while 1:
			if not qMonitor.empty():
				message = qMonitor.get()
				if message == 'exitWeb2boardPythonProgram':
					self.serial.close()
					time.sleep(0.5)
					os._exit(1)
					return
				elif message == 'stopWeb2boardPythonProgram':
					self.pause = True
				elif message == 'startWeb2boardPythonProgram':
					self.pause = False
				else:
					self.serial.write(message)
				qMonitor.task_done()


	def readBoard (self):
		while 1 :
			if self.serial.isOpen():
				out = ''
				try:
					while self.serial.inWaiting() > 0:
						out += self.serial.read(1)
					if out != '' and self.pause == False:
						qBoard.put(out)
				except:
					pass

	def ui (self):
		ex = wx.App()
		ex.MainLoop()
		self.ui = SerialMonitorUI(None)

	def readBaudRate (self):
		while 1:
			if not qBaudRate.empty():
				baudRate = qBaudRate.get()
				self.serial.close()
				time.sleep(1)
				self.serial.baudrate = baudRate
				time.sleep(1)
				self.serial.open()


class SerialMonitorUI(wx.Dialog):

	def __init__(self, parent):
		super(SerialMonitorUI, self).__init__(parent, title='bitbloq\'s Serial Monitor', size=(500,500), style=wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX | wx.RESIZE_BORDER | wx.SYSTEM_MENU | wx.CAPTION | wx.CLOSE_BOX
)
		#Timer
		self.timer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.update, self.timer)
		self.timer.Start(100)
		self.newLine = ''
		self.Pause = False
		self.charCounter = 0

		# Elements
		self.inputTextBox = wx.TextCtrl(self, size=(300,10))
		self.response = wx.TextCtrl(self, size=(10,250), style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_AUTO_URL)
		self.response.SetMaxLength(3)
		self.sendButton = wx.Button(self, label='Send',style = wx.ALIGN_RIGHT)
		self.pauseButton = wx.Button(self, label='Pause',style = wx.ALIGN_RIGHT)
		self.clearButton = wx.Button(self, label='Clear',style = wx.ALIGN_RIGHT)

		baudRates = ['300', '1200', '2400', '4800', '9600', '14400','19200', '28800', '38400', '57600', '115200']
		self.dropdown = wx.ComboBox(self, 0, '9600', (0, 0), wx.DefaultSize ,baudRates, wx.CB_DROPDOWN)

		# Events
		self.sendButton.Bind(wx.EVT_BUTTON, self.onSend)
		self.pauseButton.Bind(wx.EVT_BUTTON, self.onPause)
		self.clearButton.Bind(wx.EVT_BUTTON, self.onClear)
		self.Bind(wx.EVT_CLOSE, self.onClose)
		self.dropdown.Bind(wx.EVT_COMBOBOX, self.onBaudRateChanged)

		# Layout
		vbox = wx.BoxSizer(wx.VERTICAL)
		hbox = wx.BoxSizer(wx.HORIZONTAL)
		hbox.Add(self.inputTextBox, 1,wx.ALL^wx.CENTER|wx.EXPAND, 12)
		hbox.Add(self.sendButton, 0, wx.ALL^wx.ALIGN_RIGHT, 12)
		vbox.Add(hbox, 0, wx.EXPAND, 12)
		vbox.Add(self.response, 1, wx.ALL^wx.CENTER|wx.EXPAND, 12)
		hbox1 = wx.BoxSizer(wx.HORIZONTAL)
		hbox1.Add(self.pauseButton, 0, wx.ALL^wx.ALIGN_LEFT, 12)
		hbox1.Add(self.clearButton, 0, wx.ALL^wx.CENTER|wx.EXPAND, 12)
		hbox1.Add((0, 0), 1, wx.EXPAND)
		hbox1.Add(self.dropdown, 0, wx.ALL^wx.ALIGN_RIGHT, 12)
		vbox.Add(hbox1, 0, wx.EXPAND, 12)
		self.SetSizer(vbox)
		self.ShowModal()

	def update(self, event):
		if not qBoard.empty() and self.Pause == False:
			message = qBoard.get()
			self.logText(message)

	def logText (self, message):
		if '\n' in message:
			self.charCounter = 0
		else:
			self.charCounter+=1

		if self.response.GetNumberOfLines() >= 800 or self.charCounter > 300:
			self.response.SetValue(message)
			self.charCounter = 0
		else:
			self.response.AppendText(message)

	def onSend(self, event):
		message = self.inputTextBox.GetValue()
		self.logText(message)
		# self.response.AppendText(message+self.newLine)
		qMonitor.put(unicode(message))
		self.inputTextBox.SetValue('')

	def onPause (self, event):
		if self.pauseButton.GetLabel() == 'Pause':
			self.pauseButton.SetLabel('Continue')
			qMonitor.put('stopWeb2boardPythonProgram')
			self.Pause = True
		else:
			self.pauseButton.SetLabel('Pause')
			qMonitor.put('startWeb2boardPythonProgram')
			self.Pause = False

	def onClear (self, event):
		self.response.SetValue('')
		self.inputTextBox.SetValue('')
		self.charCounter = 0

	def onBaudRateChanged (self, event):
		qBaudRate.put(self.dropdown.GetValue())

	def onClose(self, event):
		qMonitor.put('exitWeb2boardPythonProgram')
		self.Destroy()


if __name__ == "__main__":
	if len(sys.argv) < 2:
		print 'USAGE: SerialMonitor << port >>'
		sys.exit(1)
	else:
		serialMonitor = SerialMonitor(sys.argv[1])