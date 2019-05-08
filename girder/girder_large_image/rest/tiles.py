# -*- coding: utf-8 -*-

#############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#############################################################################

import cherrypy
import os
import re
import six

from girder.api import access, filter_logging
from girder.api.v1.item import Item as ItemResource
from girder.api.describe import describeRoute, Description
from girder.api.rest import filtermodel, loadmodel, setRawResponse, setResponseHeader
from girder.exceptions import RestException
from girder.models.model_base import AccessType
from girder.models.file import File
from girder.models.item import Item

from large_image.constants import TileInputUnits
from large_image.exceptions import TileGeneralException

from ..models.image_item import ImageItem
from .. import loadmodelcache


MimeTypeExtensions = {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/tiff': 'tiff',
}
ImageMimeTypes = list(MimeTypeExtensions)


def _adjustParams(params):
    """
    Check the user agent of a request.  If it appears to be from an iOS device,
    and the request is asking for JPEG encoding (or hasn't specified an
    encoding), then make sure the output is JFIF.

    It is unfortunate that this requires analyzing the user agent, as this
    method if brittle.  However, other browsers can handle non-JFIF jpegs, and
    we do not want to encur the overhead of conversion if it is not necessary
    (converting to JFIF may require colorspace transforms).

    :param params: the request parameters.  May be modified.
    """
    try:
        userAgent = cherrypy.request.headers.get('User-Agent', '').lower()
    except Exception:
        pass
    if params.get('encoding', 'JPEG') == 'JPEG':
        if ('ipad' in userAgent or 'ipod' in userAgent or 'iphone' in userAgent or
                re.match('((?!chrome|android).)*safari', userAgent, re.IGNORECASE)):
            params['encoding'] = 'JFIF'


class TilesItemResource(ItemResource):

    def __init__(self, apiRoot):
        # Don't call the parent (Item) constructor, to avoid redefining routes,
        # but do call the grandparent (Resource) constructor
        super(ItemResource, self).__init__()

        self.resourceName = 'item'
        apiRoot.item.route('POST', (':itemId', 'tiles'), self.createTiles)
        apiRoot.item.route('GET', (':itemId', 'tiles'), self.getTilesInfo)
        apiRoot.item.route('DELETE', (':itemId', 'tiles'), self.deleteTiles)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'thumbnail'),
                           self.getTilesThumbnail)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'region'),
                           self.getTilesRegion)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'pixel'),
                           self.getTilesPixel)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'zxy', ':z', ':x', ':y'),
                           self.getTile)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'images'),
                           self.getAssociatedImagesList)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'images', ':image'),
                           self.getAssociatedImage)
        apiRoot.item.route('GET', ('test', 'tiles'), self.getTestTilesInfo)
        apiRoot.item.route('GET', ('test', 'tiles', 'zxy', ':z', ':x', ':y'),
                           self.getTestTile)
        filter_logging.addLoggingFilter(
            'GET (/[^/ ?#]+)*/item/[^/ ?#]+/tiles/zxy(/[^/ ?#]+){3}',
            frequency=250)
        # Cache the model singleton
        self.imageItemModel = ImageItem()

    @describeRoute(
        Description('Create a large image for this item.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param('fileId', 'The ID of the source file containing the image. '
                         'Required if there is more than one file in the item.',
               required=False)
        .param('notify', 'If a job is required to create the large image, '
               'a nofication can be sent when it is complete.',
               dataType='boolean', default=True, required=False)
    )
    @access.user
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.WRITE)
    @filtermodel(model='job', plugin='jobs')
    def createTiles(self, item, params):
        largeImageFileId = params.get('fileId')
        if largeImageFileId is None:
            files = list(Item().childFiles(item=item, limit=2))
            if len(files) == 1:
                largeImageFileId = str(files[0]['_id'])
        if not largeImageFileId:
            raise RestException('Missing "fileId" parameter.')
        largeImageFile = File().load(largeImageFileId, force=True, exc=True)
        user = self.getCurrentUser()
        token = self.getCurrentToken()
        try:
            return self.imageItemModel.createImageItem(
                item, largeImageFile, user, token,
                notify=self.boolParam('notify', params, default=True))
        except TileGeneralException as e:
            raise RestException(e.args[0])

    @classmethod
    def _parseTestParams(cls, params):
        _adjustParams(params)
        return cls._parseParams(params, False, [
            ('minLevel', int),
            ('maxLevel', int),
            ('tileWidth', int),
            ('tileHeight', int),
            ('sizeX', int),
            ('sizeY', int),
            ('fractal', lambda val: val == 'true'),
            ('encoding', str),
        ])

    @classmethod
    def _parseParams(cls, params, keepUnknownParams, typeList):
        """
        Given a dictionary of parameters, check that a list of parameters are
        valid data types.  The parameters within the list are validated and
        copied to a dictionary by themselves.

        :param params: the dictionary of parameters to validate.
        :param keepUnknownParams: True to copy all parameters, not just those
            in the typeList.  The parameters in the typeList are still
            validated.
        :param typeList: a list of tuples of the form (key, dataType, [outkey1,
            [outkey2]]).  If output keys are used, the original key is renamed
            to the the output key.  If two output keys are specified, the
            original key is renamed to outkey2 and placed in a sub-dictionary
            names outkey1.
        :returns: params: a validated and possibly filtered list of parameters.
        """
        results = {}
        if keepUnknownParams:
            results = dict(params)
        for entry in typeList:
            key, dataType, outkey1, outkey2 = (list(entry) + [None] * 2)[:4]
            if key in params:
                try:
                    if dataType is bool:
                        results[key] = str(params[key]).lower() in (
                            'true', 'on', 'yes', '1')
                    else:
                        results[key] = dataType(params[key])
                except ValueError:
                    raise RestException(
                        '"%s" parameter is an incorrect type.' % key)
                if outkey1 is not None:
                    if outkey2 is not None:
                        results.setdefault(outkey1, {})[outkey2] = results[key]
                    else:
                        results[outkey1] = results[key]
                    del results[key]
        return results

    def _getTilesInfo(self, item, imageArgs):
        """
        Get metadata for an item's large image.

        :param item: the item to query.
        :param imageArgs: additional arguments to use when fetching image data.
        :return: the tile metadata.
        """
        try:
            return self.imageItemModel.getMetadata(item, **imageArgs)
        except TileGeneralException as e:
            raise RestException(e.args[0], code=400)

    def _setContentDisposition(self, item, contentDisposition, mime, subname):
        """
        If requested, set the content disposition and a suggested file name.

        :param item: an item that includes a name.
        :param contentDisposition: either 'inline' or 'attachemnt', otherwise
            no header is added.
        :param mime: the mimetype of the output image.  Used for the filename
            suffix.
        :param subname: a subname to append to the item name.
        """
        if (not item or not item.get('name') or
                mime not in MimeTypeExtensions or
                contentDisposition not in ('inline', 'attachment')):
            return
        filename = os.path.splitext(item['name'])[0]
        if subname:
            filename += '-' + subname
        filename += '.' + MimeTypeExtensions[mime]
        if not isinstance(filename, six.text_type):
            filename = filename.decode('utf8', 'ignore')
        safeFilename = filename.encode('ascii', 'ignore').replace(b'"', b'')
        encodedFilename = six.moves.urllib.parse.quote(filename.encode('utf8', 'ignore'))
        setResponseHeader(
            'Content-Disposition',
            '%s; filename="%s"; filename*=UTF-8\'\'%s' % (
                contentDisposition, safeFilename, encodedFilename))

    @describeRoute(
        Description('Get large image metadata.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.public
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def getTilesInfo(self, item, params):
        # TODO: parse params?
        return self._getTilesInfo(item, params)

    @describeRoute(
        Description('Get test large image metadata.')
    )
    @access.public
    def getTestTilesInfo(self, params):
        item = {'largeImage': {'sourceName': 'test'}}
        imageArgs = self._parseTestParams(params)
        return self._getTilesInfo(item, imageArgs)

    def _getTile(self, item, z, x, y, imageArgs, mayRedirect=False):
        """
        Get an large image tile.

        :param item: the item to get a tile from.
        :param z: tile layer number (0 is the most zoomed-out).
        .param x: the X coordinate of the tile (0 is the left side).
        .param y: the Y coordinate of the tile (0 is the top).
        :param imageArgs: additional arguments to use when fetching image data.
        :param mayRedirect: if True or one of 'any', 'encoding', or 'exact',
            allow return a response whcih may be a redirect.
        :return: a function that returns the raw image data.
        """
        try:
            x, y, z = int(x), int(y), int(z)
        except ValueError:
            raise RestException('x, y, and z must be integers', code=400)
        if x < 0 or y < 0 or z < 0:
            raise RestException('x, y, and z must be positive integers',
                                code=400)
        result = self.imageItemModel._tileFromHash(
            item, x, y, z, mayRedirect=mayRedirect, **imageArgs)
        if result is not None:
            tileData, tileMime = result
        else:
            try:
                tileData, tileMime = self.imageItemModel.getTile(
                    item, x, y, z, mayRedirect=mayRedirect, **imageArgs)
            except TileGeneralException as e:
                raise RestException(e.args[0], code=404)
        setResponseHeader('Content-Type', tileMime)
        setRawResponse()
        return tileData

    @describeRoute(
        Description('Get a large image tile.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param('z', 'The layer number of the tile (0 is the most zoomed-out '
               'layer).', paramType='path')
        .param('x', 'The X coordinate of the tile (0 is the left side).',
               paramType='path')
        .param('y', 'The Y coordinate of the tile (0 is the top).',
               paramType='path')
        .param('redirect', 'If the tile exists as a complete file, allow an '
               'HTTP redirect instead of returning the data directly.  The '
               'redirect might not have the correct mime type.  "exact" must '
               'match the image encoding and quality parameters, "encoding" '
               'must match the image encoding but disregards quality, and '
               '"any" will redirect to any image if possible.', required=False,
               enum=['false', 'exact', 'encoding', 'any'], default='false')
        .produces(ImageMimeTypes)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    # Without caching, this checks for permissions every time.  By using the
    # LoadModelCache, three database lookups are avoided, which saves around
    # 6 ms in tests. We also avoid the @access.public decorator and directly
    # set the accessLevel attribute on the method.
    #   @access.public(cookie=True)
    #   @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    #   def getTile(self, item, z, x, y, params):
    #       return self._getTile(item, z, x, y, params, True)
    def getTile(self, itemId, z, x, y, params):
        _adjustParams(params)
        item = loadmodelcache.loadModel(
            self, 'item', id=itemId, allowCookie=True, level=AccessType.READ)
        # Explicitly set a expires time to encourage browsers to cache this for
        # a while.
        setResponseHeader('Expires', cherrypy.lib.httputil.HTTPDate(
            cherrypy.serving.response.time + 600))
        redirect = params.get('redirect', False)
        if redirect not in ('any', 'exact', 'encoding'):
            redirect = False
        return self._getTile(item, z, x, y, params, mayRedirect=redirect)
    getTile.accessLevel = 'public'
    getTile.cookieAuth = True

    @describeRoute(
        Description('Get a test large image tile.')
        .param('z', 'The layer number of the tile (0 is the most zoomed-out '
               'layer).', paramType='path')
        .param('x', 'The X coordinate of the tile (0 is the left side).',
               paramType='path')
        .param('y', 'The Y coordinate of the tile (0 is the top).',
               paramType='path')
        .produces(ImageMimeTypes)
    )
    @access.public(cookie=True)
    def getTestTile(self, z, x, y, params):
        item = {'largeImage': {'sourceName': 'test'}}
        imageArgs = self._parseTestParams(params)
        return self._getTile(item, z, x, y, imageArgs)

    @describeRoute(
        Description('Remove a large image from this item.')
        .param('itemId', 'The ID of the item.', paramType='path')
    )
    @access.user
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.WRITE)
    def deleteTiles(self, item, params):
        deleted = self.imageItemModel.delete(item)
        # TODO: a better response
        return {
            'deleted': deleted
        }

    @describeRoute(
        Description('Get a thumbnail of a large image item.')
        .notes('Aspect ratio is always preserved.  If both width and height '
               'are specified, the resulting thumbnail may be smaller in one '
               'of the two dimensions.  If neither width nor height is given, '
               'a default size will be returned.  '
               'This creates a thumbnail from the lowest level of the source '
               'image, which means that asking for a large thumbnail will not '
               'be a high-quality image.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param('width', 'The maximum width of the thumbnail in pixels.',
               required=False, dataType='int')
        .param('height', 'The maximum height of the thumbnail in pixels.',
               required=False, dataType='int')
        .param('fill', 'A fill color.  If width and height are both specified '
               'and fill is specified and not "none", the output image is '
               'padded on either the sides or the top and bottom to the '
               'requested output size.  Most css colors are accepted.',
               required=False)
        .param('encoding', 'Thumbnail output encoding', required=False,
               enum=['JPEG', 'PNG', 'TIFF'], default='JPEG')
        .param('contentDisposition', 'Specify the Content-Disposition response '
               'header disposition-type value.', required=False,
               enum=['inline', 'attachment'])
        .produces(ImageMimeTypes)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.public(cookie=True)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def getTilesThumbnail(self, item, params):
        _adjustParams(params)
        params = self._parseParams(params, True, [
            ('width', int),
            ('height', int),
            ('fill', str),
            ('jpegQuality', int),
            ('jpegSubsampling', int),
            ('tiffCompression', str),
            ('encoding', str),
            ('contentDisposition', str),
        ])
        try:
            result = self.imageItemModel.getThumbnail(item, **params)
        except TileGeneralException as e:
            raise RestException(e.args[0])
        except ValueError as e:
            raise RestException('Value Error: %s' % e.args[0])
        if not isinstance(result, tuple):
            return result
        thumbData, thumbMime = result
        self._setContentDisposition(
            item, params.get('contentDisposition'), thumbMime, 'thumbnail')
        setResponseHeader('Content-Type', thumbMime)
        setRawResponse()
        return thumbData

    @describeRoute(
        Description('Get any region of a large image item, optionally scaling '
                    'it.')
        .notes('If neither width nor height is specified, the full resolution '
               'region is returned.  If a width or height is specified, '
               'aspect ratio is always preserved (if both are given, the '
               'resulting image may be smaller in one of the two '
               'dimensions).  When scaling must be applied, the image is '
               'downsampled from a higher resolution layer, never upsampled.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param('left', 'The left column (0-based) of the region to process.  '
               'Negative values are offsets from the right edge.',
               required=False, dataType='float')
        .param('top', 'The top row (0-based) of the region to process.  '
               'Negative values are offsets from the bottom edge.',
               required=False, dataType='float')
        .param('right', 'The right column (0-based from the left) of the '
               'region to process.  The region will not include this column.  '
               'Negative values are offsets from the right edge.',
               required=False, dataType='float')
        .param('bottom', 'The bottom row (0-based from the top) of the region '
               'to process.  The region will not include this row.  Negative '
               'values are offsets from the bottom edge.',
               required=False, dataType='float')
        .param('regionWidth', 'The width of the region to process.',
               required=False, dataType='float')
        .param('regionHeight', 'The height of the region to process.',
               required=False, dataType='float')
        .param('units', 'Units used for left, top, right, bottom, '
               'regionWidth, and regionHeight.  base_pixels are pixels at the '
               'maximum resolution, pixels and mm are at the specified '
               'magnfication, fraction is a scale of [0-1].', required=False,
               enum=sorted(set(TileInputUnits.values())),
               default='base_pixels')

        .param('width', 'The maximum width of the output image in pixels.',
               required=False, dataType='int')
        .param('height', 'The maximum height of the output image in pixels.',
               required=False, dataType='int')
        .param('fill', 'A fill color.  If output dimensions are specified and '
               'fill is specified and not "none", the output image is padded '
               'on either the sides or the top and bottom to the requested '
               'output size.  Most css colors are accepted.', required=False)
        .param('magnification', 'Magnification of the output image.  If '
               'neither width for height is specified, the magnification, '
               'mm_x, and mm_y parameters are used to select the output size.',
               required=False, dataType='float')
        .param('mm_x', 'The size of the output pixels in millimeters',
               required=False, dataType='float')
        .param('mm_y', 'The size of the output pixels in millimeters',
               required=False, dataType='float')
        .param('exact', 'If magnification, mm_x, or mm_y are specified, they '
               'must match an existing level of the image exactly.',
               required=False, dataType='boolean', default=False)
        .param('encoding', 'Output image encoding', required=False,
               enum=['JPEG', 'PNG', 'TIFF'], default='JPEG')
        .param('jpegQuality', 'Quality used for generating JPEG images',
               required=False, dataType='int', default=95)
        .param('jpegSubsampling', 'Chroma subsampling used for generating '
               'JPEG images.  0, 1, and 2 are full, half, and quarter '
               'resolution chroma respectively.', required=False,
               enum=['0', '1', '2'], dataType='int', default='0')
        .param('tiffCompression', 'Compression method when storing a TIFF '
               'image', required=False,
               enum=['raw', 'tiff_lzw', 'jpeg', 'tiff_adobe_deflate'])
        .param('contentDisposition', 'Specify the Content-Disposition response '
               'header disposition-type value.', required=False,
               enum=['inline', 'attachment'])
        .produces(ImageMimeTypes)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
        .errorResponse('Insufficient memory.')
    )
    @access.public(cookie=True)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def getTilesRegion(self, item, params):
        _adjustParams(params)
        params = self._parseParams(params, True, [
            ('left', float, 'region', 'left'),
            ('top', float, 'region', 'top'),
            ('right', float, 'region', 'right'),
            ('bottom', float, 'region', 'bottom'),
            ('regionWidth', float, 'region', 'width'),
            ('regionHeight', float, 'region', 'height'),
            ('units', str, 'region', 'units'),
            ('unitsWH', str, 'region', 'unitsWH'),
            ('width', int, 'output', 'maxWidth'),
            ('height', int, 'output', 'maxHeight'),
            ('fill', str),
            ('magnification', float, 'scale', 'magnification'),
            ('mm_x', float, 'scale', 'mm_x'),
            ('mm_y', float, 'scale', 'mm_y'),
            ('exact', bool, 'scale', 'exact'),
            ('encoding', str),
            ('jpegQuality', int),
            ('jpegSubsampling', int),
            ('tiffCompression', str),
            ('contentDisposition', str),
        ])
        try:
            regionData, regionMime = self.imageItemModel.getRegion(
                item, **params)
        except TileGeneralException as e:
            raise RestException(e.args[0])
        except ValueError as e:
            raise RestException('Value Error: %s' % e.args[0])
        self._setContentDisposition(
            item, params.get('contentDisposition'), regionMime, 'region')
        setResponseHeader('Content-Type', regionMime)
        setRawResponse()
        return regionData

    @describeRoute(
        Description('Get a single pixel of a large image item.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param('left', 'The left column (0-based) of the pixel.',
               required=False, dataType='float')
        .param('top', 'The top row (0-based) of the pixel.',
               required=False, dataType='float')
        .param('units', 'Units used for left and top.  base_pixels are pixels '
               'at the maximum resolution, pixels and mm are at the specified '
               'magnfication, fraction is a scale of [0-1].', required=False,
               enum=sorted(set(TileInputUnits.values())),
               default='base_pixels')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.public(cookie=True)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def getTilesPixel(self, item, params):
        params = self._parseParams(params, True, [
            ('left', float, 'region', 'left'),
            ('top', float, 'region', 'top'),
            ('right', float, 'region', 'right'),
            ('bottom', float, 'region', 'bottom'),
            ('units', str, 'region', 'units'),
        ])
        try:
            pixel = self.imageItemModel.getPixel(item, **params)
        except TileGeneralException as e:
            raise RestException(e.args[0])
        except ValueError as e:
            raise RestException('Value Error: %s' % e.args[0])
        return pixel

    @describeRoute(
        Description('Get a list of additional images associated with a large image.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.public
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def getAssociatedImagesList(self, item, params):
        try:
            return self.imageItemModel.getAssociatedImagesList(item)
        except TileGeneralException as e:
            raise RestException(e.args[0], code=400)

    @describeRoute(
        Description('Get an image associated with a large image.')
        .notes('Because associated images may contain PHI, admin access to '
               'the item is required.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param('image', 'The key of the associated image.', paramType='path')
        .param('width', 'The maximum width of the image in pixels.',
               required=False, dataType='int')
        .param('height', 'The maximum height of the image in pixels.',
               required=False, dataType='int')
        .param('encoding', 'Image output encoding', required=False,
               enum=['JPEG', 'PNG', 'TIFF'], default='JPEG')
        .param('contentDisposition', 'Specify the Content-Disposition response '
               'header disposition-type value.', required=False,
               enum=['inline', 'attachment'])
        .produces(ImageMimeTypes)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.public(cookie=True)
    def getAssociatedImage(self, itemId, image, params):
        _adjustParams(params)
        # We can't use the loadmodel decorator, as we want to allow cookies
        item = loadmodelcache.loadModel(
            self, 'item', id=itemId, allowCookie=True, level=AccessType.READ)
        params = self._parseParams(params, True, [
            ('width', int),
            ('height', int),
            ('jpegQuality', int),
            ('jpegSubsampling', int),
            ('tiffCompression', str),
            ('encoding', str),
            ('contentDisposition', str),
        ])
        try:
            result = self.imageItemModel.getAssociatedImage(item, image, **params)
        except TileGeneralException as e:
            raise RestException(e.args[0], code=400)
        if not isinstance(result, tuple):
            return result
        imageData, imageMime = result
        self._setContentDisposition(
            item, params.get('contentDisposition'), imageMime, image)
        setResponseHeader('Content-Type', imageMime)
        setRawResponse()
        return imageData
