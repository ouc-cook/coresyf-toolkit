#!/usr/bin/python2
import os
from osgeo import ogr, osr, gdal
from coresyftools.tool import CoReSyFTool
from sridentify import Sridentify


DEGREE_CRS_CODE = 4326
METRE_CRS_CODE = 3857


def read_shapefile(folder_path):
    '''
    It opens a folder with a shapefile and returns an handle to the
    OGRDataSource (a GDAL OGR object with the shapefile data).

    :param str folder_path: path of folder containing a shapefile.
    '''
    # Get main file of the shapefile
    input_list = [os.path.join(folder_path, x) for x in os.listdir(folder_path)
                  if x.endswith(".shp")]
    if not input_list:
        raise IOError("Shapefile not found in '%s'!" % folder_path)
    shapefile_shp = input_list[0]

    driver = ogr.GetDriverByName('ESRI Shapefile')
    data_source = driver.Open(shapefile_shp, 0)  # 0 means read-only.
    if not data_source:
        raise IOError("Error. Unable to open shapefile at '%s'!" % folder_path)
    return data_source


def get_shapefile_polygon_extent(data_source):
    """
    Retrieves the extent of the shapefile represented as OGR:Polygon.

    :param obj data_source: a shapefile represented as a OGR:DataSource object.
    """
    layer = data_source.GetLayer()
    extent = layer.GetExtent()
    polygon_spatial_ref = layer.GetSpatialRef()

    # Create a Polygon from the extent tuple
    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(extent[0], extent[2])
    ring.AddPoint(extent[1], extent[2])
    ring.AddPoint(extent[1], extent[3])
    ring.AddPoint(extent[0], extent[3])
    ring.AddPoint(extent[0], extent[2])
    ogr_polygon = ogr.Geometry(ogr.wkbPolygon)
    ogr_polygon.AddGeometry(ring)
    ogr_polygon.AssignSpatialReference(polygon_spatial_ref)
    return ogr_polygon


def get_datasource_epsg(data_source):
    '''
    Retrieves the ESPG Code of a GDAL/OGR datasource CRS (Coordinate Reference
    System).

    :param obj data_source: must be the result of GDAL/OGR Open applied to the
                            respective data.
    '''
    if isinstance(data_source, ogr.DataSource):  # Vector
        name = data_source.GetName()
        in_layer = data_source.GetLayer()
        spatial_ref = in_layer.GetSpatialRef()
        projection_wkt = spatial_ref.ExportToWkt()
    elif isinstance(data_source, gdal.Dataset):  # Raster
        name = data_source.GetDescription()
        projection_wkt = data_source.GetProjectionRef()
    else:
        raise TypeError("Input is not of ogr.DataSource or gdal.Dataset type!")

    sridentify_obj = Sridentify(prj=projection_wkt)
    epsg_code = sridentify_obj.get_epsg()
    if not epsg_code:
        raise ValueError("Error. Unable to get ESPG code of datasource '%s'." %
                         name)
    return epsg_code


def apply_buffer_to_polygon(polygon, buffer, crs_buffer):
    '''
    Applies a specific buffer to a polygon geometry. It checks if polygon and
    buffer have the same Spatial reference, converts the buffer (if required)
    and apply it to the polygon geometry.
    :param obj polygon: OGR geometry with polygon extent.
    :param int buffer: buffer in buffer CRS units
    :param int crs_buffer: EPSG code of the buffer CRS.
    '''
    polygon_copy = polygon.Clone()
    sr_polygon = polygon_copy.GetSpatialReference()
    sr_buffer = osr.SpatialReference()
    sr_buffer.ImportFromEPSG(crs_buffer)

    if sr_buffer.IsSame(sr_polygon):
        polygon_with_buffer = polygon_copy.Buffer(buffer, 0)
    else:
        polygon_copy.TransformTo(sr_buffer)
        polygon_with_buffer = polygon_copy.Buffer(buffer, 0)
        polygon_with_buffer.TransformTo(sr_polygon)
    return polygon_with_buffer


def get_raster_resolution(data_source):
    '''
    Retrieves information about the resolution (meters/pixel or degrees/pixel)
    and the EPSG code of a raster.

    :param obj data_source: GDAL datasource of a raster.
    Return value: the resolution of the raster.
    '''
    transform = data_source.GetGeoTransform()
    resolution = abs(transform[1])
    return resolution


def buffer_to_raster_units(raster_resolution, buffer):
    '''
    Converts the units of the buffer (given in pixels) to the units of the
    image (given either in meters or degrees).
    :param float raster_resolution: raster resolution in units/pixel
    :param int buffer: buffer in pixels.
    '''
    return raster_resolution*buffer


class CoresyfImageCrop(CoReSyFTool):

    def crop_raster(self, polygon_extent, output_crs, input_path, output_path):
        '''
        Crops the image specified by input_raster using the limits defined in
        polygon_extent.

        :param obj polygon_extent: POLYGON object to be used for crop limits.
        :param int output_crs: EPSG code of the CRS of the output raster.
        :param str input_path: path to the image to be cropped.
        :param str output_path: the output file path.
        '''
        in_out_bindings = {'Ssource': input_path, 'Ttarget': output_path}
        envelope = polygon_extent.GetEnvelope()
        bounds = "{} {} {} {}".format(str(envelope[0]), str(envelope[2]),
                                      str(envelope[1]), str(envelope[3]))

        command_template = "gdalwarp -t_srs EPSG:{} -te {}".format(
            str(output_crs), bounds)
        command_template += ' {Ssource} {Ttarget}'
        self.invoke_shell_command(command_template, **in_out_bindings)

    def run(self, bindings):
        raster_path = bindings['Ssource']
        output_path = bindings['Ttarget']
        grid_path = bindings['Sgrid']
        pbuffer = bindings['Pbuffer']
        pbufferUnits = bindings['PbufferUnits']

        grid_datasource = read_shapefile(grid_path)
        grid_crs = get_datasource_epsg(grid_datasource)
        polygon_extent = get_shapefile_polygon_extent(grid_datasource)

        if pbufferUnits == 'pixels':
            raster_datasource = gdal.Open(raster_path)
            raster_resolution = get_raster_resolution(raster_datasource)
            buffer = buffer_to_raster_units(raster_resolution, pbuffer)
            buffer_crs = get_datasource_epsg(raster_datasource)
        elif pbufferUnits == 'meters':
            buffer = pbuffer
            buffer_crs = METRE_CRS_CODE
        elif pbufferUnits == 'degrees':
            buffer = pbuffer
            buffer_crs = DEGREE_CRS_CODE
        else:
            raise ValueError("Invalid buffer units: '%s'" % pbufferUnits)

        polygon_with_buffer = apply_buffer_to_polygon(polygon_extent, buffer,
                                                      buffer_crs)

        self.crop_raster(polygon_with_buffer, grid_crs,
                         raster_path, output_path)
