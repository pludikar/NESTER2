import logging
import time
import adsk.core, adsk.fusion

from math import pi, tan
import os
import traceback
from functools import wraps
from .decorators import makeTempFaceVisible

def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        startTime = time.time()
        result = func(*args, **kwargs)
        logger.debug('{}: time taken = {}'.format(func.__name__, time.time() - startTime))
        return result
    return wrapper

getFaceNormal = lambda face: face.evaluator.getNormalAtPoint(face.pointOnFace)[1]

#DbParams = namedtuple('DbParams', ['toolDia','dbType', 'fromTop', 'toolDiaOffset', 'offset', 'minimalPercent', 'longSide', 'minAngleLimit', 'maxAngleLimit' ])
logger = logging.getLogger('Nester.utils')

def getAngleBetweenFaces(edge):
    # Verify that the two faces are planar.
    face1 = edge.faces.item(0)
    face2 = edge.faces.item(1)
    if face1 and face2:
        if face1.geometry.objectType != adsk.core.Plane.classType() or face2.geometry.objectType != adsk.core.Plane.classType():
            return 0
    else:
        return 0

    # Get the normal of each face.
    ret = face1.evaluator.getNormalAtPoint(face1.pointOnFace)
    normal1 = ret[1]
    ret = face2.evaluator.getNormalAtPoint(face2.pointOnFace)
    normal2 = ret[1]
    # Get the angle between the normals.
    normalAngle = normal1.angleTo(normal2)

    # Get the co-edge of the selected edge for face1.
    if edge.coEdges.item(0).loop.face == face1:
        coEdge = edge.coEdges.item(0)
    elif edge.coEdges.item(1).loop.face == face1:
        coEdge = edge.coEdges.item(1)

    # Create a vector that represents the direction of the co-edge.
    if coEdge.isOpposedToEdge:
        edgeDir = edge.startVertex.geometry.vectorTo(edge.endVertex.geometry)
    else:
        edgeDir = edge.endVertex.geometry.vectorTo(edge.startVertex.geometry)

    # Get the cross product of the face normals.
    cross = normal1.crossProduct(normal2)

    # Check to see if the cross product is in the same or opposite direction
    # of the co-edge direction.  If it's opposed then it's a convex angle.
    if edgeDir.angleTo(cross) > pi/2:
        angle = (pi * 2) - (pi - normalAngle)
    else:
        angle = pi - normalAngle
    return angle
    
def correctedEdgeVector(edge, refVertex):
    if edge.startVertex.geometry.isEqualTo(refVertex.geometry):
        return edge.startVertex.geometry.vectorTo(edge.endVertex.geometry)
    else:
        return edge.endVertex.geometry.vectorTo(edge.startVertex.geometry)
    return False

def correctedSketchEdgeVector(edge, refPoint):
    if edge.startSketchPoint.geometry.isEqualTo(refPoint.geometry):
        return edge.startSketchPoint.geometry.vectorTo(edge.endSketchPoint.geometry)
    else:
        return edge.endSketchPoint.geometry.vectorTo(edge.startSketchPoint.geometry)
    return False

@makeTempFaceVisible
def getTmpFaceFromProfile(profile:adsk.fusion.Profile, tempBrepMgr:adsk.fusion.TemporaryBRepManager):
    profileLoops = profile.profileLoops
    for profileLoop in profileLoops:
        if not profileLoop.isOuter:
            continue
        profileCurves = profileLoop.profileCurves
        break

    # profileCurves = [l.profileCurves for l in profileLoops if l.isOuter][0]
    worldCurves = [c.sketchEntity.worldGeometry for c in profileCurves]
    tmpBody, edgemap = tempBrepMgr.createWireFromCurves(worldCurves)
    tmpFace = tempBrepMgr.createFaceFromPlanarWires([tmpBody])
    return tmpFace

@makeTempFaceVisible
def getTmpFaceFromProjectedEntities(objectCollection:adsk.core.ObjectCollection, tempBrepMgr:adsk.fusion.TemporaryBRepManager):
    worldCurves = [c.worldGeometry for c in objectCollection]
    tmpBody, edgemap = tempBrepMgr.createWireFromCurves(worldCurves)
    tmpFace = tempBrepMgr.createFaceFromPlanarWires([tmpBody])
    return tmpFace

def getCentrePoint(entity):
    if entity.objectType != adsk.fusion.Profile.classType() and entity.objectType != adsk.fusion.BRepFace.classType():
        return False
    boundingBox = adsk.core.BoundingBox3D.cast(entity.boundingBox) 
    x = (boundingBox.maxPoint.x + boundingBox.minPoint.x)/2
    y = (boundingBox.maxPoint.y + boundingBox.minPoint.y)/2
    z = (boundingBox.maxPoint.z + boundingBox.minPoint.z)/2
    point = adsk.core.Point3D.create(x, y, z)
    return point

def projectBody(sketch:adsk.fusion.Sketch, body):
    skCurves = sketch.project(body)
    for profile in sketch.profiles:
        for profileLoop in profile.profileLoops:
            for profileCurve in profileLoop.profileCurves:
                if profileCurve.sketchEntity == skCurves.item(0):
                    return profile
    return False
        
def getTopFace(faceEntity):
    normal = getFaceNormal(faceEntity)
    refPlane = adsk.core.Plane.create(faceEntity.vertices.item(0).geometry, normal)
    refLine = adsk.core.InfiniteLine3D.create(faceEntity.vertices.item(0).geometry, normal)
    refPoint = refPlane.intersectWithLine(refLine)
    faceList = []
    body = adsk.fusion.BRepBody.cast(faceEntity.body)
    for face in body.faces:
        if not normal.isParallelTo(getFaceNormal(face)):
            continue
        facePlane = adsk.core.Plane.create(face.vertices.item(0).geometry, normal)
        intersectionPoint = facePlane.intersectWithLine(refLine)
        directionVector = refPoint.vectorTo(intersectionPoint)
        distance = directionVector.dotProduct(normal)
        faceList.append([face, distance])
    sortedFaceList = sorted(faceList, key = lambda x: x[1])
    return sortedFaceList[-1][0]

def getBottomFace(faceEntity):
    normal = getFaceNormal(faceEntity)
    refPlane = adsk.core.Plane.create(faceEntity.vertices.item(0).geometry, normal)
    refLine = adsk.core.InfiniteLine3D.create(faceEntity.vertices.item(0).geometry, normal)
    refPoint = refPlane.intersectWithLine(refLine)
    faceList = []
    body = adsk.fusion.BRepBody.cast(faceEntity.body)
    for face in body.faces:
        if not normal.isParallelTo(getFaceNormal(face)):
            continue
        facePlane = adsk.core.Plane.create(face.vertices.item(0).geometry, normal)
        intersectionPoint = facePlane.intersectWithLine(refLine)
        directionVector = refPoint.vectorTo(intersectionPoint)
        distance = directionVector.dotProduct(normal)
        faceList.append([face, distance])
    sortedFaceList = sorted(faceList, key = lambda x: x[1])
    return sortedFaceList[0][0]

# Returns the magnitude of the bounding box in the specified direction
# face is expected to be planar to xy plane - no checks yet!, so make joints before calling this
def getBoundingBoxExtent(select:adsk.fusion.BRepFace):
    logger.info("getBoundingBoxExtents")
    xVector = adsk.core.Vector3D.create(1,0,0)
    maxPoint = select.boundingBox.maxPoint
    minPoint = select.boundingBox.minPoint
    deltaVector = adsk.core.Vector3D.create(maxPoint.x - minPoint.x,
                                            maxPoint.y - minPoint.y,
                                            maxPoint.z - minPoint.z )

    return deltaVector.dotProduct(xVector)

 
def centreOffsetsFromFace(face):  # assumes that face is in the xy plane - no checks done 
    logger.info(f'finding body centre offset of {face.assemblyContext.name}')
    body = face.body
    maxBodyBox = body.boundingBox.maxPoint
    minBodyBox = body.boundingBox.minPoint
    height = maxBodyBox.z - minBodyBox.z
    logger.debug(f'bounding box - Body; {minBodyBox.x: 9.3f};'
                                        f'{minBodyBox.y: 9.3f};'
                                        f'{minBodyBox.z: 9.3f};'
                                        f'{maxBodyBox.x: 9.3f};'
                                        f'{maxBodyBox.y: 9.3f};'
                                        f'{maxBodyBox.z: 9.3f}')

    bodyCentreX = (minBodyBox.x + maxBodyBox.x) /2
    bodyCentreY = (minBodyBox.y + maxBodyBox.y) /2
    # logger.debug('BodyCentre; {}; {}'.format(bodyCentreX, bodyCentreY))

    minFaceBox = face.boundingBox.minPoint
    maxFaceBox = face.boundingBox.maxPoint
    logger.debug(f'bounding box - Face; {minFaceBox.x: 9.3};'
                                        f'{minFaceBox.y: 9.3};'
                                        f'{minFaceBox.z: 9.3};'
                                        f'{maxFaceBox.x: 9.3};'
                                        f'{maxFaceBox.y: 9.3};'
                                        f'{maxFaceBox.z: 9.3}')

    faceCentreX = (minFaceBox.x + maxFaceBox.x)/2
    faceCentreY = (minFaceBox.y + maxFaceBox.y)/2
    logger.debug(f'bodyCentre; {bodyCentreX: 9.3}; {bodyCentreY: 9.3}')
    logger.debug(f'faceCentre; {faceCentreX: 9.3}; {faceCentreY: 9.3}')

    logger.debug(f'offsets ;{(bodyCentreX - faceCentreX): 9.3} ;{(bodyCentreY - faceCentreY): 9.3}')

    return ((bodyCentreX - faceCentreX), (bodyCentreY - faceCentreY), height)

# Create sliding planar joints between two faces
def createJoint(origin1, origin2):
    logger.info("createJoint")

    app = adsk.core.Application.get()
    ui = app.userInterface
    product = app.activeProduct
    design = adsk.fusion.Design.cast(product)

    # Get the root component of the active design
    rootComp = design.rootComponent

    if origin1.assemblyContext == origin2.assemblyContext:
        ui.messageBox("Faces are from the same Component.  Each part must be from a different component")
        adsk.terminate()

    elif not origin2.assemblyContext:
        ui.messageBox("Face is from the root component.  Each part must be a component")
        adsk.terminate()

    elif not origin1.assemblyContext:
        ui.messageBox("Face is from the root component.  Each part must be a component")
        adsk.terminate()

    else:
        joints = rootComp.joints
        jointInput = joints.createInput(origin1, origin2)
        jointInput.setAsPlanarJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)

        # Create the joint
        return joints.add(jointInput)

app = adsk.core.Application.get()
product = app.activeProduct
design = adsk.fusion.Design.cast(product)
rootComp = design.rootComponent

transform = adsk.core.Matrix3D.create()

def crawlAndCopy(source, target:adsk.fusion.Occurrence):

    name = 'rootComp' if source == rootComp else source.fullPathName
    logger.debug(f'new call; parent: {name}; target: {target.fullPathName}')
    childOccurrences = rootComp.occurrences if source == rootComp else source.childOccurrences
    
    sourceOccurrences = [o for o in childOccurrences if 'Manufacturing' not in o.component.name]
    logger.debug(f'source occurrences: {[o.name for o in childOccurrences]}')
    for sourceOccurrence in sourceOccurrences:
        logger.debug(f'Working on {sourceOccurrence.name}')
        logger.debug(f'{sourceOccurrence.name}: {sourceOccurrence.joints.count} joints')
        logger.debug(f'{sourceOccurrence.component.name}: {sourceOccurrence.component.joints.count} joints')
        newTargetOccurrence = None #target.childOccurrences.itemByName(childOccurrence.name)
        logger.debug(f'target sourceOccurrences: {[o.name for o in target.childOccurrences]}')
        for targetOccurrence in target.childOccurrences:
            try:
                logger.debug(f'{targetOccurrence.name }; attribute count = {targetOccurrence.attributes.count}')
                if  targetOccurrence.attributes.itemByName('nestTree', 'source').value != sourceOccurrence.name:
                    continue
            except AttributeError:
                continue
            logger.debug(f'matched: {sourceOccurrence.name} with {targetOccurrence.name }')
            # logger.debug(f'newTargetOccurrence exists {newTargetOccurrence is not None}')
            newTargetOccurrence = targetOccurrence
            break
                
        # logger.debug(f'newTargetOccurrence exists {newTargetOccurrence is not None}')
        if not newTargetOccurrence:  
            #target doesn't exist 
            if not sourceOccurrence.childOccurrences:
                # - add existing parent component if there's no child occurrences
                newTargetOccurrence = target.component.occurrences.addExistingComponent(sourceOccurrence.component, transform).createForAssemblyContext(target)
                logger.debug(f'Adding existing component {sourceOccurrence.component.name} to {target.name}')
            else:
                # - add dummy component if there are child occurrences
                newTargetOccurrence = target.component.occurrences.addNewComponent(transform).createForAssemblyContext(target)
                newTargetOccurrence.component.name = sourceOccurrence.component.name + '_'
                logger.debug(f'Adding dummy component {newTargetOccurrence.component.name} to {target.name}')
            logger.debug(f'added attribute {target.name} to {newTargetOccurrence.name}')
            attribute = newTargetOccurrence.attributes.add('nestTree','source', sourceOccurrence.name)

        # logger.debug(f'child: {childOccurrence.fullPathName}; target: {newTargetOccurrence.fullPathName}')
        if sourceOccurrence.childOccurrences:
            crawlAndCopy(sourceOccurrence, newTargetOccurrence)

def crawlAndCopy2(parent, target:adsk.fusion.Occurrence):
    # copying component, then deleteing joints
    name = 'rootComp' if parent == rootComp else parent.fullPathName
    logger.debug(f'new call; parent: {name}; target: {target.fullPathName}')
    childOccurrences = rootComp.occurrences if parent == rootComp else parent.childOccurrences
    
    parentOccurrences = [o for o in childOccurrences if o.component.name != 'Manufacturing']
    logger.debug(f'{[o.name for o in childOccurrences]}')
    for childOccurrence in parentOccurrences:
        logger.debug(f'Working on {childOccurrence.name}')
        logger.debug(f'{childOccurrence.name}: {childOccurrence.joints.count} joints')
        # logger.debug(f'{childOccurrence.component.name}: {childOccurrence.component.joints.count} joints')
        newTargetOccurrence = target.childOccurrences.itemByName(childOccurrence.name)
        logger.debug(f'newTargetOccurrence exists {newTargetOccurrence is not None}')
        if not newTargetOccurrence:  
            #target doesn't exist 
            # if not childOccurrence.childOccurrences:
                # - add existing parent component if there's no child occurrences
            newTargetOccurrence = target.component.occurrences.addExistingComponent(childOccurrence.component, transform)
            logger.debug(f'Adding existing component {childOccurrence.component.name} to {target.name}')
            marker = design.timeline.markerPosition
            for joint in newTargetOccurrence.component.joints:
                joint.timelineObject.rollTo(True)
                logger.debug(f'joint deleted: {joint.deleteMe()}')
            design.timeline.moveToEnd()

            # else:
            #     # - add dummy component if there are child occurrences
            #     newTargetOccurrence = target.component.occurrences.addNewComponent(transform)
            #     newTargetOccurrence.component.name = childOccurrence.component.name + '_'
            #     logger.debug(f'Adding dummy component {newTargetOccurrence.component.name} to {target.name}')
        # logger.debug(f'child: {childOccurrence.fullPathName}; target: {newTargetOccurrence.fullPathName}')
        if childOccurrence.childOccurrences:
            crawlAndCopy(childOccurrence, newTargetOccurrence)


   