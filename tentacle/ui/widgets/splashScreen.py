from PySide2 import QtWidgets, QtGui, QtCore

from multiprocessing import Pool



# class Form(QtWidgets.QDialog):

# 	def __init__(self, parent=None):
# 		super(Form, self).__init__(parent)
# 		self.browser = QtWidgets.QTextBrowser()

class SplashScreen(QtWidgets.QSplashScreen):
	''''''
	def __init__(self, animation='loading_indicator', flags=QtCore.Qt.WindowStaysOnTopHint):
		'''Run event dispatching in another thread.
		'''
		QtWidgets.QSplashScreen.__init__(self, QtGui.QPixmap(), flags)

		self.movie = QtGui.QMovie(animation)
		self.movie.frameChanged.connect(self.onNextFrame)
		self.movie.start()


	def onNextFrame(self):
		''''''
		pixmap = self.movie.currentPixmap()
		self.setPixmap(pixmap)
		self.setMask(pixmap.mask())




def longInitialization(arg):
	'''Put your initialization code here.
	'''
	time.sleep(arg)
	return 0



if __name__ == "__main__":
	import sys, time
	qApp = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QtWidgets.QApplication(sys.argv)

	# Create and display the splash screen
	# splash_pix = QtGui.QPixmap('qWidget_imagePlayer.gif')
	splash = SplashScreen()
#   splash.setMask(splash_pix.mask())
	#splash.raise_()
	splash.show()
	qApp.processEvents()

	# this event loop is needed for dispatching of Qt events
	initLoop = QtCore.QEventLoop()
	pool = Pool(processes=1)
	pool.apply_async(longInitialization, [2], callback=lambda exitCode: initLoop.exit(exitCode))
	initLoop.exec_()

	# form = Form()
	# form.show()
	# splash.finish(form)
	qApp.exec_()