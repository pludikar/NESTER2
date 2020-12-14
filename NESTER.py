import logging, os, sys, adsk

from .nesterClasses import NesterCommand, NestItems
from .nesterClasses.constants import *
from .nesterClasses.common import clearDebuggerDict

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

app = adsk.core.Application.get() 

logger.info('------------------------------start------------------------------')

commandName = 'Nester'
commandDescription = 'Basic Nesting for Fusion 360'
commandResources = './resources'
cmdId = 'Nester'
myWorkspace = 'FusionSolidEnvironment'
myToolbarTabID = 'Nest'
myToolbarPanelID = 'SolidScriptsAddinsPanel'

# exportCmdId = cmdId + '_export'
nestCommand = NesterCommand(commandName,
                            commandDescription,
                            commandResources, 
                            cmdId, 
                            myWorkspace, 
                            myToolbarPanelID)

def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    commandDefinitions = ui.commandDefinitions

    cmdDef = [x for x in ui.commandDefinitions if commandName in x.id]
    for x in cmdDef:
        x.deleteMe()

    toolbarPanels = [x for x in ui.allToolbarPanels if commandName in x.id]

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

    tabBars = [x for x in ui.allToolbarTabs if commandName in x.id]
    for x in tabBars:
        x.deleteMe()

    adsk.autoTerminate(False)

    nestCommand.onRun()
    pass

@clearDebuggerDict
def stop(context):
    # self.savedTab.activate()
    nestCommand.onStop()
    for handler in logger.handlers:
        if  isinstance(handler, logging.FileHandler):
            handler.flush()
            handler.close()
        logger.removeHandler(handler)
    logging.info('-------------Restart')


    
