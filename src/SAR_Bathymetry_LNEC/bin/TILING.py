#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

"""
===============================================================================
Co-ReSyF Research Application - SAR_Bathymetry
===============================================================================
 Authors: Alberto Azevedo and Francisco Sancho
 Date: June/2016
 Last update: March/2017
 
 Usage: ./SAR_Bathymetry_CoReSyF_V8.py <image input file> 
 
 For help: ./SAR_Bathymetry_CoReSyF_V8.py -h
===============================================================================
"""

import os,sys
wdir=os.getcwd()
paths=[wdir[:-6]+"bin"]
for i in paths:
    sys.path.append(i)

import numpy as np
import matplotlib.pyplot as plt
import cv2
import CSAR
import gdal
from scipy.interpolate import griddata
import matplotlib.colors as colors
from datetime import datetime
import argparse
import tarfile

def restricted_float(x):
    x = float(x)
    if x < 0.1 or x > 0.5:
        raise argparse.ArgumentTypeError("%r not in range [0.1, 0.5]"%(x,))
    return x

########## Input arguments
parser = argparse.ArgumentParser(description='Co-ReSyF: Sar Bathymetry Research Application')
parser.add_argument('-i', '--input', help='Input image', required=True)
parser.add_argument('-o', '--output', help='Output file (tar.gz) with .npz files for FFT determination', required=True)
parser.add_argument('-u', '--outlist', help='List with output file names (tar.gz) with .npz files for FFT determination (to be used by Wings)', required=True)
parser.add_argument('-c', '--out_config', help='Output configuration file with resolution values (.txt file)', required=True)
parser.add_argument('-p', '--polygon', help='Bathymetric AOI - Polygon coords list file', required=False)
parser.add_argument("-g", "--graphics", help="Show matplotlib plots while running the application", action="store_true")
parser.add_argument("-l", "--landmask", help="Apply Landmask",action="store_true")
parser.add_argument("-r", "--resDx", help="Resolution of the final bathymetric grid, in meters (m). Default=500m.", default=500., type=float,required=False)
parser.add_argument("-s", help="FFT box shift parameter. Possible values between (0.1-0.5). Default=0.5.",default=0.5, type=restricted_float,required=False)
parser.add_argument("-v","--verbose", help="increase output verbosity",action="store_true")
args = parser.parse_args()


RunId = datetime.now().strftime('%Y%m%dT%H%M%S')

# Creating temp folder (for temporary files)
curdir = os.getcwd()

PathOut = curdir + '/temp/' + str(RunId) + "/FFT_img_outputs"
#newpath = r'./'+PathOut
if not os.path.exists(PathOut):
    os.makedirs(PathOut)

Params=[ "\n#########################################################################################\n",
         "\nCo-ReSyF: Sar Bathymetry Research Application\n",
         "#########################################################################################\n",
         "RunId : %s" % RunId +"\n",
         "Input file: %s" % args.input +"\n",
         "Output file: %s" % args.output +"\n",
         "Output config: %s" % args.out_config +"\n",
         "Polygon file: %s" % args.polygon +"\n",
         "Graphics: %s" % args.graphics +"\n",
         "Grid resolution: %s" % args.resDx+"\n",
         #"Period of the swell: %s" % args.t+"\n",
         "FFT box shift parameter: %s" % args.s+"\n",
         "Landmask: %s" % args.landmask+"\n",
         "Verbosity: %s" % args.verbose+"\n",
         "\n\n"]

paramsFile = args.out_config
parOut = open(paramsFile, "w")
parOut.writelines(Params)
parOut.close()

if args.verbose:
    for i in Params:
        print i[:-1]

filein=args.input
fileout = args.output
Graphics=args.graphics
GridDx=args.resDx
shift=args.s


#### Hardcoded flags...
SFactor=1./1.
Slant_Flag=False
EPSG="WGS84"
#######################


#################################################################
#################################################################
#################################################################
#################################################################


if args.verbose:
    print "\n\nReading Image..."
img,mask,res, LMaskFile=CSAR.ReadSARImg(filein,ScaleFactor=np.float(SFactor),C_Stretch=True,SlantCorr=Slant_Flag,EPSG_flag=EPSG,Land=args.landmask, path=PathOut)

if args.verbose:
    print "\n\nReading Image... DONE!!!"

lon,lat=CSAR.GetLonLat(LMaskFile)


print (res)
print (type(res))


###
### Offset = # of pixels for half of 1 km FFT box. 
### Therefore, the Offset varies with image resolution. 
offset=CSAR.GetBoxDim(res[0])
if args.verbose:
    print "\nOffset (pixels,m):  (  %s  ;  %s  ) " % (offset,offset*res[0]) +"\n"

############################################################
###### Grid definition 
############################################################
############################################################
Pts=CSAR.SetGrid(LMaskFile,res,GridDeltaX = GridDx)
LonVec,LatVec=lon[0,:],lat[:,0]
Pontos=[]
for i in Pts:
    valx, lon_index=CSAR.find_nearest(LonVec,i[0])
    valy, lat_index=CSAR.find_nearest(LatVec,i[1])
    Pontos.append([lon_index,lat_index])
Pontos = np.array(Pontos)

if args.polygon==None:
    Polygon=CSAR.SetPolygon(LMaskFile,offset,PtsNum=10)
    np.savetxt("Polygon.txt",Polygon)
    os.system("cp -f Polygon.txt "+PathOut+".")
    for i in Polygon:
        print i
else:
    os.system("cp -f "+args.polygon+" "+PathOut+".")
    Polygon=np.loadtxt(args.polygon)
    print Polygon    

cnt=Polygon.reshape((-1,1,2)).astype(np.float32)

Pts2Keep=[]
for m,k in enumerate(Pts):
    Result=cv2.pointPolygonTest(cnt, (k[0],k[1]), False)
    if Result!=-1.0:
        Pts2Keep.append(m)
Pontos=Pontos[Pts2Keep]
#print Pontos_Final.shape


plt.figure()
plt.imshow(img,cmap="gray")
plt.scatter(Pontos[:,0],Pontos[:,1],3,marker='o',color='r')
plt.savefig(PathOut+"Grid.png", dpi=300)
if Graphics:
    plt.show()

if args.verbose:
    print "\n\n"
    print Pontos.shape
    #print Pontos
    print "\n\n"


############################################################
############################################################
####   Preparing files for FFT determination and plot  #####
############################################################
#fileout=PathOut+"FFT_img_outputs/"
#if not os.path.exists(fileout):
#    os.makedirs(fileout)
fileout=fileout+'/SAR_BathyOut_'+str(RunId)+'/FFT_img_outputs'
if args.verbose:
        print "Creating the FFT image subsets for each grid point... "


for n,i in enumerate(Pontos):
    Point_id=str(n+1)
    npz_tar_file = fileout + str(RunId) + "_FFT_"+Point_id+".tar.gz"
    tar = tarfile.open(npz_tar_file, "w")
    imgs,lons,lats=CSAR.GetFFTBoxes(i,img,lon,lat,offset,shift)
    for m,j in enumerate(imgs):
        FFTid=str(n+1)+"."+str(m+1)
        npzOut=fileout+str(RunId)+"_FFT_"+FFTid+".npz"
        #print npzOut
        np.savez(npzOut, lons=lons[m], lats=lats[m], imgs=imgs[m])
        tar.add( npzOut, os.path.basename(npzOut) )
        os.remove (npzOut)
    tar.close()
if args.verbose:
        print "The FFT .npz files were successfully created !!! "




######### END HERE =============================================
# @TODO  Create here xml with metada for WINGS



