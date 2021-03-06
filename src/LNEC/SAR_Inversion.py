#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

"""
=====================================================================================================
 Co-ReSyF Research Application: Wavelength (or wavelength distribution) inversion to depth
				 
 Authors: Florent Birrien and Alberto Azevedo and Francisco Sancho 
 Date: July/2017
 Last update: Sept/2017
=====================================================================================================
"""

import os, sys
#
import argparse
#
import numpy as np
#
import Toolbox.CSAR_Classes as CL
import Toolbox.CSAR_Utilities as UT
import Toolbox.CSAR_DepthInversion as INV



# input output
parser = argparse.ArgumentParser(description='Co-ReSyF: SAR Bathymetry Research Application')
parser.add_argument('-i', '--input', help='Input computation points files ("Computation#.out" pickle files) for depth inversion', required=True)
parser.add_argument('-o', '--output', help='Output transfer file ("Inversion#.out" pickle files) with inversion points data', required=False)
parser.add_argument('-v', '--verbose', help='Screen comments', action="store_true")
args = parser.parse_args()

# read parameters and point information
fname = args.input
index = int(filter(str.isdigit, fname))
PointInformation = UT.Unpickle_File(fname)
INV_parameters, point = PointInformation.InversionParameters, PointInformation.point

if index==0 and args.verbose:
	print '|----------------------------------------|'
	print '| 	Perform depth inversion		 |'
	print '|----------------------------------------|'

# perform inversion
# parameters
method = INV_parameters.InversionMethod
Tp = float(INV_parameters.HydrodynamicParameters.Tp)

#inversion
if method == 'direct' and (not np.isnan(Tp)):
	Point = INV.DirectDepthInversion(point, Tp)
else:
	sys.exit('Inversion method not defined // check that you provided the mandatory input hydrodynamic data')

#save point information
UT.Create_TransferFile(args,Point,'Inversion')

#clean directory
os.remove(args.input)
