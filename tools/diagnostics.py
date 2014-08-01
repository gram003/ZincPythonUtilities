import sys

def funcname():
    return sys._getframe(1).f_code.co_name
