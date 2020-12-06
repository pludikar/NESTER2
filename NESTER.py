import logging, os, sys, adsk

appPath = os.path.dirname(os.path.abspath(__file__))

logLevel = logging.DEBUG
# logging.shutdown()

logger = logging.getLogger('Nester')
logger.setLevel(logLevel)

for handler in logger.handlers:
    if  isinstance(handler, logging.FileHandler):
        handler.close()
    logger.removeHandler(handler)

# formatter = logging.Formatter('%(asctime)s; %(module)s; %(levelname)s; %(lineno)d; %(funcName)s ; %(message)s')
formatter = logging.Formatter('%(levelname)s; %(module)s; %(funcName)s; %(lineno)d; %(message)s')
logHandler = logging.FileHandler(os.path.join(appPath, 'nester.log'), mode='a+')
logHandler.setFormatter(formatter)
logHandler.setLevel(logLevel)
logHandler.flush()
logger.addHandler(logHandler)

streamHandler = logging.StreamHandler()
streamHandler.setLevel(logLevel)
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

from . import NesterCommand
from  .common.constants import *
from .common.decorators import clearDebuggerDict

# if debugging:
#     import importlib
#     importlib.reload(NesterCommand)
#     importlib.reload(common)

app = adsk.core.Application.get()
_nestItems = nestFacesDict.setdefault(app.activeDocument.name, NesterCommand.NestItems())

logger.info('------------------------------start------------------------------')

commandName1 = 'Nester'
commandDescription1 = 'Basic Nesting for Fusion 360'
commandResources1 = './resources'
cmdId1 = 'Nester'
myWorkspace1 = 'FusionSolidEnvironment'
myToolbarTabID1 = 'Nest'
myToolbarPanelID1 = 'SolidScriptsAddinsPanel'

# exportCmdId = cmdId1 + '_export'
newCommand1 = NesterCommand.NesterCommand(commandName1,
                                        commandDescription1,
                                        commandResources1, 
                                        cmdId1, 
                                        myWorkspace1, 
                                        myToolbarPanelID1,
                                        _nestItems)

def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    commandDefinitions = ui.commandDefinitions

    cmdDef = [x for x in ui.commandDefinitions if commandName1 in x.id]
    for x in cmdDef:
        x.deleteMe()

    toolbarPanels = [x for x in ui.allToolbarPanels if commandName1 in x.id]

    for panel in toolbarPanels:
        panelControls = [x.controls for x in toolbarPanels]
        for controls in panelControls:
            for control in controls:
                control.deleteMe()
            try:
                controls.deleteMe()
            except AttributeError:
                continue
        panel.deleteMe()

    tabBars = [x for x in ui.allToolbarTabs if commandName1 in x.id]
    for x in tabBars:
        x.deleteMe()

    adsk.autoTerminate(False)

    newCommand1.onRun()

@clearDebuggerDict
def stop(context):
    # self.savedTab.activate()
    for handler in logger.handlers:
        if  isinstance(handler, logging.FileHandler):
            handler.flush()
            handler.close()
        logger.removeHandler(handler)
    logging.info('-------------Restart')

    newCommand1.onStop()
    
