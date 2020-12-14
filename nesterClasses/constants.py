import adsk.core, adsk.fusion

debugging = True

CMD_ID = 'Nester'
RESOURCE_FOLDER = './resources'
COMMAND_NAME = 'Nester'

COMMAND_DESRIPTION = 'Basic Nesting for Fusion 360'
DESIGN_WORKSPACE = 'FusionSolidEnvironment'
NESTER_WORKSPACE = 'NesterEnvironment'  #Not used

NESTER_GROUP = 'NesterGroup' #for attributes
NESTER_OCCURRENCES = 'NesterOccurrences'
NESTER_TOKENS = 'NesterTokens'
NESTER_TYPE = 'NesterType'  # to identify item vs stock vs node

app = adsk.core.Application.get()
ui = app.userInterface
design :adsk.fusion.Design = app.activeProduct

# Get the root component of the active design
rootComp = design.rootComponent

nestFacesDict = {}