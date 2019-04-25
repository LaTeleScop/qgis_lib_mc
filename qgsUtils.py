# -*- coding: utf-8 -*-
"""
/***************************************************************************
 qgis-lib-mc
 PyQGIS utilities library to develop plugins or scripts
                             -------------------
        begin                : 2019-02-21
        author               : Mathieu Chailloux
        email                : mathieu.chailloux@irstea.fr
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

"""
    Useful functions to perform base operation on QGIS interface and data types.
"""

import os
from pathlib import Path
import numpy as np

from osgeo import gdal

from qgis.gui import *
from qgis.core import *
from PyQt5.QtCore import QVariant, pyqtSignal
from PyQt5.QtWidgets import QFileDialog

from . import utils

def typeIsInteger(t):
    return (t == QVariant.Int
            or t == QVariant.UInt
            or t == QVariant.LongLong
            or t == QVariant.ULongLong)
            
def typeIsFloat(t):
    return (t == QVariant.Double)
    
def typeIsNumeric(t):
    return (typeIsInteger(t) or typeIsFloat(t))

# Delete raster file and associated xml file
def removeRaster(path):
    if isLayerLoaded(path):
        utils.user_error("Layer " + str(path) + " is already loaded in QGIS, please remove it")
    utils.removeFile(path)
    aux_name = path + ".aux.xml"
    utils.removeFile(aux_name)
            
def removeVectorLayer(path):
    if isLayerLoaded(path):
        utils.user_error("Layer " + str(path) + " is already loaded in QGIS, please remove it")
    utils.removeFile(path)
    
# Returns path from QgsMapLayer
def pathOfLayer(l):
    uri = l.dataProvider().dataSourceUri()
    if l.type() == QgsMapLayer.VectorLayer:
        path = uri[:uri.rfind('|')]
    else:
        path = uri
    return path
      
def layerNameOfPath(p):
    bn = os.path.basename(p)
    res = os.path.splitext(bn)[0]
    return res
    
def getVectorFilters():
    return QgsProviderRegistry.instance().fileVectorFilters()
    
def getRasterFilters():
    return QgsProviderRegistry.instance().fileRasterFilters()
           
def getLayerByFilename(fname):
    map_layers = QgsProject.instance().mapLayers().values()
    fname_parts = Path(fname).parts
    for layer in map_layers:
        utils.debug("layer : " + str(layer.name()))
        layer_path = pathOfLayer(layer)
        path_parts = Path(layer_path).parts
        if fname_parts == path_parts:
            return layer
    else:
        return None
       
def isLayerLoaded(fname):
    return (getLayerByFilename(fname) != None)
    
def normalizeEncoding(layer):
    path = pathOfLayer(layer)
    extension = os.path.splitext(path)[1].lower()
    if extension == ".shp" and (utils.platform_sys in ["Linux","Darwin"]):
        layer.dataProvider().setEncoding('Latin-1')
    elif extension == ".shp":
        layer.dataProvider().setEncoding('System')
    elif extension == ".gpkg":
        layer.dataProvider().setEncoding('UTF-8')
       
# Opens vector layer from path.
# If loadProject is True, layer is added to QGIS project
def loadVectorLayer(fname,loadProject=False):
    utils.debug("loadVectorLayer " + str(fname))
    utils.checkFileExists(fname)
    if isLayerLoaded(fname):
       return getLayerByFilename(fname)
    layer = QgsVectorLayer(fname, layerNameOfPath(fname), "ogr")
    if layer == None:
        utils.user_error("Could not load vector layer '" + fname + "'")
    if not layer.isValid():
        utils.user_error("Invalid vector layer '" + fname + "'")
    normalizeEncoding(layer)
    if loadProject:
        QgsProject.instance().addMapLayer(layer)
    return layer
    
# Opens raster layer from path.
# If loadProject is True, layer is added to QGIS project
def loadRasterLayer(fname,loadProject=False):
    utils.checkFileExists(fname)
    if isLayerLoaded(fname):
        return getLayerByFilename(fname)
    rlayer = QgsRasterLayer(fname, layerNameOfPath(fname))
    if not rlayer.isValid():
        utils.user_error("Invalid raster layer '" + fname + "'")
    if loadProject:
        QgsProject.instance().addMapLayer(rlayer)
    return rlayer

# Opens layer from path.
# If loadProject is True, layer is added to QGIS project
def loadLayer(fname,loadProject=False):
    try:
        return (loadVectorLayer(fname,loadProject))
    except utils.CustomException:
        try:
            return (loadRasterLayer(fname,loadProject))
        except utils.CustomException:
            utils.user_error("Could not load layer '" + fname + "'")
            
def loadLayerGetType(fname,loadProject=False):
    utils.checkFileExists(fname)
    if isLayerLoaded(fname):
       return getLayerByFilename(fname)
    layer_name = layerNameOfPath(fname)
    layer = QgsVectorLayer(fname, layer_name, "ogr")
    if layer == None or not layer.isValid():
        layer = QgsRasterLayer(fname,layer_name)
        if not rlayer.isValid():
            utils.user_error("Could not load layer '" + fname + "'")
        type = 'Raster'
    else:
        normalizeEncoding(layer)
        type = 'Vector'
    if loadProject:
        QgsProject.instance().addMapLayer(layer)
    return (layer, type)
    
    
# Retrieve layer loaded in QGIS project from name
def getLoadedLayerByName(name):
    layers = QgsProject.instance().mapLayersByName('name')
    nb_layers = len(layers)
    if nb_layers == 0:
        utils.warn("No layer named '" + name + "' found")
        return None
    elif nb_layers > 1:
        utils.user_error("Several layers named '" + name + "' found")
    else:
        return layers[0]
        
        
# LAYER PARAMETERS

# Returns CRS code in lowercase (e.g. 'epsg:2154')
def getLayerCrsStr(layer):
    return str(layer.crs().authid().lower())
    
# Returns geometry type string (e.g. 'MultiPolygon')
def getLayerGeomStr(layer):
    return QgsWkbTypes.displayString(layer.wkbType())
    
# Returns simple geometry type string (e.g. 'Polygon', 'Line', 'Point')
def getLayerSimpleGeomStr(layer):
    type = layer.wkbType()
    geom_type = QgsWkbTypes.geometryType(type)
    return QgsWkbTypes.geometryDisplayString(geom_type)
    
# Checks layers geometry compatibility (raise error if not compatible)
def checkLayersCompatible(l1,l2):
    crs1 = l1.crs().authid()
    crs2 = l2.crs().authid()
    if crs1 != crs2:
        utils.user_error("Layer " + l1.name() + " SRID '" + str(crs1)
                    + "' not compatible with SRID '" + str(crs2)
                    + "' of layer " + l2.name())
    geomType1 = l1.geometryType()
    geomType2 = l1.geometryType()
    if geomType1 != geomType2:
        utils.user_error("Layer " + l1.name() + " geometry '" + str(geomType1)
                    + "' not compatible with geometry '" + str(geomType2)
                    + "' of layer " + l2.name())
    
# Initialize new layer from existing one, importing CRS and geometry
def createLayerFromExisting(inLayer,outName,geomType=None,crs=None):
    utils.debug("[createLayerFromExisting]")
    # crs=str(inLayer.crs().authid()).lower()
    # geomType=QgsWkbTypes.displayString(inLayer.wkbType())
    if not crs:
        crs=getLayerCrsStr(inLayer)
    if not geomType:
        geomType=getLayerGeomStr(inLayer)
    layerStr = geomType + '?crs='+crs
    utils.debug(layerStr)
    outLayer=QgsVectorLayer(geomType + '?crs='+crs, outName, "memory")
    return outLayer
    
# Writes file from existing QgsMapLayer
def writeShapefile(layer,outfname):
    utils.debug("[writeShapefile] " + outfname + " from " + str(layer))
    if os.path.isfile(outfname):
        os.remove(outfname)
    (error, error_msg) = QgsVectorFileWriter.writeAsVectorFormat(layer,outfname,'utf-8',destCRS=layer.sourceCrs(),driverName='ESRI Shapefile')
    if error == QgsVectorFileWriter.NoError:
        utils.info("Shapefile '" + outfname + "' succesfully created")
    else:
        utils.user_error("Unable to create shapefile '" + outfname + "' : " + str(error_msg))
    
# Writes file from existing QgsMapLayer
def writeVectorLayer(layer,outfname):
    utils.debug("[writeVectorLayer] " + outfname + " from " + str(layer))
    if os.path.isfile(outfname):
        os.remove(outfname)
    (error, error_msg) = QgsVectorFileWriter.writeAsVectorFormat(layer,outfname,'utf-8',destCRS=layer.sourceCrs())
    if error == QgsVectorFileWriter.NoError:
        utils.info("File '" + outfname + "' succesfully created")
    else:
        utils.user_error("Unable to create file '" + outfname + "' : " + str(error_msg))
        
# Return bounding box coordinates as a list
def coordsOfExtentPath(extent_path):
    layer = loadLayer(extent_path)
    extent = layer.extent()
    x_min = extent.xMinimum()
    x_max = extent.xMaximum()
    y_min = extent.yMinimum()
    y_max = extent.yMaximum()
    return [str(x_min),str(y_min),str(x_max),str(y_max)]
    
def transformBoundingBox(in_rect,in_crs,out_crs):
    transformator = QgsCoordinateTransform(in_crs,out_crs,QgsProject.instance())
    out_rect = transformator.transformBoundingBox(in_rect)
    return out_rect
    
def getLayerFieldUniqueValues(layer,fieldname):
    path = pathOfLayer(layer)
    fieldnames = layer.fields().names()
    if fieldname not in fieldnames:
        utils.internal_error("No field named '" + fieldname + "' in layer " + path)
    field_values = set()
    for f in layer.getFeatures():
        field_values.add(f[fieldname])
    return field_values
    
def getLayerAssocs(layer,key_field,val_field):
    assoc = {}
    path = pathOfLayer(layer)
    fieldnames = layer.fields().names()
    if key_field not in fieldnames:
        utils.internal_error("No field named '" + key_field + "' in layer " + path)
    if val_field not in fieldnames:
        utils.internal_error("No field named '" + val_field + "' in layer " + path)
    for f in layer.getFeatures():
        k = f[key_field]
        v = f[val_field]
        if k in assoc:
            old_v = assoc[k]
            if v not in old_v:
                old_v.append(v)
        else:
            assoc[k] = [v]
    return assoc
    
def getRasterValsFromPath(path):
    gdal_layer = gdal.Open(path)
    band1 = gdal_layer.GetRasterBand(1)
    data_array = band1.ReadAsArray()
    unique_vals = set(np.unique(data_array))
    utils.debug("Unique values init : " + str(unique_vals))
    in_nodata_val = band1.GetNoDataValue()
    utils.debug("in_nodata_val = " + str(in_nodata_val))
    unique_vals.remove(in_nodata_val)
    utils.debug("Unique values : " + str(unique_vals))
    return unique_vals
    
# IMPORT GDAL OR NOT ?
def getRasterVals(layer):
    path = pathOfLayer(layer)
    gdal_layer = gdal.Open(path)
    band1 = gdal_layer.GetRasterBand(1)
    data_array = band1.ReadAsArray()
    unique_vals = set(np.unique(data_array))
    utils.debug("Unique values init : " + str(unique_vals))
    in_nodata_val = int(band1.GetNoDataValue())
    utils.debug("in_nodata_val = " + str(in_nodata_val))
    unique_vals.remove(in_nodata_val)
    utils.debug("Unique values : " + str(unique_vals))
    return unique_vals
    
# def getRasterMinMax(layer):
    # unique_vals = getRasterVals(layer)
    # if len(unique_vals) == 0:
        # utils.user_error("Empty layer")
    # min, max = unique_vals[0], unique_vals[-1]
    # return (min, max)
    
# def getRasterNoData(layer):
    # band1 = layer.GetRasterBand(1)
    # nodata_val = band1.GetNoDataValue()
    # return nodata_val
    
# def getRasterResolution(layer):
    # pass
    
def getVectorVals(layer,field_name):
    field_values = set()
    for f in layer.getFeatures():
        field_values.add(f[field_name])
    return field_values

# Geopackages 'fid'
def getMaxFid(layer):
    max = 1
    for f in layer.getFeatures():
        id = f["fid"]
        id = f.id()
        if id > max:
            max = id
    return max
    
def normFids(layer):
    max_fid = 1
    feats = layer.getFeatures()
    layer.startEditing()
    for f in feats:
        layer.changeAttributeValue(f.id(),0,max_fid)
        #f.setId(max_fid)
        max_fid += 1
    layer.commitChanges()
    
    
# Opens file dialog in open mode
def openFileDialog(parent,msg="",filter=""):
    fname, filter = QFileDialog.getOpenFileName(parent,
                                                caption=msg,
                                                directory=utils.dialog_base_dir,
                                                filter=filter)
    return fname
    
# Opens file dialog in save mode
def saveFileDialog(parent,msg="",filter=""):
    fname, filter = QFileDialog.getSaveFileName(parent,
                                                caption=msg,
                                                directory=utils.dialog_base_dir,
                                                filter=filter)
    return fname
        
# Layer ComboDialog
class LayerComboDialog:

    def __init__(self,parent,combo,button):
        self.parent = parent
        self.combo = combo
        self.button = button
        self.layer_name = None
        self.layer = None
        self.button.clicked.connect(self.openDialog)
        
    def openDialog(self):
        fname = openFileDialog(self.parent,
                                     msg="Ouvrir la couche",
                                     filter=getVectorFilters())
        if fname:
            self.layer_name = fname
            self.layer = loadVectorLayer(fname,loadProject=True)
            utils.debug("self.layer = " +str(self.layer))
            self.combo.setLayer(self.layer)
            #self.combo.layerChanged.emit(self.layer)
        else:
            utils.user_error("Could not open file " + str(fname))
        
    def getLayer(self):
        return self.layer