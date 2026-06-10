# Copyright Epic Games, Inc. All Rights Reserved.

from .maya import mayameshutil

def clamp(value):
    if value < 0.0:
        return 0.0
    elif value < 1.0:
        return value
    else:
        return 1.0
        

def valueToColorMap(x, linearSegments):
    '''
    Converts a value to a color map value based on linear segments. The linear segments
    are defined as a list of values [(x0,y0), (x1, y1), ...], where the output
    is the linear interpolation of the y values depending on in which bucket x falls.
    '''
    numSegments = len(linearSegments)
    if x < linearSegments[0][0]:
        return linearSegments[0][1]
    for i in range(1, len(linearSegments)):
        if x < linearSegments[i][0]:
            start = linearSegments[i-1][0]
            end = linearSegments[i][0]
            v0 = linearSegments[i-1][1]
            v1 = linearSegments[i][1]
            w = (x - start)/(end - start)
            return (1-w) * v0 + w * v1
    return linearSegments[numSegments-1][1]


# the linear segments for the jet color map
jetColorRed = [(0.0, 0), (0.35, 0), (0.66, 1), (0.89, 1), (1, 0.5)]
jetColorGreen = [(0.0, 0), (0.125, 0), (0.375, 1), (0.64, 1), (0.91, 0), (1, 0)]
jetColorBlue = [(0.0, 0.5), (0.11, 1), (0.34, 1), (0.65, 0), (1, 0)]


def valueToJetColor(value):
    '''
    Converts a value clamped to 0-1 to the jet color map.
    '''
    value = clamp(value)
    red = valueToColorMap(value, jetColorRed)
    green = valueToColorMap(value, jetColorGreen)
    blue = valueToColorMap(value, jetColorBlue)
    return [red, green, blue, 1]
    

def valueToIntensity(value):
    return [value, value, value, 1]


def toJetColors(values, minValue = 0.0, maxValue = 1.0):
    return [valueToJetColor((value - minValue)/(maxValue - minValue)) for value in values]


def toIntensityColors(values, minValue = 0.0, maxValue = 1.0):
    return [valueToIntensity((value - minValue)/(maxValue - minValue)) for value in values]


def createOrClearColorSetAndSelect(meshName, colorSetName, clamped=True):
    mesh = mayameshutil.getMeshNode(meshName)
    colorSetNames = mesh.getColorSetNames()
    if colorSetName not in colorSetNames:
        mesh.createColorSet(colorSetName, clamped)
    mesh.setCurrentColorSetName(colorSetName)
    mesh.clearColors()
    
    
def assignVertexColorsToMesh(meshName, colorSetName, vtxIDs, colors, clamped=True):
    mesh = mayameshutil.getMeshNode(meshName)
    createOrClearColorSetAndSelect(meshName, colorSetName, clamped)
    if mesh.isColorClamped(colorSetName) != clamped:
        raise RuntimeError('color set {} does not have requested clamping behavior'.format(colorSetName))
    mesh.setCurrentColorSetName(colorSetName)
    mesh.clearColors()
    if vtxIDs is None:
        vtxIDs = range(len(colors))
    mesh.setVertexColors(colors, vtxIDs)
    