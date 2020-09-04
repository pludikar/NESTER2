import logging, os, sys, adsk

appPath = os.path.dirname(os.path.abspath(__file__))
if appPath not in sys.path:
    sys.path.insert(0, appPath)
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
from  .common import nestFacesDict

app = adsk.core.Application.get()
nestFaces = nestFacesDict.setdefault(app.activeDocument.name, NesterCommand.NestFaces())

logger.info('------------------------------start------------------------------')

commandName1 = 'Nester'
commandDescription1 = 'Basic Nesting for Fusion 360'
commandResources1 = './resources'
cmdId1 = 'cmdID_Nester'
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
                                        nestFaces)

def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    commandDefinitions = ui.commandDefinitions

    cmdDef = commandDefinitions.itemById(commandName1)
    if cmdDef:
        cmdDef.deleteMe()

    adsk.autoTerminate(False)

    newCommand1.onRun()

def stop(context):
    # self.savedTab.activate()
    for handler in logger.handlers:
        if  isinstance(handler, logging.FileHandler):
            handler.flush()
            handler.close()
        logger.removeHandler(handler)
    logging.info('-------------Restart')

    newCommand1.onStop()
    
