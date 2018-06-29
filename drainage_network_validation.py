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

# Drainage Network Validation
##Drainage Network Validation=name
##Validation=group
##Drainage_Lines=vector
##Frame=vector
##Frame_Tolerance=number 0.5
##Inconsistencies=output vector
##Drainage_points=output vector

Linhas_de_drenagem = Drainage_Lines
Moldura = Frame
Tolerancia = Frame_Tolerance
Insconsistencias = Inconsistencies
Pontos_de_drenagem = Drainage_points

from PyQt4.QtCore import *
from qgis.gui import QgsMessageBar
from qgis.utils import iface
from qgis.core import *
import time
import processing
from math import radians, cos, sqrt

# Abrir camada de linhas
linhas = processing.getObject(Linhas_de_drenagem)

# Abrir moldura
moldura = processing.getObject(Moldura)


# Validacao dos dados de entrada
if linhas.geometryType() != QGis.Line:
    progress.setInfo('<br/><br/><b>The Drainage Lines layer must be of the line type!</b>')
    time.sleep(5)
    iface.messageBar().pushMessage(u'Situacao', "The Drainage Lines layer must be of the line type!", level=QgsMessageBar.CRITICAL, duration=5)
elif moldura.geometryType() != QGis.Polygon:
    progress.setInfo('<br/><br/><b>The Frame layer must be of the Polygon type!</b>')
    time.sleep(5)
    iface.messageBar().pushMessage(u'Situacao', "The Frame layer must be of the Polygon type!", level=QgsMessageBar.CRITICAL, duration=5)
elif Tolerancia<=0:
    progress.setInfo('<br/><br/><b>Tolerance must be positive!</b>')
    time.sleep(5)
    iface.messageBar().pushMessage(u'Situacao', "Tolerance must be positive!", level=QgsMessageBar.CRITICAL, duration=5)
else:

    COS_ALFA = cos(radians(Tolerancia))
    # Funcao Cosseno de Alfa
    def CosAlfa(v1, v2):
        return (v1[0]*v2[0]+v1[1]*v2[1])/(sqrt(v1[0]*v1[0]+v1[1]*v1[1])*sqrt(v2[0]*v2[0]+v2[1]*v2[1]))

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
                ID = feat.id()
                att = [feat.attributes()[1:]]
                PM[ID] = {'coord':lin[0], 'M':[], 'J':[]}
                PJ[ID] = {'coord':lin[-1], 'M':[], 'J':[]}
                ATT[ID] = att

    # Gerando Buffer da Moldura
    SRC = moldura.crs()
    feat = moldura.getFeatures().next()
    pol = feat.geometry()
    coord = pol.asMultiPolygon()
    if coord:
        moldura_linha = QgsGeometry.fromMultiPolyline(coord[0])
    else:
        coord = pol.asPolygon()
        moldura_linha = QgsGeometry.fromMultiPolyline(coord)
    if SRC.geographicFlag():
        Tolerancia /= 110000.0
        moldura_buffer = moldura_linha.buffer(Tolerancia,5)
    else:
        moldura_buffer = moldura_linha.buffer(Tolerancia,5)

    # Criar camada de inconsistencias
    fields = QgsFields()
    fields.append(QgsField('problem', QVariant.String))
    writer1 = QgsVectorFileWriter(Insconsistencias, 'utf-8', fields, QGis.WKBPoint, SRC, 'ESRI Shapefile')

    # Criar camada de Pontos de Drenagem
    fields = QgsFields()
    fields.append(QgsField('type', QVariant.String))
    writer2 = QgsVectorFileWriter(Pontos_de_drenagem, 'utf-8', fields, QGis.WKBPoint, SRC, 'ESRI Shapefile')

    # Gerar relacionamento entre PM e PJ
    progress.setInfo('<b>Generating drainage network...</b><br/>')
    ID = PM.keys()
    tam = len(ID)
    for i in range(tam):
        for j in range(tam):
            if i!=j:
                pntM_A = PM[ID[i]]['coord']
                pntJ_A  = PJ[ID[i]]['coord']
                att_A = ATT[ID[i]]
                pntM_B = PM[ID[j]]['coord']
                pntJ_B  = PJ[ID[j]]['coord']
                att_B = ATT[ID[j]]
                if pntM_A == pntM_B:
                    PM[ID[i]]['M'] += [[ID[j], att_A == att_B]]
                elif pntM_A == pntJ_B:
                    PM[ID[i]]['J'] += [[ID[j], att_A == att_B]]

                if pntJ_A == pntM_B:
                    PJ[ID[i]]['M'] += [[ID[j], att_A == att_B]]
                elif pntJ_A == pntJ_B:
                    PJ[ID[i]]['J'] += [[ID[j], att_A == att_B]]

    # Verificando problemas na rede
    progress.setInfo('<b>Checking network problem(s)...</b><br/>')
    feat = QgsFeature()
    problem_rede = []
    # ponto de jusante
    for id in ID:
        geom = QgsGeometry.fromPoint(PJ[id]['coord'])
        feat.setGeometry(geom)
        if len(PJ[id]['M'])>1 and len(PJ[id]['J'])==0: # ponto de ramificacao
            feat.setAttributes(['branch'])
            writer2.addFeature(feat)
            continue
        elif len(PJ[id]['M'])==1 and len(PJ[id]['J'])==0 and not(PJ[id]['M'][0][1]): # mudanca de atributo
            feat.setAttributes(['attribute change'])
            writer2.addFeature(feat)
            continue
        elif len(PJ[id]['M'])==1 and len(PJ[id]['J'])>=1: # ponto de confluencia
            continue
        elif len(PJ[id]['M'])==0 and len(PJ[id]['J'])==0 and geom.disjoint(moldura_buffer): # sumidouro, foz
            feat.setAttributes(['end point'])
            writer2.addFeature(feat)
            continue
        else:
            if not (PJ[id]['coord'] in problem_rede)  and geom.disjoint(moldura_buffer):
                problem_rede += [PJ[id]['coord']]
                feat.setAttributes(['network problem'])
                writer1.addFeature(feat)
    # ponto de montante
    for id in ID:
        geom = QgsGeometry.fromPoint(PM[id]['coord'])
        feat.setGeometry(geom)
        if len(PM[id]['M'])>=1 and len(PM[id]['J'])==1: # ponto de ramificacao
            continue
        elif len(PM[id]['M'])==0 and len(PM[id]['J'])>1: # ponto de confluencia
            feat.setAttributes(['confluence'])
            writer2.addFeature(feat)
            continue
        elif len(PM[id]['M'])==0 and len(PM[id]['J'])==0 and geom.disjoint(moldura_buffer): # nascente, vertedouro
            feat.setAttributes(['start point'])
            writer2.addFeature(feat)
            continue
        elif len(PM[id]['M'])==0 and len(PM[id]['J'])==1 and not(PM[id]['J'][0][1]): # mudanca de atributo
            continue
        else:
            if not (PM[id]['coord'] in problem_rede) and geom.disjoint(moldura_buffer):
                problem_rede += [PM[id]['coord']]
                feat.setAttributes(['network problem'])
                writer1.addFeature(feat)

    # Verificar loop para cada PJ
    progress.setInfo('<b>Checking loop problem(s)...</b><br/>')
    def common_data(list1, list2): # Verifica existe pelo menos um elemento em comum
        sentinela = False
        for x in list1:
            for y in list2:
                if x == y:
                    sentinela = True
                    break
            if sentinela:
                break
        return sentinela

    global problem_loop
    problem_loop = []

    def VerificaLoop(pj, visitado, problem_loop):
        lista = pj['M']
        rel = []
        for item in lista:
            rel += [item[0]]
        if not rel:
            return 0
        elif common_data(visitado, rel):
            coord = PJ[visitado[-1]]['coord']
            if coord in problem_loop:
                return 1
            else:
                problem_loop += [coord]
                geom = QgsGeometry.fromPoint(coord)
                feat.setGeometry(geom)
                feat.setAttributes(['loop'])
                writer1.addFeature(feat)
                return problem_loop
        else:
            for M_ID in rel:
                visitado += [M_ID]
                VerificaLoop(PJ[M_ID], visitado, problem_loop)

    for id in ID:
        visitado = [id]
        VerificaLoop(PJ[id], visitado, problem_loop)


    del writer1, writer2
    progress.setInfo('<br/><b>Leandro Fran&ccedil;a - Eng Cart</b><br/>')
    time.sleep(5)
    iface.messageBar().pushMessage(u'Situation', "Operation Completed Successfully!", level=QgsMessageBar.INFO, duration=5)
