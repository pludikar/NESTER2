
import adsk.core, adsk.fusion, traceback

import logging, os, sys
from  . import constants

logger = logging.getLogger('Nester.F360CommandBase')
# logger.setLevel(logging.DEBUG)

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
