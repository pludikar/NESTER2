import logging

from functools import wraps

CMD_ID = 'Nester'
RESOURCE_FOLDER = './resources'
COMMAND_NAME = 'Nester'
COMMAND_DESRIPTION = 'Basic Nesting for Fusion 360'
MY_WORKSPACE = 'FusionSolidEnvironment'
# myToolbarTabID1 = 'Nest'
# myToolbarPanelID1 = 'SolidScriptsAddinsPanel'

nestFacesDict = {}

logger = logging.getLogger('Nester.common')

handlers = []


# Decorator to add eventHandler
def eventHandler(handler_cls, catch_exceptions = True):
    def decoratorWrapper(notify_method):
        @wraps(notify_method)
        def handlerWrapper(orig_self, *handler_args, **handler_kwargs):

            commandEvent = handler_args[0]
            # logger.debug(f'notify method created: {notify_method.__name__}')

            class _Handler(handler_cls):
                def __init__(self):
                    super().__init__()

                def notify( self, args, **kwargs):
                    logger.debug(f'handler notified: {commandEvent.name}')
                    # logger.debug(f'args: {args} {len(args)}')
 
                    if catch_exceptions:
                        try:
                            logger.debug(f'{args}')
                            notify_method(orig_self, args)#, *args)#, *kwargs)
                        except:
                            logger.exception(f'{commandEvent.name} error termination')
                    else:
                        notify_method(orig_self, args)#, *args)# *kwargs)
            h = _Handler()
            commandEvent.add(h)
            handlers.append((h, commandEvent)) #adds to global handlers list
            return h
        return handlerWrapper
    return decoratorWrapper
