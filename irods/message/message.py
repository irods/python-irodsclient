# http://askawizard.blogspot.com/2008/10/ordered-properties-python-saga-part-5.html
from __future__ import absolute_import
from irods.message.ordered import OrderedMetaclass, OrderedClass
import six


class MessageMetaclass(OrderedMetaclass):

    def __init__(self, name, bases, attys):
        super(MessageMetaclass, self).__init__(name, bases, attys)
        for name, prop in self._ordered_properties:
            prop.dub(name)


class Message(six.with_metaclass(MessageMetaclass, OrderedClass)):

    def __init__(self, *args, **kwargs):
        super(Message, self).__init__()
        self._values = {}
        for (name, _) in self._ordered_properties:
            if name in kwargs:
                self._values[name] = kwargs[name]

    def pack(self):
        values = []
        values.append("<%s>" % self.__class__._name)
        for (name, prop) in self._ordered_properties:
            if name in self._values:
                values.append(prop.pack(self._values[name]))
        values.append("</%s>" % self.__class__._name)
        return "".join(values)

    def unpack(self, root):
        for (name, prop) in self._ordered_properties:
            self._values[name] = prop.unpack(root.findall(name))
