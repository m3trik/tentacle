# !/usr/bin/python
# coding=utf-8
# from __future__ import print_function, absolute_import
from builtins import super

import time, random
import threading

from PySide2 import QtCore, QtWidgets


class ProgressWidget(QtWidgets.QWidget):

	# just for the purpose of this example,
	# define a fixed number of threads to run
	nthreads = 6

	def __init__(self):
		super().__init__()
		self.threads = []
		self.workers = []
		self.works = [0 for i in range(self.nthreads)]
		self.setupUi()
		self.setupWorkers()
		self.runThreads()

	def drawProgessBar(self):
		self.progressBar = QtWidgets.QProgressBar(self)
		self.progressBar.setGeometry(QtCore.QRect(20, 20, 582, 24))
		self.progressBar.minimum = 1
		self.progressBar.maximum = 100
		self.progressBar.setValue(0)

	def setupUi(self):
		self.setWindowTitle('Threaded Progress')
		self.resize(600, 60)
		self.drawProgessBar()

	def buildWorker(self, index):
		'''a generic function to build multiple workers;
		workers will run on separate threads and emit signals
		to the ProgressWidget, which lives in the main thread
		'''
		thread = QtCore.QThread()
		worker = Worker(index)
		worker.updateProgress.connect(self.handleProgress)
		worker.moveToThread(thread)
		thread.started.connect(worker.work)
		worker.finished.connect(thread.quit)
		QtCore.QMetaObject.connectSlotsByName(self)
		# retain a reference in the main thread
		self.threads.append(thread)
		self.workers.append(worker)

	def setupWorkers(self):
		for i in range(self.nthreads):
			self.buildWorker(i)

	def runThreads(self):
		for thread in self.threads:
			thread.start()

	def handleProgress(self, signal):
		'''you can add any logic you want here,
		it will be executed in the main thread
		'''
		index, progress = signal
		self.works[index] = progress
		value = 0
		for work in self.works:
			value += work
		value /= float(self.nthreads)
		# management of special cases
		if value >= 100:
			self.progressBar.hide()
			return
		# else
		self.progressBar.setValue(value)
		print('progress (ui) thread: %s  (value: %d)' % (threading.current_thread().name, value))


class Worker(QtCore.QObject):
	'''the worker for a threaded process;
	(this is created in the main thread and
	then moved to a QThread, before starting it)
	'''

	updateProgress = QtCore.Signal(tuple)
	finished = QtCore.Signal(int)

	def __init__(self, index):
		super(Worker, self).__init__()
		# store the Worker index (for thread tracking
		# and to compute the overall progress)
		self.id = index

	def work(self): 
		for i in range(100):
			print('worker thread: %s' % (threading.current_thread().name, ))
			# simulate some processing time
			time.sleep(random.random() * .2)
			# emit progress signal
			self.updateProgress.emit((self.id, i + 1))
		# emit finish signal
		self.finished.emit(1)









if __name__ == "__main__":
	import sys
	app = QtWidgets.QApplication(sys.argv)
	ui = ProgressWidget()
	ui.show()
	sys.exit(app.exec_())