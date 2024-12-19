def login(conn):
    conn._login_native()


# TODO (#499): Here, we could define client & server auth_state classes (ie state machines mimicking the mechanics
#              of 4.3+ iCommands/iRods-runtime authentication framework), using this pattern for an inheritance hook.
from . import X as X_base


class X(X_base):
    pass
