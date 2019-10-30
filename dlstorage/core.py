"""This file is part of DeepLens which is released under MIT License and 
is copyrighted by the University of Chicago. This project is developed by
the database group (chidata).

core.py defines the basic storage api in deeplens.
"""

import time
from functools import wraps

def timeit(method):
	@wraps(method)
	def timed(*args, **kw):
		ts = time.time()
		result = method(*args, **kw)
		te = time.time()
		if 'log_time' in kw:
			name = kw.get('log_name', method.__name__.upper())
			kw['log_time'][name] = int((te - ts)*1000)
		else:
			print('%r %2.2f ms\n' % (method.__name__, (te - ts) * 1000))
		return result
	return timed

class StorageManager():
	"""The StorageManager is the basic abstract class that represents a
	storage manager.
	"""
	def __init__(self, content_tagger):
		self.content_tagger = content_tagger

	#@timeit
	def put(self, filename, target, args, log_time={}):
		"""putFromFile adds a video to the storage manager from a file
		"""
		raise NotImplemented("putFromFile not implemented")

	#@timeit
	def get(self, name, condition, clip_size, log_time={}):
		"""retrievies a clip of a certain size satisfying the condition
		"""
		raise NotImplemented("getIf not implemented")

	def setThreadPool(self):
		raise ValueError("This storage manager does not support threading")

	def delete(self,name):
		raise NotImplemented("delete not implemented")

	def list(self):
		raise NotImplemented("list() not implemented")

	def size(self, name):
		raise NotImplemented("size() not implemented")


