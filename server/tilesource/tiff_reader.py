__author__ = 'dhanannjay.deo'

"""
Code to use pylibtiff, a wraper for libtiff 4.03 to extract tiles without
uncompressing them.

On windows requires C:\Python27\Lib\site-packages\libtiff in PATH, on might
require that in LD_LIBRARY_PATH
"""

import base64
import os

from xml.etree import cElementTree as ET

from libtiff import TIFF

from libtiff.libtiff_ctypes import libtiff
from libtiff.libtiff_ctypes import c_ttag_t

import ctypes

from ctypes import create_string_buffer

import logging
logger = logging.getLogger('slideatlas')


class TileReader():

    def __init__(self):
        self.jpegtable_size = ctypes.c_uint16()
        self.buf = ctypes.c_voidp()
        self.jpegtables = None
        self.dir = 0
        self.levels = {}
        self.isBigTIFF = False
        self.barcode = ""
        self.tif = None

    def close(self):
        if self.tif:
            self.tif.close()
            self.tif = None

    def __del__(self):
        pass

    def select_dir(self, dir):
        """
        :param dir: Number of Directory to select
        """
        libtiff.TIFFSetDirectory(self.tif, dir)
        self.dir = libtiff.TIFFCurrentDirectory(self.tif).value

        # Check if the operation was successful
        if self.dir != dir:
            raise Exception("Level not stored in file")

        self.update_dir_info()

    def _read_JPEG_tables(self):
        """
        """
        libtiff.TIFFGetField.argtypes = libtiff.TIFFGetField.argtypes[
            :2] + [ctypes.POINTER(ctypes.c_uint16), ctypes.POINTER(ctypes.c_void_p)]
        r = libtiff.TIFFGetField(
            self.tif, 347, self.jpegtable_size, ctypes.byref(self.buf))
        assert(r == 1)
        self.jpegtables = ctypes.cast(self.buf, ctypes.POINTER(ctypes.c_ubyte))
        #logger.debug('Size of jpegtables: %d', self.jpegtable_size.value)
        libtiff.TIFFGetField.argtypes = [TIFF, c_ttag_t, ctypes.c_void_p]

    def extract_all_tiles(self):
        """
        Assumes that tile metadata as been read for the current directory
        """

        logger.debug('Extracting all tiles .. in directory: %d', self.dir)
        cols = self.width / self.tile_width + 1
        rows = self.height / self.tile_height + 1

        for tiley in range(rows):
            for tilex in range(cols):
                tilename = "tile_%d_%d_%d.jpg" % (tiley*cols + tilex,
                                                  tilex, tiley)
                fout = open(tilename, "wb")
                self.dump_tile(tilex * self.tile_width,
                               tiley * self.tile_height, fout)
                fout.close()
                logger.debug('Writing %s', tilename)

    def parse_image_description(self):

        self.meta = self.tif.GetField("ImageDescription")

        if self.meta == None:
            # Missing meta information (typical of zeiss files)
            # Verify that the levels exist
            logger.warning('No ImageDescription in file')
            return

        try:
            xml = ET.fromstring(self.meta)

            # Parse the string for BigTIFF format
            descstr = xml.find(
                ".//*[@Name='DICOM_DERIVATION_DESCRIPTION']").text
            if descstr.find("useBigTIFF=1") > 0:
                self.isBigTIFF = True

            # Parse the barcode string
            self.barcode = base64.b64decode(
                xml.find(".//*[@Name='PIM_DP_UFS_BARCODE']").text)
            # self.barcode["words"] = self.barcode["str"].split("|")
            # self.barcode["physician_id"],  self.barcode["case_id"]= self.barcode["words"][0].split(" ")
            # self.barcode["stain_id"] = self.barcode["words"][4]

            logger.debug(self.barcode)

            # Parse the attribute named "DICOM_DERIVATION_DESCRIPTION"
            # tiff-useBigTIFF=1-clip=2-gain=10-useRgb=0-levels=10003,10002,10000,10001-q75;PHILIPS
            # UFS V1.6.5574
            descstr = xml.find(
                ".//*[@Name='DICOM_DERIVATION_DESCRIPTION']").text
            if descstr.find("useBigTIFF=1") > 0:
                self.isBigTIFF = True

            # logger.debug(descstr)

            for b in xml.findall(".//DataObject[@ObjectType='PixelDataRepresentation']"):
                level = int(
                    b.find(".//*[@Name='PIIM_PIXEL_DATA_REPRESENTATION_NUMBER']").text)
                columns = int(
                    b.find(".//*[@Name='PIIM_PIXEL_DATA_REPRESENTATION_COLUMNS']").text)
                rows = int(
                    b.find(".//*[@Name='PIIM_PIXEL_DATA_REPRESENTATION_ROWS']").text)
                self.levels[level] = [columns, rows]

            self.embedded_images = {}
            # Extract macro and label images
            for animage in xml.findall(".//*[@ObjectType='DPScannedImage']"):
                typestr = animage.find(".//*[@Name='PIM_DP_IMAGE_TYPE']").text
                if typestr == "LABELIMAGE":
                    self.embedded_images["label"] = animage.find(
                        ".//*[@Name='PIM_DP_IMAGE_DATA']").text
                    pass
                elif typestr == "MACROIMAGE":
                    self.embedded_images["macro"] = animage.find(
                        ".//*[@Name='PIM_DP_IMAGE_DATA']").text
                    pass
                elif typestr == "WSI":
                    pass
                else:
                    logger.error('Unforeseen embedded image: %s', typestr)

                #columns = int(b.find(".//*[@Name='PIIM_PIXEL_DATA_REPRESENTATION_COLUMNS']").text)

            if descstr.find("useBigTIFF=1") > 0:
                self.isBigTIFF = True

        except Exception as E:
            logger.warning('Image Description failed for valid Philips XML because %s', E.message)

    def get_embedded_image(self, imagetype):
        """

        """
        return self.embedded_images[imagetype]

    def set_input_params(self, params):
        """
        The source specific input parameters
        right now just a pointer to the file
        """

        self.tif = TIFF.open(params["fname"], "r")
        self.params = params
        self.name = os.path.basename(self.params["fname"])

        self.tile_width = self.tif.GetField("TileWidth")
        self.tile_height = self.tif.GetField("TileLength")

        self._read_JPEG_tables()

        # Get started with first image in the dir
        if "dir" in params:
            self.select_dir(params["dir"])
        else:
            self.select_dir(self.dir)  # By default zero

    def get_tile_from_number(self, tileno, fp):
        """
        This function does something.

        :param tileno: number of tile to fetch
        :param fp: file pointer to which tile data is written
        :returns:  int -- the return code.
        :raises: AttributeError, KeyError
        """
        # Getting a single tile
        tile_size = libtiff.TIFFTileSize(self.tif, tileno)

        # logger.debug('TileSize: %s', tile_size.value)
        if not isinstance(tile_size, (int, long)):
            tile_size = tile_size.value

        tmp_tile = create_string_buffer(tile_size)

        r2 = libtiff.TIFFReadRawTile(self.tif, tileno, tmp_tile, tile_size)
        # logger.debug('Valid size in tile: %s', r2.value)
        # Experiment with the file output

        fp.write(
            ctypes.string_at(self.jpegtables, self.jpegtable_size.value)[:-2])
        # Write padding
        padding = "%c" % (255) * 4
        fp.write(padding)
        fp.write(ctypes.string_at(tmp_tile, r2)[2:])
        if isinstance(r2, (int, long)):
            return r2
        return r2.value

    def _get_raw_tile_from_number(self, tilenum):
        """
        Gets the jpeg bitstream
        """
        tile_size = libtiff.TIFFTileSize(self.tif, tileno)

        # logger.debug('TileSize: %s', tile_size.value)
        if not isinstance(tile_size, (int, long)):
            tile_size = tile_size.value

        tmp_tile = create_string_buffer(tile_size)

        r2 = libtiff.TIFFReadRawTile(self.tif, tileno, tmp_tile, tile_size)
        # logger.debug('Valid size in tile: %s', r2.value)
        # Experiment with the file output

        fp.write(
            ctypes.string_at(self.jpegtables, self.jpegtable_size.value)[:-2])
        # Write padding
        padding = "%c" % (255) * 4
        fp.write(padding)
        fp.write(ctypes.string_at(tmp_tile, r2)[2:])


    def tile_number(self, x, y):
        """
        Returns tile number from current directory

        :param x: x coordinates of an example pixel in the tile
        :type y: y coordinates of an example pixel in the tile
        :returns:  int -- the return code.
        """

        if libtiff.TIFFCheckTile(self.tif, x, y, 0, 0) == 0:
            return -1
        else:
            tileno = libtiff.TIFFComputeTile(self.tif, x, y, 0, 0)
            if isinstance(tileno, (int, long)):
                return tileno

            return tileno.value

    def dump_tile(self, x, y, fp):
        """
        Returns compressed image tile data (jpeg)containing specified x and y
        coordinates

        :param x: x coordinates of an example pixel in the tile
        :type y: y coordinates of an example pixel in the tile
        :param fp: file pointer to which tile data is written
        :returns:  int -- the return code.
        :raises: AttributeError, KeyError
        """
        # Getting a single tile
        tileno = self.tile_number(x, y)
        if tileno < 0:
            return 0
        else:
            return self.get_tile_from_number(tileno, fp)

    def update_dir_info(self):
        """
        Reads width / height etc
        Must be called after the set_input_params is called
        """
        self.width = self.tif.GetField("ImageWidth")
        self.height = self.tif.GetField("ImageLength")

        # Grab the image dimensions through the metadata

        self.num_tiles = libtiff.TIFFNumberOfTiles(self.tif)
        if not isinstance(self.num_tiles, (int, long)):
            self.num_tiles = self.num_tiles.value

        self._read_JPEG_tables()
        #xml = ET.fromstring(tif.GetField("ImageDescription"))
        #self.image_width = int(xml.find(".//*[@Name='PIM_DP_IMAGE_COLUMNS']").text)
        #self.image_height = int(xml.find(".//*[@Name='PIM_DP_IMAGE_ROWS']").text)

        #self.image_width = tif.GetField("ImageWidth")
        #self.image_length = tif.GetField("ImageLength")
        # logger.debug('%s', tif.GetField('ImageDescription'))

if __name__ == "__main__":
    # for i in ["d:\\data\\phillips\\20140313T180859-805105.ptif","d:\\data\\phillips\\20140313T130524-183511.ptif"]:
    #    list_tiles(0,fname=i)
    # test_embedded_images(fname="/home/dhan/data/phillips/20140313T180859-805105.ptif")
    # write_svg(toextract=True, fname="/home/dhan/data/phillips/20140313T180859-805105.ptif")
    # write_svg(toextract=True, fname="d:\\data\\phillips\\20140313T180859-805105.ptif")
    test_barcode()
