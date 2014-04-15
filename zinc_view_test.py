
# Set API to version 2. Something is setting it to API 1 and that is
# causing an error when enaml tries to set it to 2. This has to be done
# before QtCore is imported. 
import sip
API_NAMES = ["QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"]
API_VERSION = 2
for name in API_NAMES:
    sip.setapi(name, API_VERSION)

# Import QtCore after setting the API version and before Enaml to
# prevent a clash.
from PyQt4 import QtCore

import enaml_zinc_widget

import enaml

with enaml.imports():
    from zinc_view import Main

from enaml.qt.qt_application import QtApplication

from fitter import Fitter

from main_controller import MainController
controller = MainController()

app = QtApplication()

view = Main(title="Zinc Fitting", controller=controller)

view.show()

# The zinc context is created by the EZincWidget constructor and this
# occurs after show is called so we have to retrieve the ZincWidget and
# pass it to the controller. This is not ideal, it would be better to
# pass the ZincWidget in the constructor of the controller. 
ezw = view.find("ZincWidget")
zw = ezw.get_widget()
context = ezw.get_widget().getContext()
print "context", context

# Fitter needs the ZincWidget so that it can get the selection group.
# FIXME: This is not ideal it would be better if the selection group could
# be stored in the zinc library. 
f = Fitter(context)
controller.setFitter(f)
controller.setZincWidget(zw)


app.start()
