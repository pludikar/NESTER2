import adsk.core, adsk.fusion, traceback
import logging, os, sys, math
import json

logger = logging.getLogger('Nester.command')
# logger.setLevel(logging.DEBUG)

from . import Fusion360CommandBase, utils
# from .common import nestFacesDict, handlers
# from .common import eventHandler
from .common import *

# Get the root component of the active design
rootComp = design.rootComponent

transform = adsk.core.Matrix3D.create()

# Utility casts various inputs into appropriate Fusion 360 Objects
def getSelectedObjects(selectionInput):
    logger.info("getSelectedObjects")
    objects = []
    for i in range(0, selectionInput.selectionCount):
        selection = selectionInput.selection(i)
        selectedObj = selection.entity
        if adsk.fusion.BRepBody.cast(selectedObj) or \
           adsk.fusion.BRepFace.cast(selectedObj) or \
           adsk.fusion.Occurrence.cast(selectedObj):
           objects.append(selectedObj)
    return objects

# Utility to get and format the various inputs
def getInputs(command, inputs):
    logger.info("getInputs")
    selectionInput = None

    for inputI in inputs:
        global commandId
        if inputI.id == command.parentCommandDefinition.id + '_selection':
            selectionInput = inputI
        elif inputI.id == command.parentCommandDefinition.id + '_stockObject':
            stockObjectInput = inputI
        elif inputI.id == command.parentCommandDefinition.id + '_spacing':
            spacingInput = inputI
            spacing = spacingInput.value
        # elif inputI.id == command.parentCommandDefinition.id + '_edge':
        #     edgeInput = inputI
        elif inputI.id == command.parentCommandDefinition.id + '_subAssy':
            subAssyInput = inputI
            subAssy = subAssyInput.value

    objects = getSelectedObjects(selectionInput)
    try:
        stockObject = getSelectedObjects(stockObjectInput)[0]
    except IndexError:
        stockObject = None
    # edge = adsk.fusion.BRepEdge.cast(edgeInput.selection(0).entity)

    if not objects or len(objects) == 0:
        # TODO this probably requires much better error handling
        return (objects, stockObject, spacing)
    # return(objects, stockObject, edge, spacing, subAssy)

    return (objects, stockObject, spacing)


# Creates a linked copy of all components in a new Sub Assembly
def createSubAssy(objects):
    app = adsk.core.Application.get()
    product = app.activeProduct
    design = adsk.fusion.Design.cast(product)

    # Get the root component and create a new component
    rootComp = design.rootComponent
    nestComp_Occ = rootComp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    nestComp = nestComp_Occ.component
    nestComp.name = "Nested Assembly"

    # Create a new empty collection to hold new references
    newFaces = adsk.core.ObjectCollection.create()

    # Iterate the selected face
    for originalFace in objects:

        # Get the native face from the proxy (selected face)
        nativeFace = originalFace.nativeObject

        # Copy the parent component of this face into the nested sub assy component
        newOccurence = nestComp.occurrences.addExistingComponent(originalFace.assemblyContext.component, adsk.core.Matrix3D.create())

        # Get the same face but in the context of the new occurrence
        newFace = nativeFace.createForAssemblyContext(newOccurence)

        # Add the new face to the collection
        newFaces.add(newFace)

    return newFaces



# Returns a normalized vector in positive XYZ space from a given edge
def getPositiveUnitVectorFromEdge(edge):
    # Set up a vector based on input edge
    (returnValue, startPoint, endPoint) = edge.geometry.evaluator.getEndPoints()
    directionVector = adsk.core.Vector3D.create(endPoint.x - startPoint.x,
                                           endPoint.y - startPoint.y,
                                           endPoint.z - startPoint.z )
    directionVector.normalize()

    if (directionVector.x < 0):
        directionVector.x *= -1
    if (directionVector.y < 0):
        directionVector.y *= -1
    if (directionVector.z < 0):
        directionVector.z *= -1

    return directionVector

class NestItems():
    """     
    Top level nest item management
    Keeps track of all stock and nest objects
    """
    _document = app.activeDocument.name
    _nestObjects =[]
    _stockObjects = []
    
    _positionOffset = 0
    _spacing = 0

    _addedFaces = []
    _removedFaces = []

    _addedStock = []
    _removedStock = []

    def __init__(self):
        nestAttributes:adsk.core.Attributes = design.findAttributes(NESTER_GROUP, NESTER_TYPE)

        for nestAttribute in nestAttributes:
            if nestAttribute.value == 'Item'
                self.addItem(nestAttribute.parent)
            else:
                self.addedStock(nestAttribute.parent)

        # if len(nestAttributes) >0:
        #     stockObjectTokens = json.loads(stockObjectAttribute.value)
        #     for token in stockObjectTokens:
        #         entityList = design.findEntityByToken(token)
        #         if not len(entityList):
        #             continue
        #         for stockObjectFace in entityList:
        #             self.addStock(stockObjectFace)
        #             facesAttribute =stockObjectFace.attributes.itemByName('Nester', 'faceData')

        #             if facesAttribute:
        #                 faceTokens = json.loads(facesAttribute.value)
        #                 for token in faceTokens:
        #                     entityList = design.findEntityByToken(token)
        #                     if not len(entityList):
        #                         continue
        #                     for entityFace in entityList:
        #                         self.add(entityFace, stockObjectFace)

    def save(self):
        stockObjects = [x.selectedFace.entityToken for x in self._stockObjects]
        rootComp.attributes.add(NESTER_GROUP, NESTER_OCCURRENCES, json.dumps(stockObjects)) 

#TODO
    def refresh(self):
        nesterAttrbs = design.findAttributes(NESTER_GROUP, NESTER_OCCURRENCES)
        
        for attrb in nesterAttrbs:
            self.add()



    def __iter__(self):
        for f in self._nestObjects:
            yield f

    def __next__(self):
        for f in self._nestObjects:
            yield f

    def addItem(self, newComponent, sourceComponent):
        self._occurrences.append(NestItem(newComponent, sourceComponent)) 
            
    def add(self, selectedFace, stockObjectFace):
        logger.info("NestItems.add")
        if selectedFace in self._nestObjects:
            return
        faceObject = NestItem(selectedFace, stockObjectFace)
        self._nestObjects.append(faceObject)
       
        return faceObject

    def remove(self, body):
        pass


    def addStock(self, selectedFace):
        logger.info("NestItems.addStock")
        stock = NestStock(selectedFace)
        self._stockObjects.append(stock)

    def removeStock(self, selectedFace):
        pass


    @property
    def stockObjects(self):
        return self._stockObjects

    @property
    def allFaces(self):
        return self._nestObjects

    @property
    def addedStock(self):
        return [x for x in self._stockObjects if x.added]

    @property
    def changedStock(self):
        return [x for x in self._stockObjects if x.changed]

    @property
    def removedStock(self):
        return [x for x in self._stockObjects if x.removed]

    @property
    def addedFaces(self):
        return [x for x in self._nestObjects if x.added]

    @property
    def removedFaces(self):
        return [x for x in self._nestObjects if x.removed]

    @property
    def changedFaces(self):
        return [x for x in self._nestObjects if x.changed]
    
    def find(self, selectedEnity):
        return [face for face in self._nestObjects if face == selectedEntity][0]  # this should work for both bRepFace and bRepBody

    def refreshOffsets(self):
        logger.info("NestItems.refreshOffsets")
        for stock in self._stockObjects:
            positionOffset = 0
            positionOffset += stock.offset

            for face in self._nestObjects:
                positionOffset += self._spacing
                positionOffset += face.offset
                face.positionOffset = positionOffset
                # adsk.doEvents()

    @property
    def reset(self):
       self._nestObjects = []
       self._stockObjects = []
       self._positionOffset = 0
       self._spacing = 1

    @property
    def spacing(self):
        return self._spacing

    @spacing.setter
    def spacing(self, magnitude):
        self._spacing = magnitude

class NestStock():
    def __init__ (self, occurrence:adsk.fusion.Occurrence, sourceOccurrence:adsk.fusion.Occurrence):

        logger.info("NestStock.init")
        self._selectedFaceToken = selectedFace.entityToken
        self._bodyToken = selectedFace.body.entityToken
        self._occurrenceToken  = occurrence.entityToken
        self._sourceOccurrenceToken  = sourceOccurrence.entityToken
        self._profileToken = None

        self._joint :adsk.fusion.Joint = None
        self._jointGeometry :adsk.fusion.JointGeometry = None
        self._jointOriginToken  = None

        self._xOffset = None
        self._yOffset = None
        self._angle = 0

        self._timelineObject :adsk.fusion.TimelineObject = None

        self._changed = False
        self._added = True
        self._removed = False

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (other.selectedFace == self.selectedFace) or (other.occurrence == self.occurrence)
        if other.objectType == adsk.fusion.BRepFace.classType():
            return other == self.selectedFace
        elif other.objectType == adsk.fusion.BRepBody.classType():
            return other == self.body
        return NotImplemented

    def __neq__(self, other):
        if isinstance(other, self.__class__):
            return other.selectedFace != self.selectedFace
        if other.objectType == adsk.fusion.BRepFace.classType():
            return other != self.selectedFace
        elif other.objectType == adsk.fusion.BRepBody.classType():
            return other != self.body
        return NotImplemented

    def addJointOrigin(self):
        logger.info(f"NestStock.addJointOrigin - {self.occurrence.component.name}")

        allOrigins = [x.name for x in self.occurrence.component.allJointOrigins]
        if 'nest_O_'+self.occurrence.name in allOrigins: #if joint already exists don't add another one
            return False

        self._xOffset = utils.getBoundingBoxExtent(self.body)/2
    
        # centreOffsetX, centreOffsetY, self._height = utils.centreOffsetsFromFace(utils.getTopFace(self._selectedFace))
        centreOffsetX, centreOffsetY, self._height = utils.centreOffsetsFromFace(self.selectedFace)
        
        logger.debug(f'faceJointOriginOffsets; {centreOffsetX:}; {centreOffsetY}')

        jointOrigins = self.occurrence.component.jointOrgins
        self._jointGeometry = adsk.fusion.JointGeometry.createByPlanarFace(self.selectedFace, None, adsk.fusion.JointKeyPointTypes.CenterKeyPoint)

        jointOriginInput = jointOrigins.createInput(self._jointGeometry)
        jointOriginInput.offsetX  = adsk.core.ValueInput.createByReal(centreOffsetX)
        jointOriginInput.offsetY = adsk.core.ValueInput.createByReal(centreOffsetY)

        jointOrigin = jointOrigins.add(jointOriginInput)

        self.jointOrigin = jointOrigin.createForAssemblyContext(self.occurrence)
        self.jointOrigin.name = 'nest_O_'+self.occurrence.component.name

    def changeJointOrigin(self):
        self._jointOrigin.timelineObject.rollTo(True)
        logger.info(f"NestStock.changeJointOrigin - {self.occurrence.component.name}")
        logger.debug(f"working on face: {self.selectedFace.tempId:d}")
  
        centreOffsetX, centreOffsetY, self._height = utils.centreOffsetsFromFace(self.selectedFace)
        
        logger.debug(f'faceJointOriginOffsets; {centreOffsetX: 9.3f}; {centreOffsetY: 9.3f}')

        self._jointGeometry = adsk.fusion.JointGeometry.createByPlanarFace(self.selectedFace, None, adsk.fusion.JointKeyPointTypes.CenterKeyPoint)

        self.jointOrigin.geometry = self._jointGeometry
        self.jointOrigin.offsetX.value = centreOffsetX
        self.jointOrigin.offsetY.value = centreOffsetY
        self.jointOrigin.timelineObject.rollTo(False)

        self.joint.timelineObject.rollTo(True)
        self.joint.geometryOrOriginOne = self._jointOrigin
        self.joint.timelineObject.rollTo(False)

    def saveVars(self):
        attributes = self.body.assemblyContext.attributes
        varsDict = vars(self) 
        varsDict = {k: v for k, v in varsDict.items() if not callable(v)} #only include variables that are not functions or methods
        data = json.dumps(varsDict)

        nesterAttrbs = attributes.add(NESTER_GROUP, NESTER_TOKENS, data)    
        
    def loadVars(self):
        attributes = self.body.assemblyContext.attributes
        try:
            nesterTokens = attributes.itemByName(NESTER_GROUP, NESTER_TOKENS).value
            data = json.loads(nesterTokens)
            varsDict = vars(self) 
            for item, value in data.items():
                varsDict[item] = value
        except AttributeError:
            pass
        except KeyError:
            pass

    @property
    def tempId(self):
        return self.selectedFace.tempId

    @property
    def added(self):
        return self._added

    @added.setter
    def added(self, state):
        self._added = state

    @property
    def removed(self):
        return self._removed

    @removed.setter
    def removed(self, state):
        self._removed = state

    @property
    def changed(self):
        return self._changed

    @changed.setter
    def changed(self, state):
        self._changed = state

    @property
    @entityFromToken
    def face(self):
        return self._selectedFaceToken

    @property
    @entityFromToken
    def body(self):
        return self._bodyToken

    @property
    def height(self):
        return self._height

    @property
    @entityFromToken
    def occurrence(self):
        return self._occurrenceToken

    @property
    @entityFromToken
    def joint(self):
        return self._joint

    @joint.setter
    def joint(self, newJoint:adsk.fusion.Joint):
        self._jointToken = newJoint.entityToken

    @property
    @entityFromToken
    def occurrence(self):
        return self._occurrenceToken

    @occurrence.setter
    def occurrence(self, newOccurrence:adsk.fusion.Occurrence):
        self._occurrenceToken = newOccurrence.entityToken

    @property
    @entityFromToken
    def selectedFace(self):
        return self._selectedFaceToken

    @selectedFace.setter
    def selectedFace(self, selected:adsk.fusion.BRepFace):
        logger.info('selectedFace {}'.format(selected.assemblyContext.name))
        if selected == self._selectedFace:
            return
        self.selectedFace = selected
        self.occurrence = selected.assemblyContext
        self.body = selected.body
        self.changed = True

    @property
    @entityFromToken
    def profile(self):
        return self._profileToken

    @profile.setter
    def profile(self, newProfile :adsk.fusion.Profile):
        self._profileToken = newProfile.entityToken

    @property
    @entityFromToken
    def jointOrigin(self):
        return self._jointOriginToken

    @jointOrigin.setter
    def jointOrigin(self, jointOrigin:adsk.fusion.JointOrigin):
        self._jointOriginToken = jointOrigin.entityToken

    @property
    def originPoint(self):
        return self.jointOrigin.geometry.origin

    @property
    def jointGeometry(self):
        return self._jointGeometry

    @property
    @entityFromToken
    def joint(self):
        return self._jointToken

    @joint.setter
    def joint(self, joint:adsk.fusion.Joint):
        self._jointToken = joint.entityToken

    @property
    def name(self):
        return self.occurrence.name

    @property
    def xOffset(self):
        return self._xOffset

class NestItem(NestStock):

    def __init__(self, occurrence, sourceOccurrence): #, stockObject:adsk.fusion.BRepFace
        super().__init__(occurrence, sourceOccurrence)
        logger.info("NestItem.init")

        self._xPositionOffset = 0
        self._yPositionOffset = 0
        self._angle = 0
        # self._stockObject = stockObject

    def addJoint(self):
        logger.info(f"NestItem.addJoint - {self.occurrence.name}/{self._stockObject.jointOrigin.name}")

        if self.occurrence.joints.itemByName('nest_O_'+self.occurrence.name):  #if joint already exists don't add another one
            return False

        logger.debug(f'bounding box before joint; {self.body.boundingBox.minPoint.x: 9.3f}; \
                                                {self.body.boundingBox.minPoint.y: 9.3f}; \
                                                {self.body.boundingBox.minPoint.z: 9.3f}; \
                                                {self.body.boundingBox.maxPoint.x: 9.3f}; \
                                                {self.body.boundingBox.maxPoint.y: 9.3f}; \
                                                {self.body.boundingBox.maxPoint.z: 9.3f}')

        self.joint = utils.createJoint(self.jointOrigin, self._stockObject.jointOrigin)
        self.joint.name = 'nest_J_' + self.occurrence.name

        tlOBject = self.joint.timelineObject

        # # adjust position of joint origin to be in the body centre of the face side - just in case face does not cover whole of body silhouette

        centreOffsetX, centreOffsetY, self._height = utils.centreOffsetsFromFace(self.selectedFace)

        logger.debug(f'faceJointOriginOffsets; {centreOffsetX: 9.3f}; {centreOffsetY: 9.3f}')

        self.jointOrigin.timelineObject.rollTo(True)

        self._jointGeometry.geometryOrOriginOne = self.jointOrigin
     
        self._jointGeometry.geometryOrOriginTwo = self._stockObject.jointOrigin
        
        self.jointOrigin.offsetX.value = centreOffsetX
        self.jointOrigin.offsetY.value = centreOffsetY
        self.jointOrigin.offsetZ.value = 0
        self.jointOrigin.timelineObject.rollTo(False)

        self.joint.timelineObject.rollTo(True)
        logger.debug(f'timeLine Marker at Joint adjustment {design.timeline.markerPosition}')
        self.joint.geometryOrOriginOne = self.jointOrigin
        self.joint.timelineObject.rollTo(False)
        self._xOffset = utils.getBoundingBoxExtent(self.body)/2

    def changeJoint(self):
        logger.info("NestItem.changeJoint - {}/{}".format(self.occurrence.name, self.stockObject.jointOrigin.name ))

        logger.debug(f'bounding box before joint; {self.body.boundingBox.minPoint.x: 9.3f}; \
                                                {self.body.boundingBox.minPoint.y: 9.3f}; \
                                                {self.body.boundingBox.minPoint.z: 9.3f}; \
                                                {self.body.boundingBox.maxPoint.x: 9.3f}; \
                                                {self.body.boundingBox.maxPoint.y: 9.3f}; \
                                                {self.body.boundingBox.maxPoint.z: 9.3f}')

        self.changeJointOrigin()

        self.joint.timelineObject.rollTo(True)
        self.joint.geometryOrOriginOne = self._jointOrigin
        self.joint.timelineObject.rollTo(False)

        centreOffsetX, centreOffsetY, self._height = utils.centreOffsetsFromFace(self.selectedFace)
 
        logger.debug(f'faceJointOriginOffsets; {centreOffsetX: 9.3f}; {centreOffsetY: 9.3f}')

        self.changeJointOrigin()

        self.jointOrigin.offsetX.value = centreOffsetX
        self.jointOrigin.offsetY.value = centreOffsetY
        self.jointOrigin.offsetZ.value = 0
        self.jointOrigin.timelineObject.rollTo(False)

        self.joint.timelineObject.rollTo(True)
        logger.debug(f'timeLine Marker at Joint adjustment {design.timeline.markerPosition}')
        self.joint.geometryOrOriginOne = self.jointOrigin
        self.joint.timelineObject.rollTo(False)
        self._xOffset = utils.getBoundingBoxExtent(self.body)/2

    @property
    def stock(self):
        return self._stockObject

    @property
    def xPositionOffset(self):  # gets the position of the bodyCentre joint origin relative to the centre of the stock
        return self._joint.jointMotion.primarySlideValue

    @xPositionOffset.setter
    def xPositionOffset(self, magnitude):
        self.joint.jointMotion.primarySlideValue = magnitude

    @property
    def yPositionOffset(self):  # gets the position of the bodyCentre joint origin relative to the centre of the stock
        return self.joint.jointMotion.secondarySlideValue

    @yPositionOffset.setter
    def yPositionOffset(self, magnitude):
        self._oint.jointMotion.secondarySlideValue = magnitude

    @property
    def angle(self):  # gets the position of the bodyCentre joint origin relative to the centre of the stock
        return self.joint.jointMotion.rotationValue

    @angle.setter
    def angle(self, angle):
        self.joint.jointMotion.rotationValue = angle
    
class NesterCommand:

    _spacing = None
    _offset = 0
    _flip = False

    def __init__(self, commandName, commandDescription, commandResources, cmdId, myWorkspace, myToolbarPanelID, nestFaces):
        logger.info("init")
        self.commandName = commandName
        self.commandDescription = commandDescription
        self.commandResources = commandResources
        self.cmdId = cmdId
        self.myWorkspace = myWorkspace
        self.myToolbarPanelID = myToolbarPanelID
        self.DC_CmdId = 'Show Hidden'
        self._nestFaces = nestFaces
        
        try:
            self.app = adsk.core.Application.get()
            self.ui = self.app.userInterface

        except:
            logger.exception('Couldn\'t get app or ui: {}'.format(traceback.format_exc()))


    def onRun(self):

        logger.info("onRun")

        app = adsk.core.Application.get()
        ui = app.userInterface

        allWorkspaces = ui.workspaces
        commandDefinitions_ = ui.commandDefinitions


        try:
            designWorkspace :adsk.core.Workspaces = allWorkspaces.itemById(DESIGN_WORKSPACE)

            nestWorkspace= allWorkspaces.itemById(NESTER_WORKSPACE)
            if not nestWorkspace:
                nestWorkspace = ui.workspaces.add('DesignProductType', 'NesterEnvironment', 'Nester', self.commandResources + '/nesterWorkspace' )

            try:
                self.savedTab = [t for t in designWorkspace.toolbarTabs if t.isActive][0]
            except IndexError:
                self.savedTab = None

            designTabPanels = designWorkspace.toolbarTabs.itemById('SolidTab').toolbarPanels

            #create nester start panel and button on design workspace tab
            startPanel = designTabPanels.itemById(self.cmdId +'_startPanel')

            if startPanel is None:
               startPanel = designTabPanels.add(self.cmdId + '_startPanel', 'Nest')

            startPanelControls_ = startPanel.controls
            startPanelControl_ = startPanelControls_.itemById(self.cmdId + '_start')
            
            if not startPanelControl_:
                startCommandDefinition_ = commandDefinitions_.itemById(self.cmdId + '_start')
                if not startCommandDefinition_:
                    startCommandDefinition_ = commandDefinitions_.addButtonDefinition(self.cmdId+'_start',
                                                                                        self.commandName+'_start', 
                                                                                        'Start Nester',
                                                                                        self.commandResources+'/start')
            self.onStartCreate(startCommandDefinition_.commandCreated)
            
            StartPanelControl_ = startPanelControls_.addCommand(startCommandDefinition_)
            StartPanelControl_.isPromoted = True

            #design workspace nester panel and button complete

            #now create Nester tab and panel 
            toolbarTabs = designWorkspace.toolbarTabs
            self.nesterTab_ :adsk.core.ToolbarTab = toolbarTabs.add(self.cmdId +'Tab', 'Nest')

            nesterTabPanels_ = self.nesterTab_.toolbarPanels
            nesterTabPanel_ = nesterTabPanels_.itemById(self.cmdId +'_TabPanel')

            if nesterTabPanel_ is None:
                nesterTabPanel_ = nesterTabPanels_.add(self.cmdId +'_TabPanel', 'Nester')
   
            nesterTabPanelControls_ = nesterTabPanel_.controls               
            nesterTabPanelControl_ = nesterTabPanelControls_.itemById(self.cmdId + "_TPCtrl")

            if not nesterTabPanelControl_:
                nesterCommandDefinition_ = commandDefinitions_.itemById(self.cmdId + "_TPCtrl")
                if not nesterCommandDefinition_:
                    nesterCommandDefinition_ = commandDefinitions_.addButtonDefinition(self.cmdId, 
                                                                                self.commandName, 
                                                                                self.commandDescription, 
                                                                                self.commandResources + '/nesterWorkspace')
            self.onCreate(nesterCommandDefinition_.commandCreated)

            nesterPanelControl_ = nesterTabPanelControls_.addCommand(nesterCommandDefinition_)
            nesterPanelControl_.isPromoted = True
            nesterPanelControl_.isVisible = False
    
            exportCommandDefinition_ = commandDefinitions_.itemById(self.cmdId+'_export')

            if not exportCommandDefinition_:
                exportCommandDefinition_ = commandDefinitions_.addButtonDefinition(self.cmdId+'_export', 
                                                                                    self.commandName+'_export', 
                                                                                    'export>dxf', 
                                                                                    self.commandResources+'/export')
            
            self.onExportCreate(exportCommandDefinition_.commandCreated)

            exportControl_ = nesterTabPanelControls_.addCommand(exportCommandDefinition_)
            exportControl_.isPromoted = True
            exportControl_.isVisible = True

            importCommandDefinition_ = commandDefinitions_.itemById(self.cmdId+'_import')

            if not importCommandDefinition_:
                importCommandDefinition_ = commandDefinitions_.addButtonDefinition(self.cmdId+'_import', 
                                                                                    self.commandName+'_import', 
                                                                                    'dxf>import', 
                                                                                    self.commandResources+'/import')
            self.onImportCreate(importCommandDefinition_.commandCreated)

            importPanelControl_ = nesterTabPanelControls_.addCommand(importCommandDefinition_)
            importPanelControl_.isPromoted = True

            finishTabPanel_ = self.nesterTab_.toolbarPanels.itemById(self.cmdId +'_FinishTabPanel')

            if finishTabPanel_ is None:
                finishTabPanel_ = self.nesterTab_.toolbarPanels.add(self.cmdId +'_FinishTabPanel', 'Finish Nester')

            finishTabPanelControls_ = finishTabPanel_.controls
            finishPanelControl_ = finishTabPanelControls_.itemById(self.cmdId + '_finish')
        
            if not finishPanelControl_:
                finishCommandDefinition_ = commandDefinitions_.itemById(self.cmdId + '_finish')
                if not finishCommandDefinition_:
                    finishCommandDefinition_ = commandDefinitions_.addButtonDefinition(self.cmdId+'_finish',
                                                                                        self.commandName+'_finish', 
                                                                                        'Finish Nester',
                                                                                        self.commandResources+'/finishOutcomeView')
                finishPanelControl_ = finishTabPanelControls_.addCommand(finishCommandDefinition_)

            finishPanelControl_.isPromoted = False
            finishPanelControl_.isPromotedByDefault = True
            finishPanelControl_.isVisible = False

            self.onFinishCreate(finishCommandDefinition_.commandCreated)

            self.onDocumentOpened(app.documentOpened)

            self.onDocumentSaving(app.documentSaving)

            self.onDocumentSaved(app.documentSaved)

            self.onDocumentCreated(app.documentCreated)

            self.onDocumentActivated(app.documentActivated)

            self.onDocumentDeactivated(app.documentDeactivated)

                
        except:
            logger.exception('AddIn Start Failed:' )

    def onStop(self):
        global handlers
        logger.info("Fusion360CommandBase.onStop")
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface

            nestTab = ui.allToolbarTabs.itemById(self.cmdId +'_Tab')
            designWorkspace = ui.workspaces.itemById(DESIGN_WORKSPACE)
            designWorkspace.activate()
            try:
                for tbPanel in nestTab.toolbarPanels:
                    if self.cmdId not in tbPanel.id:
                        continue
                    for dropDownControl in tbPanel.controls:
                        if self.cmdId not in dropDownControl.id:
                            continue
                        for control in dropDownControl.controls:
                            if self.cmdId not in control.id:
                                continue
                            logger.debug(f'{control.id} deleted  {control.deleteMe()}')
                        logger.debug(f'{dropDownControl.id} deleted  {dropDownControl.deleteMe()}')
                    logger.debug(f'{tbPanel.id}  deleted {tbPanel.deleteMe()}')
                logger.debug(f'{nestTab.id} deleted {nestTab.deleteMe()}')

            except AttributeError:
                pass

            cmdDef = [x for x in ui.commandDefinitions if self.cmdId in x.id]
            for x in cmdDef:
                logger.debug(f'{x.id} deleted {x.deleteMe()}')

            toolbarPanels = [x for x in ui.allToolbarPanels if self.cmdId in x.id]

            try:
                for panel in toolbarPanels:
                    panelControls = [x.controls for x in toolbarPanels]
                    for controls in panelControls:
                        for control in controls:
                            logger.debug(f'{control.id} deleted {control.deleteMe()}')
                        logger.debug(f'{controls.id} deleted {controls.deleteMe()}')
                    logger.debug(f'{panel.id} deleted {panel.deleteMe()}')
                
            except AttributeError:
                pass

            toolbarPanel_ = Fusion360CommandBase.toolbarPanelById_in_Workspace(self.myWorkspace, self.cmdId +'_Panel') 
            finishPanel_ = Fusion360CommandBase.toolbarPanelById_in_Workspace(self.myWorkspace, self.cmdId +'_FinishTabPanel') 
            startPanel_ = Fusion360CommandBase.toolbarPanelById_in_Workspace(self.myWorkspace, self.cmdId +'_startPanel') 
            
            commandControlPanel_ = Fusion360CommandBase.commandControlById_in_Panel(self.cmdId, toolbarPanel_) if toolbarPanel_ else None
            CommandDefinition_ = Fusion360CommandBase.commandDefinitionById(self.cmdId)

            exportCommandControlPanel_ = Fusion360CommandBase.commandControlById_in_Panel(self.cmdId+'_export', toolbarPanel_) if toolbarPanel_ else None
            exportCommandDefinition_ = Fusion360CommandBase.commandDefinitionById(self.cmdId+'_export') if toolbarPanel_ else None

            importCommandControlPanel_ = Fusion360CommandBase.commandControlById_in_Panel(self.cmdId+'_import', toolbarPanel_) if toolbarPanel_ else None
            importCommandDefinition_ = Fusion360CommandBase.commandDefinitionById(self.cmdId+'_import') if toolbarPanel_ else None

            finishCommandControlPanel_ = Fusion360CommandBase.commandControlById_in_Panel(self.cmdId+'_finish', finishPanel_) if finishPanel_ else None
            finishCommandDefinition_ = Fusion360CommandBase.commandDefinitionById(self.cmdId+'_finish') if finishPanel_ else None

            startCommandControlPanel_ = Fusion360CommandBase.commandControlById_in_Panel(self.cmdId+'_start', startPanel_) if startPanel_ else None
            startCommandDefinition_ = Fusion360CommandBase.commandDefinitionById(self.cmdId+'_start') if startPanel_ else None

            Fusion360CommandBase.destroyObject(commandControlPanel_)
            Fusion360CommandBase.destroyObject(CommandDefinition_)
            Fusion360CommandBase.destroyObject(exportCommandControlPanel_)
            Fusion360CommandBase.destroyObject(exportCommandDefinition_)
            Fusion360CommandBase.destroyObject(importCommandControlPanel_)
            Fusion360CommandBase.destroyObject(importCommandDefinition_)
            Fusion360CommandBase.destroyObject(finishCommandControlPanel_)
            Fusion360CommandBase.destroyObject(finishCommandDefinition_)
            Fusion360CommandBase.destroyObject(startCommandControlPanel_)
            Fusion360CommandBase.destroyObject(startCommandDefinition_)
            # Fusion360CommandBase.destroyObject

            for handler in handlers:
                event = handler.event
                if event:
                    logger.debug(f'{event.name} event removed: {event.remove(handler.handler)}')
            handlers = []


        except:
            logger.exception('AddIn Stop Failed: {}'.format(traceback.format_exc()))

    # def refreshObjects(self):
    #     nesterGroupAttrbs = design.attributes.itemsByGroup(NESTER_GROUP)
    #     for group in nesterGroupAttrbs:

            



    @eventHandler(adsk.core.CommandEventHandler)
    def onPreview(self,  args:adsk.core.CommandCreatedEventArgs):

        command  = args.command
        inputs = args.command.commandInputs

        logger.info("----------------NesterCommand.onPreview------------------")
        (objects, stockObject, spacing) = getInputs(command, inputs)
        self._nestFaces.spacing = spacing
        logger.debug('spacing; {}'.format(self._nestFaces.spacing))

        for stockObject in self._nestFaces.addedStock:
            logger.debug(f'working on added stockObjects: {stockObject.name}:{stockObject.tempId:d}')
            logger.debug('calling addJointOrigin; stockObject add loop')
            stockObject.addJointOrigin()
            stockObject.added = False

        for face in self._nestFaces.changedFaces:
            marker = design.timeline.markerPosition
            logger.debug(f'working on changed face: {face.name}:{face.tempId:d}')
            logger.debug(f'calling changeJointOrigin; face change loop')
            face.changeJoint()
            face.changed = False
            design.timeline.markerPosition = marker
    
        for face in self._nestFaces.addedFaces:
            logger.debug(f'working on adding face: {face.name}:{face.tempId:d}')
            logger.debug(f'calling addJointOrigin; face add loop')
            face.addJointOrigin()
            face.addJoint()
            face.added = False

        positionOffset = 0
        for stockObject in self._nestFaces._stockObjects:
            positionOffset += stockObject.xOffset
            for face in self._nestFaces.allFaces:
                logger.debug('working on position offset face; {}'.format(face.name))
                logger.debug('position offset before; {}'.format(positionOffset))
                positionOffset += self._nestFaces.spacing + face.xOffset
                logger.debug('new position offset after; {}'.format(positionOffset))
                face.xPositionOffset = positionOffset
                positionOffset += face.xOffset                
        
        args.isValidResult = True
        command.doExecute(False)
 
    @eventHandler(adsk.core.CommandEventHandler)
    def onDestroy(self, args:adsk.core.CommandEventArgs):
        logger.info("NesterCommand.onDestroy")

        command_ = args.firingEvent.sender
        inputs_ = command_.commandInputs
        reason_ = args.terminationReason

        logger.info(f'Command: {command_.parentCommandDefinition.id} destroyed')
        reasons = {0:"Unknown", 1:"OK", 2:"Cancelled", 3:"Aborted", 4:"PreEmpted Termination", 5:"Document closed"}
        logger.info("Reason for termination = " + reasons[reason_])

    @eventHandler(adsk.core.InputChangedEventHandler)
    def onInputChanged(self, args:adsk.core.InputChangedEventArgs):

        # args = args
        command = args.firingEvent.sender
        inputs = args.inputs
        changedInput = args.input 

        logger.info("NesterCommand.onInputChanged")

        if changedInput.id != command.parentCommandDefinition.id + '_selection' and changedInput.id != command.parentCommandDefinition.id + '_stockObject':
            return

        # Only interested in _selection and _stockObject inputs
        # because F360 doesn't make it obvious, we need to work out which specific selected faces have changed
        # activeSelections conglomerates all active command selections, so we need to differentiate between the stockObject and the selections.
        # there may be another way, but at the moment I can't find it.
                    
        activeSelections = self.ui.activeSelections.all #save active selections - selections are sensitive and fragile, any processing beyond just reading on live selections will destroy selection 
        bodySelections = self.ui.activeSelections.all
        neststockObjects = [stockObject.selectedFace for stockObject in self._nestFaces.stockObjects]
        nestFaces = [stockObject.selectedFace for stockObject in self._nestFaces.allFaces]

        if changedInput.id == command.parentCommandDefinition.id + '_stockObject':
            addedstockObjects = [stockObjectFace for stockObjectFace in activeSelections if (stockObjectFace not in neststockObjects) and (stockObjectFace not in nestFaces) ]
            logger.debug('added stockObjects {}'.format([x.assemblyContext.name for x in addedstockObjects]))
            removedstockObjects = [stockObjectFace for stockObjectFace in neststockObjects if stockObjectFace not in activeSelections ]
            logger.debug('removed stockObjects {}'.format([x.assemblyContext.name for x in removedstockObjects]))
            changedInput.commandInputs.itemById(command.parentCommandDefinition.id + '_selection').hasFocus = True
            for stockObject in addedstockObjects:
                if addedstockObjects:
                    self._nestFaces.addStock(stockObject)
                    # self.ui.activeSelections.all = activeSelections
                if removedstockObjects:
                    self._nestFaces.removeStock(stockObject)
                return

        #remove stock faces from selection collection
        for stockObjectFace in self._nestFaces.stockObjects:
            bodySelections.removeByItem(stockObjectFace.selectedFace)

        bodyList = [x.selectedFace.body for x in self._nestFaces._nestObjects]
        
        for stockObject in self._nestFaces.stockObjects:

            addedFaces = [face for face in bodySelections if face not in nestFaces ]
            logger.debug('added faces {[x.assemblyContext.name for x in addedFaces]}')
            removedFaces = [face for face in nestFaces if face not in bodySelections ]
            logger.debug(f'removed faces {[x.assemblyContext.name for x in removedFaces]}')

            #==============================================================================
            #            processing changes to face selections
            #==============================================================================            

            for face in removedFaces:
                #==============================================================================
                #         Faces have been removed
                #==============================================================================
                if self._flip:
                    faceObject = [o for o in self._nestFaces if o == face][0]
                    flippedFace = utils.getBottomFace(face)
                    faceObject.selectedFace = flippedFace
                    changedInput.addSelection(flippedFace)
                    self._flip = False
                    return
                self._nestFaces.remove(face)
                            
            for face in addedFaces:
            #==============================================================================
            #             Faces has been added 
            #==============================================================================
                     
                selectedFace = face
                if face != utils.getTopFace(face):
                     ui.activeSelections.removeByEntity(face)
                     selectedFace = utils.getTopFace(face)
                     changedInput.addSelection(selectedFace)

                faceObject = [o for o in self._nestFaces if o == selectedFace.body]

                if len(faceObject):
                    faceObject = faceObject[0]
                    if faceObject != face:
                        status = ui.activeSelections.removeByEntity(faceObject.selectedFace)
                        logger.debug(f'selection status {status} ')
                        faceObject.selectedFace = face
                        faceObject.changed = True
                        return

                self._nestFaces.add(selectedFace, stockObject)

            return

    @eventHandler(adsk.core.MouseEventHandler)
    def onMouseClick(self, args:adsk.core.MouseEventArgs):

        kbModifiers = args.keyboardModifiers

        logger.info("NesterCommand.onMouseClick")
        if kbModifiers != adsk.core.KeyboardModifiers.AltKeyboardModifier:
            self._flip = False
            return
        self._flip = True
        pass

    @eventHandler(adsk.core.CommandEventHandler)
    def onExecute(self, args):

        logger.info("NesterCommand.onExecute")

        command_ = args.command
        inputs_ = command_.commandInputs

        if not self._nestFaces.spacing:
            (objects, stockObject, spacing) = getInputs(command_, inputs_)
            self._nestFaces.spacing = spacing

    @eventHandler(adsk.core.CommandEventHandler)
    def onExportExecute(self, args:adsk.core.CommandEventArgs):
        command = args.command
        inputs = command.commandInputs

        logger.info("NesterCommand.onExportExecute")
        fileDialog = ui.createFileDialog()
        fileDialog.title = 'Export to Dxf'
        fileDialog.filter = '*.dxf'

        dlgResult = fileDialog.showSave()

        if dlgResult == adsk.core.DialogResults.DialogCancel:
            return

        filename = fileDialog.filename

        if design.snapshots.hasPendingSnapshot:
            design.snapshots.add() 
        sketch = rootComp.sketches.add(self._nestFaces.stockObjects[0].selectedFace)
        for stock in self._nestFaces.stockObjects:
            stock.profileEntities =sketch.project(stock.body)
        for entity in self._nestFaces._nestObjects:
            entity.profileEntities = sketch.project(entity.body)
            rotationProperty = entity.selectedFace.appearance.appearanceProperties.itemByName('Rotation')
            if rotationProperty:
                rotationAngle = rotationProperty.value
                
        s = sketch.saveAsDXF(filename)
        sketch.isVisible = True
        logger.debug(f'sketch save = {s} {filename}')

    @eventHandler(adsk.core.CommandEventHandler)
    def onImportExecute(self, args:adsk.core.CommandEventArgs):

        command = args.command
        inputs = command.commandInputs

        # baseFeats = rootComp.features.baseFeatures
        # baseFeat = baseFeats.add()
        logger.info("NesterCommand.onImportExecute")
        fileDialog = ui.createFileDialog()
        fileDialog.title = 'Import from Dxf'
        fileDialog.filter = '*.dxf'

        dlgResult = fileDialog.showOpen()

        if dlgResult == adsk.core.DialogResults.DialogCancel:
            return

        filename = fileDialog.filename

        importManager = app.importManager
        dxfOptions = importManager.createDXF2DImportOptions(filename, self._nestFaces.stockObjects[0].selectedFace)
        dxfOptions.isSingleSketchResult = True
        position = adsk.core.Point2D.create(3/8*2.54, -(self._nestFaces.stockObjects[0].xOffset*2 - 3/8*2.54))
        dxfOptions.position = position

        sketch = rootComp.sketches.itemByName('nestImport')
        if sketch:
            # sketch.timelineObject.rollTo(True)
            try:
                sketch.deleteMe()
                extrudeFeature = self._nestFaces.stockObjects[0].occurrence.component.features.itemByName('nestExtrude')
                extrudeFeature.deleteMe()
            except AttributeError:
                pass


        sketch = adsk.fusion.Sketch.cast(importManager.importToTarget2(dxfOptions, rootComp).item(0))
        sketch.name = 'nestImport'

        if design.snapshots.hasPendingSnapshot:
            design.snapshots.add() 
        tempBrepMgr = adsk.fusion.TemporaryBRepManager.get()
        nestedProfiles = sketch.profiles
        transformMatrix = adsk.core.Matrix3D.create()
        rotate90 = adsk.core.Matrix3D.create()
        xAxis = adsk.core.Vector3D.create(1,0,0)
        yAxis = adsk.core.Vector3D.create(0,1,0)
        zAxis = adsk.core.Vector3D.create(0,0,1)
        offsetVector = adsk.core.Vector3D.create(0,0,0)
        stockCentre = self._nestFaces.allFaces[0].stock.originPoint
        defaultUnits = design.unitsManager.defaultLengthUnits
        profileCurves = []
        # baseFeat.startEdit()

        faces = self._nestFaces.allFaces.copy()

        for nestedProfile in nestedProfiles:
 
            #check profile with each candidate face
            for face in faces:
                tmpFace = utils.getTmpFaceFromProjectedEntities(face.profileEntities, tempBrepMgr)
                if abs((nestedProfile.areaProperties().area - tmpFace.area))/nestedProfile.areaProperties().area*100 > 0.001:
                    continue  #areas don't match, so can't be the same profile - 
                logger.debug(f'working on {face.name}')
                tmpNestedFace = utils.getTmpFaceFromProfile(nestedProfile, tempBrepMgr)
                tempNestedCentre = utils.getCentrePoint(tmpNestedFace.faces.item(0))
                tmpFaceCentre = utils.getCentrePoint(tmpFace.faces.item(0))
                logger.debug(f'tmpFaceCentre: {tmpFaceCentre.asArray()}; faceCentre: {face.originPoint.asArray()}')
                transformMatrix.setToAlignCoordinateSystems(tmpFaceCentre, xAxis, yAxis,zAxis,  tempNestedCentre, xAxis,yAxis, zAxis)
                tempBrepMgr.transform(tmpFace, transformMatrix)
                tmpFaceCopy = tempBrepMgr.copy(tmpFace)
                for x in range(0, 3):
                    rotate90.setToRotation(90*x, zAxis, tempNestedCentre)
                    tempBrepMgr.transform(tmpFaceCopy, rotate90)
                    bodies = tempBrepMgr.booleanOperation(tmpFaceCopy, tmpNestedFace, adsk.fusion.BooleanTypes.DifferenceBooleanType)
                    logger.debug(f'rotation {x}; target {tmpFaceCopy.area}; tool {tmpNestedFace.area}')
                    if abs((tmpFaceCopy.area - tmpNestedFace.area))/tmpNestedFace.area*100 > 99.999 :
                        # centre = sketch.project(tempNestedCentre)
                        profileCurves.append((nestedProfile.profileLoops.item(0).profileCurves.item(0).sketchEntity, tmpFaceCentre))
                        logger.debug(f'rotation success - {face.name}')
                        faces.remove(face)
                        tempBrepMgr.transform(tmpFace, rotate90)
                        # dispBodies.add(tmpFace, baseFeat)
                        offsetVector = stockCentre.vectorTo(tempNestedCentre)
                        face.xPositionOffset = offsetVector.dotProduct(xAxis) 
                        face.yPositionOffset = offsetVector.dotProduct(yAxis)
                        face.angle  = x*math.pi/2
                        logger.debug(f'xPos: {face.xPositionOffset/2.54}; yPos: {face.yPositionOffset/2.54}; angle: {face.angle}')
                        break
                    tmpFaceCopy = tempBrepMgr.copy(tmpFace)
        # baseFeat.finishEdit()            

        if design.snapshots.hasPendingSnapshot:
            design.snapshots.add()

        stockComponent = adsk.fusion.Component.cast(self._nestFaces.stockObjects[0].selectedFace.body.parentComponent)
        loopCollection = adsk.core.ObjectCollection.create()
        # sketchProfiles = [p for p in sketch.profiles] 
        # logger.debug(f'sketchProfiles: {sketchProfiles}')
        for curve, centre in profileCurves:
            sketchLoopCurves = sketch.findConnectedCurves(curve)
            offsetloops = sketch.offset(sketchLoopCurves, centre, 1/4*2.54)
            # newProfile = stockComponent.createOpenProfile(offsetloops)
            loopCollection.add(offsetloops)
        profileCollection = adsk.core.ObjectCollection.create()
        for profile in sketch.profiles:
            for loop in profile.profileLoops:
                if loop.isOuter:
                    continue
            profileCollection.add(profile)

        zero = adsk.core.ValueInput.createByReal(0)
        start = adsk.fusion.FromEntityStartDefinition.create(self._nestFaces.stockObjects[0].selectedFace, zero)

        extrudeInput = rootComp.features.extrudeFeatures.createInput(profileCollection, adsk.fusion.FeatureOperations.CutFeatureOperation)
        extrudeInput.participantBodies = [stockComponent.bRepBodies.item(0)]
        heightVal = adsk.core.ValueInput.createByReal(self._nestFaces.stockObjects[0].height)
        height = adsk.fusion.DistanceExtentDefinition.create(heightVal)
        extrudeInput.setOneSideExtent(height,adsk.fusion.ExtentDirections.NegativeExtentDirection)
        extrudeInput.startExtent = start
        extrude = stockComponent.features.extrudeFeatures.add(extrudeInput)
        extrude.name = 'nestExtrude'


    @eventHandler(adsk.core.CommandCreatedEventHandler)
    def onCreate(self, args:adsk.core.CommandCreatedEventArgs):

        command = args.command
        inputs = command.commandInputs
        
        selectionstockObjectInput = inputs.addSelectionInput(command.parentCommandDefinition.id + '_stockObject',
                                                        'Select Base Face',
                                                        'Select Face to mate to')
        selectionstockObjectInput.setSelectionLimits(1,1)
        selectionstockObjectInput.addSelectionFilter('PlanarFaces')

        selectionInput = inputs.addSelectionInput(command.parentCommandDefinition.id + '_selection',
                                                'Select other faces',
                                                'Select bodies or occurrences')
        selectionInput.setSelectionLimits(1,0)
        selectionInput.addSelectionFilter('PlanarFaces')

        app = adsk.core.Application.get()
        product = app.activeProduct
        design = adsk.fusion.Design.cast(product)
        unitsMgr = design.unitsManager
        spacingInput = inputs.addValueInput(command.parentCommandDefinition.id + '_spacing', 'Component Spacing',
                                            unitsMgr.defaultLengthUnits,
                                            adsk.core.ValueInput.createByReal(2.54))

        if self._nestFaces.allFaces:
            for stock in self._nestFaces.stockObjects:
                selectionstockObjectInput.addSelection(stock.selectedFace)
            for face in self._nestFaces.allFaces:
                selectionInput.addSelection(face.selectedFace)
                selectionInput.hasFocus = True

        self.onExecute(command.execute) 

        self.onInputChanged(command.inputChanged)  

        self.onDestroy(command.destroy)            
        
        self.onPreview(command.executePreview) 

        self.onMouseClick(command.mouseClick)


    @eventHandler(adsk.core.CommandCreatedEventHandler)
    def onStartCreate(self, args:adsk.core.CommandCreatedEventArgs):

        command_ = args.command
        inputs_ = command_.commandInputs

        self.onStartExecute(command_.execute)

        self.onDestroy(command_.destroy)
                            
        logger.info('Finish Panel command created successfully')
        
        self.nesterTab_.activate()

    @eventHandler(adsk.core.CommandCreatedEventHandler)
    def onExportCreate(self, args:adsk.core.CommandCreatedEventArgs):

        command_ = args.command
        inputs_ = command_.commandInputs

        self.onExportExecute(command_.execute)


    @eventHandler(adsk.core.CommandCreatedEventHandler)
    def onImportCreate(self, args:adsk.core.CommandCreatedEventArgs):

        command_ = args.command
        inputs_ = command_.commandInputs
        
        self.onImportExecute(command_.execute)    

        self.onDestroy(command_.destroy)
                                    
        logger.info('Panel command created successfully')


    @eventHandler(adsk.core.CommandCreatedEventHandler)
    def onFinishCreate(self, args:adsk.core.CommandCreatedEventArgs):
        
        command_ = args.command
        inputs_ = command_.commandInputs
        
        tabPanels = self.nesterTab_.toolbarPanels
        self.savedTab.activate()
        rootOccurrences = [o for o in rootComp.occurrences if o.component.name != 'Manufacturing']
        for occurence in rootOccurrences:
            occurence.isLightBulbOn = True
        manufOccurrence = [o for o in rootComp.occurrences if o.component.name == 'Manufacturing'][0]
        manufOccurrence.isLightBulbOn = False

        design.activateRootComponent()

        self.onDestroy(command_.destroy)
                            
        logger.info('Finish Panel command created successfully')


    @eventHandler(adsk.core.CommandEventHandler)
    def onStartExecute(self, args:adsk.core.CommandEventArgs):

        command_ = args.command
        inputs_ = command_.commandInputs

        transform = adsk.core.Matrix3D.create()
        compNamesAtRoot = [c.component.name for c in rootComp.occurrences]
        manufOccurrence = [o for o in rootComp.occurrences if o.component.name == 'Manufacturing']
        if not manufOccurrence:
            manufOccurrence = rootComp.occurrences.addNewComponent(transform)
            manufOccurrence.component.name = 'Manufacturing'
        else:
            manufOccurrence = manufOccurrence[0]
        manufOccurrence.isLightBulbOn = True
 
        self.crawlAndCopy(rootComp, manufOccurrence)
        rootOccurrences = [o for o in rootComp.occurrences if o.component.name != 'Manufacturing']
        for occurence in rootOccurrences:
            occurence.isLightBulbOn = False
        manufOccurrence.activate()

    def crawlAndCopy(self, source, target:adsk.fusion.Occurrence):  
        #crawls the rootComponent structure and makes a copy of everything under Manufacturing root

        name = 'rootComp' if source == rootComp else source.fullPathName
        logger.debug(f'new call; parent: {name}; target: {target.fullPathName}')
        childOccurrences = rootComp.occurrences if source == rootComp else source.childOccurrences
        
        #List of all components that under root, except those under Manufacturing  
        sourceOccurrences = [o for o in childOccurrences if 'Manufacturing' not in o.component.name] 
        logger.debug(f'source occurrences: {[o.name for o in childOccurrences]}')

        for sourceOccurrence in sourceOccurrences:  #Work through each source occurrence
            logger.debug(f'Working on {sourceOccurrence.name}')
            logger.debug(f'{sourceOccurrence.name}: {sourceOccurrence.joints.count} joints')
            logger.debug(f'{sourceOccurrence.component.name}: {sourceOccurrence.component.joints.count} joints')
            newTargetOccurrence = None #target.childOccurrences.itemByName(childOccurrence.name)
            logger.debug(f'target sourceOccurrences: {[o.name for o in target.childOccurrences]}')

            for targetOccurrence in target.childOccurrences:
                try:
                    logger.debug(f'{targetOccurrence.name }; attribute count = {targetOccurrence.attributes.count}')
                    if  targetOccurrence.attributes.itemByName(NESTER_GROUP, NESTER_OCCURRENCES).value != sourceOccurrence.name:
                        continue
                except AttributeError:
                    continue
                logger.debug(f'matched: {sourceOccurrence.name} with {targetOccurrence.name }')
                newTargetOccurrence = targetOccurrence
                break
                    
            if not newTargetOccurrence:  
                #target doesn't exist 
                if not sourceOccurrence.childOccurrences:
                    # - add existing parent component if there's no child occurrences ie. it's a branch end
                    newTargetOccurrence = target.component.occurrences.addExistingComponent(sourceOccurrence.component, transform).createForAssemblyContext(target)
                    self._nestFaces.addComponent(newTargetOccurrence, sourceOccurrence)
                    logger.debug(f'Adding existing component {sourceOccurrence.component.name} to {target.name}')
                else:
                    # - add dummy component if there are child occurrences ie it's a node
                    newTargetOccurrence = target.component.occurrences.addNewComponent(transform).createForAssemblyContext(target)
                    newTargetOccurrence.component.name = sourceOccurrence.component.name + '_'
                    logger.debug(f'Adding dummy component {newTargetOccurrence.component.name} to {target.name}')
                logger.debug(f'added attribute {target.name} to {newTargetOccurrence.name}')
                attribute = newTargetOccurrence.attributes.add(NESTER_GROUP,NESTER_TOKENS, sourceOccurrence.name)

            if sourceOccurrence.childOccurrences:  #if the source component has children - then recurse component to find and process children 
                self.crawlAndCopy(sourceOccurrence, newTargetOccurrence)

            #no more children to process, so return


    @eventHandler(adsk.core.DocumentEventHandler)
    def onDocumentOpened(self, args:adsk.core.DocumentEventArgs):

        command = args.firingEvent.sender

        logger.debug(f'active Doc: {app.activeDocument.name}; from:{args.document.name};to:{command.activeDocument.name} - Document Opened')
        pass

    @eventHandler(adsk.core.DocumentEventHandler)
    def onDocumentSaving(self, args:adsk.core.DocumentEventArgs):

        command = args.firingEvent.sender

        logger.debug(f'active Doc: {app.activeDocument.name}; from:{args.document.name};to:{command.activeDocument.name} - Document Saving')
        pass

    @eventHandler(adsk.core.DocumentEventHandler)
    def onDocumentCreated(self, args:adsk.core.DocumentEventArgs):

        command = args.firingEvent.sender

        try:
            logger.debug(f'active Doc: {app.activeDocument.name}; from:{args.document.name};to:{command.activeDocument.name} - Document Created')
        except AttributeError:
            pass
        pass

    @eventHandler(adsk.core.DocumentEventHandler)
    def onDocumentSaved(self, args:adsk.core.DocumentEventArgs):

        command = args.firingEvent.sender

        logger.debug(f'active Doc: {app.activeDocument.name}; from:{args.document.name};to:{command.activeDocument.name} - Document Saved')

        presentDocVersion = args.document.name.rsplit(' ')[-1].split('v')[1]
        docVersionLen = len(presentDocVersion)
        docName = args.document.name[:-docVersionLen]
        nestFacesDict[docName + str(int(presentDocVersion)+1)] = nestFacesDict.pop(args.document.name, NestItems())

        pass

    @eventHandler(adsk.core.DocumentEventHandler)
    def onDocumentActivated(self, args:adsk.core.DocumentEventArgs):

        command = args.firingEvent.sender

        logger.debug(f'active Doc: {app.activeDocument.name}; from:{args.document.name};to:{command.activeDocument.name} - Document Activated')
        nestFaces = nestFacesDict.setdefault(command.activeDocument.name, NestItems())
        pass

    @eventHandler(adsk.core.DocumentEventHandler)
    def onDocumentDeactivated(self, args:adsk.core.DocumentEventArgs):
        command = args.firingEvent.sender

        logger.debug(f'from:{args.document.name};to:{command.activeDocument.name} - Document Deactivated')

        pass

# class OnCreateHandler(adsk.core.CommandCreatedEventHandler):
#     def __init__(self):
#         super().__init__()
#     def notify(self, args):
#         eventArgs :adsk.core.CommandEventArgs = args

#     # Code to react to the event.
#         app = adsk.core.Application.get()
#         des :adsk.fusion.Design = app.activeProduct

#         self.onCreate(eventArgs)       
    