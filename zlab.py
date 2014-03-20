# Mayavi mlab workalike for OpenCMISS-zinc

# It may be a good idea to borrow some if the architecture of mayavi. It is
# quite complex so may take some time to understand. Therefore the structure,
# namespaces and method names of this module are highly likely to change.

import sys
import threading
import Queue

from opencmiss.zinc.context import Context

import zinc_util.mesh as mesh

try:
    from PySide import QtGui, QtCore
except ImportError:
    from PyQt4 import QtGui, QtCore

from zlab_ui import Ui_ZlabDlg

# FIXME: probably need a class to hold these
_ctxt = None
initialised = False
_app = None
_messageQueue = Queue.Queue()
_window = None

def getApp():
    global _app
    return _app

def _init():
    global _ctxt
    if _ctxt is None:
        _ctxt = Context("zlab")

def read_txtnode(filename):
    return mesh.read_txtnode(filename)

def read_txtelem(filename):
    return mesh.read_txtelem(filename)
    
def linear_mesh(node_coordinate_set, element_set):
    '''
    Create linear finite elements given node and element lists
    '''
    _init()
    global _ctxt
    mesh.linear_mesh(_ctxt, node_coordinate_set, element_set)
    
def data_points(coordinate_set):
    
    if len(coordinate_set) == 0:
        raise RuntimeError("Empty datapoint list") 
    
    _init()
    
    mesh.data_points(_ctxt, coordinate_set)

def createGraphics():
    
    _init()
    
    global _ctxt
    createGraphics(_ctxt)
    
def show():
    # Show the Zinc window in a separate thread.
    # FIXME: everything that uses the context needs to be called in this thread
    
    def thread_func():
    
        class ZlabDlg(QtGui.QWidget):
            '''
            Create a dialog window.
            '''
            
            def __init__(self, parent=None):
                '''
                Initialise the ZlabDlg widget, first calling the QWidget __init__ function.
                '''
                super(ZlabDlg, self).__init__(parent)
                
                # Using composition to include the visual element of the GUI.
                self.ui = Ui_ZlabDlg()
                self.ui.setupUi(self)
                #self.setWindowIcon(QtGui.QIcon("cmiss_icon.ico"))
                
                _init()
                            
                global _ctxt
                self.ui._zincWidget.setContext(_ctxt)
                
                self.ui._zincWidget.graphicsInitialized.connect(self.postGLInitialise)
            
            def postGLInitialise(self):
                # It seems to work OK if this isn't called.               
                self.ui._zincWidget.viewAll()
    
        def poll():
            global _messageQueue
            while not _messageQueue.empty():
                func = _messageQueue.get_nowait()
                if func is not None:
                    func()

        # create the app and UI widget
        global _app
        _app = QtGui.QApplication.instance()
        if _app is None:
            _app = QtGui.QApplication(sys.argv)
        
        global _window
        if _window is None:
            _window = ZlabDlg()
        _window.show()
        
        timer = QtCore.QTimer()
        timer.setInterval(100)
        timer.timeout.connect(poll)
        timer.start(100)
        
        _app.exec_()
    
    zinc_thread = threading.Thread(target=thread_func)
    zinc_thread.start()

    
def hide():
    def _hideWindow():
        global _window
        _window.hide()
    
    _messageQueue.put(_hideWindow)


def close():
    def _closeWindow():
        global _window
        _window.close()
    
    _messageQueue.put(_closeWindow)
    

def exit_():
    def _exitApp():
        global _app
        _app.exit()
    
    _messageQueue.put(_exitApp)
    