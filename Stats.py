

import geopandas
from geopandas import GeoDataFrame
import pandas as pd
from shapely import affinity
from shapely.geometry import Point, Polygon, MultiPolygon, shape, mapping

strBati="D:/DOC/Photogrammetrie/Eure/Bati_Eure.shp"
strHiddens="D:/DOC/Photogrammetrie/Eure/2022/Hiddens.shp"

print("Lecture bâti")
dfBati: GeoDataFrame= geopandas.read_file(strBati)
print("Total bâti : ",strBati," ",len(dfBati.index))

print("Lecture faces cachées")
dfHiddens: GeoDataFrame= geopandas.read_file(strHiddens)
print("Total hiddens : ",strHiddens," ", len(dfHiddens.index))

dfMerged = pd.merge(dfBati,dfHiddens,on="ID")
print("Total merged : ", len(dfMerged.index))

rDevers = []
lNbPerCentile = []
for k in range(100):
    lNbPerCentile.append(0)
lAreaPerCentile = []
for k in range(100):
    lAreaPerCentile.append(0)

np=dfMerged.to_numpy()
k=0
for i in np:
    geomB=i[18]
    geomH=i[19]
    if geomH==None:
        k=k+1
        continue
    devers=geomH.area/geomB.area
    rDevers.append(devers)
    lNbPerCentile[min(int(devers * 100),99)]=lNbPerCentile[min(int(devers * 100),99)]+1
    lAreaPerCentile[min(int(devers * 100),99)]=lAreaPerCentile[min(int(devers * 100),99)]+geomH.area
print ("Total sans geom : ",k)

print("Nbre par centile")
for k in range(100):
    print(lNbPerCentile[k],end=";")
print("Aire par centile")
for k in range(100):
    print(lAreaPerCentile[k],end=";")


