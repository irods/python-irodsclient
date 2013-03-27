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

    def pack(self, value):
        values = []
        values.append("<%s>" % self.name)
        values.append(self.format(value))
        values.append("</%s>" % self.name)
        return "".join(values)

class IntegerProperty(MessageProperty):
    def format(self, value):
        return str(value)

class LongProperty(MessageProperty):
    def format(self, value):
        return str(value)

class BinaryProperty(MessageProperty):
    def __init__(self, length):
        self.length = length
        super(BinaryProperty, self).__init__()

    def format(self, value):
        return value

class StringProperty(MessageProperty):
    def __init__(self, length=None):
        self.length = length
        super(StringProperty, self).__init__()

    def format(self, value):
        return value

class ArrayProperty(MessageProperty):
    def __init__(self, property):
        self.property = property
        super(ArrayProperty, self).__init__()

    def pack(self, values):
        self.property.dub(self.name)
        return "".join([self.property.pack(v) for v in values])

class SubmessageProperty(MessageProperty):
    def __init__(self, message_cls):
        self.message_cls = message_cls
        super(SubmessageProperty, self).__init__()

    def format(self, value):
        return value.pack()
