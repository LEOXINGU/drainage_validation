"""
/***************************************************************************
 LEOXINGU
                              -------------------
        begin                : 2018-06-18
        copyright            : (C) 2018 by Leandro Franca - Cartographic Engineer
        email                : geoleandro.franca@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation.                              *
 *                                                                         *
 ***************************************************************************/
"""

# Drainage Geometry Validation
##Drainage Geometry Validation=name
##Validation=group
##Drainage_Lines=vector
##Minimum_angle=number 45.0
##Search_distance_for_short_vector=number 0.5
##Inconsistencies=output vector

Linhas_de_drenagem = Drainage_Lines
Angulo_minimo = Minimum_angle
Tolerancia = Search_distance_for_short_vector
Insconsistencias = Inconsistencies

from PyQt4.QtCore import *
from qgis.gui import QgsMessageBar
from qgis.utils import iface
from qgis.core import *
import time
import processing
from math import radians, cos, sqrt

# Abrir camada de linhas
linhas = processing.getObject(Linhas_de_drenagem)
SRC = linhas.crs()
if SRC.geographicFlag():
    Tolerancia /= 110000.0

# Validacao dos dados de entrada
if linhas.geometryType() != QGis.Line:
    progress.setInfo('<br/><br/><b>The Drainage Lines layer must be of the line type!</b>')
    time.sleep(5)
    iface.messageBar().pushMessage(u'Situacao', "The Drainage Lines layer must be of the line type!", level=QgsMessageBar.CRITICAL, duration=5)
elif Angulo_minimo<0 or Angulo_minimo>90:
    progress.setInfo('<br/><br/><b>Minimum angle should be between 0 and 90 degrees!</b>')
    time.sleep(5)
    iface.messageBar().pushMessage(u'Situacao', "Minimum angle should be between 0 and 90 degrees!", level=QgsMessageBar.CRITICAL, duration=5)
elif Tolerancia<=0:
    progress.setInfo('<br/><br/><b>Tolerance must be positive!</b>')
    time.sleep(5)
    iface.messageBar().pushMessage(u'Situacao', "Tolerance must be positive!", level=QgsMessageBar.CRITICAL, duration=5)
else:

    COS_ALFA = cos(radians(Angulo_minimo))
    # Funcao Cosseno de Alfa
    def CosAlfa(v1, v2):
        denominador = sqrt(v1[0]*v1[0]+v1[1]*v1[1])*sqrt(v2[0]*v2[0]+v2[1]*v2[1])
        if denominador > 0:
            return (v1[0]*v2[0]+v1[1]*v2[1])/denominador
        else:
            return None

    # pontos a montante e jusante
    lin_list = []
    PM, PJ, ATT = {},{},{}
    for feat in linhas.getFeatures():
            geom = feat.geometry()
            if geom:
                lin = geom.asPolyline()
                if not (lin):
                    lin = geom.asMultiPolyline()[0]
                lin_list +=[lin]

    # Criar camada de inconsistencias
    fields = QgsFields()
    fields.append(QgsField('problem', QVariant.String))
    writer1 = QgsVectorFileWriter(Insconsistencias, 'utf-8', fields, QGis.WKBPoint, SRC, 'ESRI Shapefile')

    # # Checar auto-intersecao
    # progress.setInfo('<b>Checking for self-intersections...</b><br/>')
    # lista_pnts = []
    # feature = QgsFeature()
    # TAM = len(lin_list)
    # for index, coord in enumerate(lin_list):
    #     tam = len(coord)
    #     if tam > 3:
    #         for i in range(0,tam-3):
    #             segA = [coord[i], coord[i+1]]
    #             geomA = QgsGeometry.fromPolyline(segA)
    #             for j in range(i+2,tam-1):
    #                 segB = [coord[j], coord[j+1]]
    #                 geomB = QgsGeometry.fromPolyline(segB)
    #                 if geomA.crosses(geomB):
    #                     point = geomA.intersection(geomB)
    #                     if not(point in lista_pnts or point.asPoint() == coord[0]):
    #                         lista_pnts += [point]
    #                         feature.setAttributes(['Self-intersection'])
    #                         feature.setGeometry(point)
    #                         writer1.addFeature(feature)
    #
    # # Checar se linhas se cruzam ou se sobrepoe
    # progress.setInfo('<b>Checking whether lines intersect or overlap...</b><br/>')
    # tam = len(lin_list)
    # feature = QgsFeature()
    # for i in range(0,tam-1):
    #     for j in range(i+1,tam):
    #         linA = QgsGeometry.fromPolyline(lin_list[i])
    #         linB = QgsGeometry.fromPolyline(lin_list[j])
    #         if linA.crosses(linB):
    #             Intersecao = linA.intersection(linB)
    #             feature.setAttributes(['Crossing between lines'])
    #             if Intersecao.isMultipart():
    #                 for ponto in Intersecao.asMultiPoint():
    #                     feature.setGeometry(QgsGeometry.fromPoint(ponto))
    #                     writer1.addFeature(feature)
    #             else:
    #                 feature.setGeometry(Intersecao)
    #                 writer1.addFeature(feature)
    #         elif linA.intersects(linB):
    #             Intersecao = linA.intersection(linB)
    #             if Intersecao.type() == 1: # Tipo linha
    #                 feature.setAttributes(['Overlap between lines'])
    #                 if Intersecao.isMultipart():
    #                     for linha in Intersecao.asMultiPolyline():
    #                         geom = QgsGeometry.fromPolyline(linha)
    #                         feature.setGeometry(geom.centroid())
    #                         writer1.addFeature(feature)
    #                 else:
    #                     feature.setGeometry(Intersecao.centroid())
    #                     writer1.addFeature(feature)

    # Verificar linhas nao ligadas
    progress.setInfo('<b>Checking lines not connected...</b><br/>')
    tam = len(lin_list)
    feature = QgsFeature()
    for i in range(tam):
        for j in range(tam):
            if i != j:
                pA_ini = QgsGeometry.fromPoint(lin_list[i][0])
                pA_ini_buffer = pA_ini.buffer(Tolerancia, 5)
                pA_fim = QgsGeometry.fromPoint(lin_list[i][-1])
                pA_fim_buffer = pA_fim.buffer(Tolerancia, 5)
                linB = QgsGeometry.fromPolyline(lin_list[j])
                if linB.intersects(pA_ini_buffer) and lin_list[i][0] != lin_list[j][0] and lin_list[i][0] != lin_list[j][-1]:
                    feature.setAttributes(['Line not connected'])
                    feature.setGeometry(pA_ini)
                    writer1.addFeature(feature)
                if linB.intersects(pA_fim_buffer) and lin_list[i][-1] != lin_list[j][0] and lin_list[i][-1] != lin_list[j][-1]:
                    feature.setAttributes(['Line not connected'])
                    feature.setGeometry(pA_fim)
                    writer1.addFeature(feature)

    # # Verificar Angulos Fechados
    # progress.setInfo('<b>Checking minimum angles...</b><br/>')
    # feature = QgsFeature()
    # for index, coord in enumerate(lin_list):
    #     ind = 0
    #     while ind < len(coord)-2:
    #         p1 = coord[ind]
    #         p2 = coord[ind+1]
    #         p3 = coord[ind+2]
    #         v1 = [p1.x()-p2.x(), p1.y()-p2.y()]
    #         v2 = [p3.x()-p2.x(), p3.y()-p2.y()]
    #         if CosAlfa(v1, v2) > COS_ALFA:
    #             feature.setAttributes(['Minimum angle'])
    #             feature.setGeometry(QgsGeometry.fromPoint(p2))
    #             writer1.addFeature(feature)
    #         ind += 1

    del writer1
    progress.setInfo('<br/><b>Leandro Fran&ccedil;a - Eng Cart</b><br/>')
    time.sleep(5)
    iface.messageBar().pushMessage(u'Situation', "Operation Completed Successfully!", level=QgsMessageBar.INFO, duration=5)
