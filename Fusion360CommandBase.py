
import adsk.core, adsk.fusion, traceback

import logging, os, sys
from  .common import _nestItemsDict, handlers
from .common import eventHandler

logger = logging.getLogger('Nester.F360CommandBase')
# logger.setLevel(logging.DEBUG)

# handlers = [] 

# Removes the command control and definition 
def cleanUpNavDropDownCommand(cmdId, DC_CmdId):
    logger.info("cleanUpNavDropDownCommand")
    
    objArrayNav = []
    dropDownControl_ = commandControlById_in_NavBar(DC_CmdId)
    commandControlNav_ = commandControlById_in_DropDown(cmdId, dropDownControl_)
        
    if commandControlNav_:
        objArrayNav.append(commandControlNav_)
    
    commandDefinitionNav_ = commandDefinitionById(cmdId)
    if commandDefinitionNav_:
        objArrayNav.append(commandDefinitionNav_)
        
    for obj in objArrayNav:
        destroyObject(obj)


# Finds command definition in active UI
def commandDefinitionById(cmdId):
    logger.info("commandDefinitionById")
    app = adsk.core.Application.get()
    ui = app.userInterface
    
    if not cmdId:
        logger.info('Command Definition:  ' + cmdId + '  is not specified')
        return None
    commandDefinitions_ = ui.commandDefinitions
    commandDefinition_ = commandDefinitions_.itemById(cmdId)
    return commandDefinition_
    
def commandControlById_in_NavBar(cmdId):
    logger.info("commandControlById_in_NavBar")
    app = adsk.core.Application.get()
    ui = app.userInterface
    
    if not cmdId:
        logger.info('Command Control:  ' + cmdId + '  is not specified')
        return None
    
    toolbars_ = ui.toolbars
    Nav_toolbar = toolbars_.itemById('NavToolbar')
    Nav_toolbarControls = Nav_toolbar.controls
    cmd_control = Nav_toolbarControls.itemById(cmdId)
    
    if cmd_control is not None:
        return cmd_control

# Get a commmand Control in a Nav Bar Drop Down    
def commandControlById_in_DropDown(cmdId, dropDownControl):   
    cmd_control = dropDownControl.controls.itemById(cmdId)
    
    if cmd_control is not None:
        return cmd_control

# Destroys a given object
def destroyObject(tobeDeleteObj):
    if not tobeDeleteObj:
        return False
    logger.info(f"destroyObject - {tobeDeleteObj.id} ")
    app = adsk.core.Application.get()
    ui = app.userInterface
    if ui and tobeDeleteObj:
        if tobeDeleteObj.isValid:
            tobeDeleteObj.deleteMe()
        else:
            logger.info(tobeDeleteObj.id + 'is not a valid object')

# Returns the id of a Toolbar Panel in the given Workspace
def toolbarPanelById_in_Workspace(myWorkspaceID, myToolbarPanelID):
    logger.info("toolbarPanelById_in_Workspace")
    app = adsk.core.Application.get()
    ui = app.userInterface
        
    Allworkspaces = ui.workspaces
    thisWorkspace = Allworkspaces.itemById(myWorkspaceID)
    allToolbarPanels = thisWorkspace.toolbarPanels
    ToolbarPanel_ = allToolbarPanels.itemById(myToolbarPanelID)
    
    return  ToolbarPanel_

# Returns the Command Control from the given panel
def commandControlById_in_Panel(cmdId, ToolbarPanel):
    logger.info("commandControlById_in_Panel")
    
    app = adsk.core.Application.get()
    ui = app.userInterface
    
    if not cmdId:
        logger.info('Command Control:  ' + cmdId + '  is not specified')
        return None
    
    cmd_control = ToolbarPanel.controls.itemById(cmdId)
    
    if cmd_control is not None:
        return cmd_control

# Base Class for creating Fusion 360 Commands
# class Fusion360CommandBase:
    
    # def __init__(self, commandName, commandDescription, commandResources, cmdId, myWorkspace, myToolbarPanelID, _nestItems):
    #     logger.info("Fusion360CommandBase.init")
    #     self.commandName = commandName
    #     self.commandDescription = commandDescription
    #     self.commandResources = commandResources
    #     self.cmdId = cmdId
    #     self.myWorkspace = myWorkspace
    #     self.myToolbarPanelID = myToolbarPanelID
    #     self.DC_CmdId = 'Show Hidden'
    #     self.__nestItems = _nestItems
        
    #     # global set of event handlers to keep them referenced for the duration of the command
    #     # self.handlers = []
        
    #     try:
    #         self.app = adsk.core.Application.get()
    #         self.ui = self.app.userInterface

    #     except:
    #         logger.exception('Couldn\'t get app or ui: {}'.format(traceback.format_exc()))
    
    # def onPreview(self, args):
    #     pass 

    # def onDestroy(self, args):    
    #     pass   

    # def onInputChanged(self, args):
    #     pass

    # def onExecute(self, args):
    #     pass

    # def onCreate(self, args):
    #     pass
     
    # def onRun(self):

        # logger.info("Fusion360CommandBase.onRun")

        # app = adsk.core.Application.get()
        # ui = app.userInterface

        # allWorkspaces = ui.workspaces
        # commandDefinitions_ = ui.commandDefinitions

        # try:
        #     nestWorkspace = adsk.core.Workspace.cast(allWorkspaces.itemById(self.myWorkspace))

        #     try:
        #         self.savedTab = [t for t in nestWorkspace.toolbarTabs if t.isActive][0]
        #     except IndexError:
        #         self.savedTab = None

        #     toolbarTabs = nestWorkspace.toolbarTabs
        #     solidTabPanels = nestWorkspace.toolbarTabs.itemById('SolidTab').toolbarPanels

        #     startPanel = solidTabPanels.itemById(self.cmdId +'_startPanel')

        #     if startPanel is None:
        #        startPanel = solidTabPanels.add(self.cmdId + '_startPanel', 'Nest')

        #     self.nesterTab_ =  adsk.core.ToolbarTab.cast(toolbarTabs.add(self.cmdId +'_Tab', 'Nest'))

        #     nesterTabPanels_ = self.nesterTab_.toolbarPanels
        #     nesterTabPanel_ = nesterTabPanels_.itemById(self.cmdId +'_TabPanel')

        #     if nesterTabPanel_ is None:
        #         nesterTabPanel_ = nesterTabPanels_.add(self.cmdId +'_TabPanel', 'Nester')
        #     nesterTabPanel_.isVisible = True
    
        #     self.nesterTab_.isVisible = False
        #     self.nesterTab_.activate()
    
        #     nesterTabPanelControls_ = nesterTabPanel_.controls               
        #     nesterTabPanelControl_ = nesterTabPanelControls_.itemById(self.cmdId)

        #     if not nesterTabPanelControl_:
        #         nesterCommandDefinition_ = commandDefinitions_.itemById(self.cmdId)
        #         if not nesterCommandDefinition_:
        #             nesterCommandDefinition_ = commandDefinitions_.addButtonDefinition(self.cmdId, 
        #                                                                         self.commandName, 
        #                                                                         self.commandDescription, 
        #                                                                         self.commandResources + '/nesterWorkspace')
                
        #     # onCommandCreatedHandler_ = CommandCreatedEventHandler(self)
        #     # handlers.append(onCommandCreatedHandler_)
        #     # nesterCommandDefinition_.commandCreated.add(onCommandCreatedHandler_)
        #     x = self.onCreate(nesterCommandDefinition_.commandCreated)

        #     nesterPanelControl_ = nesterTabPanelControls_.addCommand(nesterCommandDefinition_)
        #     nesterPanelControl_.isVisible = True
        #     nesterPanelControl_.isPromoted = True
    
        #     exportCommandDefinition_ = commandDefinitions_.itemById(self.cmdId+'_export')

        #     if not exportCommandDefinition_:
        #         exportCommandDefinition_ = commandDefinitions_.addButtonDefinition(self.cmdId+'_export', 
        #                                                                             self.commandName+'_export', 
        #                                                                             'export>dxf', 
        #                                                                             self.commandResources+'/export')

        #     onExportCreatedHandler_ = ExportCreatedEventHandler(self)
        #     handlers.append(onExportCreatedHandler_)
        #     exportCommandDefinition_.commandCreated.add(onExportCreatedHandler_)

        #     exportControl_ = nesterTabPanelControls_.addCommand(exportCommandDefinition_)
        #     exportControl_.isPromoted = True

        #     importCommandDefinition_ = commandDefinitions_.itemById(self.cmdId+'_import')

        #     if not importCommandDefinition_:
        #         importCommandDefinition_ = commandDefinitions_.addButtonDefinition(self.cmdId+'_import', 
        #                                                                             self.commandName+'_import', 
        #                                                                             'dxf>import', 
        #                                                                             self.commandResources+'/import')
        #         onImportCreatedHandler_ = ImportCreatedEventHandler(self)
        #         importCommandDefinition_.commandCreated.add(onImportCreatedHandler_)
        #         handlers.append(onImportCreatedHandler_)

        #         importPanelControl_ = nesterTabPanelControls_.addCommand(importCommandDefinition_)
        #     importPanelControl_.isPromoted = True

        #     finishTabPanel_ = self.nesterTab_.toolbarPanels.itemById(self.cmdId +'_FinishTabPanel')

        #     if finishTabPanel_ is None:
        #         finishTabPanel_ = self.nesterTab_.toolbarPanels.add(self.cmdId +'_FinishTabPanel', 'Finish Nester')

        #     finishTabPanel_.isVisible = False
        #     finishTabPanelControls_ = finishTabPanel_.controls
        #     finishPanelControl_ = finishTabPanelControls_.itemById(self.cmdId + '_finish')
        
        #     if not finishPanelControl_:
        #         finishCommandDefinition_ = commandDefinitions_.itemById(self.cmdId + '_finish')
        #         if not finishCommandDefinition_:
        #             finishCommandDefinition_ = commandDefinitions_.addButtonDefinition(self.cmdId+'_finish',
        #                                                                                 self.commandName+'_finish', 
        #                                                                                 'Finish Nester',
        #                                                                                 self.commandResources+'/finishOutcomeView')
        #         finishPanelControl_ = finishTabPanelControls_.addCommand(finishCommandDefinition_)

        #     finishPanelControl_.isPromoted = False
        #     finishPanelControl_.isPromotedByDefault = True
        #     finishPanelControl_.isVisible = True
        #     finishTabPanel_.isVisible = True

        #     onFinishCreatedHandler_ = FinishCreatedEventHandler(self)
        #     finishCommandDefinition_.commandCreated.add(onFinishCreatedHandler_)
        #     handlers.append(onFinishCreatedHandler_)

        #     # finishPanelControl_ = nesterTabPanelControls_.addCommand(finishCommandDefinition_)
        #     startPanelControls_ = startPanel.controls
        #     startPanelControl_ = startPanelControls_.itemById(self.cmdId + '_start')
            
        #     if not startPanelControl_:
        #         startCommandDefinition_ = commandDefinitions_.itemById(self.cmdId + '_start')
        #         if not startCommandDefinition_:
        #             startCommandDefinition_ = commandDefinitions_.addButtonDefinition(self.cmdId+'_start',
        #                                                                                 self.commandName+'_start', 
        #                                                                                 'Start Nester',
        #                                                                                 self.commandResources+'/start')
        #     onStartCreatedHandler_ = StartCreatedEventHandler(self)
        #     startCommandDefinition_.commandCreated.add(onStartCreatedHandler_)
        #     handlers.append(onStartCreatedHandler_)
            
        #     StartPanelControl_ = startPanelControls_.addCommand(startCommandDefinition_)
        #     StartPanelControl_.isPromoted = True

        #     onDocumentOpenedHandler_ = DocumentOpenedHandler(self)
        #     app.documentOpened.add(onDocumentOpenedHandler_)
        #     handlers.append(onDocumentOpenedHandler_)

        #     onDocumentSavingHandler_ = DocumentSavingHandler(self)
        #     app.documentSaving.add(onDocumentSavingHandler_)
        #     handlers.append(onDocumentSavingHandler_)

        #     onDocumentSavedHandler_ = DocumentSavedHandler(self)
        #     app.documentSaved.add(onDocumentSavedHandler_)
        #     handlers.append(onDocumentSavedHandler_)

        #     onDocumentCreatedHandler_ = DocumentCreatedHandler(self)
        #     app.documentCreated.add(onDocumentCreatedHandler_)
        #     handlers.append(onDocumentCreatedHandler_)

        #     onDocumentActivatedHandler_ = DocumentActivatedHandler(self)
        #     app.documentActivated.add(onDocumentActivatedHandler_)
        #     handlers.append(onDocumentActivatedHandler_)

        #     onDocumentDeactivatedHandler_ = DocumentDeactivatedHandler(self)
        #     app.documentDeactivated.add(onDocumentDeactivatedHandler_)
        #     handlers.append(onDocumentDeactivatedHandler_)
                
        # except:
        #     logger.exception('AddIn Start Failed:' )

    # def onStop(self):
    #     logger.info("Fusion360CommandBase.onStop")
    #     try:
    #         app = adsk.core.Application.get()
    #         ui = app.userInterface

    #         nestTab = ui.allToolbarTabs.itemById(self.cmdId +'_Tab')
    #         try:
    #             for tbPanel in nestTab.toolbarPanels:
    #                 if self.cmdId not in tbPanel.id:
    #                     continue
    #                 for dropDownControl in tbPanel.controls:
    #                     if self.cmdId not in dropDownControl.id:
    #                         continue
    #                     for control in dropDownControl.controls:
    #                         if self.cmdId not in control.id:
    #                             continue
    #                         logger.debug(f'{control.id} deleted  {control.deleteMe()}')
    #                     logger.debug(f'{dropDownControl.id} deleted  {dropDownControl.deleteMe()}')
    #                 logger.debug(f'{tbPanel.id}  deleted {tbPanel.deleteMe()}')
    #             logger.debug(f'{nestTab.id} deleted {nestTab.deleteMe()}')

    #         except AttributeError:
    #             pass

    #         cmdDef = [x for x in ui.commandDefinitions if self.cmdId in x.id]
    #         for x in cmdDef:
    #             logger.debug(f'{x.id} deleted {x.deleteMe()}')

    #         toolbarPanels = [x for x in ui.allToolbarPanels if self.cmdId in x.id]

    #         try:
    #             for panel in toolbarPanels:
    #                 panelControls = [x.controls for x in toolbarPanels]
    #                 for controls in panelControls:
    #                     for control in controls:
    #                         logger.debug(f'{control.id} deleted {control.deleteMe()}')
    #                     logger.debug(f'{controls.id} deleted {controls.deleteMe()}')
    #                 logger.debug(f'{panel.id} deleted {panel.deleteMe()}')
                
    #         except AttributeError:
    #             pass

    #         toolbarPanel_ = toolbarPanelById_in_Workspace(self.myWorkspace, self.cmdId +'_Panel') 
    #         finishPanel_ = toolbarPanelById_in_Workspace(self.myWorkspace, self.cmdId +'_FinishTabPanel') 
    #         startPanel_ = toolbarPanelById_in_Workspace(self.myWorkspace, self.cmdId +'_startPanel') 
            
    #         commandControlPanel_ = commandControlById_in_Panel(self.cmdId, toolbarPanel_)
    #         CommandDefinition_ = commandDefinitionById(self.cmdId)

    #         exportCommandControlPanel_ = commandControlById_in_Panel(self.cmdId+'_export', toolbarPanel_)
    #         exportCommandDefinition_ = commandDefinitionById(self.cmdId+'_export')

    #         importCommandControlPanel_ = commandControlById_in_Panel(self.cmdId+'_import', toolbarPanel_)
    #         importCommandDefinition_ = commandDefinitionById(self.cmdId+'_import')

    #         finishCommandControlPanel_ = commandControlById_in_Panel(self.cmdId+'_finish', finishPanel_)
    #         finishCommandDefinition_ = commandDefinitionById(self.cmdId+'_finish')

    #         startCommandControlPanel_ = commandControlById_in_Panel(self.cmdId+'_start', startPanel_)
    #         startCommandDefinition_ = commandDefinitionById(self.cmdId+'_start')

    #         destroyObject(commandControlPanel_)
    #         destroyObject(CommandDefinition_)
    #         destroyObject(exportCommandControlPanel_)
    #         destroyObject(exportCommandDefinition_)
    #         destroyObject(importCommandControlPanel_)
    #         destroyObject(importCommandDefinition_)
    #         destroyObject(finishCommandControlPanel_)
    #         destroyObject(finishCommandDefinition_)
    #         destroyObject(startCommandControlPanel_)
    #         destroyObject(startCommandDefinition_)
    #         destroyObject

    #         handlers.clear()

    #     except:
    #         logger.exception('AddIn Stop Failed: {}'.format(traceback.format_exc()))


    # @eventHandler(adsk.core.InputChangedEventHandler)
    # def inputChangedHandler(self, args):

    #     args = adsk.core.InputChangedEventArgs.cast(args)

    #     command_ = args.sender
    #     inputs_ = command_.commandInputs
    #     changedInput_ = args.input 

    #     logger.info('Input: {} changed event triggered'.format(command_.parentCommandDefinition.id))
    #     logger.info('The Input: {} was the command'.format(changedInput_.id))
   
    #     self.myObject_.onInputChanged(command_, inputs_, changedInput_)


# Intended to create commands in a drop down menu in the nav bar    
# class Fusion360NavCommandBase:
    
#     def __init__(self, commandName, commandDescription, commandResources, cmdId, DC_CmdId, DC_Resources, info):
#         logger.info('Fusion360NavCommandBase.__init__')
#         self.commandName = commandName
#         self.commandDescription = commandDescription
#         self.commandResources = commandResources
#         self.cmdId = cmdId
#         self.info = info
#         self.DC_CmdId = DC_CmdId
#         self.DC_Resources = DC_Resources
        
#         # global set of event handlers to keep them referenced for the duration of the command
#         # self.handlers = []
        
#         try:
#             self.app = adsk.core.Application.get()
#             self.ui = self.app.userInterface

#         except:
#             logger.exception('Couldn\'t get app or ui: {}'.format(traceback.format_exc()))

#     def onPreview(self, command, inputs):
#         logger.info('')
#         pass
    
#     def onDestroy(self, command, inputs, reason_):    
#         logger.info('')
#         pass
    
#     def onInputChanged(self, command, inputs, changedInput):
#         logger.info('')
#         pass

#     # def onExecute(self, command, inputs):
#     #     logger.info('')
#     #     pass
    
#     # def onCreate(self, command, inputs):
#     #     logger.info('')
#     #     pass
     
#     def onRun(self):
#         # global handlers
#         logger.info('')

#         try:
#             app = adsk.core.Application.get()
#             ui = app.userInterface
#             commandDefinitions_ = ui.commandDefinitions
                
#             toolbars_ = ui.toolbars
#             navBar = toolbars_.itemById('NavToolbar')
#             toolbarControlsNAV = navBar.controls
            
#             dropControl = toolbarControlsNAV.itemById(self.DC_CmdId) 
            
#             if not dropControl:             
#                 dropControl = toolbarControlsNAV.addDropDown(self.DC_CmdId, self.DC_Resources, self.DC_CmdId) 
            
#             NAV_Control = toolbarControlsNAV.itemById(self.cmdId)
            
#             if not NAV_Control:
#                 commandDefinition_ = commandDefinitions_.itemById(self.cmdId)
#                 if not commandDefinition_:
#                     # commandDefinitionNAV = cmdDefs.addSplitButton(showAllBodiesCmdId, otherCmdDefs, True)
#                     commandDefinition_ = commandDefinitions_.addButtonDefinition(self.cmdId, self.commandName, self.commandDescription, self.commandResources)
                
#                 onCommandCreatedHandler_ = CommandCreatedEventHandler(self)
#                 handlers.append(onCommandCreatedHandler_)
#                 commandDefinition_.commandCreated.add(onCommandCreatedHandler_)
                
                
#                 NAV_Control = dropControl.controls.addCommand(commandDefinition_)
#                 NAV_Control.isVisible = True
        
#         except:
#             logger.exception('AddIn Start Failed: {}'.format(traceback.format_exc()))

    
#     def onStop(self):
#         logger.info('')
#         ui = None
#         try:
            
#             dropDownControl_ = commandControlById_in_NavBar(self.DC_CmdId)
#             commandControlNav_ = commandControlById_in_DropDown(self.cmdId, dropDownControl_)
#             commandDefinitionNav_ = commandDefinitionById(self.cmdId)
#             destroyObject(commandControlNav_)
#             destroyObject(commandDefinitionNav_)
            
#             if dropDownControl_.controls.count == 0:
#                 commandDefinition_DropDown = commandDefinitionById(self.DC_CmdId)
#                 destroyObject(dropDownControl_)
#                 destroyObject(commandDefinition_DropDown)
             
#         except:
#             logger.exception('AddIn Stop Failed: {}'.format(traceback.format_exc()))

# class ExecutePreviewHandler(adsk.core.CommandEventHandler):
#     def __init__(self, myObject):
#         super().__init__()
#         logger.info("ExecutePreviewHandler")
#         self.myObject_ = myObject
#     def notify(self, args):
#         logger.info("ExecutePreviewHandler.notify")
#         app = adsk.core.Application.get()
#         ui = app.userInterface

#         command_ = args.firingEvent.sender
#         inputs_ = command_.commandInputs

#         logger.info('Preview: {} execute preview event triggered'.format(command_.parentCommandDefinition.id))
    
#         try:               
#             self.myObject_.onPreview(command_, inputs_, args)
#         except:
#             logger.exception('Execute preview event failed: {}'.format(traceback.format_exc()))

# class DestroyHandler(adsk.core.CommandEventHandler):
#     def __init__(self, myObject):
#         logger.info("DestroyHandler")
#         super().__init__()
#         self.myObject_ = myObject
#     def notify(self, args:adsk.core.CommandEventArgs):
#         logger.info("DestroyHandler")
#         # Code to react to the event.
#         app = adsk.core.Application.get()
#         ui = app.userInterface

#         command_ = args.firingEvent.sender
#         inputs_ = command_.commandInputs
#         reason_ = args.terminationReason

#         logger.info(f'Command: {command_.parentCommandDefinition.id} destroyed')
#         reasons = {0:"Unknown", 1:"OK", 2:"Cancelled", 3:"Aborted", 4:"PreEmpted Termination", 5:"Document closed"}
#         logger.info("Reason for termination = " + reasons[reason_])

#         try:
#             self.myObject_.onDestroy(command_, inputs_, reason_)
            
#         except:
#             logger.exception('Input changed event failed: {}'.format(traceback.format_exc()))

# class InputChangedHandler(adsk.core.InputChangedEventHandler):
#     def __init__(self, myObject):
#         super().__init__()
#         logger.info("InputChangedHandler")
#         self.myObject_ = myObject
#     def notify(self, args:adsk.core.InputChangedEventArgs):
#         logger.info("InputChangedHandler")
#         app = adsk.core.Application.get()
#         ui = app.userInterface

#         command_ = args.firingEvent.sender
#         inputs_ = command_.commandInputs
#         changedInput_ = args.input 

#         logger.info('Input: {} changed event triggered'.format(command_.parentCommandDefinition.id))
#         logger.info('The Input: {} was the command'.format(changedInput_.id))
   
#         try:
#             self.myObject_.onInputChanged(command_, inputs_, changedInput_)
#         except:
#             logger.exception('Input changed event failed: {}'.format(traceback.format_exc()))

# class CommandExecuteHandler(adsk.core.CommandEventHandler):
#     def __init__(self, myObject):
#         super().__init__()
#         logger.info("CommandExecuteHandler")
#         self.myObject_ = myObject
#     def notify(self, args):
#         logger.info("CommandExecuteHandler")
#         app = adsk.core.Application.get()
#         ui = app.userInterface
#         command_ = args.firingEvent.sender
#         inputs_ = command_.commandInputs

#         try:
#             # global handlers
#             logger.info('command: {} executed successfully'.format(command_.parentCommandDefinition.id))
#             self.myObject_.onExecute(command_, inputs_)
            
#         except:
#             logger.exception('command executed failed: {}'.format(traceback.format_exc()))

# class StartExecuteHandler(adsk.core.CommandEventHandler):
#     def __init__(self, myObject):
#         super().__init__()
#         logger.info("StartExecuteHandler")
#         self.myObject_ = myObject
#     def notify(self, args):
#         logger.info("StartExecuteHandler")
#         # global handlers
#         app = adsk.core.Application.get()
#         ui = app.userInterface

#         command_ = args.firingEvent.sender
#         inputs_ = command_.commandInputs

#         logger.info(f'command: {command_.parentCommandDefinition.id} executed successfully')

#         try:
#             self.myObject_.onStartExecute(command_, inputs_)
#             # adsk.autoTerminate(False)
            
#         except:
#             logger.exception('command executed failed: {}'.format(traceback.format_exc()))

# class ExportCommandExecuteHandler(adsk.core.CommandEventHandler):
#     def __init__(self, myObject):
#         super().__init__()
#         logger.info("ExportCommandExecuteHandler")
#         self.myObject_ = myObject
#     def notify(self, args):
#         logger.info("ExportCommandExecuteHandler")
#         app = adsk.core.Application.get()
#         ui = app.userInterface

#         command_ = args.firingEvent.sender
#         inputs_ = command_.commandInputs

#         logger.info(f'command: {command_.parentCommandDefinition.id} executed successfully')
#         try:
#             # global handlers
#             self.myObject_.onExportExecute(command_, inputs_)
#             # adsk.autoTerminate(False)
            
#         except:
#             logger.exception('command executed failed: {}'.format(traceback.format_exc()))

# class ImportCommandExecuteHandler(adsk.core.CommandEventHandler):
#     def __init__(self, myObject):
#         super().__init__()
#         logger.info("ImportCommandExecuteHandler")
#         self.myObject_ = myObject
#     def notify(self, args):
#         logger.info("ImportCommandExecuteHandler")
#         app = adsk.core.Application.get()
#         ui = app.userInterface
        
#         command_ = args.firingEvent.sender
#         inputs_ = command_.commandInputs
        
#         logger.info(f'command: {command_.parentCommandDefinition.id} executed successfully')
#         try:
#             # global handlers
#             self.myObject_.onImportExecute(command_, inputs_)
#             # adsk.autoTerminate(False)
            
#         except:
#             logger.exception('command executed failed: {}'.format(traceback.format_exc()))

# class MouseClickHandler(adsk.core.MouseEventHandler):
#     def __init__(self, myObject):
#         super().__init__()
#         logger.info("MouseClickHandler")
#         self.myObject_ = myObject
#     def notify(self, args):
#         logger.info("MouseClickHandler")
#         app = adsk.core.Application.get()
#         ui = app.userInterface
#         command_ = args.firingEvent.sender
#         inputs_ = command_.commandInputs
        
#         kbModifiers = args.keyboardModifiers
#         logger.info('command: {} executed successfully'.format(command_.parentCommandDefinition.id))
        
#         try:
#             self.myObject_.onMouseClick(kbModifiers, command_, inputs_)
            
#         except:
#             logger.exception('command mouseClick failed: {}'.format(traceback.format_exc()))

# class DocumentOpenedHandler(adsk.core.DocumentEventHandler):
#     def __init__(self, myObject):
#         super().__init__()
#         logger.info("DocumentOpenedHandler - init")
#         self.myObject_ = myObject
#     def notify(self, args):
#         logger.info("DocumentOpenedEvent")
#         try:
#             command_ = args.firingEvent.sender
#             # logger.info('command: {} executed successfully'.format(command_.parentCommandDefinition.id))
#             self.myObject_.onDocumentOpened(command_, args)
            
#         except:
#             logger.exception('command document Opened failed: {}'.format(traceback.format_exc()))

# class DocumentSavingHandler(adsk.core.DocumentEventHandler):
#     def __init__(self, myObject):
#         super().__init__()
#         logger.info("DocumentSavingHandler - init")
#         self.myObject_ = myObject
#     def notify(self, args):
#         logger.info("DocumentSavingEvent")
#         try:
#             command_ = args.firingEvent.sender
#             # logger.info('command: {} executed successfully'.format(command_.parentCommandDefinition.id))
#             self.myObject_.onDocumentSaving(command_, args)
            
#         except:
#             logger.exception('command document saved failed: {}'.format(traceback.format_exc()))

# class DocumentCreatedHandler(adsk.core.DocumentEventHandler):
#     def __init__(self, myObject):
#         super().__init__()
#         logger.info("DocumentCreatedHandler - init")
#         self.myObject_ = myObject
#     def notify(self, args):
#         logger.info("DocumentCreatedEvent")
#         try:
#             command_ = args.firingEvent.sender
#             # logger.info('command: {} executed successfully'.format(command_.parentCommandDefinition.id))
#             self.myObject_.onDocumentCreated(command_, args)
            
#         except:
#             logger.exception('command document saved failed: {}'.format(traceback.format_exc()))

# class DocumentSavedHandler(adsk.core.DocumentEventHandler):
#     def __init__(self, myObject):
#         super().__init__()
#         logger.info("DocumentSavedHandler - init")
#         self.myObject_ = myObject
#     def notify(self, args):
#         logger.info("DocumentSavedEvent")
#         try:
#             command_ = args.firingEvent.sender
#             # logger.info('command: {} executed successfully'.format(command_.parentCommandDefinition.id))
#             self.myObject_.onDocumentSaved(command_, args)
            
#         except:
#             logger.exception('command document saved failed: {}'.format(traceback.format_exc()))

# class DocumentActivatedHandler(adsk.core.DocumentEventHandler):
#     def __init__(self, myObject):
#         super().__init__()
#         logger.info("DocumentActivatedHandler - init")
#         self.myObject_ = myObject
#     def notify(self, args):
#         logger.info("DocumentActivatedEvent")
#         try:
#             command_ = args.firingEvent.sender
#             # logger.info('command: {} executed successfully'.format(command_.parentCommandDefinition.id))
#             self.myObject_.onDocumentActivated(command_, args)
            
#         except:
#             logger.exception('command document activated failed: {}'.format(traceback.format_exc()))

# class DocumentDeactivatedHandler(adsk.core.DocumentEventHandler):
#     def __init__(self, myObject):
#         super().__init__()
#         logger.info("DocumentDeactivatedHandler - init")
#         self.myObject_ = myObject
#     def notify(self, args):
#         logger.info("DocumentDectivatedEvent")
#         try:
#             command_ = args.firingEvent.sender
#             # logger.info('command: {} executed successfully'.format(command_.parentCommandDefinition.id))
#             self.myObject_.onDocumentDeactivated(command_, args)
            
#         except:
#             logger.exception('command document deactivated failed: {}'.format(traceback.format_exc()))

# class CommandCreatedEventHandler(adsk.core.CommandCreatedEventHandler):

#     def __init__(self, myObject):
#         super().__init__()
#         logger.info("CommandCreatedEventHandler")
#         self.myObject_ = myObject

#     def notify(self, args):
#         logger.info("CommandCreatedEvent")

#         app = adsk.core.Application.get()
#         ui = app.userInterface

#         command_ = args.command
#         inputs_ = command_.commandInputs
            
#         try:
#             # global handlers
            
#             onExecuteHandler_ = CommandExecuteHandler(self.myObject_) #onExecute()
#             handlers.append(onExecuteHandler_)
#             command_.execute.add(onExecuteHandler_)
            
#             onInputChangedHandler_ = InputChangedHandler(self.myObject_)
#             handlers.append(onInputChangedHandler_)
#             command_.inputChanged.add(onInputChangedHandler_)
            
#             onDestroyHandler_ = DestroyHandler(self.myObject_)
#             handlers.append(onDestroyHandler_)
#             command_.destroy.add(onDestroyHandler_)
            
#             onExecutePreviewHandler_ = ExecutePreviewHandler(self.myObject_)
#             handlers.append(onExecutePreviewHandler_)
#             command_.executePreview.add(onExecutePreviewHandler_)
       
#             onMouseClickHandler_ = MouseClickHandler(self.myObject_)
#             handlers.append(onMouseClickHandler_)
#             command_.mouseClick.add(onMouseClickHandler_)
                   
#             logger.info('Panel command created successfully')
            
#             self.myObject_.onCreate(command_, inputs_)

#         except:
#             logger.exception('Panel command created failed: {}'.format(traceback.format_exc()))

# class ExportCreatedEventHandler(adsk.core.CommandCreatedEventHandler):

#     def __init__(self, myObject):
#         super().__init__()
#         logger.info("ExportCreatedEventHandler")
#         self.myObject_ = myObject

#     def notify(self, args):
#         logger.info("ExportCreatedEventHandler")
#         try:
#             # global handlers
            
#             app = adsk.core.Application.get()
#             ui = app.userInterface
#             command_ = args.command
#             inputs_ = command_.commandInputs
            
#             onExecuteHandler_ = ExportCommandExecuteHandler(self.myObject_)
#             handlers.append(onExecuteHandler_)
#             command_.execute.add(onExecuteHandler_)
                        
#             onDestroyHandler_ = DestroyHandler(self.myObject_)
#             handlers.append(onDestroyHandler_)
#             command_.destroy.add(onDestroyHandler_)
                   
#             logger.info('Panel command created successfully')
            
#             self.myObject_.onExportCreate(command_, inputs_)
#         except:
#             logger.exception('Panel command created failed: {}'.format(traceback.format_exc()))

# class ImportCreatedEventHandler(adsk.core.CommandCreatedEventHandler):
#     def __init__(self, myObject):
#         super().__init__()
#         logger.info("ImportCreatedEventHandler")
#         self.myObject_ = myObject
#     def notify(self, args):
#         logger.info("ImportCreatedEventHandler")
#         try:
#             # global handlers
            
#             app = adsk.core.Application.get()
#             ui = app.userInterface
#             command_ = args.command
#             inputs_ = command_.commandInputs
            
#             onExecuteHandler_ = ImportCommandExecuteHandler(self.myObject_)
#             handlers.append(onExecuteHandler_)
#             command_.execute.add(onExecuteHandler_)
          
#             onDestroyHandler_ = DestroyHandler(self.myObject_)
#             handlers.append(onDestroyHandler_)
#             command_.destroy.add(onDestroyHandler_)
                               
#             logger.info('Panel command created successfully')
            
#             self.myObject_.onExportCreate(command_, inputs_)
#         except:
#             logger.exception('Panel command created failed: {}'.format(traceback.format_exc()))
            
# class FinishCreatedEventHandler(adsk.core.CommandCreatedEventHandler):
#     def __init__(self, myObject):
#         super().__init__()
#         logger.info("FinishCreatedEventHandler")
#         self.myObject_ = myObject
#     def notify(self, args):
#         logger.info("FinishCreatedEventHandler")
#         try:
#             # global handlers
            
#             app = adsk.core.Application.get()
#             ui = app.userInterface
#             command_ = args.command
#             inputs_ = command_.commandInputs

#             onDestroyHandler_ = DestroyHandler(self.myObject_)
#             handlers.append(onDestroyHandler_)
#             command_.destroy.add(onDestroyHandler_)
                               
#             logger.info('Finish Panel command created successfully')
            
#             self.myObject_.onFinishCreate(command_, inputs_)
#         except:
#             logger.exception('Finish Panel command created failed: {}'.format(traceback.format_exc()))

# class StartCreatedEventHandler(adsk.core.CommandCreatedEventHandler):
#     def __init__(self, myObject):
#         super().__init__()
#         logger.info("StartCreatedEventHandler")
#         self.myObject_ = myObject
#     def notify(self, args):
#         logger.info("StartCreatedEventHandler")
#         try:
#             # global handlers
            
#             app = adsk.core.Application.get()
#             ui = app.userInterface
#             command_ = args.command
#             inputs_ = command_.commandInputs

#             onStartExecuteHandler_ = StartExecuteHandler(self.myObject_)
#             handlers.append(onStartExecuteHandler_)
#             command_.execute.add(onStartExecuteHandler_)


#             onDestroyHandler_ = DestroyHandler(self.myObject_)
#             handlers.append(onDestroyHandler_)
#             command_.destroy.add(onDestroyHandler_)
                               
#             logger.info('Finish Panel command created successfully')
            
#             self.myObject_.onStartCreate(command_, inputs_)
#         except:
#             logger.exception('Finish Panel command created failed: {}'.format(traceback.format_exc()))