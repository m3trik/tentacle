from PySide2.QtCore import Qt, QThread, Signal
from PySide2.QtGui import QCursor, QMovie
from PySide2.QtWidgets import QWidget, QApplication


class LoadingIndicator(QWidget):
	def __init__(self, parent, movie_file):
		super().__init__(parent)
		print (movie_file)
		self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
		self.setAttribute(Qt.WA_TranslucentBackground, True)
		self.setCursor(QCursor(Qt.WaitCursor))
		self.movie = QMovie(movie_file)
		self.movie.frameChanged.connect(self.update)
		self.resize(self.movie.currentPixmap().size())

	def paintEvent(self, event):
		current_frame = self.movie.currentPixmap()
		frame_rect = current_frame.rect()
		frame_rect.moveCenter(self.rect().center())
		if event.region().intersects(frame_rect):
			painter = QtGui.QPainter(self)
			painter.setOpacity(0.85)
			painter.drawPixmap(frame_rect.topLeft(), current_frame)

	def start(self):
		self.move(QCursor.pos())
		self.show()
		self.movie.start()

	def stop(self):
		self.movie.stop()
		self.hide()

	def close(self):
		self.movie.stop()
		super().close()


# --------------------------------------------------------------------------------------------








# --------------------------------------------------------------------------------------------
if __name__=='__main__':
	...

# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------



# --------------------------------------------------------------------------------------------
# deprecated:
# --------------------------------------------------------------------------------------------