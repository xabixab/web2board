#!/usr/bin/python
# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------#
#                                                                       #
# This file is part of the web2board project                            #
#                                                                       #
# Copyright (C) 2015 Mundo Reader S.L.                                  #
#                                                                       #
# Date: May 2015                                                        #
# Author: Irene Sanz Nieto <irene.sanz@bq.com>                          #
#                                                                       #
#-----------------------------------------------------------------------#
import os
import subprocess
import re
from os.path import expanduser
import platform
import shutil
import time 

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
import unicodedata

import arduino_compiler

class Compiler:
	def __init__(self, pathToMain):
		self.pathToMain = pathToMain
		self.userLibs = ''
		self.tmpPath = expanduser("~")+'/.web2board/'
		self.oficialArduinoLibs = ['EEPROM', 'Esplora', 'Ethernet', 'Firmata', 'GSM', 'LiquidCrystal', 'Robot_Control', 'RobotIRremote', 'Robot_Motor', 'SD', 'Servo', 'SoftwareSerial', 'SPI', 'Stepper', 'TFT', 'WiFi', 'Wire'];

		self.ide_path = os.path.realpath(__file__)
		if self.ide_path[len(self.ide_path)-1] == 'c':
			self.ide_path = self.ide_path[:-25]
		else:
			self.ide_path = self.ide_path[:-24]
		self.ide_path = os.path.join(self.ide_path ,'res','arduino')
		self.core_path = self.ide_path+'/hardware/arduino/cores/arduino'


	def removePreviousFiles (self):
		shutil.rmtree(self.tmpPath)

	def createMakefile(self, board,  arduinoDir, sketchbookDir):
		if not os.path.exists(self.tmpPath):
			os.makedirs(self.tmpPath)
		fo = open(self.pathToMain+"/res/Makefile", "r")
		makefile = fo.read()
		fo.close()
		fo = open(self.tmpPath+"Makefile", "w")
		fo.write("MODEL = "+board+"\n")
		fo.write("ARDLIBS = "+self.getArduinoLibs()+"\n")
		fo.write("USERLIBS = "+self.getUserLibs()+"\n")
		fo.write("ARDUINO_DIR = "+arduinoDir+"\n")
		fo.write("HOME_LIB = "+sketchbookDir+"\n")
		fo.write("TARGET = tmp\n")
		fo.write(makefile)
		fo.close()

	def createSketchFile (self, code):
		if not os.path.exists(self.tmpPath):
			os.makedirs(self.tmpPath)
		fo = open(self.tmpPath+"tmp.ino", "w")
		fo.write(code)
		fo.close()

	def getArduinoLibs(self):
		return self.arduinoLibs

	def getUserLibs (self):
		return self.userLibs

	def setArduinoLibs(self, arduinoLibs):
		self.arduinoLibs = arduinoLibs

	def setUserLibs (self, userLibs):
		self.userLibs = userLibs

	def find_all(self,a_str, sub):
		start = 0
		while True:
			start = a_str.find(sub, start)
			if start == -1: return
			yield start
			start += len(sub) # use start += 1 to find overlapping matches

	def parseLibs(self, code):
		arduinoLibs = []
		userLibs = []
		lib = ''
		initIndexes= list(self.find_all(code,'#include'))
		finalIndexes= list(self.find_all(code,'\n'))
		if len(initIndexes) > 1:
			for i in range(len(initIndexes)):
				lib = code[initIndexes[i]: finalIndexes[i]]
				#remove all spaces, #include ,< & >,",.h
				lib = lib.replace(' ','').replace('#include','').replace('<','').replace('>','').replace('"','').replace('.h','')
				if lib in self.oficialArduinoLibs:
					arduinoLibs.append(lib)
				else:
					if (lib == 'bqLiquidCrystal'):
						userLibs.append('MCP23008')
					userLibs.append(lib)

		#remove duplicates from lists of libs
		arduinoLibs = sorted(set(arduinoLibs))
		userLibs = sorted(set(userLibs))
		#join lists into strings
		self.setArduinoLibs(' '.join(arduinoLibs))
		self.setUserLibs(' '.join(userLibs))
		return arduinoLibs+userLibs

	def createUnicodeString(self, input_str):
		return  unicodedata.normalize('NFKD', unicode(input_str)).encode('ASCII','ignore')

	def compilerStderr (self, stdErr):
		#split the stdErr with each line ending
		stdErrSplitted = stdErr.split('\n')
		errorReport = []
		errorNum = -1
		parsingError = False
		try:
			for error in stdErrSplitted:
				error = self.createUnicodeString(error)
				#These characters are the report of in which function the error is happening 
				if 'In function' in error:
					errorNum +=1
					error = re.sub('^(.*?): In function ', '',error)
					error = error.replace(':', '')
					errorReport.append({'function': error, 'error':[]})
				elif 'error: expected initializer before' in error:
					error = re.sub('^(.*?)error: expected initializer before ', '', error)
					errorReport.append({'function': error, 'error':'expected initializer before function'})
				else:
					#Remove non important parts of the string
					error = re.sub('^(.*?)applet/tmp.cpp', '', error)
					error = re.sub(r'error', '', error)
					#Find the line number in the error report
					line = re.findall(':\d*:', error)
					#If there is a line, there is an error to report
					if len(line)>0:
						line = line[0]
						line = line.replace(':','')
						#Replace everything but the error info
						error = re.sub(':\d*:', '',error)
						#If there appears this characters, there is no error, is the final line of the error report
						if 'make: *** [applet/tmp.o]' in error:
							error = ''
						if 'warning:' not in error:
							#Append the error report
							errorReport[errorNum]['error'].append({'line':line, 'error':error})
		except :
			print 'Compiler parsing exception'
			parsingError = True

		return parsingError, errorReport

	def compileWithMakefile(self, code, board,  arduinoDir, sketchbookDir):
		self.removePreviousFiles();
		self.parseLibs(code)
		self.createMakefile(board,  arduinoDir, sketchbookDir)
		self.createSketchFile(code)
		p = subprocess.Popen('make', shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=(platform.system() != 'Windows'), cwd=self.tmpPath)
		stdOut = p.stdout.read()
		stdErr = p.stderr.read()
		parsingError, compilerStderr = self.compilerStderr(stdErr)
		errorReport =  {'stdOut':stdOut,'stdErr':stdErr, 'errorReport':compilerStderr}
		if len(errorReport['errorReport'])>= 1 or parsingError:#or len(stdErr)>0:
			errorReport['status'] = 'KO'
		else:
			errorReport['status'] = 'OK'
		return errorReport


	def compile(self, code, board, arduinoDir, sketchbookDir, target_board_mcu, build_f_cpu):
		self.parseLibs(code)
		self.createSketchFile(code)

		self.libs = ''
		for lib in self.getArduinoLibs().split(' '): 
				self.libs+= ' -I "/usr/share/arduino/libraries/'+lib+'" '
		for lib in self.getUserLibs().split(' '): 
				self.libs+= ' -I "/home/irene-sanz/sketchbook/libraries/bitbloqLibs/" '

		self.libs += '-I "'+self.ide_path+'/hardware/arduino/variants/standard"'


		if platform.system() == 'Windows':
			self.ide_path = self.ide_path.replace('/', '\\')
			self.core_path = self.core_path.replace('/', '\\')
			self.libs = self.libs.replace('/', '\\')

 
		compiler = arduino_compiler.Compiler(self.tmpPath, self.libs, self.core_path, self.ide_path, build_f_cpu, target_board_mcu)
		stdErr = compiler.build()
		parsingError, compilerStderr = self.compilerStderr(stdErr)
		errorReport =  {'stdOut':'','stdErr':stdErr, 'errorReport':compilerStderr}
		if len(errorReport['errorReport'])>= 1 or parsingError:#or len(stdErr)>0:
			errorReport['status'] = 'KO'
		else:
			errorReport['status'] = 'OK'
		return errorReport

