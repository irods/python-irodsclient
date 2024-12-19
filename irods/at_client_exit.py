import atexit
import enum
import logging
import sys
import threading

logger = logging.getLogger(__name__)


class LibraryCleanupStage(enum.Enum):
    # Integer value determines relative order of execution among the stages.
    BEFORE = 10
    DURING = 20
    AFTER = 30

    def __lt__(self, other):
        return self.value < other.value


def NOTIFY_VIA_ATTRIBUTE(func, stage):
    func.at_exit_stage = stage


initialization_lock = threading.Lock()
initialized = False
_stage_notify = {}


def _register(stage_for_execution, function, stage_notify_function=None):
    with initialization_lock:
        global initialized
        if not initialized:
            initialized = True
            atexit.register(_call_cleanup_functions)
    array = _cleanup_functions[stage_for_execution]
    if function not in array:
        array.append(function)
        _stage_notify[function] = stage_notify_function


def _reset_cleanup_functions():
    global _cleanup_functions
    _cleanup_functions = {
        LibraryCleanupStage.BEFORE: [],
        LibraryCleanupStage.DURING: [],
        LibraryCleanupStage.AFTER: [],
    }


_reset_cleanup_functions()


def _call_cleanup_functions():
    ordered_funclists = sorted((pri, fl) for (pri, fl) in _cleanup_functions.items())
    try:
        # Run each cleanup stage.
        for stage, function_list in ordered_funclists:
            # Within each cleanup stage, run all registered functions last-in, first-out. (Per atexit conventions.)
            for function in reversed(function_list):
                # Ensure we execute all cleanup functions regardless of some of them raising exceptions.
                try:
                    notify = _stage_notify.get(function)
                    if notify:
                        notify(function, stage)
                    function()
                except Exception as exc:
                    logger.warning("%r raised from %s", exc, function)
    finally:
        _reset_cleanup_functions()


# The primary interface: 'before' and 'after' are the execution order relative to the DURING stage,
# in which the Python client cleans up its own session objects and runs the optional data object auto-close facility.


def register_for_execution_before_prc_cleanup(function, **kw_args):
    """Register a function to be called by the Python iRODS Client (PRC) at exit time.
    It will be called without arguments, and before PRC begins its own cleanup tasks."""
    return _register(LibraryCleanupStage.BEFORE, function, **kw_args)


def register_for_execution_after_prc_cleanup(function, **kw_args):
    """Register a function to be called by the Python iRODS Client (PRC) at exit time.
    It will be called without arguments, and after PRC is done with its own cleanup tasks.
    """
    return _register(LibraryCleanupStage.AFTER, function, **kw_args)


class unique_function_invocation:
    """Wrap a function object to provide a unique handle for registration of a given
    function multiple times, possibly with different arguments.
    """

    def __init__(self, func, tup_args=(), kw_args=()):
        self.tup_args = tup_args
        self.kw_args = dict(kw_args)
        self.func = func
        self.at_exit_stage = None

    def __call__(self):
        return (self.func)(*self.tup_args, **self.kw_args)


def get_stage(n=2):
    """A utility function that can be called from within the highest call frame (use a higher
    "n" for subordinate frames) of a user-defined cleanup function to get the currently active
    cleanup stage, defined by a LibraryCleanupStage enum value.  The user-defined function must have been
    wrapped by an instance of class unique_function_invocation, and that wrapper object
    registered using the keyword argument: stage_notify_function = NOTIFY_VIA_ATTRIBUTE.
    """
    caller = sys._getframe(n).f_locals.get("self")
    if isinstance(caller, unique_function_invocation):
        return caller.at_exit_stage
