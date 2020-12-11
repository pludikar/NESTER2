import adsk.core, adsk.fusion, traceback
import logging, os, sys, math
import json

logger = logging.getLogger('Nester.command')
# logger.setLevel(logging.DEBUG)

from ..common.constants import *
from ..common.decorators import entityFromToken, eventHandler, handlers
from ..common import utils

from . import Fusion360CommandBase #, utils

if debugging:
    import importlib
    importlib.reload(Fusion360CommandBase)
    importlib.reload(utils)
    # importlib.reload(common)

# Get the root component of the active design
rootComp = design.rootComponent

# transform = adsk.core.Matrix3D.create()

# Utility casts various inputs into appropriate Fusion 360 Objects
class NestStock():
    def __init__ (self, item:adsk.fusion.Occurrence, sourceItem:adsk.fusion.Occurrence = None):

        tokenAttribute = item.attributes.itemByName(NESTER_GROUP, NESTER_TOKENS)
        if tokenAttribute:
            self.loadVars(tokenAttribute)
            self.selectedFace = None
        else:
            # logger.info("NestStock.init")
            self._occurrenceToken  = item.entityToken
            self._sourceOccurrenceToken  = sourceItem.entityToken if sourceItem else None

            self._selectedFaceToken = None

            # self._body = self.occurrence.bRepBodies[0] #item.bRepBodies[0].entityToken if item.bRepBodies else None #TODO - check what happens if more than one body
                # occurrence = selectedFace.body.createForAssemblyContext

            self._profileToken = None

            self._joint :adsk.fusion.Joint = None
            self._jointGeometry :adsk.fusion.JointGeometry = None
            self._jointOriginToken  = None

            self._xOffset = None
            self._yOffset = None
            self._angle = 0

            self._timelineObject :adsk.fusion.TimelineObject = None

            self._changed = False
            self._added = True
            self._removed = False
        if type(self) == NestStock:
            item.attributes.add(NESTER_GROUP, NESTER_TYPE, 'Stock')
            self.saveVars()

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (other.selectedFace == self.selectedFace) or (other.occurrence == self.occurrence)
        elif isinstance(other,  adsk.fusion.Occurrence):
            return other == self.occurrence
        elif other.objectType == adsk.fusion.BRepFace.classType():
            return other == self.selectedFace
        elif other.objectType == adsk.fusion.BRepBody.classType():
            return other == self.body
        return NotImplemented

    def __neq__(self, other):
        if isinstance(other, self.__class__):
            return other.selectedFace != self.selectedFace
        elif isinstance(other,  adsk.fusion.Occurrence):
            return other != self.occurrence
        if other.objectType == adsk.fusion.BRepFace.classType():
            return other != self.selectedFace
        elif other.objectType == adsk.fusion.BRepBody.classType():
            return other != self.body
        return NotImplemented

    def addJointOrigin(self):
        logger.info(f"NestStock.addJointOrigin - {self.occurrence.component.name}")

        allOrigins = [x.name for x in self.occurrence.component.allJointOrigins]
        if 'nest_O_'+self.occurrence.name in allOrigins: #if joint already exists don't add another one
            return False

        self._xOffset = utils.getBoundingBoxExtent(self.body)/2
    
        # centreOffsetX, centreOffsetY, self._height = utils.centreOffsetsFromFace(utils.getTopFace(self._selectedFace))
        centreOffsetX, centreOffsetY, self._height = utils.centreOffsetsFromFace(self.selectedFace)
        
        logger.debug(f'faceJointOriginOffsets; {centreOffsetX:}; {centreOffsetY}')

        jointOrigins = self.occurrence.component.jointOrgins
        self._jointGeometry = adsk.fusion.JointGeometry.createByPlanarFace(self.selectedFace, None, adsk.fusion.JointKeyPointTypes.CenterKeyPoint)

        jointOriginInput = jointOrigins.createInput(self._jointGeometry)
        jointOriginInput.offsetX  = adsk.core.ValueInput.createByReal(centreOffsetX)
        jointOriginInput.offsetY = adsk.core.ValueInput.createByReal(centreOffsetY)

        jointOrigin = jointOrigins.add(jointOriginInput)

        self.jointOrigin = jointOrigin.createForAssemblyContext(self.occurrence)
        self.jointOrigin.name = 'nest_O_'+self.occurrence.component.name

    def changeJointOrigin(self):
        self._jointOrigin.timelineObject.rollTo(True)
        logger.info(f"NestStock.changeJointOrigin - {self.occurrence.component.name}")
        logger.debug(f"working on face: {self.selectedFace.tempId:d}")
  
        centreOffsetX, centreOffsetY, self._height = utils.centreOffsetsFromFace(self.selectedFace)
        
        logger.debug(f'faceJointOriginOffsets; {centreOffsetX: 9.3f}; {centreOffsetY: 9.3f}')

        self._jointGeometry = adsk.fusion.JointGeometry.createByPlanarFace(self.selectedFace, None, adsk.fusion.JointKeyPointTypes.CenterKeyPoint)

        self.jointOrigin.geometry = self._jointGeometry
        self.jointOrigin.offsetX.value = centreOffsetX
        self.jointOrigin.offsetY.value = centreOffsetY
        self.jointOrigin.timelineObject.rollTo(False)

        self.joint.timelineObject.rollTo(True)
        self.joint.geometryOrOriginOne = self._jointOrigin
        self.joint.timelineObject.rollTo(False)

    def saveVars(self):
        attributes = self.occurrence.attributes
        varsDict = vars(self) 
        varsDict = {k: v for k, v in varsDict.items() if not callable(v)} #only include variables that are not functions or methods
        data = json.dumps(varsDict)

        nesterAttrbs = self.occurrence.attributes.add(NESTER_GROUP, NESTER_TOKENS, data)    
        
    def loadVars(self, attribute):
        try:
            nesterTokens = attribute.value
            data = json.loads(nesterTokens)
            # varsDict = vars(self) 
            for item, value in data.items():
                setattr(self, item, value)#varsDict[item] = value
        except AttributeError:
            pass
        except KeyError:
            pass

    @property
    def tempId(self):
        return self.selectedFace.tempId

    @property
    def added(self):
        return self._added

    @added.setter
    def added(self, state):
        self._added = state

    @property
    def removed(self):
        return self._removed

    @removed.setter
    def removed(self, state):
        self._removed = state

    @property
    def changed(self):
        return self._changed

    @changed.setter
    def changed(self, state):
        self._changed = state

    @property
    @entityFromToken
    def face(self):
        return self._selectedFaceToken

    @property
    def body(self):
        return self.occurrence.bRepBodies[0]

    @property
    def height(self):
        return self._height

    @property
    @entityFromToken
    def occurrence(self):
        return self._occurrenceToken

    @property
    def parentName(self):
        try:
            fullPath = self.occurrence.fullPathName.split("+" )
            return fullPath[-2:-1][0]
        except IndexError:
            return ''

    @property
    @entityFromToken
    def joint(self):
        return self._joint

    @joint.setter
    def joint(self, newJoint:adsk.fusion.Joint):
        self._jointToken = newJoint.entityToken

    @property
    @entityFromToken
    def sourceOccurrence(self):
        return self._sourceOccurrenceToken

    @sourceOccurrence.setter
    def occurrence(self, newOccurrence:adsk.fusion.Occurrence):
        self._sourceOccurrenceToken = newOccurrence.entityToken

    @property
    @entityFromToken
    def occurrence(self):
        return self._occurrenceToken

    @occurrence.setter
    def occurrence(self, newOccurrence:adsk.fusion.Occurrence):
        self._occurrenceToken = newOccurrence.entityToken

    @property
    @entityFromToken
    def selectedFace(self):
        return self._selectedFaceToken

    @selectedFace.setter
    def selectedFace(self, selected:adsk.fusion.BRepFace):
        logger.info(f'selectedFace {selected.assemblyContext.name}')
        self._selectedFaceToken = selected.entityToken
        self.changed = True
        self.saveVars()

    @property
    @entityFromToken
    def profile(self):
        return self._profileToken

    @profile.setter
    def profile(self, newProfile :adsk.fusion.Profile):
        self._profileToken = newProfile.entityToken

    @property
    @entityFromToken
    def jointOrigin(self):
        return self._jointOriginToken

    @jointOrigin.setter
    def jointOrigin(self, jointOrigin:adsk.fusion.JointOrigin):
        self._jointOriginToken = jointOrigin.entityToken

    @property
    def originPoint(self):
        return self.jointOrigin.geometry.origin

    @property
    def jointGeometry(self):
        return self._jointGeometry

    @property
    @entityFromToken
    def joint(self):
        return self._jointToken

    @joint.setter
    def joint(self, joint:adsk.fusion.Joint):
        self._jointToken = joint.entityToken

    @property
    def name(self):
        return self.occurrence.name

    @property
    def xOffset(self):
        return self._xOffset

