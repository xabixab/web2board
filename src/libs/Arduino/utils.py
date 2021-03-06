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
import subprocess
import platform

def callAvrdude(args):
	if platform.system() =='Windows':
		cmd = "E:\web2board\\avrdude\\avrdude.exe "+args
	else:
		cmd = "avrdude "+args
	print ('--->', cmd)
	p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=(platform.system() != 'Windows'))
	output = p.stdout.read()
	err = p.stderr.read()
	return output, err


class BoardConfig :
	def __init__ (self, args):
		for arg in args:
			if 'build.mcu' in arg[0]:
				self.build_mcu= arg[1]
			if 'upload.speed' in arg[0]:
				self.upload_speed= arg[1]
			if 'f_cpu' in arg[0]:
				self.f_cpu = arg[1]
	def getBaudRate(self):
		return self.upload_speed
	def getMaxSize (self):
		return self.upload_maximum_size
	def getMCU (self):
		return self.build_mcu
	def getFCPU (self):
		return self.f_cpu