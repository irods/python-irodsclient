# A parser for the iRODS XML-like protocol.
# The interface aims to be compatible with xml.etree.ElementTree,
# at least for the features used by python-irodsclient.

class Element():
    """
    Represents <name>body</name>.

    (Where `body' is either a string or a list of sub-elements.)
    """

    @property
    def tag(self): return self.name

    def __init__(self, name, body):
        """Initialize with the tag's name and the body (i.e. content)."""
        if body == []:
            # Empty element.
            self.text = None
        elif type(body) is not list:
            # String element: decode body.
            body = decode_entities(body)
            self.text = body

        self.name = name
        self.body = body

    def find(self, name):
        """Get first matching child element by name."""
        for x in self.findall(name):
            return x

    def findall(self, name):
        """Get matching child elements by name."""
        return list(self.findall_(name))

    def findall_(self, name):
        """Get matching child elements by name (generator variant)."""
        return (el for el in self.body if el.name == name)

    # For debugging convenience:
    def __str__(self):
        if type(self.body) is list:
            return '<{}>{}</{}>'.format(self.name, ''.join(map(str, self.body)), self.name)
        else:
            return '<{}>{}</{}>'.format(self.name, encode_entities(self.body), self.name)

    def __repr__(self):
        return '{}({})'.format(self.name, repr(self.body))


class Token(object):
    """A utility class for parsing XML."""
    def __init__(self, s):
        """Create a `Token' object from `s', the text comprising the parsed token."""
        self.text = s
    def __repr__(self):
        return str(type(self).__name__) + '(' + self.text.decode('utf-8') + ')'
    def __str__(self):
        return repr(self)

class TokenTagOpen(Token):
    """An opening tag (<foo>)"""
class TokenTagClose(Token):
    """An closing tag (</foo>)"""
class TokenCData(Token):
    """Textual element body"""

class QuasiXmlParseError(Exception):
    """Indicates parse failure of XML protocol data."""

def tokenize(s):
    """Parse an XML-ish string into a list of tokens."""
    tokens = []

    # Consume input until empty.
    while True:
        nextclose = s.find(b'</')
        nextopen  = s.find(b'<')
        if nextopen < nextclose or nextopen == -1:
            # Either we have no tags left, or we are in a non-cdata element body: strip whitespace.
            s = s.lstrip()

        if len(s) == 0:
            return tokens

            # Closing tag?
        elif s.startswith(b'</'):
            try:
                name, s = s[2:].split(b'>', 1)
            except Exception:
                raise QuasiXmlParseError('protocol error: unterminated close tag')
            tokens.append(TokenTagClose(name))
            s = s.lstrip() # consume space after closing tag

            # Opening tag?
        elif s.startswith(b'<'):
            try:
                name, s = s[1:].split(b'>', 1)
            except Exception:
                raise QuasiXmlParseError('protocol error: unterminated open tag')
            tokens.append(TokenTagOpen(name))

        else:
            # capture cdata till next tag.
            try:
                cdata, s = s.split(b'<', 1)
            except Exception:
                raise QuasiXmlParseError('protocol error: unterminated cdata')
            s = b'<' + s
            tokens.append(TokenCData(cdata))

def fromtokens(tokens):
    """Parse XML-ish tokens into an Element."""

    def parse_elem(tokens):
        """Parse some tokens into one Element, and return unconsumed tokens."""
        topen, tokens = tokens[0], tokens[1:]
        if type(topen) is not TokenTagOpen:
            raise QuasiXmlParseError('protocol error: data does not start with open tag')

        children = []
        cdata    = None

        while len(tokens) > 0:
            t, tokens = tokens[0], tokens[1:]
            if type(t) is TokenTagOpen:
                # Slurp a sub-element.
                el, tokens = parse_elem([t] + tokens)
                children.append(el)
                # Continue with non-consumed tokens.
            elif type(t) == TokenTagClose:
                if t.text != topen.text:
                    raise QuasiXmlParseError('protocol error: close tag <{}> does not match opening tag <{}>'.format(t.text, topen.text))
                elif cdata is not None and len(children):
                    raise QuasiXmlParseError('protocol error: mixed cdata and child elements')
                return Element(topen.text.decode('utf-8'), cdata.decode('utf-8') if cdata is not None else children), tokens
            else:
                cdata = t.text

    elem, rest = parse_elem(tokens)
    if rest != []:
        raise QuasiXmlParseError('protocol error: trailing data')

    return elem


try:
    unicode         # Python 2
except NameError:
    unicode = str


def fromstring(s):
    if type(s) is unicode:
        s = s.encode('utf-8')
    if type(s) is not bytes:
        raise TypeError('expected a bytes-object, got {}'.format(type(s).__name__))

    return fromtokens(tokenize(s))


def encode_entities(s):
    from . import XML_entities_active
    for k, v in XML_entities_active():
        s = s.replace(k, v)
    return s

def decode_entities(s):
    from . import XML_entities_active
    rev = list(XML_entities_active())
    rev.reverse() # (make sure &amp; is decoded last)
    for k, v in rev:
        s = s.replace(v, k)
    return s
