class iRODSMeta(object):
    def __init__(self, name, value, units, id=None):
        self.id = id
        self.name = name
        self.value = value
        self.units = units

    def __repr__(self):
        return "<iRODSMeta (%s, %s, %s, %s)>" % (
            self.name, self.value, self.units, str(self.id)
        )
