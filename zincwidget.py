# This python module is intended to facilitate users creating their own applications that use OpenCMISS-Zinc
# See the examples at https://svn.physiomeproject.org/svn/cmiss/zinc/bindings/trunk/python/ for further
# information.

# Prefer PyQt4 over PySide
try:
    from PyQt4 import QtCore, QtOpenGL
except ImportError:
    from PySide import QtCore, QtOpenGL

# from opencmiss.zinc.glyph import Glyph
from opencmiss.zinc.sceneviewer import Sceneviewer, Sceneviewerevent
from opencmiss.zinc.sceneviewerinput import Sceneviewerinput
from opencmiss.zinc.element import Element, Elementbasis
from opencmiss.zinc.scenecoordinatesystem import \
        SCENECOORDINATESYSTEM_LOCAL, \
        SCENECOORDINATESYSTEM_WINDOW_PIXEL_TOP_LEFT,\
        SCENECOORDINATESYSTEM_WORLD
from opencmiss.zinc.field import Field
from opencmiss.zinc.glyph import Glyph
from opencmiss.zinc.status import OK
from opencmiss.zinc.selection import Selectionevent
from opencmiss.zinc.region import Region

import tools.graphics as graphics

# mapping from qt to zinc start
# Create a button map of Qt mouse buttons to Zinc input buttons
button_map = {QtCore.Qt.LeftButton: Sceneviewerinput.BUTTON_TYPE_LEFT,
              QtCore.Qt.MidButton: Sceneviewerinput.BUTTON_TYPE_MIDDLE,
              QtCore.Qt.RightButton: Sceneviewerinput.BUTTON_TYPE_RIGHT}

# Create a modifier map of Qt modifier keys to Zinc modifier keys
def modifier_map(qt_modifiers):
    '''
    Return a Zinc SceneViewerInput modifiers object that is created from
    the Qt modifier flags passed in.
    '''
    modifiers = Sceneviewerinput.MODIFIER_FLAG_NONE
    if qt_modifiers & QtCore.Qt.SHIFT:
        modifiers = modifiers | Sceneviewerinput.MODIFIER_FLAG_SHIFT

    return modifiers
# mapping from qt to zinc end

# selectionMode start
class _SelectionMode(object):

    NONE = -1
    EXCLUSIVE = 0
    ADDITIVE = 1
# selectionMode end

class ZincWidget(QtOpenGL.QGLWidget):
    
    try:
        # PySide
        graphicsInitialized = QtCore.Signal()
        graphicsSelected = QtCore.Signal(object, object)
    except AttributeError:
        # PyQt
        graphicsInitialized = QtCore.pyqtSignal()
        # parameters are
        #     item - element or node
        #     Field.DomainType
        graphicsPicked = QtCore.pyqtSignal(object, object)
    

    # init start
    def __init__(self, parent=None):
        '''
        Call the super class init functions, set the  Zinc context and the scene viewer handle to None.
        Initialise other attributes that deal with selection and the rotation of the plane.
        '''
        super(ZincWidget, self).__init__(parent)
        # The context is created externally so that other code has access to it. 
        #self._context = Context("ZincWidget")
        self._context = None
        self._scene_viewer = None

        # Selection attributes
        self._nodeSelectMode = True
        self._dataSelectMode = True
        self._elemSelectMode = True
        self._selectionMode = _SelectionMode.NONE
        self._selectionGroup = None
        self._selectionGroupName = "SelectionGroup"
        self._selectionBox = None
        self._selectionAlwaysAdditive = False
        
        # init end

    def setContext(self, context):
        '''
        Sets the context for this ZincWidget.  This should be set before the initializeGL()
        method is called otherwise the scene viewer cannot be created.
        '''
        self._context = context
        region = context.getDefaultRegion()
        region.setName("root")
        self.setCurrentRegion(region)

    def getContext(self):
        if not self._context is None:
            return self._context
        else:
            raise RuntimeError("Zinc context has not been set.")
        
    def setCurrentRegion(self, region):
        self._current_region = region

    def getCurrentRegion(self):
        return self._current_region

    def getSceneviewer(self):
        '''
        Get the scene viewer for this ZincWidget.
        '''
        return self._scene_viewer
    
    def setSelectionModeAdditive(self, state):
        self._selectionAlwaysAdditive = state

    def _createSceneFilterForDomainType(self, domainType):
        filter_module = self._context.getScenefiltermodule()
        visible = filter_module.createScenefilterVisibilityFlags()
        domain = filter_module.createScenefilterFieldDomainType(domainType)
        and_filter = filter_module.createScenefilterOperatorAnd()
        and_filter.appendOperand(visible)
        and_filter.appendOperand(domain)
        return and_filter

    def setSelectModeNode(self):
        '''
        Set the selection mode to select *only* nodes.
        '''
        self._nodeSelectMode = True
        self._dataSelectMode = False
        self._elemSelectMode = False
        scene_filter = self._createSceneFilterForDomainType(Field.DOMAIN_TYPE_NODES)
        self._scene_picker.setScenefilter(scene_filter)

    def setSelectModeData(self):
        '''
        Set the selection mode to select *only* datapoints.
        '''
        self._nodeSelectMode = False
        self._dataSelectMode = True
        self._elemSelectMode = False
        scene_filter = self._createSceneFilterForDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        self._scene_picker.setScenefilter(scene_filter)

    def setSelectModeElement(self):
        '''
        Set the selection mode to select *only* elements.
        '''
        self._nodeSelectMode = False
        self._dataSelectMode = False
        self._elemSelectMode = True
        scene_filter = self._createSceneFilterForDomainType(Field.DOMAIN_TYPE_MESH3D)
        self._scene_picker.setScenefilter(scene_filter)

    def setSelectModeFace(self):
        '''
        Set the selection mode to select *only* faces (2D mesh objects).
        '''
        self._nodeSelectMode = False
        self._dataSelectMode = False
        self._elemSelectMode = True
        scene_filter = self._createSceneFilterForDomainType(Field.DOMAIN_TYPE_MESH2D)
        self._scene_picker.setScenefilter(scene_filter)

    def setSelectModeLine(self):
        '''
        Set the selection mode to select *only* lines (1D mesh objects).
        '''
        self._nodeSelectMode = False
        self._dataSelectMode = False
        self._elemSelectMode = True
        scene_filter = self._createSceneFilterForDomainType(Field.DOMAIN_TYPE_MESH1D)
        self._scene_picker.setScenefilter(scene_filter)

    def setSelectModeAll(self):
        '''
        Set the selection mode to select anything in the scene.
        '''
        self._nodeSelectMode = True
        self._dataSelectMode = True
        self._elemSelectMode = True
        self._scene_picker.setScenefilter(None)
        
    def setSelectModeNone(self):
        '''
        Turn selection off and clear the filter on the scene picker.
        '''
        self._nodeSelectMode = False
        self._dataSelectMode = False
        self._elemSelectMode = False
        self._scene_picker.setScenefilter(None)
        
    def getSelectionGroup(self):
        return self._selectionGroup

    def getSelectionGroupName(self):
        """
        Get the selection group name that can be used to query the field module
        to get the selection group.
        E.g.:
        selectionGroup = field_module m.findFieldByName(name).castGroup()
        """
        return self._selectionGroupName
        
    def setProjectionMode(self, mode):
        '''
        Set the projection mode for this scene viewer.
        
            from opencmiss.zinc.sceneviewer import Sceneviewer
            Sceneviewer.PROJECTION_MODE_PERSPECTIVE
            Sceneviewer.PROJECTION_MODE_PARALLEL
        '''
        self._scene_viewer.setProjectionMode(mode)

    # initializeGL start
    def initializeGL(self):
        '''
        Initialise the Zinc scene for drawing the axis glyph at a point.  
        '''
        # Get the scene viewer module.
        scene_viewer_module = self._context.getSceneviewermodule()

        # From the scene viewer module we can create a scene viewer, we set up the
        # scene viewer to have the same OpenGL properties as the QGLWidget.
        self._scene_viewer = scene_viewer_module.createSceneviewer(Sceneviewer.BUFFERING_MODE_DOUBLE,
                                                                   Sceneviewer.STEREO_MODE_DEFAULT)
        # Create a filter for visibility flags which will allow us to see our graphic.
        filter_module = self._context.getScenefiltermodule()
        # By default graphics are created with their visibility flags set to on (or true).
        graphics_filter = filter_module.createScenefilterVisibilityFlags()

        # Set the graphics filter for the scene viewer otherwise nothing will be visible.
        self._scene_viewer.setScenefilter(graphics_filter)
        region = self.getCurrentRegion()
        # FIXME: the below needs to go in setCurrentRegion
        scene = region.getScene()
        fieldmodule = region.getFieldmodule()
        self._selectionGroup = fieldmodule.createFieldGroup()
        self._selectionGroup.setName(self._selectionGroupName)
        scene.setSelectionField(self._selectionGroup)
        self._scene_picker = scene.createScenepicker()
        # set the filter to allow only picking of visible graphics
        self._scene_picker.setScenefilter(graphics_filter) 
        self._scene_viewer.setScene(scene)

        # Using a really cheap workaround for creating a rubber band for selection.
        # This will create strange visual artifacts when using two scene viewers looking at
        # the same scene.  Waiting on a proper solution in the API.
        graphics.defineStandardGlyphs(self._context)
        self._selectionBox = scene.createGraphicsPoints()
        self._selectionBox.setScenecoordinatesystem(SCENECOORDINATESYSTEM_WINDOW_PIXEL_TOP_LEFT)
        attributes = self._selectionBox.getGraphicspointattributes()
        attributes.setGlyphShapeType(Glyph.SHAPE_TYPE_CUBE_WIREFRAME)
        attributes.setBaseSize([10, 10, 0.9999])
        attributes.setGlyphOffset([1, -1, 0])
        self._selectionBox_setBaseSize = attributes.setBaseSize
        self._selectionBox_setGlyphOffset = attributes.setGlyphOffset

        self._selectionBox.setVisibilityFlag(False)

        # Set up unproject pipeline
        self._window_coords_from = fieldmodule.createFieldConstant([0, 0, 0])
        self._global_coords_from = fieldmodule.createFieldConstant([0, 0, 0])
        unproject = fieldmodule.createFieldSceneviewerProjection(self._scene_viewer,
                                                                 SCENECOORDINATESYSTEM_WINDOW_PIXEL_TOP_LEFT,
                                                                 SCENECOORDINATESYSTEM_WORLD)
        project = fieldmodule.createFieldSceneviewerProjection(self._scene_viewer,
                                                               SCENECOORDINATESYSTEM_WORLD, 
                                                               SCENECOORDINATESYSTEM_WINDOW_PIXEL_TOP_LEFT)

#         unproject_t = fieldmodule.createFieldTranspose(4, unproject)
        self._global_coords_to = fieldmodule.createFieldProjection(self._window_coords_from, unproject)
        self._window_coords_to = fieldmodule.createFieldProjection(self._global_coords_from, project)

        self._scene_viewer.viewAll()

#         #  Not really applicable to us yet.
#         self._selection_notifier = scene.createSelectionnotifier()
#         self._selection_notifier.setCallback(self._zincSelectionEvent)

        self._scene_viewer_notifier = self._scene_viewer.createSceneviewernotifier()
        self._scene_viewer_notifier.setCallback(self._zincSceneviewerEvent)
        
        # Notify the user that the graphics are ready to use.
        # This must be called after initializeGL has exited so use a
        # timer to create a callback that will be called from the
        # event loop.
        QtCore.QTimer.singleShot(0, self.graphicsInitialized.emit)

        # initializeGL end

    def getLookAtParameters(self):
        '''
        Get the lookat parameters of the scene viewer.  Returns a tuple
        of lookat, eye, and up vectors as lists.  If the method fails None
        is returned.
        '''
        result, lookat, eye, up = self._scene_viewer.getLookatParameters()
        if result == OK:
            return (lookat, eye, up)

        return None

    def project(self, x, y, z):
        '''
        project the given point in global coordinates into window coordinates
        with the origin at the window's top left pixel.
        '''
        in_coords = [x, y, z]
        fieldmodule = self._global_coords_from.getFieldmodule()
        fieldcache = fieldmodule.createFieldcache()
        self._global_coords_from.assignReal(fieldcache, in_coords)
        result, out_coords = self._window_coords_to.evaluateReal(fieldcache, 3)
        if result == OK:
            return out_coords  # [out_coords[0] / out_coords[3], out_coords[1] / out_coords[3], out_coords[2] / out_coords[3]]

        return None

    def unproject(self, x, y, z):
        '''
        unproject the given point in window coordinates where the origin is
        at the window's top left pixel into global coordinates.  The z value
        is a depth which is mapped so that 0 is on the near plane and 1 is 
        on the far plane.
        '''
        in_coords = [x, y, z]
        fieldmodule = self._window_coords_from.getFieldmodule()
        fieldcache = fieldmodule.createFieldcache()
        self._window_coords_from.assignReal(fieldcache, in_coords)
        result, out_coords = self._global_coords_to.evaluateReal(fieldcache, 3)
        if result == OK:
            return out_coords  # [out_coords[0] / out_coords[3], out_coords[1] / out_coords[3], out_coords[2] / out_coords[3]]

        return None

    def viewAll(self):
        '''
        Helper method to set the current scene viewer to view everything
        visible in the current scene.
        '''
        self._scene_viewer.viewAll()

    # paintGL start
    def paintGL(self):
        '''
        Render the scene for this scene viewer.  The QGLWidget has already set up the
        correct OpenGL buffer for us so all we need do is render into it.  The scene viewer
        will clear the background so any OpenGL drawing of your own needs to go after this
        API call.
        '''
        self._scene_viewer.renderScene()
        # paintGL end

    def _zincSceneviewerEvent(self, event):
        '''
        Process a scene viewer event.  The updateGL() method is called for a
        repaint required event all other events are ignored.
        '''
        if event.getChangeFlags() & Sceneviewerevent.CHANGE_FLAG_REPAINT_REQUIRED:
            self.updateGL()

#     #  Not applicable at the current point in time.
#     def _zincSelectionEvent(self, event):
#         flags = event.getChangeFlags()
#         print "change flags", flags
#         
#         # print('go the selection change')
#         if event.getChangeFlags() == Selectionevent.CHANGE_FLAG_ADD:
#             print "selection added"
#             
#         elif event.getChangeFlags() == Selectionevent.CHANGE_FLAG_REMOVE:
#             print "selection removed"
# 
#         elif event.getChangeFlags() == Selectionevent.CHANGE_FLAG_FINAL:
#             print "selection final"

    # resizeGL start
    def resizeGL(self, width, height):
        '''
        Respond to widget resize events.
        '''
        self._scene_viewer.setViewportSize(width, height)
        # resizeGL end

    def mousePressEvent(self, mouseevent):
        '''
        Inform the scene viewer of a mouse press event.  Performs selection
        on left mouse click if the ctrl key is pressed and selection of some sort is enabled.
        If the shift key is also pressed then the new selection will be added to
        the current selection, otherwise the current selection is cleared.
        '''
        if (mouseevent.modifiers() & QtCore.Qt.CTRL) and \
                (self._nodeSelectMode or self._elemSelectMode or self._dataSelectMode) and \
                button_map[mouseevent.button()] == Sceneviewerinput.BUTTON_TYPE_LEFT:
            self._selectionPositionStart = (mouseevent.x(), mouseevent.y())
            self._selectionMode = _SelectionMode.EXCLUSIVE
            # Set self._selectionAlwaysAdditive so that using the shift key is not necessary
            # This also makes it harder to lose the current selection. 
            if self._selectionAlwaysAdditive or mouseevent.modifiers() & QtCore.Qt.SHIFT:
                self._selectionMode = _SelectionMode.ADDITIVE
        else:

            scene_input = self._scene_viewer.createSceneviewerinput()
            scene_input.setPosition(mouseevent.x(), mouseevent.y())
            scene_input.setEventType(Sceneviewerinput.EVENT_TYPE_BUTTON_PRESS)
            scene_input.setButtonType(button_map[mouseevent.button()])
            scene_input.setModifierFlags(modifier_map(mouseevent.modifiers()))

            self._scene_viewer.processSceneviewerinput(scene_input)

    def mouseReleaseEvent(self, mouseevent):
        '''
        Inform the scene viewer of a mouse release event.
        '''
        if self._selectionMode != _SelectionMode.NONE:
            x = mouseevent.x()
            y = mouseevent.y()
            # Construct a small frustum to look for nodes in.
            current_region = self.getCurrentRegion()
            current_region.beginHierarchicalChange()
            self._selectionBox.setVisibilityFlag(False)
            
            item = None
            domain = None
            
            if (x != self._selectionPositionStart[0] and y != self._selectionPositionStart[1]):
                left = min(x, self._selectionPositionStart[0])
                right = max(x, self._selectionPositionStart[0])
                bottom = min(y, self._selectionPositionStart[1])
                top = max(y, self._selectionPositionStart[1])
                self._scene_picker.setSceneviewerRectangle(self._scene_viewer,
                                                           SCENECOORDINATESYSTEM_LOCAL,
                                                           left, bottom, right, top);
                if self._selectionMode == _SelectionMode.EXCLUSIVE:
                    self._selectionGroup.clear()
                if self._nodeSelectMode or self._dataSelectMode:
                    self._scene_picker.addPickedNodesToFieldGroup(self._selectionGroup)
                if self._elemSelectMode:
                    self._scene_picker.addPickedElementsToFieldGroup(self._selectionGroup)
            else:

                self._scene_picker.setSceneviewerRectangle(self._scene_viewer,
                                                           SCENECOORDINATESYSTEM_LOCAL,
                                                           x - 0.5, y - 0.5, x + 0.5, y + 0.5);
                
                fielddomaintype = self._scene_picker.getNearestGraphics().getFieldDomainType()
                
                if self._nodeSelectMode and \
                        self._elemSelectMode and \
                        self._selectionMode == _SelectionMode.EXCLUSIVE and not \
                        self._scene_picker.getNearestGraphics().isValid():
                    self._selectionGroup.clear()

                if ((self._nodeSelectMode and \
                        (self._scene_picker.getNearestGraphics().getFieldDomainType()
                            in [Field.DOMAIN_TYPE_NODES])) or \
                    (self._dataSelectMode and \
                        (self._scene_picker.getNearestGraphics().getFieldDomainType()
                            in [Field.DOMAIN_TYPE_DATAPOINTS]))):
                    node = self._scene_picker.getNearestNode()
                    nodeset = node.getNodeset()
                    
                    if __debug__:
                        if self._scene_picker.getNearestGraphics().getFieldDomainType() \
                                in [Field.DOMAIN_TYPE_NODES]:
                            print "selecting node", node.getIdentifier(), "in region", nodeset.getFieldmodule().getRegion().getName()
                        else:
                            print "selecting datapoint", node.getIdentifier(), "in region", nodeset.getFieldmodule().getRegion().getName()

                    nodegroup = self._selectionGroup.getFieldNodeGroup(nodeset)
                    if not nodegroup.isValid():
                        nodegroup = self._selectionGroup.createFieldNodeGroup(nodeset)

                    group = nodegroup.getNodesetGroup()
                    if self._selectionMode == _SelectionMode.EXCLUSIVE:
                        remove_current = group.getSize() == 1 and group.containsNode(node)
                        self._selectionGroup.clear()
                        if not remove_current:
                            group.addNode(node)
                            item = node
                            #domain = nodeset
                    elif self._selectionMode == _SelectionMode.ADDITIVE:
                        if group.containsNode(node):
                            group.removeNode(node)
                        else:
                            group.addNode(node)
                            item = node
                            #domain = nodeset

                if self._elemSelectMode and \
                    (self._scene_picker.getNearestGraphics().getFieldDomainType()
                        in [Field.DOMAIN_TYPE_MESH1D,
                            Field.DOMAIN_TYPE_MESH2D,
                            Field.DOMAIN_TYPE_MESH3D,
                            Field.DOMAIN_TYPE_MESH_HIGHEST_DIMENSION]):
                    elem = self._scene_picker.getNearestElement()
                    mesh = elem.getMesh()
                    
                    if __debug__: print "selecting element", elem.getIdentifier(),\
                        "of field domain type", fielddomaintype,\
                        "in region", mesh.getFieldmodule().getRegion().getName()

                    elementgroup = self._selectionGroup.getFieldElementGroup(mesh)
                    if not elementgroup.isValid():
                        elementgroup = self._selectionGroup.createFieldElementGroup(mesh)

                    group = elementgroup.getMeshGroup()
                    if self._selectionMode == _SelectionMode.EXCLUSIVE:
                        remove_current = group.getSize() == 1 and group.containsElement(elem)
                        self._selectionGroup.clear()
                        if not remove_current:
                            group.addElement(elem)
                            item = elem
                            #domain = mesh
                    elif self._selectionMode == _SelectionMode.ADDITIVE:
                        if group.containsElement(elem):
                            group.removeElement(elem)
                        else:
                            group.addElement(elem)
                            item = elem
                            #domain = mesh

            current_region.endHierarchicalChange()
            self._selectionMode = _SelectionMode.NONE
            if not item is None:
                self.graphicsPicked.emit(item, fielddomaintype)

        else:
            scene_input = self._scene_viewer.createSceneviewerinput()
            scene_input.setPosition(mouseevent.x(), mouseevent.y())
            scene_input.setEventType(Sceneviewerinput.EVENT_TYPE_BUTTON_RELEASE)
            scene_input.setButtonType(button_map[mouseevent.button()])

            self._scene_viewer.processSceneviewerinput(scene_input)

    def mouseMoveEvent(self, mouseevent):
        '''
        Inform the scene viewer of a mouse move event and update the OpenGL scene to reflect this
        change to the viewport.
        '''

        if self._selectionMode != _SelectionMode.NONE:
            x = mouseevent.x()
            y = mouseevent.y()
            xdiff = float(x - self._selectionPositionStart[0])
            ydiff = float(y - self._selectionPositionStart[1])
            if abs(xdiff) < 0.0001:
                xdiff = 1
            if abs(ydiff) < 0.0001:
                ydiff = 1
            xoff = float(self._selectionPositionStart[0]) / xdiff + 0.5
            yoff = float(self._selectionPositionStart[1]) / ydiff + 0.5
            scene = self._selectionBox.getScene()
            scene.beginChange()
            self._selectionBox_setBaseSize([xdiff, ydiff, 0.999])
            self._selectionBox_setGlyphOffset([xoff, -yoff, 0])
            self._selectionBox.setVisibilityFlag(True)
            scene.endChange()
        else:
            scene_input = self._scene_viewer.createSceneviewerinput()
            scene_input.setPosition(mouseevent.x(), mouseevent.y())
            scene_input.setEventType(Sceneviewerinput.EVENT_TYPE_MOTION_NOTIFY)
            if mouseevent.type() == QtCore.QEvent.Leave:
                scene_input.setPosition(-1, -1)

            self._scene_viewer.processSceneviewerinput(scene_input)

