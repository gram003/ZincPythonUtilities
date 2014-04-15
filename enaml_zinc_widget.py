
from zincwidget import ZincWidget
from opencmiss.zinc.context import Context

from atom.api import set_default
from enaml.widgets.api import RawWidget

class EZincWidget(RawWidget):
    hug_width = set_default('ignore')
    hug_height = set_default('ignore')
    
    def create_widget(self, parent):
        
        c = Context("EZincWidget")

        widget = ZincWidget(parent)
        widget.setContext(c)
        return widget
