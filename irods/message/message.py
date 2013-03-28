# http://askawizard.blogspot.com/2008/10/ordered-properties-python-saga-part-5.html
from struct import unpack, pack
from ordered import OrderedProperty, OrderedMetaclass, OrderedClass
import xml.etree.ElementTree as ET

class MessageMetaclass(OrderedMetaclass):
    def __init__(self, name, bases, attys):
        super(MessageMetaclass, self).__init__(name, bases, attys)
        for name, property in self._ordered_properties:
            property.dub(name)

class Message(OrderedClass):
    __metaclass__ = MessageMetaclass

    def __init__(self, *args, **kwargs):
        super(Message, self).__init__()
        self._values = {}
        for (name, _) in self._ordered_properties:
            if name in kwargs:
                self._values[name] = kwargs[name]

    def pack(self):
        values = []
        values.append("<%s_PI>" % self.__class__.__name__)
        for (name, property) in self._ordered_properties:
            if name in self._values:
                values.append(property.pack(self._values[name]))
        values.append("</%s_PI>" % self.__class__.__name__)
        return "".join(values)

    def unpack(self, root):
        #root = ET.fromstring(xml_str)
        for (name, property) in self._ordered_properties:
            self._values[name] = property.unpack(root)