# http://askawizard.blogspot.com/2008/10/ordered-properties-python-saga-part-5.html
from struct import unpack, pack
from ordered import OrderedProperty, OrderedMetaclass, OrderedClass

class MessageMetaclass(OrderedMetaclass):
    def __init__(self, name, bases, attys):
        super(MessageMetaclass, self).__init__(name, bases, attys)
        for name, property in self._ordered_properties:
            property.dub(name)
        #self._format = "".join(
        #    property._format
        #    for name, property in self._ordered_properties
        #)

class Message(OrderedClass):
    __metaclass__ = MessageMetaclass

    def __init__(self, *args, **kws):
        super(Message, self).__init__(*args, **kws)
        self._values = {}

    #def unpack(self, value, prefix = None):
    #    if prefix is None: prefix = ""
    #    for (name, property), value in zip(
    #        self._ordered_properties,
    #        unpack(prefix + self._format, value)
    #    ):
    #        self._values[name] = value

    #def pack(self, prefix=None):
    #    if prefix is None: prefix = ""
    #    values = []
    #    for (name, property) in self._ordered_properties:
    #        values.append(self._values[name])
    #    return pack(self._format, *values)

    def pack(self):
        values = []
        values.append("<%s_PI>" % self.__class__.__name__)
        for (name, property) in self._ordered_properties:
            if name in self._values:
                values.append(property.pack(self._values[name]))
        values.append("</%s_PI>" % self.__class__.__name__)
        return "".join(values)
