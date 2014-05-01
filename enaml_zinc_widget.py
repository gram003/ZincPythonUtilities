
from zincwidget import ZincWidget

from atom.api import set_default, Typed
from enaml.widgets.api import RawWidget
from enaml.core.api import d_

#import atom.api
from opencmiss.zinc.context import Context

class EZincWidget(RawWidget):
    hug_width = set_default('ignore')
    hug_height = set_default('ignore')
    context = d_(Typed(Context))
    #widget = d_(Typed(ZincWidget))
    
#     def __init__(self, parent):
#         super(EZincWidget, self).__init__(parent)
    
    def set_zinc_context(self, context):
        #self._context.s
        print "set_zinc_context", context
        self.context = context
        
    def create_widget(self, parent):
        widget = ZincWidget(parent)
        widget.setContext(self.context)
        return widget
