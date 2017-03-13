from __future__ import absolute_import
from base64 import b64encode, b64decode

from irods.message.ordered import OrderedProperty
import six


class MessageProperty(OrderedProperty):

    def __get__(self, obj, cls):
        return obj._values[self.name]

    def __set__(self, obj, value):
        obj._values[self.name] = value

    def dub(self, name):
        self.name = name
        return self

    def pack(self, value):
        values = []
        values.append("<%s>" % self.name)
        my_value = self.format(value)
        if six.PY3 and isinstance(my_value, bytes):
            my_value = my_value.decode("utf-8")
        values.append(my_value)
        values.append("</%s>" % self.name)
        return "".join(values)

    def unpack(self, els):
        if len(els):
            el = els[0]
            return self.parse(el.text)
        return None


class IntegerProperty(MessageProperty):

    def format(self, value):
        return str(value)

    def parse(self, value):
        return int(value)


class LongProperty(MessageProperty):

    def format(self, value):
        return str(value)

    def parse(self, value):
        return int(value)


class BinaryProperty(MessageProperty):

    def __init__(self, length=None):
        self.length = length
        super(BinaryProperty, self).__init__()

    def format(self, value):
        if six.PY3 and not isinstance(value, bytes):
            val = b64encode(value.encode())
        else:
            val = b64encode(value)
        return val

    def parse(self, value):
        val = b64decode(value)
        if six.PY3:
            val = val.decode('utf-8')
        return val


class StringProperty(MessageProperty):

    def __init__(self, length=None):
        self.length = length
        super(StringProperty, self).__init__()

    def format(self, value):
        if six.PY3 and isinstance(value, bytes):
            value = value.decode()
        return value

    def parse(self, value):
        return value


class ArrayProperty(MessageProperty):

    def __init__(self, prop):
        self.prop = prop
        super(ArrayProperty, self).__init__()

    def pack(self, values):
        self.prop.dub(self.name)
        return "".join([self.prop.pack(v) for v in values])

    def unpack(self, els):
        return [self.prop.unpack([el]) for el in els]


class SubmessageProperty(MessageProperty):

    def __init__(self, message_cls=None):
        self.message_cls = message_cls
        super(SubmessageProperty, self).__init__()

    def pack(self, value):
        return value.pack()

    def unpack(self, els):
        if len(els):
            el = els[0]
            msg = self.message_cls()
            msg.unpack(el)
            return msg
        return None
