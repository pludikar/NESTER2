import adsk.core, adsk.fusion, traceback

import logging, os, sys
from  .common import handlers
from .common import CMD_ID,
                    RESOURCE_FOLDER,
                    MY_WORKSPACE,
                    COMMAND_NAME,
                    COMMAND_DESRIPTION
import traceback
import weakref

logger = logging.getLogger('Nester.Navigation')

app = adsk.core.Application.get()
ui = app.userInterface
allWorkspaces = ui.workspaces
commandDefinitions_ = ui.commandDefinitions

class Tab(adsk.core.ToolbarTab):
    panels = []

    def __init__(self, name, title, workspace):
        super().__init__()
        self.workspace = adsk.core.Workspace.cast(allWorkspaces.itemById(workspace))
        toolbarTabs = self.workspace.toolbarTabs

        self.tab_ = toolbarTabs.itemById(CMD_ID + name)
        if not self.tab_:
            self.tab_ = adsk.core.ToolbarTab.cast(toolbarTabs.add(CMD_ID + name, title))
        self.tabPanels_ = self.tab_.toolbarPanels

    def addTabPanel(self, name, title ):
        newPanel = TabPanel(self, name, title)
        if not newPanel:
            return False
        panels.append(newPanel)
        return newPanel
        

class TabPanel(adsk.core.ToolbarPanel):
    commandControls_ = []

    def __init__(self, parent, name, title ):
        super().__init__()
        self.parent = weakref.ref(parent)()
        commandDefinition_ = commandDefinitions_.itemById(CMD_ID + name)
        if not commandDefinition_:
                commandDefinition_ = commandDefinitions_.addButtonDefinition(CMD_ID + name) 


    def addButton(self, name, tooltip, subFolder, handler_cls, notify_method, commandEvent):
        button = CommandControl(self,
                                name,
                                tooltip,
                                subFolder,
                                handler_cls,
                                notify_method,
                                commandEvent))
        CommandControls_.append(button)
        return button

class CommandControl(adsk.core.ToolbarControl):

    def __init__(self, parent, name, tooltip, subFolder, handler_cls, notify_method, commandEvent)
        self.parent = weakref.ref(parent)()
        commandDefinition_ = commandDefinitions_.itemById(self.cmdId + name)
        if not commandDefinition_:
            commandDefinition_ = commandDefinitions_.addButtonDefinition(CMD_ID + name + 'CMD', 
                                                                        name, 
                                                                        tooltip, 
                                                                        RESOURCE_FOLDER + subFolder)
        handlers.make_handler(handler_cls,
                                notify_method, 
                                commandEvent)

