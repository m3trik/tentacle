# !/usr/bin/python
# coding=utf-8
import sys, os

try:
	import numpy as np
except ImportError as error:
	print ('{}\n	# Error: {} #'.format(__file__, error))
try:
	from PIL import Image, ImageChops, ImageDraw
except ImportError as error:
	print ('{}\n	# Error: {} #'.format(__file__, error))
try:
	from PySide2 import QtWidgets
except ImportError as error:
	print ('{}\n	# Error: {} #'.format(__file__, error))

from tentacle.slots.tk import filetk, itertk


class Imgtk():
	'''Helper methods for working with image file formats.
	'''
	app = QtWidgets.QApplication.instance()
	if not app:
		app = QtWidgets.QApplication(sys.argv)

	mapTypes = { #Get map type from filename suffix.
			'Base_Color':('Base_Color', 'BaseColor', '_BC'),
			'Roughness':('Roughness', 'Rough', '_R'),
			'Metallic':('Metallic', 'Metal', 'Metalness', '_M'),
			'Ambient_Occlusion':('Mixed_AO', 'AmbientOcclusion', 'Ambient_Occlusion', '_AO'),
			'Normal':('Normal', 'Norm', '_N'),
			'Normal_DirectX':('Normal_DirectX', 'NormalDirectX', 'NormalDX', '_NDX'),
			'Normal_OpenGL':('Normal_OpenGL', 'NormalOpenGL', 'NormalGL', '_NGL'),
			'Height':('Height', 'High', '_H'),
			'Emissive':('Emissive', 'Emit', '_E'),
			'Diffuse':('Diffuse', '_DF', 'Diff', 'Dif', '_D'),
			'Specular':('Specular', 'Spec', '_S'),
			'Glossiness':('Glossiness', 'Gloss', 'Glos', 'Glo', '_G'),
			'Displacement':('Displacement', '_DP', 'Displace', 'Disp', 'Dis', '_D'),
			'Refraction':('Refraction', 'IndexofRefraction', '_IOR'),
			'Reflection':('Reflection', '_RF'),
			'Opacity':('Opacity', 'Transparancy', 'Alpha', 'Alpha_Mask', '_O'),
	}

	mapBackgrounds = { #Get default map backgrounds in RGBA format from map type.
			'Base_Color':(127, 127, 127, 255),
			'Roughness':(255, 255, 255, 255),
			'Metallic':(0, 0, 0, 255),
			'Ambient_Occlusion':(255, 255, 255, 255),
			'Normal':(127, 127, 255, 255),
			'Normal_DirectX':(127, 127, 255, 255),
			'Normal_OpenGL':(127, 127, 255, 255),
			'Height':(127, 127, 127, 255),
			'Emissive':(0, 0, 0, 255),
			'Diffuse':(0, 0, 0, 255),
			'Specular':(0, 0, 0, 255),
			'Glossiness':(0, 0, 0, 255),
			'Displacement':(0, 0, 0, 255),
			'Refraction':(0, 0, 0, 255),
			'Reflection':(0, 0, 0, 255),
	}

	mapModes = { #Get default map mode from map type.
			'Base_Color':'RGB',
			'Roughness':'L',
			'Metallic':'L',
			'Ambient_Occlusion':'L',
			'Normal':'RGB',
			'Normal_DirectX':'RGB',
			'Normal_OpenGL':'RGB',
			'Height':'I', #I 32bit mode conversion from rgb not currently working.
			'Emissive':'L',
			'Diffuse':'RGB',
			'Specular':'L',
			'Glossiness':'L',
			'Displacement':'L',
			'Refraction':'L',
			'Reflection':'L',
	}

	bitDepth = { #Get bit depth from mode.
			'1': 1, 
			'L': 8, 
			'P': 8, 
			'RGB': 24, 
			'RGBA': 32, 
			'CMYK': 32, 
			'YCbCr': 24, 
			'LAB': 24, 
			'HSV': 24, 
			'I': 32, 
			'F': 32, 
			'I;16': 16, 
			'I;16B': 16, 
			'I;16L': 16, 
			'I;16S': 16, 
			'I;16BS': 16, 
			'I;16LS': 16, 
			'I;32': 32, 
			'I;32B': 32, 
			'I;32L': 32, 
			'I;32S': 32, 
			'I;32BS': 32, 
			'I;32LS': 32
	}


	@staticmethod
	def imhelp(a=None):
		'''Get help documentation on a specific PIL image attribute 
		or list all available attributes.

		:Parameters:
			a (str) = A specific PIL image attribute (ie. 'resize') 
					or if None given; list all available attributes.
		'''
		im = Image.new('RGB', (32, 32))

		if a is None:
			for i in dir(im):
				if i.startswith('_'):
					continue
				print (i)
		else:
			print (help(getattr(im, a)))

		del(im)


	@staticmethod
	def createImage(mode, size=(4096, 4096), color=None):
		'''Create a new image.

		:Parameters:
			mode (str) = Image color mode. ex. 'I', 'L', 'RGBA'
			size (tuple) = Size as x and y coordinates.
			color (int)(tuple) = Color values.
					'I' mode image color must be int or single-element tuple.
		:Return:
			(obj) image.
		'''
		return Image.new(mode, size, color)


	@staticmethod
	def resizeImage(image, x, y):
		'''Returns a resized copy of an image. It doesn't modify the original.

		:Parameters:
			image (str)(obj) = An image or path to an image.
			x (int) = Size in the x coordinate.
			y (int) = Size in the y coordinate.

		:Return:
			(obj) new image of the given size.
		'''
		im = Image.open(image) if isinstance(image, str) else image
		return im.resize((x, y), Image.Resampling.LANCZOS)


	@staticmethod
	def saveImageFile(image, name):
		'''
		:Parameters:
			image (obj) = PIL image object.
			name (str) = Path + filename including extension. ie. new_image.png
		'''
		im = Image.open(image) if isinstance(image, str) else image
		im.save(name)


	@classmethod
	def getImages(cls, directory, inc='*.png|*.jpg|*.bmp|*.tga|*.tiff|*.gif', exc=''):
		'''Get bitmap images from a given directory as PIL images.

		:Parameters:
			directory (string) = A full path to a directory containing images with the given fileTypes.
			inc (str) = The files to include. 
					supports using the '*' operator: startswith*, *endswith, *contains*
			exc (str) = The files to exclude.
					(exlude take precidence over include)
		:Return:
			(dict) {<full file path>:<image object>}
		'''
		images={}
		for f in filetk.getDirContents(directory, 'filepaths', incFiles=inc.split('|'), excFiles=exc.split('|')):

			im = Image.open(f) #closing will destroy the image core and release its memory. The image data will be unusable afterward.
			images[f] = im

		return images


	@staticmethod
	def getImageFiles(fileTypes='*.png|*.jpg|*.bmp|*.tga|*.tiff|*.gif'):
		'''Open a dialog prompt to choose image files of the given type(s).

		:Parameters:
			fileTypes (str) = The extensions of image types to include.

		:Return:
			(list)
		'''
		files = QtWidgets.QFileDialog.getOpenFileNames(None, 
			"Select one or more image files to open", "/home", "Images ({})".format(' '.join(fileTypes.split('|'))))[0]

		return files


	@staticmethod
	def getImageDirectory():
		'''Open a dialog prompt to choose a directory.

		:Return:
			(list)
		'''
		image_dir = QtWidgets.QFileDialog.getExistingDirectory(None, 
			"Select a directory containing image files", "/home")

		return image_dir


	@classmethod
	def getImageTypeFromFilename(cls, file, key=True):
		'''
		:Parameters:
			file (str) = Image filename, fullpath, or map type suffix.
			key (bool) = Get the corresponding key from the type in 'mapTypes'. 
				ie. Base_Color from <filename>_BC or BC. else: _BC from <filename>_BC.

		:Return:
			(str)
		'''
		name = filetk.formatPath(file, 'name')

		if key:
			result = next((k for k, v in cls.mapTypes.items() for i in v if name.lower().endswith(i.lower())), None)
		else:
			result = next((i for v in cls.mapTypes.values() for i in v if name.lower().endswith(i.lower())), (''.join(name.split('_')[-1]) if '_' in name else None))
		if result:
			return result


	@classmethod
	def filterImagesByType(cls, files, types=''):
		'''
		:Parameters:
			files (list) = A list of image filenames, fullpaths, or map type suffixes.
			types (str) = Any of the keys in the 'map_types' dict.
				Multiple types can be given separated by '|' ex. 'Base_Color|Roughness'
				ex. 'Base_Color','Roughness','Metallic','Ambient_Occlusion','Normal',
					'Normal_DirectX','Normal_OpenGL','Height','Emissive','Diffuse','Specular',
					'Glossiness','Displacement','Refraction','Reflection'
		:Return:
			(dict)
		'''
		types = itertk.makeList(types.split('|'))
		return [f for f in files if cls.getImageTypeFromFilename(f) in types]


	@classmethod
	def sortImagesByType(cls, files):
		'''Sort images files by map type.

		:Parameters:
			files (list)(dict) = filenames, fullpaths, or map type suffixes as the first element 
					of two element tuples or keys in a dictionary. ex. [('file', <image>)] or {'file': <image>}
		:Return:
			(dict) ex. {Height:[('img_height.png', <image>)]}
		'''
		if not isinstance(files, (list, tuple, set)):
			files = files.items()

		sorted_images={}
		for file, image in files:
			typ = cls.getImageTypeFromFilename(file)
			if not typ:
				continue

			try:
				sorted_images[typ].append((file, image))
			except KeyError as error:
				sorted_images[typ] = [(file, image)]

		return sorted_images


	@classmethod
	def containsMapTypes(cls, files, map_types):
		'''Check if the given images contain the given map types.

		:Parameters:
			files (list)(dict) = filenames, fullpaths, or map type suffixes as the first element 
					of two element tuples or keys in a dictionary. ex. [('file', <image>)] or {'file': <image>} or {'type': ('file', <image>)}
			map_types (str)(list) = The map type(s) to query. Any of the keys in the 'map_types' dict.
					Multiple types can be given separated by '|' ex. 'Base_Color|Roughness'
					ex. 'Base_Color','Roughness','Metallic','Ambient_Occlusion','Normal',
						'Normal_DirectX','Normal_OpenGL','Height','Emissive','Diffuse','Specular',
						'Glossiness','Displacement','Refraction','Reflection'
		:Return:
			(bool)
		'''
		if isinstance(files, (list, set, tuple)):
			files = cls.sortImagesByType(files) #convert list to dict of the correct format.

		if isinstance(map_types, str):
			map_types = map_types.split('|')

		result = next((True for i in files.keys() 
			if cls.getImageTypeFromFilename(i) in map_types), False)

		return True if result else False


	@classmethod
	def isNormalMap(cls, file):
		'''Check the map type for one of the normal values in mapTypes.

		:Parameters:
			file (str) = Image filename, fullpath, or map type suffix.

		:Return:
			(bool)
		'''
		typ = cls.getImageTypeFromFilename(file)
		return any((typ in cls.mapTypes['Normal_DirectX'], 
				typ in cls.mapTypes['Normal_OpenGL'], 
				typ in cls.mapTypes['Normal']))


	@staticmethod
	def invertChannels(image, channels='RGB'):
		'''Invert RGB channels.

		:Parameters:
			image (str)(obj) = An image or path to an image.
			channels (str) = Specify which channels to invert.
				valid: 'R','G','B' case insensitive.
		:Return:
			(obj) image.
		'''
		im = Image.open(image) if isinstance(image, str) else image
		alpha = None

		try:
			r, g, b = im.split()
		except ValueError as error:
			r, g, b, a = im.split()

		r = ImageChops.invert(r) if 'r' in channels.lower() else r
		g = ImageChops.invert(g) if 'g' in channels.lower() else g
		b = ImageChops.invert(b) if 'b' in channels.lower() else b

		return Image.merge('RGB', (r, g, b))# if alpha else Image.merge('RGB', (red, green, blue))


	@classmethod
	def createDXFromGL(cls, file):
		'''Create and save an OpenGL map using a given DirectX image.
		The new map will be saved next to the existing map.

		:Parameters:
			file (str) = The fullpath to a DirectX normal map file.

		:Return:
			(str) filepath of the new image.
		'''
		inverted_image = cls.invertChannels(file, 'g')

		output_dir = filetk.formatPath(file, 'path')
		name = filetk.formatPath(file, 'name')
		ext = filetk.formatPath(file, 'ext')

		typ = cls.getImageTypeFromFilename(file, key=False)
		try:
			index = cls.mapTypes['Normal_OpenGL'].index(typ)
			new_type = cls.mapTypes['Normal_DirectX'][index]
		except (IndexError, ValueError) as error:
			print ('{} in createDXFromGL\n\t# Error: {} #'.format(__file__, error))
			new_type = 'Normal_DirectX'

		name = name.removesuffix(typ)
		filepath = '{}/{}{}.{}'.format(output_dir, name, new_type, ext)
		inverted_image.save(filepath)

		return filepath


	@classmethod
	def createGLFromDX(cls, file):
		'''Create and save an DirectX map using a given OpenGL image.
		The new map will be saved next to the existing map.

		:Parameters:
			file (str) = The fullpath to a OpenGL normal map file.

		:Return:
			(str) filepath of the new image.
		'''
		inverted_image = cls.invertChannels(file, 'g')

		output_dir = filetk.formatPath(file, 'path')
		name = filetk.formatPath(file, 'name')
		ext = filetk.formatPath(file, 'ext')

		typ = cls.getImageTypeFromFilename(file, key=False)
		try:
			index = cls.mapTypes['Normal_DirectX'].index(typ)
			new_type = cls.mapTypes['Normal_OpenGL'][index]
		except IndexError as error:
			print ('{} in createGLFromDX\n\t# Error: {} #'.format(__file__, error))
			new_type = 'Normal_OpenGL'

		name = name.removesuffix(typ)
		filepath = '{}/{}{}.{}'.format(output_dir, name, new_type, ext)
		inverted_image.save(filepath)

		return filepath


	@classmethod
	def createMask(cls, images, mask, background=(0, 0, 0, 255), foreground=(255, 255, 255, 255)):
		'''Create mask(s) from the given image(s).

		:Parameters:
			images (str)(obj)(list) = Image(s) or path(s) to an image.
			mask (tuple)(image) = The color to isolate as a mask. (RGB) or (RGBA) 
					or an Image(s) or path(s) to an image. The image's background color will be used.
			background (tuple) = Mask background color. (RGB) or (RGBA)
			foreground (tuple) = Mask foreground color. (RGB) or (RGBA)

		:Return:
			(obj)(list) 'L' mode images. list if 'images' given as a list. else; single image.
		'''
		if not isinstance(mask, (tuple, list, set)):
			mask = cls.getBackground(mask)

		result=[]
		for image in itertk.makeList(images):
			im = Image.open(image) if isinstance(image, str) else image
			mode = im.mode
			im = im.convert('RGBA')
			width, height = im.size
			data = np.array(im)

			r1, g1, b1, a1 = mask if len(mask)==4 else mask+(None,)

			r, g, b, a = data[:,:,0], data[:,:,1], data[:,:,2], data[:,:,3]

			bool_list = ((r==r1) & (g==g1) & (b==b1) & (a==a1)) if len(mask)==4 else ((r==r1) & (g==g1) & (b==b1))

			data[:,:,:4][bool_list.any()] = foreground
			data[:,:,:4][bool_list] = background

			#set the border to background color:
			data[0, 0] = background #get the pixel value at top left coordinate.
			data[width-1, 0] = background #			""	 top right coordinate.
			data[0, height-1] = background #			""	 bottom right coordinate.
			data[width-1, height-1] = background #		""	 bottom left coordinate.

			m = Image.fromarray(data).convert('L')
			result.append(m)

		return itertk.formatReturn(result, images)


	@classmethod
	def fillMaskedArea(cls, image, color, mask):
		'''
		:Parameters:
			image (str)(obj) = An image or path to an image.
			color (list) = RGB or RGBA color values.
			mask () = 

		:Return:
			(obj) image.
		'''
		im = Image.open(image) if isinstance(image, str) else image
		mode = im.mode
		im = im.convert('RGBA')

		background = cls.createImage(mode=im.mode, size=im.size, color=color)

		return Image.composite(im, background, mask).convert(mode)


	@staticmethod
	def fill(image, color=(0, 0, 0, 0)):
		'''
		:Parameters:
			image (str)(obj) = An image or path to an image.
			color (list) = RGB or RGBA color values.

		:Return:
			(obj) image.
		'''
		im = Image.open(image) if isinstance(image, str) else image

		draw = ImageDraw.Draw(im)
		draw.rectangle([(0,0), im.size], fill=color)

		return im


	@staticmethod
	def getBackground(image, mode=None, average=False):
		'''Sample the pixel values of each corner of an image and if they are uniform, return the result.

		:Parameters:
			image (str)(obj) = An image or path to an image.
			mode (str) = The returned image color mode. ex. 'RGBA'
					If None is given, the original mode will be returned.
			average (bool) = Average the sampled pixel values.

		:Return:
			(int)(tuple) dependant on mode. ex. 32767 for mode 'I' or (211, 211, 211, 255) for 'RGBA' 
		'''
		im = Image.open(image) if isinstance(image, str) else image

		if mode and not im.mode==mode:
			im = im.convert(mode)

		width, height = im.size

		tl = im.getpixel((0, 0)) #get the pixel value at top left coordinate.
		tr = im.getpixel((width-1, 0)) #			""	 top right coordinate.
		br = im.getpixel((0, height-1)) #			""	 bottom right coordinate.
		bl = im.getpixel((width-1, height-1)) #		""	 bottom left coordinate.

		if len(set([tl, tr, br, bl]))==1: #list of pixel values are all identical.
			return tl

		elif average:
			return tuple(int(np.mean(i)) for i in zip(*[tl, tr, br, bl]))

		else:
			return None #non-uniform background.


	@staticmethod
	def replaceColor(image, from_color=(0, 0, 0, 0), to_color=(0, 0, 0, 0), mode=None):
		'''
		:Parameters:
			image (str)(obj) = An image or path to an image.
			from_color (tuple) = The starting color. (RGB) or (RGBA)
			to_color (tuple) = The ending color. (RGB) or (RGBA)
			mode (str) = The image is converted to rgba for the operation specify the returned image mode. the original image mode will be returned if None is given. ex. 'RGBA' to return in rgba format.

		:Return:
			(obj) image.
		'''
		im = Image.open(image) if isinstance(image, str) else image
		mode = mode if mode else im.mode
		im = im.convert('RGBA')
		data = np.array(im)

		r1, g1, b1, a1 = from_color if len(from_color)==4 else from_color+(None,)

		r, g, b, a = data[:,:,0], data[:,:,1], data[:,:,2], data[:,:,3]

		mask = ((r==r1) & (g==g1) & (b==b1) & (a==a1)) if len(from_color)==4 else ((r==r1) & (g==g1) & (b==b1))
		data[:,:,:4][mask] = to_color if len(to_color)==4 else to_color+(255,)

		return Image.fromarray(data).convert('RGBA')


	@staticmethod
	def setContrast(image, level=255):
		'''
		:Parameters:
			image (str)(obj) = An image or path to an image.
			level (int) = Contrast level from 0-255.

		:Return:
			(obj) image.
		'''
		im = Image.open(image) if isinstance(image, str) else image

		factor = (259 * (level + 255)) / (255 * (259 - level))
		_contrast = lambda c: int(max(0, min(255, 128 + factor * (c - 128)))) #make sure the contrast filter only return values within the range [0-255].

		return im.point(_contrast)


	@staticmethod
	def convert_rgb_to_gray(data):
		'''Convert an RGB Image data array to grayscale.

		:Paramters:
			data (str)(obj)(array) = An image, path to an image, or 
					Image data as numpy array.
		:Return:
			(array)

		# gray_data = np.average(data, weights=[0.299, 0.587, 0.114], axis=2)
		# gray_data = (data[:,:,:3] * [0.2989, 0.5870, 0.1140]).sum(axis=2)
		'''
		if not isinstance(data, np.ndarray):
			im = data.open(data) if (isinstance(data, str)) else data
			data = np.array(im)

		gray_data = np.dot(data[...,:3], [0.2989, 0.5870, 0.1140])

		# array = gray_data.reshape(gray_data.shape[0], gray_data.shape[1], 1)
		#print (array.shape)

		return gray_data


	@staticmethod
	def convert_RGB_to_HSV(image):
		'''Manually convert the image to a NumPy array, iterate over the pixels 
		and use the colorsys module to convert the colors from RGB to HSV.
		PIL images can be converted usin: image.convert("HSV")
		PNG files cannot be saved as HSV.

		:Parameters:
			image (str)(obj) = An image or path to an image.

		:Return:
			(obj) image.
		'''
		import colorsys

		im = Image.open(image) if isinstance(image, str) else image
		data = np.array(im)
		
		# Convert the colors from RGB to HSV
		hsv = np.empty_like(data)
		for i in range(data.shape[0]):
			for ii in range(data.shape[1]):
				r, g, b = data[i, ii]
				h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
				hsv[i, ii] = (int(h * 360), int(s * 100), int(v * 100))

		return Image.fromarray(hsv, mode='HSV')


	@staticmethod
	def convert_I_to_L(image):
		'''Convert to 8 bit 'L' grayscale.

		:Parameters:
			image (str)(obj) = An image or path to an image.

		:Return:
			(obj) image.
		'''
		im = Image.open(image) if isinstance(image, str) else image
		data = np.array(im)

		data = np.asarray(data, np.uint8) #np.uint8(data / 256)
		return Image.fromarray(data)


	@staticmethod
	def areIdentical(imageA, imageB):
		'''Check if two images are the same.

		:Parameters:
			imageA (str)(obj) = An image or path to an image.
			imageB (str)(obj) = An image or path to an image.

		:Return:
			(bool)
		'''
		imA = Image.open(imageA) if (isinstance(imageA, str)) else imageA
		imB = Image.open(imageB) if (isinstance(imageB, str)) else imageB

		if np.sum(np.array(ImageChops.difference(imA, imB).getdata())) == 0:
			return True
		return False

# --------------------------------------------------------------------------------------------
from tentacle import addMembers
addMembers(__name__)









if __name__=='__main__':
	pass



# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------



# Deprecated ------------------------------------


# def getBitDepth(cls, image):
# 		'''
# 		'''
# 		im = Image.open(image) if isinstance(image, str) else image
# 		data = np.array(im)

# 		bitDepth = {'uint8':8, 'uint16':16, 'uint32':32, 'uint64':64}

# 		return bitDepth[str(data.dtype)]


# width, height = im.size
 
		# for i in range(0, width):# process all pixels
		# 	for ii in range(0, height):
		# 		data = im.getpixel((i, ii))
		# 		# data[0] = Red,  [1] = Green, [2] = Blue
		# 		# data[0,1,2] range = 0~255
		# 		if data==mask:
		# 		# if data[0] > 150 and data[1] < 50 and data[2] < 50 :
		# 			im.putpixel((i, ii), (0, 0, 0))
		# 		else :
		# 			im.putpixel((i, ii), (255, 255, 255))

		# return im.convert(mode)


	# def isolateColor(cls, image, color):
	# 	'''Return an image with only pixels of the given color retained.
	# 	'''
	# 	im = Image.open(image) if isinstance(image, str) else image
	# 	data = np.array(im)

	# 	r, g, b =  color[:3]
	# 	array = np.where(data == r, g, b)

	# 	return Image.fromarray(array.astype('uint8')) #Image.fromarray(converted.astype('uint8'))


	# def createMask(cls, image, mask):
	# 	'''
	# 	'''
	# 	im = Image.open(image) if isinstance(image, str) else image

	# 	im = cls.replaceColor(im, from_color=mask, to_color=(0, 177, 64, 255))

	# 	# background = cls.createImage(mode='RGBA', size=im.size, rgba=(0, 177, 64, 255))
	# 	# im = Image.alpha_composite(background, im) #(background, foreground)

	# 	# im = cls.isolateColor(im, (0, 177, 64))
	# 	# im = cls.replaceColor(im, from_color=(0, 177, 64), to_color=(255, 255, 255, 255), background_color=(0, 0, 0, 255))
	# 	# im = cls.setContrast(im, 255)
	# 	return im



	# def convertDXToGL(cls):
	# 	'''
	# 	'''
	# 	files = cls.getImageFiles()
	# 	for file, image in files.items():
	# 		inverted_image = cls.invertChannels(image, 'g')
	# 		# name = filetk.formatPath(file, remove='_DirectX', append='_OpenGL')
	# 		# cls.saveImageFile(inverted_image, name)


	# def convertGLToDX(cls):
	# 	'''
	# 	'''
	# 	files = cls.getImageFiles()
	# 	for file, image in files.items():
	# 		inverted_image = cls.invertChannels(image, 'g')
	# 		# name = filetk.formatPath(file, remove='_OpenGL', append='_DirectX')
	# 		# cls.saveImageFile(inverted_image, name)



	# def changeColorDepth(cls, image, depth):
	# 	'''
	# 	'''
		# return image.convert(image.mode, colors=depth)

		# import math

		# grayscale_color_count = 256
		# rgb_color_count = 256

		# if image.mode=='L':
		# 	raito = grayscale_color_count / colorCount
		# 	change = lambda value: math.trunc(value/raito)*raito
		# 	return image.point(change)

		# if image.mode=='RGB' or image.mode=='RGBA':
		# 	raito = rgb_color_count / colorCount
		# 	change = lambda value: math.trunc(value/raito)*raito
		# 	return Image.eval(image, change)

		# raise ValueError('invalid image mode: {mode}'.format(mode=image.mode))






		# appended = '{}{}.{}'.format(''.join(string.split('.')[:-1]), append, ''.join(string.split('.')[-1]))
		# removed = appended.replace(remove, '')

		# return '{}/{}'.format(path, removed)
