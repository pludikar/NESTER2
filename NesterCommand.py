import adsk.core, adsk.fusion, traceback
import logging, os, sys, math

logger = logging.getLogger('Nester.command')
# logger.setLevel(logging.DEBUG)

from . import Fusion360CommandBase, utils
from  .common import nestFacesDict, handlers

app = adsk.core.Application.get()
ui = app.userInterface
product = app.activeProduct
design = adsk.fusion.Design.cast(product)

# Get the root component of the active design
rootComp = design.rootComponent

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
        elif inputI.id == command.parentCommandDefinition.id + '_plane':
            planeInput = inputI
        elif inputI.id == command.parentCommandDefinition.id + '_spacing':
            spacingInput = inputI
            spacing = spacingInput.value
        # elif inputI.id == command.parentCommandDefinition.id + '_edge':
        #     edgeInput = inputI
        elif inputI.id == command.parentCommandDefinition.id + '_subAssy':
            subAssyInput = inputI
            subAssy = subAssyInput.value

    objects = getSelectedObjects(selectionInput)
    plane = getSelectedObjects(planeInput)[0]
    # edge = adsk.fusion.BRepEdge.cast(edgeInput.selection(0).entity)

    if not objects or len(objects) == 0:
        # TODO this probably requires much better error handling
        return (objects, plane, spacing)
    # return(objects, plane, edge, spacing, subAssy)

    return (objects, plane, spacing)


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

class NestFaces():
    _document = app.activeDocument.name
    _faces =[]
    _planes = []
    _positionOffset = 0
    _spacing = 0
    _removedFaces = []
    _addedFaces = []
    _addedStock = []
    _removedStock = []


    def __iter__(self):
        for f in self._faces:
            yield f

    def __next__(self):
        for f in self._faces:
            yield f
            
    def add(self, selectedFace, planeFace):
        logger.info("NestFaces.add")
        if selectedFace in self._faces:
            return
        faceObject = NestFace(selectedFace, planeFace)
        self._faces.append(faceObject)
       
        return faceObject

    def remove(self, body):
        pass


    def addStock(self, selectedFace):
        logger.info("NestFaces.addStock")
        stock = NestStock(selectedFace)
        self._planes.append(stock)

    def removeStock(self, selectedFace):
        pass


    @property
    def planes(self):
        return self._planes

    @property
    def allFaces(self):
        return self._faces

    @property
    def addedStock(self):
        return [x for x in self._planes if x.added]

    @property
    def changedStock(self):
        return [x for x in self._planes if x.changed]

    @property
    def removedStock(self):
        return [x for x in self._planes if x.removed]

    @property
    def addedFaces(self):
        return [x for x in self._faces if x.added]

    @property
    def removedFaces(self):
        return [x for x in self._faces if x.removed]

    @property
    def changedFaces(self):
        return [x for x in self._faces if x.changed]
    
    def find(self, selectedEnity):
        return [face for face in self._faces if face == selectedEntity][0]  # this should work for both bRepFace and bRepBody

    def refreshOffsets(self):
        logger.info("NestFaces.refreshOffsets")
        for stock in self._planes:
            positionOffset = 0
            positionOffset += stock.offset

            for face in self._faces:
                positionOffset += self._spacing
                positionOffset += face.offset
                face.positionOffset = positionOffset
                # adsk.doEvents()

    @property
    def reset(self):
       self._faces = []
       self._planes = []
       self._positionOffset = 0
       self._spacing = 1

    @property
    def spacing(self):
        return self._spacing

    @spacing.setter
    def spacing(self, magnitude):
        self._spacing = magnitude

class NestStock():
    def __init__ (self, selectedFace:adsk.fusion.BRepFace):
        logger.info("NestStock.init")

        self._selectedFace = selectedFace
        self._body = selectedFace.body
        self._tempId = selectedFace.tempId
        self._occurrence = adsk.fusion.Occurrence.cast(selectedFace.assemblyContext)
        self._profileEntities = None
        self._joint = adsk.fusion.Joint.cast(None)
        self._jointGeometry = adsk.fusion.JointGeometry.cast(None)
        self._jointOrigin = adsk.fusion.JointOrigin.cast(None)
        self._xOffset = None
        self._yOffset = None
        self._angle = 0
        self._timelineObject = adsk.fusion.TimelineObject.cast(None)
        self._changed = False
        self._added = True
        self._removed = False

    def __eq__(self, other):
        if other.objectType == adsk.fusion.BRepFace.classType():
            return other == self._selectedFace
        elif other.objectType == adsk.fusion.BRepBody.classType():
            return other == self._body
        return NotImplemented

    def __neq__(self, other):
        if other.objectType == adsk.fusion.BRepFace.classType():
            return other != self._selectedFace
        elif other.objectType == adsk.fusion.BRepBody.classType():
            return other != self._body
        return NotImplemented

    def addJointOrigin(self):
        logger.info("NestStock.addJointOrigin - {}".format(self._occurrence.component.name))

        allOrigins = [x.name for x in self._occurrence.component.allJointOrigins]
        if 'nest_O_'+self._occurrence.component.name in allOrigins: #if joint already exists don't add another one
            return False

        self._xOffset = utils.getBoundingBoxExtent(self._body)/2
    
        # centreOffsetX, centreOffsetY, self._height = utils.centreOffsetsFromFace(utils.getTopFace(self._selectedFace))
        centreOffsetX, centreOffsetY, self._height = utils.centreOffsetsFromFace(self._selectedFace)
        
        logger.debug('faceJointOriginOffsets; {}; {}'.format(centreOffsetX, centreOffsetY))

        jointOrigins = self._occurrence.component.jointOrgins
        self._jointGeometry = adsk.fusion.JointGeometry.createByPlanarFace(self._selectedFace, None, adsk.fusion.JointKeyPointTypes.CenterKeyPoint)

        jointOriginInput = jointOrigins.createInput(self._jointGeometry)
        jointOriginInput.offsetX  = adsk.core.ValueInput.createByReal(centreOffsetX)
        jointOriginInput.offsetY = adsk.core.ValueInput.createByReal(centreOffsetY)

        jointOrigin = jointOrigins.add(jointOriginInput)

        self._jointOrigin = jointOrigin.createForAssemblyContext(self._occurrence)
        self._jointOrigin.name = 'nest_O_'+self._occurrence.component.name

    def changeJointOrigin(self):
        self._jointOrigin.timelineObject.rollTo(True)
        logger.info(f"NestStock.changeJointOrigin - {self._occurrence.component.name}")
        logger.debug(f"working on face: {self._selectedFace.tempId:d}")
  
        centreOffsetX, centreOffsetY, self._height = utils.centreOffsetsFromFace(self._selectedFace)
        
        logger.debug(f'faceJointOriginOffsets; {centreOffsetX:.3f}; {centreOffsetY:.3f}')

        self._jointGeometry = adsk.fusion.JointGeometry.createByPlanarFace(self._selectedFace, None, adsk.fusion.JointKeyPointTypes.CenterKeyPoint)

        self._jointOrigin.geometry = self._jointGeometry
        self._jointOrigin.offsetX.value = centreOffsetX
        self._jointOrigin.offsetY.value = centreOffsetY
        self._jointOrigin.timelineObject.rollTo(False)

        self._joint.timelineObject.rollTo(True)
        self._joint.geometryOrOriginOne = self._jointOrigin
        self._joint.timelineObject.rollTo(False)

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
    def face(self):
        return self._selectedFace

    @property
    def body(self):
        return self._body

    @property
    def height(self):
        return self._height

    @property
    def occurrence(self):
        return self._occurrence

    @property
    def joint(self):
        return self._joint

    @joint.setter
    def joint(self, newJoint):
        self._joint = newJoint

    @property
    def selectedFace(self):
        return self._selectedFace

    @selectedFace.setter
    def selectedFace(self, selected:adsk.fusion.BRepFace):
        logger.info('selectedFace {}'.format(selected.assemblyContext.name))
        if selected == self._selectedFace:
            return
        self._selectedFace = selected
        self._occurrence = selected.assemblyContext
        self._body = selected.body
        self._tempId = selected.tempId
        self._changed = True

    @property
    def tempId(self):
        return self._tempId

    @property
    def profileEntities(self):
        return self._profileEntities

    @profileEntities.setter
    def profileEntities(self, newProfile):
        self._profileEntities = newProfile

    @property
    def jointOrigin(self):
        return self._jointOrigin

    @property
    def originPoint(self):
        return self._jointOrigin.geometry.origin

    @property
    def jointGeometry(self):
        return self._jointGeometry

    @property
    def joint(self):
        return self._joint

    @property
    def name(self):
        return self._occurrence.name

    @property
    def xOffset(self):
        return self._xOffset

class NestFace(NestStock):

    def __init__(self, selectedFace, plane):
        super().__init__(selectedFace)
        logger.info("NestFace.init")

        self._xPositionOffset = 0
        self._yPositionOffset = 0
        self._angle = 0
        self._plane = plane

    def addJoint(self):
        logger.info("NestFace.addJoint - {}/{}".format(self._occurrence.name, self._plane.jointOrigin.name ))

        if self._occurrence.joints.itemByName('nest_O_'+self._occurrence.name):  #if joint already exists don't add another one
            return False

        logger.debug(f'bounding box before joint; {self._body.boundingBox.minPoint.x:.3f}; \
                                                {self._body.boundingBox.minPoint.y:.3f}; \
                                                {self._body.boundingBox.minPoint.z:.3f}; \
                                                {self._body.boundingBox.maxPoint.x:.3f}; \
                                                {self._body.boundingBox.maxPoint.y:.3f}; \
                                                {self._body.boundingBox.maxPoint.z:.3f}')

        self._joint = utils.createJoint(self._jointOrigin, self._plane.jointOrigin)
        self._joint.name = 'nest_J_' + self._occurrence.name

        tlOBject = self._joint.timelineObject

        # # adjust position of joint origin to be in the body centre of the face side - just in case face does not cover whole of body silhouette

        centreOffsetX, centreOffsetY, self._height = utils.centreOffsetsFromFace(self._selectedFace)

        logger.debug(f'faceJointOriginOffsets; {centreOffsetX:.3f}; {centreOffsetY:.3f}')

        self._jointOrigin.timelineObject.rollTo(True)

        self._jointGeometry.geometryOrOriginOne = self._jointOrigin
     
        self._jointGeometry.geometryOrOriginTwo = self._plane.jointOrigin
        
        self._jointOrigin.offsetX.value = centreOffsetX
        self._jointOrigin.offsetY.value = centreOffsetY
        self._jointOrigin.offsetZ.value = 0
        self._jointOrigin.timelineObject.rollTo(False)

        self._joint.timelineObject.rollTo(True)
        logger.debug(f'timeLine Marker at Joint adjustment {design.timeline.markerPosition}')
        self._joint.geometryOrOriginOne = self._jointOrigin
        self._joint.timelineObject.rollTo(False)
        self._xOffset = utils.getBoundingBoxExtent(self._body)/2

    def changeJoint(self):
        logger.info("NestFace.changeJoint - {}/{}".format(self._occurrence.name, self._plane.jointOrigin.name ))

        logger.debug(f'bounding box before joint; {self._body.boundingBox.minPoint.x:.3f}; \
                                                {self._body.boundingBox.minPoint.y:.3f}; \
                                                {self._body.boundingBox.minPoint.z:.3f}; \
                                                {self._body.boundingBox.maxPoint.x:.3f}; \
                                                {self._body.boundingBox.maxPoint.y:.3f}; \
                                                {self._body.boundingBox.maxPoint.z:.3f}')

        self.changeJointOrigin()

        self._joint.timelineObject.rollTo(True)
        self._joint.geometryOrOriginOne = self._jointOrigin
        self._joint.timelineObject.rollTo(False)

        centreOffsetX, centreOffsetY, self._height = utils.centreOffsetsFromFace(self._selectedFace)
 
        logger.debug(f'faceJointOriginOffsets; {centreOffsetX:.3f}; {centreOffsetY:.3f}')

        self.changeJointOrigin()

        self._jointOrigin.offsetX.value = centreOffsetX
        self._jointOrigin.offsetY.value = centreOffsetY
        self._jointOrigin.offsetZ.value = 0
        self._jointOrigin.timelineObject.rollTo(False)

        self._joint.timelineObject.rollTo(True)
        logger.debug(f'timeLine Marker at Joint adjustment {design.timeline.markerPosition}')
        self._joint.geometryOrOriginOne = self._jointOrigin
        self._joint.timelineObject.rollTo(False)
        self._xOffset = utils.getBoundingBoxExtent(self._body)/2

    @property
    def stock(self):
        return self._plane

    @property
    def xPositionOffset(self):  # gets the position of the bodyCentre joint origin relative to the centre of the stock
        return self._joint.jointMotion.primarySlideValue

    @xPositionOffset.setter
    def xPositionOffset(self, magnitude):
        self._joint.jointMotion.primarySlideValue = magnitude

    @property
    def yPositionOffset(self):  # gets the position of the bodyCentre joint origin relative to the centre of the stock
        return self._joint.jointMotion.secondarySlideValue

    @yPositionOffset.setter
    def yPositionOffset(self, magnitude):
        self._joint.jointMotion.secondarySlideValue = magnitude

    @property
    def angle(self):  # gets the position of the bodyCentre joint origin relative to the centre of the stock
        return self._joint.jointMotion.rotationValue

    @angle.setter
    def angle(self, angle):
        self._joint.jointMotion.rotationValue = angle
    
class NesterCommand(Fusion360CommandBase.Fusion360CommandBase):
    # _nestFaces = NestFaces()
    _spacing = None
    _offset = 0
    _flip = False

    def onPreview(self, command:adsk.core.Command, inputs, args):
        logger.info("----------------NesterCommand.onPreview------------------")
        (objects, plane, spacing) = getInputs(command, inputs)
        self._nestFaces.spacing = spacing
        logger.debug('spacing; {}'.format(self._nestFaces.spacing))

        for plane in self._nestFaces.addedStock:
            logger.debug(f'working on added planes: {plane.name}:{plane.tempId:d}')
            logger.debug('calling addJointOrigin; plane add loop')
            plane.addJointOrigin()
            plane.added = False

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
        for plane in self._nestFaces._planes:
            positionOffset += plane.xOffset
            for face in self._nestFaces.allFaces:
                logger.debug('working on position offset face; {}'.format(face.name))
                logger.debug('position offset before; {}'.format(positionOffset))
                positionOffset += self._nestFaces.spacing + face.xOffset
                logger.debug('new position offset after; {}'.format(positionOffset))
                face.xPositionOffset = positionOffset
                positionOffset += face.xOffset                
        
        args.isValidResult = True
        command.doExecute(False)
 
    def onDestroy(self, command, inputs, reason_):
        logger.info("NesterCommand.onDestroy")
        # self._nestFaces.reset


    def onInputChanged(self, command, inputs:adsk.core.CommandInputs, changedInput:adsk.core.CommandInput):
        logger.info("NesterCommand.onInputChanged")

        if changedInput.id != command.parentCommandDefinition.id + '_selection' and changedInput.id != command.parentCommandDefinition.id + '_plane':
            return

        # Only interested in _selection and _plane inputs
        # because F360 doesn't make it obvious, we need to work out which specific selected faces have changed
        # activeSelections conglomerates all active command selections, so we need to differentiate between the plane and the selections.
        # there may be another way, but at the moment I can't find it.
                    
        activeSelections = self.ui.activeSelections.all #save active selections - selections are sensitive and fragile, any processing beyond just reading on live selections will destroy selection 
        bodySelections = self.ui.activeSelections.all
        nestPlanes = [plane.selectedFace for plane in self._nestFaces.planes]
        nestFaces = [plane.selectedFace for plane in self._nestFaces.allFaces]

        if changedInput.id == command.parentCommandDefinition.id + '_plane':
            addedPlanes = [planeFace for planeFace in activeSelections if (planeFace not in nestPlanes) and (planeFace not in nestFaces) ]
            logger.debug('added planes {}'.format([x.assemblyContext.name for x in addedPlanes]))
            removedPlanes = [planeFace for planeFace in nestPlanes if planeFace not in activeSelections ]
            logger.debug('removed planes {}'.format([x.assemblyContext.name for x in removedPlanes]))
            changedInput.commandInputs.itemById(command.parentCommandDefinition.id + '_selection').hasFocus = True
            for plane in addedPlanes:
                if addedPlanes:
                    self._nestFaces.addStock(plane)
                    # self.ui.activeSelections.all = activeSelections
                if removedPlanes:
                    self._nestFaces.removeStock(plane)
                return

        #remove stock faces from selection collection
        for planeFace in self._nestFaces.planes:
            bodySelections.removeByItem(planeFace.selectedFace)

        bodyList = [x.selectedFace.body for x in self._nestFaces._faces]
        
        for plane in self._nestFaces.planes:

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

                self._nestFaces.add(selectedFace, plane)


            return

    def onMouseClick(self, kbModifiers, command, inputs):
        logger.info("NesterCommand.onMouseClick")
        if kbModifiers != adsk.core.KeyboardModifiers.AltKeyboardModifier:
            self._flip = False
            return
        self._flip = True
        pass

    def onExecute(self, command, inputs):
        logger.info("NesterCommand.onExecute")

        # design.snapshots.add()

        if not self._nestFaces.spacing:
            (objects, plane, spacing) = getInputs(command, inputs)
            self._nestFaces.spacing = spacing

    def onExportExecute(self, command, inputs):
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
        sketch = rootComp.sketches.add(self._nestFaces.planes[0].selectedFace)
        for stock in self._nestFaces.planes:
            stock.profileEntities =sketch.project(stock.body)
        for entity in self._nestFaces._faces:
            entity.profileEntities = sketch.project(entity.body)
        s = sketch.saveAsDXF(filename)
        sketch.isVisible = True
        logger.debug(f'sketch save = {s} {filename}')

    def onImportExecute(self, command, inputs):
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
        dxfOptions = importManager.createDXF2DImportOptions(filename, self._nestFaces.planes[0].selectedFace)
        dxfOptions.isSingleSketchResult = True
        position = adsk.core.Point2D.create(3/8*2.54, -(self._nestFaces.planes[0].xOffset*2 - 3/8*2.54))
        dxfOptions.position = position

        sketch = rootComp.sketches.itemByName('nestImport')
        if sketch:
            # sketch.timelineObject.rollTo(True)
            try:
                sketch.deleteMe()
                extrudeFeature = self._nestFaces.planes[0].occurrence.component.features.itemByName('nestExtrude')
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
        for nestedProfile in nestedProfiles:
 
            faces = self._nestFaces.allFaces.copy()
            #check profile with each candidate face
            while len(faces):
                face = faces.pop()
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
                    rotate90.setToRotation(math.pi/2*x, zAxis, tempNestedCentre)
                    tempBrepMgr.transform(tmpFaceCopy, rotate90)
                    bodies = tempBrepMgr.booleanOperation(tmpFaceCopy, tmpNestedFace, adsk.fusion.BooleanTypes.DifferenceBooleanType)
                    logger.debug(f'rotation {x}; target {tmpFaceCopy.area}; tool {tmpNestedFace.area}')
                    if abs((tmpFaceCopy.area - tmpNestedFace.area))/tmpNestedFace.area*100 > 99.999 :
                        # centre = sketch.project(tempNestedCentre)
                        profileCurves.append((nestedProfile.profileLoops.item(0).profileCurves.item(0).sketchEntity, tmpFaceCentre))
                        logger.debug(f'rotation success - {face.name}')
                        tempBrepMgr.transform(tmpFace, rotate90)
                        # dispBodies.add(tmpFace, baseFeat)
                        offsetVector = stockCentre.vectorTo(tempNestedCentre)
                        face.xPositionOffset = offsetVector.dotProduct(xAxis) 
                        face.yPositionOffset = offsetVector.dotProduct(yAxis)
                        face.angle  = x*math.pi/2
                        logger.debug(f'xPos: {face.xPositionOffset}; yPos: {face.yPositionOffset}; angle: {face.angle}')
                        break
                    tmpFaceCopy = tempBrepMgr.copy(tmpFace)
        # baseFeat.finishEdit()            

        if design.snapshots.hasPendingSnapshot:
            design.snapshots.add()

        stockComponent = adsk.fusion.Component.cast(self._nestFaces.planes[0].selectedFace.body.parentComponent)
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
        start = adsk.fusion.FromEntityStartDefinition.create(self._nestFaces.planes[0].selectedFace, zero)

        extrudeInput = rootComp.features.extrudeFeatures.createInput(profileCollection, adsk.fusion.FeatureOperations.CutFeatureOperation)
        extrudeInput.participantBodies = [stockComponent.bRepBodies.item(0)]
        heightVal = adsk.core.ValueInput.createByReal(self._nestFaces.planes[0].height)
        height = adsk.fusion.DistanceExtentDefinition.create(heightVal)
        extrudeInput.setOneSideExtent(height,adsk.fusion.ExtentDirections.NegativeExtentDirection)
        extrudeInput.startExtent = start
        extrude = stockComponent.features.extrudeFeatures.add(extrudeInput)
        extrude.name = 'nestExtrude'



    def onCreate(self, command, inputs:adsk.core.CommandInputs):
        selectionPlaneInput = inputs.addSelectionInput(command.parentCommandDefinition.id + '_plane',
                                                        'Select Base Face',
                                                        'Select Face to mate to')
        selectionPlaneInput.setSelectionLimits(1,1)
        selectionPlaneInput.addSelectionFilter('PlanarFaces')

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
            for stock in self._nestFaces.planes:
                selectionPlaneInput.addSelection(stock.selectedFace)
            for face in self._nestFaces.allFaces:
                selectionInput.addSelection(face.selectedFace)
                selectionInput.hasFocus = True

    def onExportCreate(self, command, inputs:adsk.core.CommandInputs):
        pass

    def onImportCreate(self, command, inputs:adsk.core.CommandInputs):
        pass

    def onFinishCreate(self, command, inputs:adsk.core.CommandInputs):
        self.toolbarTab_.isVisible = False
        self.savedTab.activate()
        rootOccurrences = [o for o in rootComp.occurrences if o.component.name != 'Manufacturing']
        for occurence in rootOccurrences:
            occurence.isLightBulbOn = True
        manufOccurrence = [o for o in rootComp.occurrences if o.component.name == 'Manufacturing'][0]
        manufOccurrence.isLightBulbOn = False

        design.activateRootComponent()

    def onStartCreate(self, command:adsk.core.Command, inputs:adsk.core.CommandInputs):
        # self.toolbarTab_.isVisible = False
        self.toolbarTab_.activate()
        # command.doExecute()

    def onStartExecute(self, command, inputs:adsk.core.CommandInputs):
        # self.toolbarTab_.isVisible = False
        transform = adsk.core.Matrix3D.create()
        compNamesAtRoot = [c.component.name for c in rootComp.occurrences]
        manufOccurrence = [o for o in rootComp.occurrences if o.component.name == 'Manufacturing']
        if not manufOccurrence:
            manufOccurrence = rootComp.occurrences.addNewComponent(transform)
            manufOccurrence.component.name = 'Manufacturing'
        else:
            manufOccurrence = manufOccurrence[0]
        manufOccurrence.isLightBulbOn = True
 
        utils.crawlAndCopy(rootComp, manufOccurrence)
        rootOccurrences = [o for o in rootComp.occurrences if o.component.name != 'Manufacturing']
        for occurence in rootOccurrences:
            occurence.isLightBulbOn = False
        manufOccurrence.activate()

    def onDocumentOpened(self, command, args):
        logger.debug(f'active Doc: {app.activeDocument.name}; from:{args.document.name};to:{command.activeDocument.name} - Document Opened')
        pass

    def onDocumentSaving(self, command, args):
        logger.debug(f'active Doc: {app.activeDocument.name}; from:{args.document.name};to:{command.activeDocument.name} - Document Saving')
        pass

    def onDocumentCreated(self, command, args):
        try:
            logger.debug(f'active Doc: {app.activeDocument.name}; from:{args.document.name};to:{command.activeDocument.name} - Document Created')
        except AttributeError:
            pass
        pass

    def onDocumentSaved(self, command, args):
        logger.debug(f'active Doc: {app.activeDocument.name}; from:{args.document.name};to:{command.activeDocument.name} - Document Saved')
        presentDocVersion = args.document.name.rsplit(' ')[-1].split('v')[1]
        docVersionLen = len(presentDocVersion)
        docName = args.document.name[:-docVersionLen]
        nestFacesDict[docName + str(int(presentDocVersion)+1)] = nestFacesDict.pop(args.document.name, NestFaces())

        pass

    def onDocumentActivated(self, command, args):
        logger.debug(f'active Doc: {app.activeDocument.name}; from:{args.document.name};to:{command.activeDocument.name} - Document Activated')
        nestFaces = nestFacesDict.setdefault(command.activeDocument.name, NestFaces())
        pass

    def onDocumentDeactivated(self, command:adsk.core.ApplicationCommandEventArgs, args):
        logger.debug(f'from:{args.document.name};to:{command.activeDocument.name} - Document Deactivated')
        pass

    