import atexit
import enum

_cleanup_functions = {}

class priority(enum.Enum):
    BEFORE_PRC = 10
    DURING_PRC = 20
    AFTER_PRC = 30

# So that we can access priority.ENUM_NAME as simply ENUM_NAME at module level.
for _ in priority.__members__:
    exec('{}=priority.{}'.format(_,_))

initialized = False

def register(priority_for_execution, function):
    global initialized
    if not initialized:
        initialized = True
        atexit.register(call_cleanup)
    _cleanup_functions[function] = priority( priority_for_execution )

def call_cleanup():
   funclist = sorted((pri.value,func) for func,pri in _cleanup_functions.items())
   for priority,function in funclist:
       try:
           # Ensure we execute all cleanup functions regardless of some of them raising exceptions.
           function()
       except Exception as exc:
           logger.getLogger(__name__).debug("%r raised from %s",exc,function)


if __name__ == '__main__':
    def after():
        print('after')
    register(AFTER_PRC,after)
    def before():
        print('before')
    register(BEFORE_PRC,before)
    def during():
        print('during')
    register(DURING_PRC,during)
