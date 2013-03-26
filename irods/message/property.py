from ordered import OrderedProperty, OrderedMetaclass, OrderedClass

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

class LongProperty(MessageProperty):
    _format = 'q'
