'''
Created on 30/04/2014

@author: glenn
'''

import contextlib

@contextlib.contextmanager
def get_scene(region):
    """
    A context manager for the Scene class. When used with the Python
    with statement ensures that beginChange() and endChange() are called.
    Usage:
        with get_scene(region) as scene:
            scene.some_method()
    """
    scene = region.getScene()
    scene.beginChange()
    try:
        yield scene
    finally:
        scene.endChange()
    return


@contextlib.contextmanager
def get_field_module(region):
    """
    A context manager for the Fieldmodule class. When used with the Python
    with statement ensures that beginChange() and endChange() are called.
    Usage:
        with get_field_module(region) as field_module:
            field_module.some_method()
    """
    fm = region.getFieldmodule()
    fm.beginChange()
    try:
        yield fm
    finally:
        fm.endChange()
    return

@contextlib.contextmanager
def get_tessellation_module(context):
    """
    A context manager for the Tessellationmodule class. When used with the Python
    with statement ensures that beginChange() and endChange() are called.
    Usage:
        with get_tessellation_module(context) as tessellation_module:
            tessellation_module.some_method()
    """
    tm = context.getTessellationmodule()
    tm.beginChange()
    try:
        yield tm
    finally:
        tm.endChange()
    return
