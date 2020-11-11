import logging
import weakref
import adsk.core, adsk.fusion
from typing import Callable, List, NamedTuple

from functools import wraps

class Handler(NamedTuple):
    handler: any
    event: any #weakref.ReferenceType
handlers: List[Handler] = []

CMD_ID = 'Nester'
RESOURCE_FOLDER = './resources'
COMMAND_NAME = 'Nester'

COMMAND_DESRIPTION = 'Basic Nesting for Fusion 360'
DESIGN_WORKSPACE = 'FusionSolidEnvironment'
NESTER_WORKSPACE = 'NesterEnvironment'  #Not used

NESTER_GROUP = 'NesterGroup' #for attributes
NESTER_OCCURRENCES = 'NesterOccurrences'
NESTER_TOKENS = 'NesterTokens'
NESTER_TYPE = 'NesterType'  # to identify item vs stock

app = adsk.core.Application.get()
ui = app.userInterface
design :adsk.fusion.Design = app.activeProduct

# Get the root component of the active design
rootComp = design.rootComponent


_nestItemsDict = {}

logger = logging.getLogger('Nester.common')

# Decorator to add eventHandler
def eventHandler(handler_cls):
    def decoratorWrapper(notify_method):
        @wraps(notify_method)
        def handlerWrapper(orig_self, *handler_args, **handler_kwargs):

            event = handler_args[0]
            logger.debug(f'notify method created: {notify_method.__name__}')

            try:

                class _Handler(handler_cls):
                    def __init__(self):
                        super().__init__()

                    def notify( self, args, **kwargs):
                        try:
                            logger.debug(f'{notify_method.__name__} handler notified: {args.firingEvent.name}')
                            notify_method(orig_self, args)#, *args)#, *kwargs)
                        except:
                            logger.exception(f'{args.firingEvent.name} error termination')
                h = _Handler()
                event.add(h)
                handlers.append(Handler(h, event)) #adds to global handlers list
            except:
                logger.exception(f'{handler_cls.name} handler creation error')
            return h
        return handlerWrapper
    return decoratorWrapper



class Button(adsk.core.ButtonControlDefinition):
    def __init__():
        super().__init__()

    def addCmd(self, 
                parentDefinition, 
                commandId, 
                commandName, 
                tooltip, 
                resourceFolder,
                handlerMethod, 
                parentControl):
        commandDefinition_ = parentDefinition.itemById(commandId)

        if not commandDefinition_:
            commandDefinition_ = parentDefinition.addButtonDefinition(commandId, 
                                                                        commandName, 
                                                                        tooltip, 
                                                                        resourceFolder)
        
        handlerMethod(commandDefinition_.commandCreated)

        control_ = parentControl.addCommand(exportCommandDefinition_)
        exportControl_.isPromoted = True

        return commandDefinition_


def makeTempFaceVisible(method):
    @wraps(method)
    def wrapper (*args, **kwargs):

        # Create a base feature
        baseFeats = rootComp.features.baseFeatures
        baseFeat = baseFeats.add()
        
        baseFeat.startEdit()
        bodies = rootComp.bRepBodies

        tempBody = method(*args, **kwargs)
        tempBody.name = "Debug_" + method.__name__
        bodies.add(tempBody)

        baseFeat.finishEdit()
        return tempBody
    return wrapper

def entityFromToken(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        entityToken = method(*args, **kwargs)
        entity = design.findEntityByToken(entityToken)
        return entity[0]
    return wrapper


        


    
     
        

 
