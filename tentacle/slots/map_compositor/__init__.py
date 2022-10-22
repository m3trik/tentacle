# !/usr/bin/python
# coding=utf-8
import sys, os

import importlib
import inspect



def import_modules(importAll=False):
	'''
	'''
	sys.path.append(os.path.dirname(os.path.abspath(__file__))) #append this dir to the system path.

	for module in os.listdir(os.path.dirname(__file__)):

		mod_name = module[:-3]
		mod_ext = module[-3:]

		if module == '__init__.py' or mod_ext != '.py':
			continue

		mod = importlib.import_module(mod_name)

		if importAll:
			if '__all__' in mod.__dict__: #is there an __all__?  if so respect it.
				names = mod.__dict__['__all__']

			else: #otherwise we import all names that don't begin with _.
				names = [x for x in mod.__dict__ if not x.startswith('_')]

			# now drag them in
			globals().update({k: getattr(mod, k) for k in names})

		else:
			cls_members = inspect.getmembers(sys.modules[mod_name], inspect.isclass)

			for cls_name, cls_mem in cls_members:
				globals()[cls_name] = cls_mem

		del module

import_modules(importAll=0)



import sys, os

import numpy as np

from PySide2 import QtCore, QtWidgets
from PIL import Image
from PIL.ImageChops import invert

from switchboard import Switchboard
from utils import Utils



class Map_compositor(QtCore.QObject):
	'''
	'''
	__version__ = '1.01'

	msg_intro = '''<u>Required Substance Painter Export Settings:</u><br>Padding: <b>Dilation + transparent</b> or <b>Dilation + default backgound color</b>.
		<br><br><u>Works best with map filenames (case insensitive) ending in:</u>'''
	msg_error_maskCreation = '<br><hl style="color:rgb(255, 100, 100);"><b>Error:</b> Unable to create masks from the source images.<br>To create a mask, at least one set of source maps need to a transparent or have a solid single color backround,<br>alternatively a set of mask maps can be added to the source folder. ex. &lt;map_name&gt;_mask.png</hl>'
	msg_operation_successful = '<br><hl style="color:rgb(0, 255, 255);"><b>COMPLETED.</b></hl>'

	for k, v in Utils.mapTypes.items(): #format msg_intro using the mapTypes in imtools.
		line = '<br><b>{}:</b>  {}'.format(k, v)
		msg_intro+=line

	removeNormalMap = True
	renameMixedAOMap = True
	total_len = 0
	total_progress = 0
	masks=[]

	def __init__(self, parent=None):
		QtCore.QObject.__init__(self, parent)


	def compositeImages(self, sorted_images, output_dir, name='', callback=print):
		'''
		'''
		failed={}
		for typ, images in sorted_images.items():

			filepath0 = images[0][0]
			first_image = images[0][1]
			second_image = images[1][1] if len(images)>1 else first_image
			remaining_images = images[1:]
			width, height = first_image.size
			mode = first_image.mode
			ext = Utils.formatFilepath(filepath0, 'ext')

			key = Utils.getImageType(typ) #get key from type value in mapTypes dict. ie. 'Base_Color' from '_BC' value.
			bitDepth = Utils.bitDepth[Utils.mapModes[key]]

			if mode=='I':
				first_image = Utils.convert_to_32bit_I(first_image)

			map_background = Utils.getImageBackground(first_image, 'RGBA') #get the image background in RGBA format.
			map_background2 = Utils.getImageBackground(second_image, 'RGBA') #get the image background in RGBA format.

			if not (map_background and map_background==map_background2): #if not a uniform background, or the background of map1 is not equal to map2:
				failed[typ] = images
				continue

			else:
				if not self.masks and map_background[3]==0:
					callback('<i><br>Attempting to create masks using source <b>{}</b> ..</i>'.format(typ))
					images = [i[1] for i in images] #get the images from the (filepath, image) list of tuples.
					self.masks = Utils.createMasks(images, map_background); #debug: [self.saveImageFile(i, name=output_dir+'/'+str(n)+'_mask.png') for n, i in enumerate(self.masks)]

			length = len(remaining_images) if len(remaining_images)>1 else 1

			callback('<u><br><b>{} {} {}bit {}</b> {}x{}:</u>'.format(typ.rstrip('_'), Utils.mapModes[key], bitDepth, ext.upper(), width, height))
			self.total_progress+=1
			callback(Utils.formatFilepath(filepath0, 'file'), (1/length) *100, (self.total_progress/self.total_len) *100) #first_image self.total_progress.


			composited_image = first_image.convert('RGBA')
			for n, (file, im) in enumerate(remaining_images, 1):
				self.total_progress+=1
				callback(Utils.formatFilepath(file, 'file'), (n/length) *100, (self.total_progress/self.total_len) *100) #remaining_images self.total_progress.

				if mode=='I':
					im = Utils.convert_to_32bit_I(im)
				im = Utils.replaceColor(im, from_color=map_background, mode='RGBA')

				try:
					composited_image = Image.alpha_composite(composited_image, im.convert('RGBA')) #(background, foreground)
				except ValueError as error:
					callback('<br><hl style="color:rgb(255, 100, 100);"><b>Error:</b> '+str(error)+'</hl>')

			try:
				if map_background[3]==0:
					map_background = Utils.mapBackgrounds[key] #using this may not 
				mode = Utils.mapModes[key]
			except KeyError as error:
				pass

			result = Image.new('RGBA', composited_image.size, map_background[:3]+(255,))
			result.paste(composited_image, mask=composited_image)
			result = result.convert(mode) if not mode=='I' else Utils.convert_to_32bit_I(result) #return im to it's original mode.

			result.save('{}/{}_{}.{}'.format(output_dir, name, typ, ext))

			#convert normal maps:
			if not Utils.containsMapTypes(sorted_images, 'Normal_OpenGL'):
				try: #convert DirectX to OpenGL
					index = Utils.mapTypes['Normal_DirectX'].index(typ)

					new_type = Utils.mapTypes['Normal_OpenGL'][index]
					inverted_image = Utils.invertChannels(result, 'g')
					inverted_image.save('{}/{}_{}.{}'.format(output_dir, name, new_type, ext))

					callback('<br><u><b>{} {} {}bit {}</b> {}x{}:</u>'.format(new_type.rstrip('_'), mode, bitDepth, ext.upper(), width, height))
					callback('Created using {}_{}.{}'.format(name, typ, ext))

				except ValueError as error:
					if not Utils.containsMapTypes(sorted_images, 'Normal_DirectX'):
						try: #convert OpenGL to DirectX
							index = Utils.mapTypes['Normal_OpenGL'].index(typ)

							new_type = Utils.mapTypes['Normal_DirectX'][index]
							inverted_image = Utils.invertChannels(result, 'g')
							inverted_image.save('{}/{}_{}.{}'.format(output_dir, name, new_type, ext))

							callback('<br><u><b>{} {} {}bit {}</b> {}x{}:</u>'.format(new_type.rstrip('_'), mode, bitDepth, ext.upper(), width, height))
							callback('Created using {}_{}.{}'.format(name, typ, ext))

						except ValueError as error:
							continue
		return failed


	def retryFailed(self, failed, name, callback):
		'''
		'''
		failed_images={}
		for typ, images in failed.items():

			for n, (filepath, image) in enumerate(images):

				try:
					mask = self.masks[n]
				except IndexError as error:
					callback('<br><hl style="color:rgb(255, 100, 100);"><b>Error:</b> Composite failed: <b>{}_{}: {}</b></hl>'.format(name, typ, filepath))
					continue

				key = Utils.getImageType(typ) #

				try:
					background = Utils.mapBackgrounds[key]
					im = self.fillMaskedArea(image, background, mask)
					mode = Utils.mapModes[key]
					im = im.convert(mode)

				except KeyError as error:
					background = Utils.getImageBackground(image, 'RGBA', average=True) #get the averaged background color.
					im = self.fillMaskedArea(image, background, mask)

				try:
					failed_images[typ].append((filepath, im))
				except KeyError as error:
					failed_images[typ] = [(filepath, im)]

		return failed_images



class Map_compositor_slots(Map_compositor):

	def __init__(self, **kwargs):
		'''
		'''
		self.ui = self.sb.currentUi

		path = '{}/{}.json'.format(self.sb.defaultDir, 'map_compositor')
		Utils.setJsonFile(path) #set json file name

		#load any saved info:
		try:
			prev_input_dirs = [i for i in Utils.getJson('prev_input_dirs') if not i=='/']
			self.ui.cmb000.addItems_(prev_input_dirs[-10:], '/')
		except TypeError as error:
			pass
		try:
			prev_output_dirs = [i for i in Utils.getJson('prev_output_dirs') if not i=='/']
			self.ui.cmb001.addItems_(prev_output_dirs[-10:], '/', ascending=True)
		except TypeError as error:
			pass
		try:
			prev_map_names = [i for i in Utils.getJson('prev_map_names') if not i=='/']
			self.ui.cmb002.addItems_(prev_map_names[-10:], '/', ascending=True)
		except TypeError as error:
			pass

		self.orig_toolTip_txt000 = self.ui.txt000.toolTip()
		self.orig_toolTip_txt001 = self.ui.txt001.toolTip()

		self.ui.txt000.setText(Utils.getJson('input_dir'))
		self.ui.txt001.setText(Utils.getJson('output_dir'))
		self.ui.txt002.setText(Utils.getJson('map_name'))
		self.ui.txt003.setText(self.msg_intro)

		#disable the browser open buttons if there isn't a directory.
		if not self.ui.txt000.text():
			self.ui.b003.setDisabled(True)
		if not self.ui.txt001.text():
			self.ui.b004.setDisabled(True)


	@property
	def input_dir(self) -> str:
		'''Get the source directory from the user input text field.

		:Return:
			(str) directory path.
		'''
		return self.ui.txt000.text()


	@property
	def output_dir(self) -> str:
		'''Get the export directory from the user input text field.

		:Return:
			(str) directory path.
		'''
		return self.ui.txt001.text()


	@property
	def map_name(self) -> str:
		'''Get the map name from the user input text field.

		:Return:
			(str)
		'''
		return self.ui.txt002.text()


	def cmb000(self, index):
		'''
		'''
		cmb = self.ui.cmb000
		txt = self.ui.txt000

		if index>0:
			text = cmb.itemText(index)
			txt.setText(text)
			cmb.setCurrentIndex(0)


	def cmb001(self, index):
		'''
		'''
		cmb = self.ui.cmb001
		txt = self.ui.txt001

		if index>0:
			text = cmb.itemText(index)
			txt.setText(text)
			cmb.setCurrentIndex(0)


	def cmb002(self, index):
		'''
		'''
		cmb = self.ui.cmb002
		txt = self.ui.txt002

		if index>0:
			text = cmb.itemText(index)
			txt.setText(text)
			cmb.setCurrentIndex(0)


	def txt000(self, text=None):
		'''
		'''
		cmb = self.ui.cmb000
		txt = self.ui.txt000
		text = txt.text()

		if text:
			curItems = cmb.items[1:]
			if not text in cmb.items and Utils.isValidPath(text): #add value to json dict.
				cmb.addItems_(curItems+[text], '/', ascending=True)
				Utils.setJson('prev_input_dirs', cmb.items)

			self.ui.b003.setDisabled(False)
			txt.setToolTip(text)
		else:
			self.ui.b003.setDisabled(True)
			txt.setToolTip(self.orig_toolTip_txt000)

		Utils.setJson('input_dir', text)


	def txt001(self, text=None):
		'''
		'''
		cmb = self.ui.cmb001
		txt = self.ui.txt001
		text = txt.text()

		if text:
			curItems = cmb.items[1:]
			if not text in curItems and Utils.isValidPath(text): #add value to json dict.
				cmb.addItems_(curItems+[text], '/', ascending=True)
				Utils.setJson('prev_output_dirs', cmb.items)

			self.ui.b004.setDisabled(False)
			self.ui.txt001.setToolTip(text)
		else:
			self.ui.b004.setDisabled(True)
			self.ui.txt001.setToolTip(self.orig_toolTip_txt001)

		Utils.setJson('output_dir', text)


	def txt002(self, text=None):
		'''
		'''
		cmb = self.ui.cmb002
		txt = self.ui.txt002
		text = txt.text()

		if text:
			curItems = cmb.items[1:]
			if not text in cmb.items: #add value to json dict.
				cmb.addItems_(curItems+[text], '/', ascending=True)
				Utils.setJson('prev_map_names', cmb.items)

		Utils.setJson('map_name', text)


	def b000(self):
		'''
		'''
		input_dir = Utils.getImageDirectory()
		if input_dir:
			self.txt000(input_dir) #set the text AND enable the 'open' button if disabled.


	def b001(self):
		'''
		'''
		output_dir = Utils.getImageDirectory()
		if output_dir:
			self.ui.txt001.setText(output_dir)
			self.txt001(output_dir) #set the text AND enable the 'open' button if disabled.


	def b002(self):
		'''
		'''
		self.ui.txt003.clear()

		images = Utils.getImages(self.input_dir)
		self.process(images, self.input_dir, self.output_dir, self.map_name, self.callback)


	def b003(self):
		'''
		'''
		try:
			os.startfile(self.input_dir)
		except (FileNotFoundError, TypeError) as error:
			pass


	def b004(self):
		'''
		'''
		try:
			os.startfile(self.output_dir)
		except (FileNotFoundError, TypeError) as error:
			pass


	def process(self, images, input_dir, output_dir, map_name=None, callback=print):
		'''
		'''
		self.callback('<i>Loading maps ..</i>', clear=True)

		if not (input_dir and output_dir):
			self.ui.txt003.clear() if not 'Error:' in self.ui.txt003.toPlainText() else None
			self.ui.txt003.append('<br><hl style="color:rgb(255, 100, 100);"><b>Error:</b> You must specify a source and destination directory.</hl>')
			return
		elif not Utils.isValidPath(input_dir):
			self.ui.txt003.clear() if not 'Error:' in self.ui.txt003.toPlainText() else None
			self.ui.txt003.append('<br><hl style="color:rgb(255, 100, 100);"><b>Error:</b> Directory is invalid: <b>{}</b>.</hl>'.format(input_dir))
			return
		elif not Utils.isValidPath(output_dir):
			self.ui.txt003.clear() if not 'Error:' in self.ui.txt003.toPlainText() else None
			self.ui.txt003.append('<br><hl style="color:rgb(255, 100, 100);"><b>Error:</b> Directory is invalid: <b>{}</b>.</hl>'.format(output_dir))
			return

		#save the current lineEdit values to the json file.
		self.txt000()
		self.txt001()
		self.txt002()

		if not map_name:
			map_name = Utils.formatFilepath(input_dir, 'dir')

		sorted_images = Utils.sortImagesByType(images)
		total_maps = 1 if Utils.containsMapTypes(sorted_images, ['Normal_DirectX', 'Normal_OpenGL']) else None #account for an additional converted normal map.

		if self.removeNormalMap:
			if Utils.containsMapTypes(sorted_images, ['Normal_DirectX', 'Normal_OpenGL']):
				normal = next((i for i in sorted_images.keys() #delete the standard normal map from the output.
					if Utils.getImageType(i)=='Normal'), False)
				if normal:
					del sorted_images[normal]

		if self.renameMixedAOMap:
			if 'Mixed_AO' in sorted_images and not 'AmbientOcclusion' in sorted_images:
				sorted_images['AmbientOcclusion'] = sorted_images.pop('Mixed_AO')

		self.total_maps = len(sorted_images) + total_maps
		self.total_len = sum([len(i) for i in sorted_images.values()])

		callback('<i>Sorting <b>{}</b> images, into <b>{}</b> maps ..</i>'.format(self.total_len, self.total_maps))

		try:
			failed = self.compositeImages(sorted_images, output_dir, map_name, callback)
			if failed:
				callback('<i><br>Processing additional maps that require a mask ..</i>')
				failed_images = self.retryFailed(failed, map_name, callback)
				if failed_images:
					self.compositeImages(failed_images, output_dir, map_name, callback)
					callback(self.msg_operation_successful)
				else:
					callback(self.msg_error_maskCreation)
			else:
				callback(self.msg_operation_successful)

		except Exception as error:
			callback('<br><hl style="color:rgb(255, 100, 100);"><b>Error:</b> Operation encountered the following error:<br>{}</hl>'.format(error))
			raise error



	def callback(self, string, progress=None, total_progress=None, clear=False):
		'''
		'''
		if clear:
			self.ui.txt003.clear()
		self.ui.txt003.append(string)

		if progress is not None:
			self.ui.progressBar.setValue(progress)

		if total_progress is not None:
			self.ui.progressBar_total.setValue(total_progress)

			QtWidgets.QApplication.processEvents()



class Map_compositor_main(Map_compositor):
	'''
	'''
	def __init__(self, parent=None):
		super().__init__(parent)

		sb = Switchboard(self, widgetLoc='O:/Cloud/Code/_scripts/tentacle/tentacle/ui/widgets', slotLoc=Map_compositor_slots)
		ui = sb.map_compositor
		sb.setStyle(ui.widgets)
		ui.show()









if __name__ == "__main__":
	import sys

	app = QtWidgets.QApplication.instance()
	if not app:
		app = QtWidgets.QApplication(sys.argv)

	main = Map_compositor_main()

	sys.exit(app.exec_())


# --------------------------------
# Notes
# --------------------------------



# Deprecated ---------------------










#module name
# print (__name__)
# ======================================================================
# Notes
# ======================================================================