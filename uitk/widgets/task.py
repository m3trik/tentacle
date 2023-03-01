import os, sys, time
from PySide2 import QtCore, QtWidgets, QtGui


class WorkIndicator(QtWidgets.QDialog):
	def __init__(self, parent=None):
		super().__init__(parent)

		self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowStaysOnTopHint)
		self.setModal(True)

		gif_path = "O:/Cloud/Code/_scripts/uitk/uitk/widgets/loading_indicator.gif"
		self.movie = QtGui.QMovie(gif_path, parent=self)
		self.movie.setCacheMode(QtGui.QMovie.CacheAll)
		self.movie.setScaledSize(QtCore.QSize(75, 75))

		label = QtWidgets.QLabel(self)
		label.setMovie(self.movie)
		label.setAlignment(QtCore.Qt.AlignCenter)

		layout = QtWidgets.QVBoxLayout(self)
		layout.addWidget(label)
		self.setLayout(layout)

		self.setFixedSize(self.movie.frameRect().size())

	def start(self):
		self.movie.start()
		self.show()
		self.move(QtGui.QCursor.pos() - QtCore.QPoint(self.width()/2, self.height()/2))

	def stop(self):
		self.movie.stop()
		self.accept()


class Task(QtCore.QThread):
	complete = QtCore.Signal()

	def __init__(self):
		super().__init__()
		self.work_indicator = WorkIndicator()
		self.complete.connect(self.work_indicator.stop)

	def start_task(self, task_function):
		self.task_function = task_function
		self.finished.connect(self.on_finished)
		self.start()
		self.work_indicator.start()

	def run(self):
		self.task_function()
		self.complete.emit()

	def on_finished(self):
		self.finished.disconnect(self.on_finished)
		self.task_function = None
		self.deleteLater()

# --------------------------------------------------------------------------------------------








# --------------------------------------------------------------------------------------------
if __name__=='__main__':
	class MainWindow(QtWidgets.QWidget):
		def __init__(self):
			super().__init__()

			layout = QtWidgets.QVBoxLayout()
			self.setLayout(layout)

			button = QtWidgets.QPushButton("Perform Long Running Task")
			button.clicked.connect(self.perform_long_running_task)
			layout.addWidget(button)

			self.task = Task()

		def perform_long_running_task(self):
			# Create a separate thread to perform the long running task.
			self.task.start_task(self.long_running_task)
			

		def long_running_task(self):
			time.sleep(2)  # Move the time.sleep(5) to this method

	app = QtWidgets.QApplication([])
	main = MainWindow()
	main.show()
	sys.exit(app.exec_())

# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------



# --------------------------------------------------------------------------------------------
# deprecated:
# --------------------------------------------------------------------------------------------