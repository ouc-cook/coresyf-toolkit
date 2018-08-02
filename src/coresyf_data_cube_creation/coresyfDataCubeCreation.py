# coding: utf-8
# ! python2
"""This module collects function to creates 3D data cube of grid data.

The data cube is a 3D data structure grid with following axes:

    1. time
    2. columns
    3. rows

The 3D data structure is a NetCDF file. Each slice of this axes is array of data for one day.
The grid structure is defined by columns and rows with additional dimensions.
"""

__author__ = "Julius Schroeder"
__version__ = "0.0.1"
__copyright__ = "Copyright 2018, MaREI Centre for Marine and Renewable Energy"

# import python modules
import dateutil.parser
import glob
import itertools
import logging
import numpy as np
import os
import rasterio as rio
import sys
import time



from collections import namedtuple
from dateutil.parser import parse
from pathlib2 import Path

# import third party modules
from netCDF4 import Dataset, date2num

from coresyftools.tool import CoReSyFTool


def get_inputs(folder, data="", mask="", extension=".img"):
    """Find inputs files in folder by names and extention.
    Inputs are matched by date parsed from file name.

    Parameters
    ----------

    folder: str
        Path of folder to search in

    data: str
        Data file name

    mask: str
        Data file name

    extension: str
        File type extension
        Default: ".img"

    Returns
    -------
    inputs: list
        List contains date and matched mask and data file path as tuple.

    Example
    -------
    > get_inputs("data/")
    """
    # get list of all files with extension
    inputs = Path(folder).glob("*{}".format(extension))

    # get acquisition date
    dated_inputs = []
    for input in inputs:
        name = input.name
        parts = name.replace("_", "-").split("-")

        for p in parts:
            try:
                date = parse(p)
                break  # stop searching after first found
            except ValueError:
                pass
        dated_inputs.append(tuple([date, input]))

    data_inputs = []
    mask_inputs = []
    for date, input in dated_inputs:
        if data in str(input):
            data_inputs.append(tuple([date, input]))
        elif mask in str(input):
            mask_inputs.append(tuple([date, input]))

    # match data and mask by date
    Pair = namedtuple('InputPair', 'date, data, mask')
    matched_pairs = [
        Pair(date=data[0], data=data[1], mask=mask[1])
        for data in data_inputs
        for mask in mask_inputs
        if data[0] == mask[0]
    ]

    sorted_pairs = sorted(matched_pairs, key=lambda pair: pair.date, reverse=True)

    return sorted_pairs


def create_stack(template_pair, ds_path, variables, dtype='float32'):
    """This open a NetCDF4 file and creates basic stack structure.

    Parameters
    ----------

    template: img path

    ds_path: string
        Destination Path for stack file.

    Returns
    -------
    stack: file object
        Stack as open file handle.

    """

    dim_stacking = "date"

    # open target file
    try:
        stack = Dataset(ds_path, 'w', format="NETCDF4")
    except IOError:
        raise

    data_path = str(template_pair.data)
    mask_path = str(template_pair.mask)
    with rio.open(data_path) as data, rio.open(mask_path) as mask:

        # get coordinates
        start_x = data.transform[2]
        stop_x = start_x + (data.width * data.transform[0])
        print start_x, stop_x

        stop_y = data._transform[3]
        start_y = data._transform[3] - (data.height * data.transform[0])
        print start_y, stop_y



        temp_dim_lat = np.linspace(start_y, stop_y, data.width)
        temp_dim_lon = np.linspace(start_x, stop_x, data.height)

        # get meta data
        no_data = data.nodata

    # create dimmensions
    stack.createDimension(dim_stacking, None)
    stack.createDimension("lat", len(temp_dim_lat))
    stack.createDimension("lon", len(temp_dim_lon))

    # create date variable in order to create stack
    date = stack.createVariable(dim_stacking, "i8", (dim_stacking,))
    date.units = "days since 1-01-01 00:00:00 UTC"
    date.calendar = "gregorian"

    stack_lat = stack.createVariable("lat", dtype, ("lat",))
    stack_lon = stack.createVariable("lon", dtype, ("lon",))

    stack_lat[:] = temp_dim_lat
    stack_lon[:] = temp_dim_lon

    # create variables
    for name in variables:
        stack_var = stack.createVariable(
            name,
            datatype=dtype,
            dimensions=("date", "lon", "lat"),
            zlib=True,
            fill_value=no_data
        )

    # set meta data
    stack.description = "3D data cube of {}".format(" and ".join(variables))
    stack.history = "Created " + time.ctime(time.time())
    stack.crs = "WGS 84"
    stack.epsg = "EPSG:4326"
    stack_lat.units = "degrees north"
    stack_lon.units = "degrees east"

    return stack


def stacking(inputs, variables, output):
    """This loob over inputs, extract data, write slices to file.

    Parameters
    ----------

    inputs: list of tuple
        List of tuples holding input files and date e.g. (date, data1, data2).

    variables: list
        Variables to stack. Define data an mask variable from input.

    output: string
        Path to the 3D file.

    Side effect
    -------
    Create 3D stack file from inputs file.

    Example
    -------
    """

    logging.info('Create {} file.'.format(output))
    try:
        # create new stack by using input as template
        stack = create_stack(inputs[0], output, variables)
    except EnvironmentError as e:
        logging.error("Can't create {}".format(output))
        logging.debug((os.strerror(e.errno)))
        raise e

    for index, pair in enumerate(inputs):

        date, data, mask = pair  # unpack input tuple
        logging.info('Extracting data from {}'.format(data))

        with rio.open(str(data)) as data, rio.open(str(mask)) as mask:
            stack_data = stack.variables[variables[0]]
            stack_mask = stack.variables[variables[1]]

            stack_data[index, :, :] = data.read(1)
            stack_mask[index, :, :] = mask.read(1)
            stack.variables["date"][index] = date2num(date, "days since 1-01-01 00:00:00 UTC", 'gregorian')

    stack.close()


class CoReSyFDataCubeCreation(CoReSyFTool):

    def run(self, bindings):

        # parse Parameters
        folder = bindings['Ssource']
        data_name = bindings['Ddata_name']
        mask_name = bindings['Mmask_name']
        extension = bindings['.img']
        variables = tuple(bindings['var'].split(','))
        output = bindings['Ttarget']

        try:
            inputs = get_inputs(folder, data=data_name, mask=mask_name, extension=extension)
        except IOError as e:
            logging.error("No inputs found.".format(output))
            logging.debug((os.strerror(e.errno)))
            sys.exit()

        try:
            stacking(inputs, variables, output)
        except Exception as e:
            raise e
            sys.exit()
