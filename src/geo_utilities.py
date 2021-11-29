""" Module that collects variety utility functions for geospatial programming """

import functools
import glob
import os
import time
from functools import lru_cache

import fiona
from osgeo import gdal, osr, ogr
from pyproj import Proj, transform
from shapely.geometry import shape, mapping
from shapely.ops import cascaded_union

import ogr2ogr


def time_decorator(func):
    """ Decorator that prints information about time of function execution """

    @functools.wraps(func)
    def time_wrapper(*args, **kwargs):
        start_time = time.time()
        print("\n0. Czas rozpoczęcia wykonywania funkcji '" + func.__name__ + "': " +
              time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time)))

        # Wykonujemy główną fukcję
        ret_vals = func(*args, **kwargs)

        time_passed = time.time() - start_time
        print("\n1. Łączny czas wykonywania funkcji '" + func.__name__ + "': {:.2f} sekundy".format(time_passed))

        return ret_vals

    return time_wrapper


@time_decorator
def compress_imgs(img_form, comp_alg, comp_pred):
    """ Function that compress images of given format (e.g. Gtiff) using given compression algorithm (e.g. LZW)
     and predictor of compression (e.g. 2)"""

    translateoptions = gdal.TranslateOptions(gdal.ParseCommandLine("-of " + img_form + " -co COMPRESS= " + comp_alg +
                                                                   " -co PREDICTOR=" + comp_pred + " -co TILED=YES"))
    curr_tif = "org_img.tif"
    gdal.Translate("comp_img.tif", curr_tif, options=translateoptions)


def create_coords_transform(in_epsg, out_epsg, change_map_strateg=False):
    """ Function that creates object that transforms geographical coordinates """

    # Zmieniamy system koordynatow dla gmin
    in_sp_ref = osr.SpatialReference()
    in_sp_ref.ImportFromEPSG(in_epsg)

    # Zmieniamy mapping strategy, bo koordynaty dla gmin podawane sa w odwrotnej kolejnosc tzw. "starej"
    if change_map_strateg:
        in_sp_ref.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    out_sp_ref = osr.SpatialReference()
    out_sp_ref.ImportFromEPSG(out_epsg)

    # Zmieniamy mapping strategy, bo k0ordynaty dla gmin podawane sa w odwrotnej kolejnosc tzw. "starej"
    if change_map_strateg:
        out_sp_ref.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    return osr.CoordinateTransformation(in_sp_ref, out_sp_ref)


def clear_xml_node(curr_node):
    """ Function that clears unnecessary XML nodes from RAM memory """
    curr_node.clear()

    for ancestor in curr_node.xpath('ancestor-or-self::*'):
        while ancestor.getprevious() is not None:
            del ancestor.getparent()[0]


def raster2geojson():
    """ Function that generalize and vectorise raster GeoTiff file and finally converts it to geojson format """

    base_dir = os.getcwd()
    driver = gdal.GetDriverByName('GTiff')
    in_ds = gdal.Open(base_dir + "\\temp1.tif", gdal.GA_ReadOnly)
    myarray = in_ds.GetRasterBand(1).ReadAsArray()
    myarray[myarray < 0] = 0

    if myarray is None or in_ds is None:
        print("myarray or in_ds is None for:" + base_dir + "\\temp1.tif")

    # Tworzymy pomocniczy obiekt GeoTiff, przypisujemy mu poprawioną macierz i zapisujemy go na dysku
    r = driver.Create(base_dir + "\\temp1.tif", in_ds.RasterXSize, in_ds.RasterYSize, 1, gdal.GDT_Int16,
                      options=['COMPRESS=LZW'])
    r.SetGeoTransform(in_ds.GetGeoTransform())
    r.SetProjection(in_ds.GetProjection())
    r.GetRasterBand(1).WriteArray(myarray)
    # in_ds = None
    # r = None

    # Czekamy 1 sekundę, żeby plik zdążył się zapisać
    time.sleep(1)

    # Otwieramy nowoutworzony plik temp1.tif
    in_ds2 = gdal.Open(base_dir + "\\temp1.tif", gdal.GA_ReadOnly)

    # Generalizujemy nowoutworzony plik do postaci 50m x 50m przy użyciu algorytmu uśredniającego
    raster = gdal.Wrap(base_dir + "\\temp1.tif", in_ds2, format='GTiff', xRes=50, yRes=50,
                       resampleAlg=gdal.GRA_CubicSpline, options=['COMPRESS=LZW'])
    # in_ds2 = None

    myarray2 = raster.GetRasterBand(1).ReadAsArray().astype(float)
    myarray2[myarray2 > 0] = 1

    new_shp_fn = base_dir + "\\test.shp"
    shp_driver = ogr.GetDriverByName('ESRI Shapefile')
    srs = osr.SpatialReference()
    srs.ImportFromWkt(raster.GetProjectionRef())
    out_data_source = shp_driver.CreateDataSource(new_shp_fn)
    out_layer = out_data_source.CreateLayer(new_shp_fn, srs=srs)
    new_field = ogr.FieldDefn('Depth', ogr.OFTInteger)
    out_layer.CreateField(new_field)
    band = raster.GetRasterBand(1)
    band.WriteArray(myarray2)

    # Wektoryzujemy warstwę
    gdal.Polygonize(band, None, out_layer, 0, [], callback=None)
    out_data_source.Destroy()
    # raster = None
    os.remove(base_dir + "\\temp1.tif")
    os.remove(base_dir + "\\temp0.tif")

    # Czekamy 1 sekundę, żeby plik zdążył się zapisać
    time.sleep(1)

    # Laczenie wszystkich shapefilow w jeden laczny plik shp
    os.chdir(base_dir + "\\test")
    shp_list = glob.glob("*.shp")
    meta = fiona.open(shp_list[0]).meta

    with fiona.open("merged_file.shp", 'w', **meta) as output:
        geom_list = [
            [shape(features['geometry']) for features in fiona.open(shp) if features['properties']['Depth'] == 1]
            for shp in shp_list]
        polygons = []

        for lst1 in geom_list:
            polygons += lst1

        union = cascaded_union(polygons)
        output.write({'geometry': mapping(union), 'properties': {'Depth': 1}})

    # Upraszczamy shapefile, żeby zmniejszyć jego wagę
    ogr2ogr.main(["", "-f", "ESRI Shapefile", 'merged_file_ligth.shp', 'merged_file.shp', '-simplify', "50", "-lco",
                  "ENCODING=Windows-1250"])

    # Zapisujemy uzyskany plik jako GEOJSON
    # Opcja "RFC7946=YES" zostala dodana, żeby generował się plik geojson we właściwym formacie
    # Opcja "COORDINATE_PRECISION=5" zostala dodana, żeby koordynaty miały precyzję pięciu miejsc po przecinku, czyli
    # mniej więcej 1 metra
    ogr2ogr.main(["", "-f", "GeoJSON", "test.geojson", "merged_file_light.shp", "-lco", "RFC7946=YES", "-lco",
                  "COORDINATE_PRECISION=4"])


@lru_cache
def get_sectors_params(sekts_num):
    """ Calculating basic parameters of sectors """
    # Ustalamy podstawowe parametry
    plnd_max_szer = 55
    plnd_min_szer = 48
    sekt_szer = (plnd_max_szer - plnd_min_szer) / sekts_num
    plnd_min_dl = 13
    plnd_max_dl = 25
    sekt_dl = (plnd_max_dl - plnd_min_dl) / sekts_num

    return sekt_szer, sekt_dl, plnd_min_szer, plnd_min_dl


def get_sector_codes(poly_centr_y, poly_centr_x, sekts_num):
    """ Function that returns sector code for given coordinates """

    # Wyliczamy finalny kod sektora
    sekt_szer, sekt_dl, plnd_min_szer, plnd_min_dl = get_sectors_params(sekts_num)
    c_sekt_szer = ((poly_centr_y - plnd_min_szer) / sekt_szer).astype(int)
    c_sekt_dl = ((poly_centr_x - plnd_min_dl) / sekt_dl).astype(int)
    return c_sekt_szer, c_sekt_dl


def convert_coords(all_coords, in_system, out_system):
    """ Function that converts multiple coordinates between given systems """

    in_proj = Proj('epsg:' + in_system)
    out_proj = Proj('epsg:' + out_system)
    return transform(in_proj, out_proj, all_coords[:, 0], all_coords[:, 1])
