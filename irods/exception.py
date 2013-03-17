class iRODSException(Exception):
	def __init__(self, error_id):
		Exception.__init__(self, "iRODS error %d" % error_id)
