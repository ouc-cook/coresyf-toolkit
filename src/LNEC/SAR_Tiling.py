#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

"""
=====================================================================================================
 Co-ReSyF Research Application: Image Processing and Subsets definition
				 
 Authors: Florent Birrien and Alberto Azevedo and Francisco Sancho 
 Date: July/2017
 Last update: Sept/2017
=====================================================================================================
"""
#
import os,sys,shutil
#
import numpy as np
#
import Toolbox.CSAR_Classes as CL
import Toolbox.CSAR_Utilities as UT
import Toolbox.CSAR_ImageProcessing as IP
import Toolbox.CSAR_Subsets as SUB
#

#-------------------
# input parameters
#-------------------
SubsetsParameters, ImageParameters, args, verbose = IP.InputSubsetParameters()

#**********************************
#
#  Pre-processing step
#
#**********************************

# clean old directories and create new ones
if os.path.isdir('Output'):
	shutil.rmtree('Output')

# create new directory and subdirectories 
Main_Dir, Sub_Dir = ['Output'], ['SubsetSpectra', 'Results', 'Bathymetry']
UT.CreateDirectories(Main_Dir, Sub_Dir); 
#------------
# read image
#------------
if verbose:
	print '|------------------------------------------------|'
	print '| 	Read and Process SAR image		 |'
	print '|------------------------------------------------|'
coordinates, image, pixelresolution = IP.ReadSARImg(ImageParameters)
FlagFlip = IP.CheckImageOrientation(coordinates)			# check whether preprocessing image flip process affects direction estimate
data = CL.Subset(0, image, coordinates, pixelresolution, FlagFlip)	# store main data (image, coordinates) as list
if verbose:
	print 'nb of pixels (x,y)', coordinates.easting.shape[0], coordinates.northing.shape[1]
	print 'pixel resolution (m)', pixelresolution

# npz files to (1) save processed and image coordinates and (2) save parameters
UT.Create_Image_Parameters_TransferFile(SubsetsParameters, ImageParameters, data)
#UT.CreateImageParametersNPZ(parameters,data)

#---------------------
# read grid points
#---------------------
if verbose:
	print '|--------------------------------|'
	print '| 	Read Grid Points         |'
	print '|--------------------------------|'
Points, flagbathy = UT.ReadGridPoints(args, coordinates)

if verbose:
	print 'number of grid points', Points.shape[0]

#------------------------------
# inversion crucial parameters
#------------------------------

# check if enough data are available for further computation (Tp and bathymetry)
if (not flagbathy) and (args.Tp == 0):
	sys.exit("not enough input data (bathymetry/Tp) to perform bathymetry inversion")

#-------------------------
# get subset dimensions
#-------------------------
dimension = SUB.GetBoxDim(SubsetsParameters, data)	

#---------------------------------------------------------------------------
# parallelised and run the Spectrum/Inversion scripts for each point subset
#---------------------------------------------------------------------------
Spectra = []; wavelength=[]; bathymetry = []; ComputationPoints = []; 

if verbose:
	print '|-------------------------------|'
	print '| 	Create Subsets		|'
	print '|-------------------------------|'

for index, point in enumerate(Points):  
	#***********************
	# Subset definitions
	#***********************
	# point indices (related to image pixels)
	Point = np.array([point.IndexEasting, point.IndexNorthing])
	
	# gather subset data	
	Subsetparameters = CL.SubsetParameters(Point, SubsetsParameters.DomainDimension, SubsetsParameters.FlagPowerofTwo, SubsetsParameters.Shift, SubsetsParameters.BoxNb)
	
	# main subset
        subset = SUB.GetImageSubset(Subsetparameters, data, dimension)

        # computation subsets (5 or 9 boxes)
        Subsets = SUB.GetFFTBoxes(Subsetparameters, data, dimension)
	
	# store data
	UT.Create_Subset_TransferFile(index, SubsetsParameters, point, Subsets, args.output)

