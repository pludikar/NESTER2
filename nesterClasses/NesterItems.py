import adsk.core, adsk.fusion, traceback
import logging, os, sys, math
import json

logger = logging.getLogger('Nester.command')
# logger.setLevel(logging.DEBUG)

from ..common.constants import *
from ..common.decorators import entityFromToken, eventHandler, handlers
from ..common import utils
from .NesterItem import NestItem
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
class NestItems():
    """     
    Top level nest item management
    Keeps track of all stock and nest objects
    """


    def __init__(self):
        nestTypeAttributes:adsk.core.Attributes = design.findAttributes(NESTER_GROUP, NESTER_TYPE)
        nestTokensAttributes:adsk.core.Attributes = design.findAttributes(NESTER_GROUP, NESTER_TOKENS)

        # result = map(lambda x: x.deleteMe(), [a for a in nestTypeAttributes if  not a.parent]) 
        # result = map(lambda x: x.deleteMe(), [a for a in nestTokensAttributes if not a.parent])

        # nestTypeAttributes:adsk.core.Attributes = design.findAttributes(NESTER_GROUP, NESTER_TYPE)
        # nestTokensAttributes:adsk.core.Attributes = design.findAttributes(NESTER_GROUP, NESTER_TOKENS)


        self._document = app.activeDocument.name
        self._stockObjects = []
        self._itemObjects = []
        
        self._positionOffset = 0
        self._spacing = 0

        self._addedFaces = []
        self._removedFaces = []

        self._addedStock = []
        self._removedStock = []


        for nestAttribute in nestTypeAttributes:
            try:
                logger.debug(f'attribute {nestAttribute.groupName}/{nestAttribute.name}:{nestAttribute.value}')
                assert nestAttribute.parent
                if nestAttribute.value == 'Item' :
                    self.addItem(item = nestAttribute.parent) 
                    logger.debug(f'found and added nestItem: {nestAttribute.parent.name} ')
                elif nestAttribute.value == 'Stock':
                    self.addStock(stockOccurrence = nestAttribute.parent)
                    logger.debug(f'found and added stockItem: {nestAttribute.parent.name}')

            except AssertionError:
                nestAttribute.deleteMe()
                continue

            except AttributeError:
                nestAttribute.deleteMe() #TODO indicates that the object is deleted too 


    def save(self):
        stockObjects = [x.selectedFace.entityToken for x in self._stockObjects]
        rootComp.attributes.add(NESTER_GROUP, NESTER_OCCURRENCES, json.dumps(stockObjects)) 

#TODO
    def refresh(self):
        nestAttributes:adsk.core.Attributes = design.findAttributes(NESTER_GROUP, NESTER_TYPE)

        for nestAttribute in nestAttributes:
            try:
                if not nestAttribute.parent: 
                    raise AttributeError()  #Could have just done an if else, but this way it reminds me
                if nestAttribute.value == 'Item':
                    self.addItem(nestAttribute.parent) 
                    logger.debug(f'found and added nestItem: {nestAttribute.parent.name} ')
                else:
                    self.addStock(nestAttribute.parent)
                    logger.debug(f'found and added stockItem: {nestAttribute.parent.name}')
            except AttributeError:
                nestAttribute.deleteMe() #TODO indicates that the object is deleted too  

    def __iter__(self):
        for f in self.nestObjects:
            yield f

    def __next__(self):
        for f in self.nestObjects:
            yield f

    def getItem(self, entity):
        try:
            return self._itemObjects[self._itemObjects.index(entity)]#list(filter(lambda x: x == entity, self._itemObjects))
        except ValueError:
            if isinstance(entity, adsk.fusion.BRepFace):
                return NestItem(entity.assemblyContext)
            elif isinstance(entity, adsk.fusion.Occurrence):
                return NestItem(entity)
        finally:
            return False

    def getStock(self, entity):
        try:
            return self.stockObjects[self.stockObjects.index(entity)]#list(filter(lambda x: x == entity, self._itemObjects))
        except ValueError:
            if isinstance(entity, adsk.fusion.BRepFace):
                return NestStock(entity.assemblyContext)
            elif isinstance(entity, adsk.fusion.Occurrence):
                return NestStock(entity)
        finally:
            return False
      
    def addItem(self, item:adsk.fusion.Occurrence):
        try:
            logger.info("NestItems.addItem")
            self._itemObjects.append(NestItem(item = item)) 
        except:
            pass    

    def remove(self, entity):
        try:
            del self._itemObjects[self._itemObjects.index(entity)]
            self._itemObjects.remove(entity)
        except ValueError:
            pass
        try:
            del self._itemObjects[self._itemObjects.index(entity)]
            self._itemObjects.remove(entity)
        except ValueError:
            return False
        return True

    def addStock(self, stockOccurrence:adsk.fusion.Occurrence):
        logger.info("NestItems.addStock")
        stockObject = NestStock(item = stockOccurrence)
        stockOccurrence.attributes.add(NESTER_GROUP, NESTER_TYPE, "Stock")
        self._stockObjects.append(stockObject)

    def removeStock(self, selectedFace):
        pass

    @property
    def stockObjects(self):
        return self._stockObjects

    @property
    def nestObjects(self):
        return self._itemObjects + self._stockObjects

    @property
    def allItemFaces(self):
        return [o.selectedFace for o in self.nestObjects if o.selectedFace]

    @property
    def allStockFaces(self):
        return [o.selectedFace for o in self.stockObjects if o.selectedFace]

    @property
    def addedStock(self):
        return [x for x in self._stockObjects if x.added]

    @property
    def changedStock(self):
        return [x for x in self._stockObjects if x.changed]

    @property
    def removedStock(self):
        return [x for x in self._stockObjects if x.removed]

    @property
    def addedItems(self):
        return [x for x in self._itemObjects if x.added]

    @property
    def removedItems(self):
        return [x for x in self._itemObjects if x.removed]

    @property
    def changedItems(self):
        return [x for x in self._itemObjects if x.changed]
    
    def refreshOffsets(self):
        logger.info("NestItems.refreshOffsets")
        for stock in self._stockObjects:
            positionOffset = 0
            positionOffset += stock.offset

            for itemObject in self._itemObjects:
                positionOffset += self._spacing
                positionOffset += itemObject.offset
                itemObject.positionOffset = positionOffset
                # adsk.doEvents()

    @property
    def reset(self):
       self._itemObjects = []
       self._stockObjects = []
       self._positionOffset = 0
       self._spacing = 1

    @property
    def spacing(self):
        return self._spacing

    @spacing.setter
    def spacing(self, magnitude):
        self._spacing = magnitude