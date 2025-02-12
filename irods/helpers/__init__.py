import contextlib
import re
from ..test.helpers import home_collection, make_session as make_test_session
from irods.message import ET, XML_Parser_Type

__all__ = ["make_session", "home_collection", "xml_mode"]


def make_session(test_server_version=False, **kwargs):
    return make_test_session(test_server_version=test_server_version, **kwargs)


make_session.__doc__ = re.sub(
    r"(test_server_version\s*)=\s*\w+", r"\1 = False", make_test_session.__doc__
)


@contextlib.contextmanager
def xml_mode(s):
    """In a with-block, this context manager can temporarily change the client's choice of XML parser.

    Example usages:
        with("QUASI_XML"):
            # ...
        with(XML_Parser_Type.QUASI_XML):
            # ..."""

    try:
        if isinstance(s, str):
            ET(getattr(XML_Parser_Type, s))  # e.g. xml_mode("QUASI_XML")
        elif isinstance(s, XML_Parser_Type):
            ET(s)  # e.g. xml_mode(XML_Parser_Type.QUASI_XML)
        else:
            msg = "xml_mode argument must be a string (e.g. 'QUASI_XML') or an XML_Parser_Type enum."
            raise ValueError(msg)
        yield
    finally:
        ET(None)


class _unlikely_value:
    pass


@contextlib.contextmanager
def temporarily_assign_attribute(
    target, attr, value, not_set_indicator=_unlikely_value()
):
    save = not_set_indicator
    try:
        save = getattr(target, attr, not_set_indicator)
        setattr(target, attr, value)
        yield
    finally:
        if save != not_set_indicator:
            setattr(target, attr, save)
        else:
            delattr(target, attr)
