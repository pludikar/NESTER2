import adsk.core, adsk.fusion, traceback
import logging, os, sys, math
import json

logger = logging.getLogger('Nester.NesterCommand')
# logger.setLevel(logging.DEBUG)

from .constants import *
from .common import entityFromToken, eventHandler, handlers
from .common import utils
from .NestItems import NestItems

from . import Fusion360CommandBase #, utils

if debugging:
    import importlib
    importlib.reload(Fusion360CommandBase)
    importlib.reload(utils)

# Get the root component of the active design
rootComp = design.rootComponent

# Utility casts various inputs into appropriate Fusion 360 Objects
class NesterCommand:
    ''' Creates command interface 

    '''

    _spacing = None
    _offset = 0
    _flip = False

    def __init__(self, commandName, commandDescription, commandResources, cmdId, myWorkspace, myToolbarPanelID):
        logger.info("init")
        self.commandName = commandName
        self.commandDescription = commandDescription
        self.commandResources = commandResources
        self.cmdId = cmdId
        self.myWorkspace = myWorkspace
        self.myToolbarPanelID = myToolbarPanelID
        self.DC_CmdId = 'Show Hidden'
        self._nestItemsDict = {}
        self._nestItems = self._nestItemsDict.setdefault(app.activeDocument.name, NestItems())
        
        try:
            self.app = adsk.core.Application.get()
            self.ui = self.app.userInterface

        except:
            logger.exception('Couldn\'t get app or ui: {}'.format(traceback.format_exc()))

    def setNestDocument(self):
        self._nestItems = self._nestItemsDict.setdefault(app.activeDocument.name, NestItems())

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
                    try:
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
                    except AttributeError:
                        continue
                logger.debug(f'{nestTab.id} deleted {nestTab.deleteMe()}')
            except AttributeError:
                pass

            cmdDef = [x for x in ui.commandDefinitions if self.cmdId in x.id]
            for x in cmdDef:
                logger.debug(f'{x.id} deleted {x.deleteMe()}')

            toolbarPanels = [x for x in ui.allToolbarPanels if self.cmdId in x.id]

            for panel in toolbarPanels:
                try:
                    panelControls = [x.controls for x in toolbarPanels]
                    for controls in panelControls:
                        for control in controls:
                            logger.debug(f'{control.name} deleted {control.deleteMe()}')
                        logger.debug(f'{controls.name} deleted {controls.deleteMe()}')
                    logger.debug(f'{panel.id} deleted {panel.deleteMe()}')
                
                except AttributeError:
                    logger.exception(f'deleting control panel {panel}{control}')
                    continue

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


    @eventHandler(adsk.core.CommandEventHandler)
    def onPreview(self,  args:adsk.core.CommandCreatedEventArgs):

        command  = args.command
        inputs = args.command.commandInputs

        logger.info("----------------NesterCommand.onPreview------------------")
        (objects, stockObject, spacing) = utils.getInputs(command, inputs)
        self._nestItems.spacing = spacing
        logger.debug('spacing; {}'.format(self._nestItems.spacing))

        for stockObject in self._nestItems.addedStock:
            logger.debug(f'working on added stockObjects: {stockObject.name}')
            logger.debug('calling addJointOrigin; stockObject add loop')
            stockObject.addJointOrigin()
            stockObject.added = False

        for face in self._nestItems.changedFaces:
            marker = design.timeline.markerPosition
            logger.debug(f'working on changed face: {face.name}')
            logger.debug(f'calling changeJointOrigin; face change loop')
            face.changeJoint()
            face.changed = False
            design.timeline.markerPosition = marker
    
        for face in self._nestItems.addedFaces:
            logger.debug(f'working on adding face: {face.name}')
            logger.debug(f'calling addJointOrigin; face add loop')
            face.addJointOrigin()
            face.addJoint()
            face.added = False

        positionOffset = 0
        for stockObject in self._nestItems._stockObjects:
            positionOffset += stockObject.xOffset
            for face in self._nestItems.allFaces:
                logger.debug('working on position offset face; {}'.format(face.name))
                logger.debug('position offset before; {}'.format(positionOffset))
                positionOffset += self._nestItems.spacing + face.xOffset
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
        nestStockFaces = self._nestItems.allStockFaces #[stockObject.selectedFace for stockObject in self._nestItems.stockObjects]
        nestFaces = self._nestItems.allItemFaces #[stockObject.selectedFace for stockObject in self._nestItems.allFaces if stockObject.selectedFace]

        if changedInput.id == command.parentCommandDefinition.id + '_stockObject':
            addedstockFaces:adsk.fusion.BRepFaces = [stockObjectFace for stockObjectFace in activeSelections if (stockObjectFace not in nestStockFaces) and (stockObjectFace not in nestFaces) ]
            logger.debug('added stockObjects {}'.format([x.assemblyContext.name for x in addedstockFaces]))
            removedstockFaces = [stockObjectFace for stockObjectFace in nestStockFaces if stockObjectFace not in activeSelections ]
            logger.debug('removed stockObjects {}'.format([x.assemblyContext.name for x in removedstockFaces]))
            changedInput.commandInputs.itemById(command.parentCommandDefinition.id + '_selection').hasFocus = True
            for stockFace in addedstockFaces:
                stockObject = self._nestItems.getStock(stockFace)
                if addedstockFaces:
                    stockObject.selectedFace =  stockFace #self._nestItems.addStock(stockFace)
                    # self.ui.activeSelections.all = activeSelections
                if removedstockFaces:
                    self._nestItems.removeStock(stockFace.assemblyContext)
            return

        #remove stock faces from selection collection
        for stockObjectFace in self._nestItems.stockObjects:
            bodySelections.removeByItem(stockObjectFace.selectedFace)


#TODO
        bodyList = [x.selectedFace.body for x in self._nestItems.nestObjects if x.selectedFace] 
        for stockObject in self._nestItems.stockObjects:

            addedFaces = [face for face in bodySelections if face not in nestFaces ]
            logger.debug(f'added faces {[x.assemblyContext.name for x in addedFaces]}')
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
                    faceObject = [o for o in self._nestItems if o == face][0]
                    flippedFace = utils.getBottomFace(face)
                    faceObject.selectedFace = flippedFace
                    changedInput.addSelection(flippedFace)
                    self._flip = False
                    return
                self._nestItems.remove(face)
                            
            for face in addedFaces:
            #==============================================================================
            #             Faces has been added 
            #==============================================================================
                     
                selectedFace = face
                if face != utils.getTopFace(face):  #if face is other than topface on same body, then swap out existing face with new face
                     ui.activeSelections.removeByEntity(face)
                     selectedFace = utils.getTopFace(face)
                     changedInput.addSelection(selectedFace)

                faceObject = self._nestItems.get(face, NestItem)

                if len(faceObject):
                    faceObject = faceObject[0]
                    if faceObject != face:
                        try:
                            status = ui.activeSelections.removeByEntity(faceObject.selectedFace)
                            logger.debug(f'selection status {status} ')
                        except RuntimeError:
                            pass                            
                        faceObject.selectedFace = face
                        faceObject.changed = True
                        return

                self._nestItems.add(selectedFace, stockObject)

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

        if not self._nestItems.spacing:
            (objects, stockObject, spacing) = utils.getInputs(command_, inputs_)
            self._nestItems.spacing = spacing

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
        sketch = rootComp.sketches.add(self._nestItems.stockObjects[0].selectedFace)
        for stock in self._nestItems.stockObjects:
            stock.profileEntities =sketch.project(stock.body)
        for entity in self._nestItems._nestObjects:
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
        dxfOptions = importManager.createDXF2DImportOptions(filename, self._nestItems.stockObjects[0].selectedFace)
        dxfOptions.isSingleSketchResult = True
        position = adsk.core.Point2D.create(3/8*2.54, -(self._nestItems.stockObjects[0].xOffset*2 - 3/8*2.54))
        dxfOptions.position = position

        sketch = rootComp.sketches.itemByName('nestImport')
        if sketch:
            # sketch.timelineObject.rollTo(True)
            try:
                sketch.deleteMe()
                extrudeFeature = self._nestItems.stockObjects[0].occurrence.component.features.itemByName('nestExtrude')
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
        stockCentre = self._nestItems.allFaces[0].stock.originPoint
        defaultUnits = design.unitsManager.defaultLengthUnits
        profileCurves = []
        # baseFeat.startEdit()

        faces = self._nestItems.allFaces.copy()

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

        stockComponent = adsk.fusion.Component.cast(self._nestItems.stockObjects[0].selectedFace.body.parentComponent)
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
        start = adsk.fusion.FromEntityStartDefinition.create(self._nestItems.stockObjects[0].selectedFace, zero)

        extrudeInput = rootComp.features.extrudeFeatures.createInput(profileCollection, adsk.fusion.FeatureOperations.CutFeatureOperation)
        extrudeInput.participantBodies = [stockComponent.bRepBodies.item(0)]
        heightVal = adsk.core.ValueInput.createByReal(self._nestItems.stockObjects[0].height)
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

        try:
            for stockFace in self._nestItems.allStockFaces:
                selectionstockObjectInput.addSelection(stockFace)
            for face in self._nestItems.allItemFaces:
                selectionInput.addSelection(face)
                selectionInput.hasFocus = True
        except RuntimeError:
            pass
        except AttributeError:
            pass

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
        # compNamesAtRoot = [c.component.name for c in rootComp.occurrences]
        manufOccurrence = [o for o in rootComp.occurrences if o.component.name == 'Manufacturing']
        if not manufOccurrence:
            manufOccurrence = rootComp.occurrences.addNewComponent(transform)
            manufOccurrence.component.name = 'Manufacturing'
        else:
            manufOccurrence = manufOccurrence[0]  #will take 1st instance of Manufacturing - TODO what if there is more?

        # nestTreeAttributes = design.findAttributes(NESTER_GROUP, NESTER_TYPE)
        # if not nestTreeAttributes:
        #     manufOccurrence.attributes.add(NESTER_GROUP, NESTER_TYPE, manufOccurrence.entityToken)
        manufOccurrence.isLightBulbOn = True
 
        self.crawlAndCopy(rootComp, manufOccurrence)
        rootOccurrences = [o for o in rootComp.occurrences if o.component.name != 'Manufacturing']
        for occurence in rootOccurrences:
            occurence.isLightBulbOn = False
        manufOccurrence.activate()

    def crawlAndCopy(self, source, target:adsk.fusion.Occurrence):  
        '''crawls the rootComponent structure and makes a copy of everything under Manufacturing root'''

        name = 'rootComp' if source == rootComp else source.fullPathName
        logger.debug(f'new call; parent: {name}; target: {target.fullPathName}')
        childOccurrences = rootComp.occurrences if source == rootComp else source.childOccurrences

        #List of all components that under root, except those under Manufacturing  
        sourceOccurrences = [o for o in childOccurrences if 'Manufacturing' not in o.component.name] 

        targetChildren = target.childOccurrences
        targetChildrenFromNestObjects = list(filter(lambda object: object.parentName == target.name, self._nestItems.nestObjects))

        sourcesOfTargets = [n.sourceOccurrence for n in targetChildrenFromNestObjects]

        extraTargets = [n for n in sourcesOfTargets if n not in sourceOccurrences]
        missingTargets = [n for n in sourceOccurrences if n not in sourcesOfTargets]

        logger.debug(f'source occurrences: {[o.name for o in childOccurrences]}')

        #Work through each source occurrence, if source has children then recurse into children and create dummy component (prevents joints etc being copied), 
        # if source has no children it's a leaf, then add copy of source onto manufacturing parent component 
        for sourceOccurrence in sourceOccurrences:  
            logger.debug(f'Working on {sourceOccurrence.name}')
            logger.debug(f'{sourceOccurrence.name}: {sourceOccurrence.joints.count} joints')
            logger.debug(f'{sourceOccurrence.component.name}: {sourceOccurrence.component.joints.count} joints')

            logger.debug(f'target sourceOccurrences: {[o.name for o in target.childOccurrences]}')
                  
            extra = sourceOccurrence in extraTargets
            missing = sourceOccurrence in missingTargets

            """ 
            options:
            * source is node, target is None - create new target child and new nestItem.addNode
            * source is node, target is leaf - create new target child and new nestItem.addNode
            * source is node, target is node, nestItem doesn't exist - add new nestItem.addNode
            * source is node, target is node, nestItem exists - do nothing
            * source is leaf, target is None - create new target child and new nestItem.addNode
            * source is leaf, target is leaf, nestItem doesn't exist - add new nestItem.addItem
            * source is leaf, target is leaf, nestItem exists - do nothing
            * source is leaf, target is node, nestItem doesn't exist - delete target node
            * source is leaf, target is node, nestItem exists - delete target node and possibly nestItem
             """
            item = self._nestItems.getItem(sourceOccurrence)
            if not sourceOccurrence.childOccurrences:
                # - add source component to target (ie make new child) if there's no source child occurrences ie. it's a leaf
                newTargetOccurrence = target.component.occurrences.addExistingComponent(sourceOccurrence.component, sourceOccurrence.transform).createForAssemblyContext(target)
                self._nestItems.addItem(item = newTargetOccurrence, sourceItem = sourceOccurrence)
                logger.debug(f'Adding existing component {sourceOccurrence.component.name} to {target.name}')
            else:
                # - add dummy component to target if there are source child occurrences ie it's a node
                newTargetOccurrence = target.component.occurrences.addNewComponent(sourceOccurrence.transform).createForAssemblyContext(target)
                newTargetOccurrence.component.name = sourceOccurrence.component.name + '_'
                self._nestItems.addItem(item = newTargetOccurrence)  #, sourceItem = sourceOccurrence)
                logger.debug(f'Adding dummy component {newTargetOccurrence.component.name} to {target.name}')

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