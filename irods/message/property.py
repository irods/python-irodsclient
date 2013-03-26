from ordered import OrderedProperty, OrderedMetaclass, OrderedClass
from struct import pack

class MessageProperty(OrderedProperty):
    def __get__(self, objekt, klass):
        return objekt._values[self.name]
    def __set__(self, objekt, value):
        objekt._values[self.name] = value
    def dub(self, name):
        self.name = name
        return self

class IntegerProperty(MessageProperty):
    _format = 'i'
    def format(self, value):
        return pack(">i", value)

class LongProperty(MessageProperty):
    _format = 'q'
    def format(self, value):
        return pack(">q", value)
