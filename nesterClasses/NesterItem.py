import adsk.core, adsk.fusion, traceback
import logging, os, sys, math
import json

logger = logging.getLogger('Nester.command')
# logger.setLevel(logging.DEBUG)

from ..common.constants import *
from ..common.decorators import entityFromToken, eventHandler, handlers
from ..common import utils
from .NesterStock import NestStock

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
class NestItem(NestStock):

    def __init__(self, **kwargs): #occurrence:adsk.fusion.Occurrence, sourceOccurrence:adsk.fusion.Occurrence = None):  sourceOccurrence, stockObject:adsk.fusion.BRepFace
        super().__init__(**kwargs)
        # logger.info("NestItem.init")

        self._xPositionOffset = 0
        self._yPositionOffset = 0
        self._angle = 0
        kwargs['item'].attributes.add(NESTER_GROUP, NESTER_TYPE, 'Item')
        self.saveVars()
        self._stockObject = None #kwargs['sourceItem']

    def addJoint(self):
        logger.info(f"NestItem.addJoint - {self.occurrence.name}/{self._stockObject.jointOrigin.name}")

        if self.occurrence.joints.itemByName('nest_O_'+self.occurrence.name):  #if joint already exists don't add another one
            return False

        logger.debug(f'bounding box before joint; {self.body.boundingBox.minPoint.x: 9.3f}; \
                                                {self.body.boundingBox.minPoint.y: 9.3f}; \
                                                {self.body.boundingBox.minPoint.z: 9.3f}; \
                                                {self.body.boundingBox.maxPoint.x: 9.3f}; \
                                                {self.body.boundingBox.maxPoint.y: 9.3f}; \
                                                {self.body.boundingBox.maxPoint.z: 9.3f}')

        self.joint = utils.createJoint(self.jointOrigin, self._stockObject.jointOrigin)
        self.joint.name = 'nest_J_' + self.occurrence.name

        tlOBject = self.joint.timelineObject

        # # adjust position of joint origin to be in the body centre of the face side - just in case face does not cover whole of body silhouette

        centreOffsetX, centreOffsetY, self._height = utils.centreOffsetsFromFace(self.selectedFace)

        logger.debug(f'faceJointOriginOffsets; {centreOffsetX: 9.3f}; {centreOffsetY: 9.3f}')

        self.jointOrigin.timelineObject.rollTo(True)

        self._jointGeometry.geometryOrOriginOne = self.jointOrigin
     
        self._jointGeometry.geometryOrOriginTwo = self._stockObject.jointOrigin
        
        self.jointOrigin.offsetX.value = centreOffsetX
        self.jointOrigin.offsetY.value = centreOffsetY
        self.jointOrigin.offsetZ.value = 0
        self.jointOrigin.timelineObject.rollTo(False)

        self.joint.timelineObject.rollTo(True)
        logger.debug(f'timeLine Marker at Joint adjustment {design.timeline.markerPosition}')
        self.joint.geometryOrOriginOne = self.jointOrigin
        self.joint.timelineObject.rollTo(False)
        self._xOffset = utils.getBoundingBoxExtent(self.body)/2

    def changeJoint(self):
        logger.info(f"NestItem.changeJoint - {self.occurrence.name}/{self.stock.jointOrigin.name}")

        logger.debug(f'bounding box before joint; {self.body.boundingBox.minPoint.x: 9.3f}; \
                                                {self.body.boundingBox.minPoint.y: 9.3f}; \
                                                {self.body.boundingBox.minPoint.z: 9.3f}; \
                                                {self.body.boundingBox.maxPoint.x: 9.3f}; \
                                                {self.body.boundingBox.maxPoint.y: 9.3f}; \
                                                {self.body.boundingBox.maxPoint.z: 9.3f}')

        self.changeJointOrigin()

        self.joint.timelineObject.rollTo(True)
        self.joint.geometryOrOriginOne = self._jointOrigin
        self.joint.timelineObject.rollTo(False)

        centreOffsetX, centreOffsetY, self._height = utils.centreOffsetsFromFace(self.selectedFace)
 
        logger.debug(f'faceJointOriginOffsets; {centreOffsetX: 9.3f}; {centreOffsetY: 9.3f}')

        self.changeJointOrigin()

        self.jointOrigin.offsetX.value = centreOffsetX
        self.jointOrigin.offsetY.value = centreOffsetY
        self.jointOrigin.offsetZ.value = 0
        self.jointOrigin.timelineObject.rollTo(False)

        self.joint.timelineObject.rollTo(True)
        logger.debug(f'timeLine Marker at Joint adjustment {design.timeline.markerPosition}')
        self.joint.geometryOrOriginOne = self.jointOrigin
        self.joint.timelineObject.rollTo(False)
        self._xOffset = utils.getBoundingBoxExtent(self.body)/2

    @property
    @entityFromToken
    def stock(self):
        return self._stockObjectToken

    @stock.setter
    def stock(self, newStock):
        self._stockObjectToken = newStock.entityToken

    @property
    def xPositionOffset(self):  # gets the position of the bodyCentre joint origin relative to the centre of the stock
        return self._joint.jointMotion.primarySlideValue

    @xPositionOffset.setter
    def xPositionOffset(self, magnitude):
        self.joint.jointMotion.primarySlideValue = magnitude

    @property
    def yPositionOffset(self):  # gets the position of the bodyCentre joint origin relative to the centre of the stock
        return self.joint.jointMotion.secondarySlideValue

    @yPositionOffset.setter
    def yPositionOffset(self, magnitude):
        self._oint.jointMotion.secondarySlideValue = magnitude

    @property
    def angle(self):  # gets the position of the bodyCentre joint origin relative to the centre of the stock
        return self.joint.jointMotion.rotationValue

    @angle.setter
    def angle(self, angle):
        self.joint.jointMotion.rotationValue = angle
