import sys
import time
from datetime import datetime

import numpy as np
from shapely import affinity
from shapely.geometry import Point, Polygon, MultiPolygon, shape, mapping
from shapely.ops import unary_union
import rtree
import fiona

from collections import OrderedDict

sys.path.append("D:\\DOC\\Photogrammetrie\\PySocle\\src")
from pysocle.photogrammetry.ta import Ta

# Calcul du décalage terrain entre un point d'altitude zmin et un autre de même x,y, d'altitude zmax, non redressé
def offset(pt, zmin, zmax, img):
    i = img.imc.world_to_image (np.array([pt.x, pt.y, zmin]))
    j = img.imc.world_to_image (np.array([pt.x, pt.y, zmax]))

    m1 = img.imc.image_z_to_world (i,zmin)
    m2 = img.imc.image_z_to_world (j,zmin)
    return m2[0]-m1[0],m2[1]-m1[1]

# Retourne le zmin et le zmax d'un bâti
def zminmax(feature):
    if ("Z_MIN_SOL" in feature["properties"]):
        zmin = feature["properties"]["Z_MIN_SOL"]
    else:
        return None,None
    if zmin is None:
        return None,None
    if ("HAUTEUR" in feature["properties"]):
        hauteur = featureB["properties"]["HAUTEUR"]
    else:
        return None,None
    if hauteur is None:
        return None,None
    zmax = zmin + hauteur
    return zmin,zmax

#strTA="D:\\DOC\\Photogrammetrie\\Rhone\\20FD6925_adjust.XML"
#strTA="D:\\DOC\\Photogrammetrie\\Eure\\2019\\2019_19FD27_C_25.XML"
strTA="D:\\DOC\\Photogrammetrie\\Eure\\2022\\22FD2720_adjust_tri.XML"
#strGraphe="D:\\DOC\\Photogrammetrie\\Rhone\\Graphe_simplifie.shp"
strGraphe="D:\\DOC\\Photogrammetrie\\Eure\\2022\\Graphe_2022_simplifie.shp"
#strBati="D:\\DOC\\Photogrammetrie\\EUre\\Bati_Zone.shp"
#strBati="D:\\DOC\\Photogrammetrie\\Eure\\Bati_Zone3.shp"
strBati="D:\\DOC\\Photogrammetrie\\Eure\\Bati_Eure.shp"

# Lecture du fichier de TA en XML
print("Initialisation TA ")
ta = Ta.from_xml(strTA)
print(ta.project.print())

# Lecture des fichiers d'entrée
print("Lecture du graphe de mosaïquage")
with fiona.open(
        strGraphe,
        "r") as shpGraphe:
    print("Lecture du bâti ")
    with fiona.open(
            strBati,
            "r") as shpBati:
        print("Initialisation des shapefile : murs, toits, faces cachées")
        with fiona.open(
                "D:\\DOC\\Photogrammetrie\\Eure\\Tmp\\Walls.shp",
                "w",
                driver=shpBati.driver,
                crs=shpBati.crs,
                schema={
                    'geometry': "MultiPolygon",
                    'idbati': "str"
                }
            ) as shpWalls:
            with fiona.open(
                     "D:\\DOC\\Photogrammetrie\\Eure\\Tmp\\Roofs.shp",
                     "w",
                     driver=shpBati.driver,
                     crs=shpBati.crs,
                     schema={
                         'geometry': "Polygon",
                         'idbati': "str"
                     }
                ) as shpRoofs:
                with fiona.open(
                        "D:\\DOC\\Photogrammetrie\\Eure\\Tmp\\Hiddens.shp",
                        "w",
                        driver=shpBati.driver,
                        crs=shpBati.crs,
                        schema={
                            'geometry': "MultiPolygon",
                            'properties': OrderedDict([("ID","str")])
                        }
                    ) as shpHiddens:
                        nbHiddens=0
                        nb1=0
                        nb2=0
                        nb3=0

                        #Initialisation de l'index spatial des bâtiments
                        print("Indexation des bâtiments ",len (shpBati)," batiments")
                        indexB = rtree.index.Index ()
                        for iB, fB in shpBati.items():
                            if iB % 200 == 0:
                                print ("\r", end="")
                                print (f'{iB / len (shpBati) * 100:.2f}', end="%")
                                time.sleep (0.01)
                            indexB.insert (iB, shape(fB['geometry']).bounds)
                        print("")

                        print("Calcul des faces cachées")
                        # Boucle sur les clichés
                        for iG, featureG in shpGraphe.items():
                            print(str(datetime.now())," : Cliché ", featureG["properties"]["CLICHE"]," (", iG, " sur ", len(shpGraphe))
                            #if featureG["properties"]["CLICHE"]!='22FD2720x00022_02069':
                            #    continue
                            geomG = featureG["geometry"]
                            img = ta.project.find_shot (featureG["properties"]["CLICHE"])  # Récupération de l'image voulue
                            if img==None:
                                continue

                            # Liste des bâtiments  intersectant le rectangle englobant le cliché
                            idBs = [int (i) for i in indexB.intersection (shape(geomG).bounds)]
                            print(len(idBs)," bâtiments")
                            k=0
                            for idB in idBs:
                                featureB = shpBati[idB]
                                #print(featureB["properties"]["ID"])

                                #if featureB["properties"]["ID"]!="BATIMENT0000000338569531":
                                #    continue

                                geomB = featureB['geometry']
                                #print(idB)
                                t1 = datetime.now()
                                # Contrôle de l'intersection effective du bâtiment avec le cliché
                                if shape(geomG).intersects (shape(geomB)):
                                    # Calcul du décalage du toit avec la base
                                    zmin, zmax = zminmax(featureB)
                                    if zmin==None:
                                        nb1=nb1+1
                                        continue

                                    c=Point(shape(geomB).centroid)
                                    offset_x, offset_y = offset(c,zmin,zmax,img)

                                    # Exclusion des bâtiments coupés en plusieurs polygones en bord de chantier
                                    if geomB["type"] == 'MultiPolygon':
                                        nb2=nb2+1
                                        continue

                                    seqHoles = []
                                    for iH in range(1,len (geomB["coordinates"])):
                                        seqHoles.append(geomB["coordinates"][iH])
                                    empriseB = Polygon(geomB["coordinates"][0],seqHoles)

                                    # Recherche des bâtiments connexes
                                    BatiC = []
                                    idBcs = [int (j) for j in indexB.intersection (shape (geomB).bounds)]

                                    for idBc in idBcs:
                                       # if (idB==4946):
                                        #    for ii,b in enumerate indexB
                                        featureBc = shpBati[idBc]
                                        geomBc = featureBc['geometry']
                                        if shape (geomBc).intersects (shape (geomB)):
                                            BatiC.append(geomBc)

                                    # Construction des toits
                                    roof = affinity.translate(empriseB,offset_x,offset_y)
                                    shpRoofs.write ({
                                        "geometry": {"type": "Polygon",
                                                     "coordinates": mapping (roof)["coordinates"]},
                                        "idbati": featureB["properties"]["ID"]
                                    })

                                    # Liste des points du polygone du bâti
                                    list_pt = []
                                    for x,y in empriseB.exterior.coords:
                                        list_pt.append(Point(x,y))

                                    # Reconstruction des murs
                                    walls = []
                                    for iPt, pt in enumerate (list_pt):
                                        if (iPt==len (list_pt)-1):
                                            break
                                        next_pt = list_pt[iPt+1]
                                        seq = [pt,
                                               next_pt,
                                               Point(next_pt.x+offset_x,next_pt.y+offset_y,zmin),
                                               Point(pt.x+offset_x,pt.y+offset_y,zmin),
                                               pt]
                                        walls.append(Polygon(seq))
                                    walls.append (Polygon (roof))
                                    united_walls=unary_union(shape(MultiPolygon(walls)))

                                    #shpWalls.write ({
                                     #   "geometry": {"type": "MultiPolygon",
                                      #               "coordinates": mapping (united_walls)["coordinates"]},
                                       # "idbati": featureB["properties"]["ID"]
                                    #})

                                    # Construction des face cachées
                                    seqH = []
                                    hidden = united_walls
                                    for Bc in BatiC:
                                        hidden = hidden.difference (shape (Bc))

                                    if hidden.geom_type == 'Polygon':
                                        seqH.clear()
                                        seqH.append (hidden)
                                        hidden = MultiPolygon (seqH)
                                    elif hidden.geom_type == 'GeometryCollection':
                                            hidden = MultiPolygon (
                                                p for p in hidden.geoms if p.geom_type == 'Polygon')
                                    elif hidden.geom_type != 'MultiPolygon':
                                        nb3=nb3+1
                                        continue
                                    nbHiddens=nbHiddens+1
                                    shpHiddens.write ({
                                        "geometry": {"type": "MultiPolygon",
                                                     "coordinates": mapping (hidden)["coordinates"]},
                                        "properties": OrderedDict([('ID',featureB["properties"]["ID"])])
                                    })
                                    #t5=datetime.now()
                                    #indexB.delete (idB, shape (geomB).bounds)
                                    #print(t2-t1," ",t3-t2," ",t4-t3," ",t5-t4," ",t5-t1)
                                    continue




                        print("NbHiddens = ",nbHiddens)
                        print(nb1," ",nb2," ",nb3)