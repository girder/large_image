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

import hashlib
import math
import os
import pathlib
import pickle
import re
import urllib

import cherrypy

import large_image
from girder.api import access, filter_logging
from girder.api.describe import Description, autoDescribeRoute, describeRoute
from girder.api.rest import filtermodel, loadmodel, setRawResponse, setResponseHeader
from girder.api.v1.item import Item as ItemResource
from girder.constants import AccessType, TokenScope
from girder.exceptions import RestException
from girder.models.file import File
from girder.models.item import Item
from girder.utility.progress import setResponseTimeLimit
from large_image.cache_util import strhash
from large_image.constants import TileInputUnits, TileOutputMimeTypes
from large_image.exceptions import TileGeneralError

from .. import loadmodelcache
from ..models.image_item import ImageItem

MimeTypeExtensions = {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/tiff': 'tiff',
}
for key, value in TileOutputMimeTypes.items():
    if value not in MimeTypeExtensions:
        MimeTypeExtensions[value] = key.lower()
ImageMimeTypes = list(MimeTypeExtensions)
EncodingTypes = list(TileOutputMimeTypes.keys()) + [
    'pickle', 'pickle:3', 'pickle:4', 'pickle:5']


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


def _handleETag(key, item, *args, **kwargs):
    """
    Add or check an ETag header.

    :param key: key for making a distinct etag.
    :param item: item used for the item _id and updated timestamp.
    :param max_age: the maximum cache duration.
    :param *args, **kwargs: additional arguments for generating an etag.
    """
    max_age = kwargs.get('max_age', 3600)
    id = str(item['_id'])
    date = item.get('updated', item.get('created'))
    etag = hashlib.md5(strhash(key, id, date, *args, **kwargs).encode()).hexdigest()
    setResponseHeader('ETag', '"%s"' % etag)
    conditions = [str(x) for x in cherrypy.request.headers.elements('If-Match') or []]
    if conditions and not (conditions == ['*'] or etag in conditions):
        raise cherrypy.HTTPError(
            412, 'If-Match failed: ETag %r did not match %r' % (etag, conditions))
    conditions = [str(x).strip('"')
                  for x in cherrypy.request.headers.elements('If-None-Match') or []]
    if conditions == ['*'] or etag in conditions:
        raise cherrypy.HTTPRedirect([], 304)
    # Explicitly set a max-age to recheck the cache after a while
    setResponseHeader('Cache-control', f'public, max-age={max_age}')


def _pickleParams(params):
    """
    Check if the output should be returned as pickled data and adjust the
    parameters accordingly.

    :param params: a dictionary of parameters.  If encoding starts with
        'pickle', numpy format will be requested.
    :return: None if the output should not be pickled.  Otherwise, the pickle
        protocol that should be used.
    """
    if not str(params.get('encoding')).startswith('pickle'):
        return None
    params['format'] = large_image.constants.TILE_FORMAT_NUMPY
    pickle = params['encoding'].split(':')[-1]
    del params['encoding']
    return int(pickle) or 4 if pickle.isdigit() else 4


def _pickleOutput(data, protocol):
    """
    Pickle some data using a specific protocol and return the pickled data
    and the recommended mime type.

    :param data: the data to pickle.
    :param protocol: the pickle protocol level.
    :returns: the pickled data and the mime type.
    """
    return (
        pickle.dumps(data, protocol=min(protocol, pickle.HIGHEST_PROTOCOL)),
        'application/octet-stream')


class TilesItemResource(ItemResource):

    def __init__(self, apiRoot):
        # Don't call the parent (Item) constructor, to avoid redefining routes,
        # but do call the grandparent (Resource) constructor
        super(ItemResource, self).__init__()

        self.resourceName = 'item'
        apiRoot.item.route('POST', (':itemId', 'tiles'), self.createTiles)
        apiRoot.item.route('POST', (':itemId', 'tiles', 'convert'), self.convertImage)
        apiRoot.item.route('GET', (':itemId', 'tiles'), self.getTilesInfo)
        apiRoot.item.route('DELETE', (':itemId', 'tiles'), self.deleteTiles)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'thumbnail'), self.getTilesThumbnail)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'thumbnails'), self.listTilesThumbnails)
        apiRoot.item.route('DELETE', (':itemId', 'tiles', 'thumbnails'), self.deleteTilesThumbnails)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'region'), self.getTilesRegion)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'tile_frames'), self.tileFrames)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'tile_frames', 'quad_info'),
                           self.tileFramesQuadInfo)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'pixel'), self.getTilesPixel)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'histogram'), self.getHistogram)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'bands'), self.getBandInformation)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'zxy', ':z', ':x', ':y'), self.getTile)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'fzxy', ':frame', ':z', ':x', ':y'),
                           self.getTileWithFrame)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'images'), self.getAssociatedImagesList)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'images', ':image'),
                           self.getAssociatedImage)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'images', ':image', 'metadata'),
                           self.getAssociatedImageMetadata)
        apiRoot.item.route('GET', ('test', 'tiles'), self.getTestTilesInfo)
        apiRoot.item.route('GET', ('test', 'tiles', 'zxy', ':z', ':x', ':y'), self.getTestTile)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'dzi.dzi'), self.getDZIInfo)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'dzi_files', ':level', ':xandy'),
                           self.getDZITile)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'internal_metadata'),
                           self.getInternalMetadata)
        # Logging rate limiters
        filter_logging.addLoggingFilter(
            'GET (/[^/ ?#]+)*/item/[^/ ?#]+/tiles/zxy(/[^/ ?#]+){3}',
            frequency=250, duration=10)
        filter_logging.addLoggingFilter(
            'GET (/[^/ ?#]+)*/item/[^/ ?#]+/tiles/fzxy(/[^/ ?#]+){3}',
            frequency=250, duration=10)
        filter_logging.addLoggingFilter(
            'GET (/[^/ ?#]+)*/item/[^/ ?#]+/tiles/dzi_files(/[^/ ?#]+){2}',
            frequency=250, duration=10)
        filter_logging.addLoggingFilter(
            'GET (/[^/ ?#]+)*/item/[^/ ?#]+/tiles/region',
            frequency=100, duration=10)
        # Cache the model singleton
        self.imageItemModel = ImageItem()

    @describeRoute(
        Description('Create a large image for this item.')
        .param('itemId', 'The source item.', paramType='path')
        .param('fileId', 'The source file containing the image.  Required if '
               'there is more than one file in the item.', required=False)
        .param('force', 'Always use a job to create the large image.',
               dataType='boolean', default=False, required=False)
        .param('notify', 'If a job is required to create the large image, '
               'a nofication can be sent when it is complete.',
               dataType='boolean', default=True, required=False)
        .param('localJob', 'If true, run as a local job; if false, run via '
               'the remote worker', dataType='boolean', required=False)
        .param('tileSize', 'Tile size', dataType='int', default=256,
               required=False)
        .param('compression', 'Internal compression format', required=False,
               enum=['none', 'jpeg', 'deflate', 'lzw', 'zstd', 'packbits', 'webp', 'jp2k'])
        .param('quality', 'JPEG compression quality where 0 is small and 100 '
               'is highest quality', dataType='int', default=90,
               required=False)
        .param('level', 'Compression level for deflate (zip) or zstd.',
               dataType='int', required=False)
        .param('predictor', 'Predictor for deflate (zip) or lzw.',
               required=False, enum=['none', 'horizontal', 'float', 'yes'])
        .param('psnr', 'JP2K compression target peak-signal-to-noise-ratio '
               'where 0 is lossless and otherwise higher numbers are higher '
               'quality', dataType='int', required=False)
        .param('cr', 'JP2K target compression ratio where 1 is lossless',
               dataType='int', required=False)
        .param('concurrent', 'Suggested number of maximum concurrent '
               'processes to use during conversion.  Values less than or '
               'equal to 0 use the number of logical cpus less that value.  '
               'Default is -2.', dataType='int', required=False)
    )
    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.WRITE)
    @filtermodel(model='job', plugin='jobs')
    def createTiles(self, item, params):
        if 'concurrent' in params:
            params['_concurrency'] = params.pop('concurrent')
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
        notify = self.boolParam('notify', params, default=True)
        params.pop('notify', None)
        localJob = self.boolParam('localJob', params, default=None)
        params.pop('localJob', None)
        try:
            return self.imageItemModel.createImageItem(
                item, largeImageFile, user, token,
                createJob='always' if self.boolParam('force', params, default=False) else True,
                notify=notify,
                localJob=localJob,
                **params)
        except TileGeneralError as e:
            raise RestException(e.args[0])

    @describeRoute(
        Description('Create a new large image item based on an existing item')
        .notes('This can be used to make an item that is a different internal '
               'format than the original item.')
        .param('itemId', 'The source item.', paramType='path')
        .param('fileId', 'The source file containing the image.  Required if '
               'there is more than one file in the item.', required=False)
        .param('folderId', 'The destination folder.', required=False)
        .param('name', 'A new name for the output item.', required=False)
        .param('localJob', 'If true, run as a local job; if false, run via '
               'the remote worker', dataType='boolean', required=False)
        .param('tileSize', 'Tile size', dataType='int', default=256,
               required=False)
        .param('onlyFrame', 'Only convert a specific 0-based frame of a '
               'multiframe file.  If not specified, all frames are converted.',
               dataType='int', required=False)
        .param('format', 'File format', required=False,
               enum=['tiff', 'aperio'])
        .param('compression', 'Internal compression format', required=False,
               enum=['none', 'jpeg', 'deflate', 'lzw', 'zstd', 'packbits', 'webp', 'jp2k'])
        .param('quality', 'JPEG compression quality where 0 is small and 100 '
               'is highest quality', dataType='int', default=90,
               required=False)
        .param('level', 'Compression level for deflate (zip) or zstd.',
               dataType='int', required=False)
        .param('predictor', 'Predictor for deflate (zip) or lzw.',
               required=False, enum=['none', 'horizontal', 'float', 'yes'])
        .param('psnr', 'JP2K compression target peak-signal-to-noise-ratio '
               'where 0 is lossless and otherwise higher numbers are higher '
               'quality', dataType='int', required=False)
        .param('cr', 'JP2K target compression ratio where 1 is lossless',
               dataType='int', required=False)
        .param('concurrent', 'Suggested number of maximum concurrent '
               'processes to use during conversion.  Values less than or '
               'equal to 0 use the number of logical cpus less that value.  '
               'Default is -2.', dataType='int', required=False)
    )
    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    @filtermodel(model='job', plugin='jobs')
    def convertImage(self, item, params):
        if 'concurrent' in params:
            params['_concurrency'] = params.pop('concurrent')
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
        params.pop('notify', None)
        localJob = self.boolParam('localJob', params, default=True)
        params.pop('localJob', None)
        try:
            return self.imageItemModel.convertImage(
                item, largeImageFile, user, token, localJob=localJob, **params)
        except TileGeneralError as e:
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
            ('frame', int),
            ('frames', str),
            ('monochrome', lambda val: val == 'true'),
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
                if dataType == 'boolOrInt':
                    dataType = bool if str(params[key]).lower() in (
                        'true', 'false', 'on', 'off', 'yes', 'no') else int
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
        except TileGeneralError as e:
            raise RestException(e.args[0], code=400)

    def _setContentDisposition(self, item, contentDisposition, mime, subname, fullFilename=None):
        """
        If requested, set the content disposition and a suggested file name.

        :param item: an item that includes a name.
        :param contentDisposition: either 'inline' or 'attachment', otherwise
            no header is added.
        :param mime: the mimetype of the output image.  Used for the filename
            suffix.
        :param subname: a subname to append to the item name.
        :param fullFilename: if specified, use this instead of the item name
            and the subname.
        """
        if (not item or not item.get('name') or
                mime not in MimeTypeExtensions or
                contentDisposition not in ('inline', 'attachment')):
            return
        if fullFilename:
            filename = fullFilename
        else:
            filename = os.path.splitext(item['name'])[0]
            if subname:
                filename += '-' + subname
            filename += '.' + MimeTypeExtensions[mime]
        if not isinstance(filename, str):
            filename = filename.decode('utf8', 'ignore')
        safeFilename = filename.encode('ascii', 'ignore').replace(b'"', b'')
        encodedFilename = urllib.parse.quote(filename.encode('utf8', 'ignore'))
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
    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def getTilesInfo(self, item, params):
        return self._getTilesInfo(item, params)

    @describeRoute(
        Description('Get large image internal metadata.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def getInternalMetadata(self, item, params):
        try:
            return self.imageItemModel.getInternalMetadata(item, **params)
        except TileGeneralError as e:
            raise RestException(e.args[0], code=400)

    @describeRoute(
        Description('Get test large image metadata.')
    )
    @access.public(scope=TokenScope.DATA_READ)
    def getTestTilesInfo(self, params):
        item = {'largeImage': {'sourceName': 'test'}}
        imageArgs = self._parseTestParams(params)
        return self._getTilesInfo(item, imageArgs)

    @describeRoute(
        Description('Get DeepZoom compatible metadata.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param('overlap', 'Pixel overlap (default 0), must be non-negative.',
               required=False, dataType='int')
        .param('tilesize', 'Tile size (default 256), must be a power of 2',
               required=False, dataType='int')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def getDZIInfo(self, item, params):
        if 'encoding' in params and params['encoding'] not in ('JPEG', 'PNG'):
            raise RestException('Only JPEG and PNG encodings are supported', code=400)
        info = self._getTilesInfo(item, params)
        tilesize = int(params.get('tilesize', 256))
        if tilesize & (tilesize - 1):
            raise RestException('Invalid tilesize', code=400)
        overlap = int(params.get('overlap', 0))
        if overlap < 0:
            raise RestException('Invalid overlap', code=400)
        result = ''.join([
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<Image',
            ' TileSize="%d"' % tilesize,
            ' Overlap="%d"' % overlap,
            ' Format="%s"' % ('png' if params.get('encoding') == 'PNG' else 'jpg'),
            ' xmlns="http://schemas.microsoft.com/deepzoom/2008">',
            '<Size',
            ' Width="%d"' % info['sizeX'],
            ' Height="%d"' % info['sizeY'],
            '/>'
            '</Image>',
        ])
        setResponseHeader('Content-Type', 'text/xml')
        setRawResponse()
        return result

    def _getTile(self, item, z, x, y, imageArgs, mayRedirect=False):
        """
        Get an large image tile.

        :param item: the item to get a tile from.
        :param z: tile layer number (0 is the most zoomed-out).
        .param x: the X coordinate of the tile (0 is the left side).
        .param y: the Y coordinate of the tile (0 is the top).
        :param imageArgs: additional arguments to use when fetching image data.
        :param mayRedirect: if True or one of 'any', 'encoding', or 'exact',
            allow return a response which may be a redirect.
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
            except TileGeneralError as e:
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
    #   @access.public(cookie=True, scope=TokenScope.DATA_READ)
    #   @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    #   def getTile(self, item, z, x, y, params):
    #       return self._getTile(item, z, x, y, params, True)
    def getTile(self, itemId, z, x, y, params):
        _adjustParams(params)
        item = loadmodelcache.loadModel(
            self, 'item', id=itemId, allowCookie=True, level=AccessType.READ)
        _handleETag('getTile', item, z, x, y, params)
        redirect = params.get('redirect', False)
        if redirect not in ('any', 'exact', 'encoding'):
            redirect = False
        return self._getTile(item, z, x, y, params, mayRedirect=redirect)
    getTile.accessLevel = 'public'
    getTile.cookieAuth = True
    getTile.requiredScopes = TokenScope.DATA_READ

    @describeRoute(
        Description('Get a large image tile with a frame number.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param('frame', 'The frame number of the tile.', paramType='path')
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
    # See getTile for caching rationale
    def getTileWithFrame(self, itemId, frame, z, x, y, params):
        _adjustParams(params)
        item = loadmodelcache.loadModel(
            self, 'item', id=itemId, allowCookie=True, level=AccessType.READ)
        _handleETag('getTileWithFrame', item, frame, z, x, y, params)
        redirect = params.get('redirect', False)
        if redirect not in ('any', 'exact', 'encoding'):
            redirect = False
        params['frame'] = frame
        return self._getTile(item, z, x, y, params, mayRedirect=redirect)
    getTileWithFrame.accessLevel = 'public'

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
    @access.public(cookie=True, scope=TokenScope.DATA_READ)
    def getTestTile(self, z, x, y, params):
        item = {'largeImage': {'sourceName': 'test'}}
        imageArgs = self._parseTestParams(params)
        return self._getTile(item, z, x, y, imageArgs)

    @describeRoute(
        Description('Get a DeepZoom image tile.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param('level', 'The deepzoom layer number of the tile (8 is the '
               'most zoomed-out layer).', paramType='path')
        .param('xandy', 'The X and Y coordinate of the tile in the form '
               '(x)_(y).(extension) where (0_0 is the left top).',
               paramType='path')
        .produces(ImageMimeTypes)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.public(cookie=True, scope=TokenScope.DATA_READ)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def getDZITile(self, item, level, xandy, params):
        _adjustParams(params)
        tilesize = int(params.get('tilesize', 256))
        if tilesize & (tilesize - 1):
            raise RestException('Invalid tilesize', code=400)
        overlap = int(params.get('overlap', 0))
        if overlap < 0:
            raise RestException('Invalid overlap', code=400)
        x, y = (int(xy) for xy in xandy.split('.')[0].split('_'))
        _handleETag('getDZITile', item, level, xandy, params)
        metadata = self.imageItemModel.getMetadata(item, **params)
        level = int(level)
        maxlevel = int(math.ceil(math.log(max(
            metadata['sizeX'], metadata['sizeY'])) / math.log(2)))
        if level < 1 or level > maxlevel:
            raise RestException('level must be between 1 and the image scale',
                                code=400)
        lfactor = 2 ** (maxlevel - level)
        region = {
            'left': (x * tilesize - overlap) * lfactor,
            'top': (y * tilesize - overlap) * lfactor,
            'right': ((x + 1) * tilesize + overlap) * lfactor,
            'bottom': ((y + 1) * tilesize + overlap) * lfactor,
        }
        width = height = tilesize + overlap * 2
        if region['left'] < 0:
            width += int(region['left'] / lfactor)
            region['left'] = 0
        if region['top'] < 0:
            height += int(region['top'] / lfactor)
            region['top'] = 0
        if region['left'] >= metadata['sizeX']:
            raise RestException('x is outside layer', code=400)
        if region['top'] >= metadata['sizeY']:
            raise RestException('y is outside layer', code=400)
        if region['left'] < metadata['sizeX'] and region['right'] > metadata['sizeX']:
            region['right'] = metadata['sizeX']
            width = int(math.ceil(float(region['right'] - region['left']) / lfactor))
        if region['top'] < metadata['sizeY'] and region['bottom'] > metadata['sizeY']:
            region['bottom'] = metadata['sizeY']
            height = int(math.ceil(float(region['bottom'] - region['top']) / lfactor))
        regionData, regionMime = self.imageItemModel.getRegion(
            item,
            region=region,
            output=dict(maxWidth=width, maxHeight=height),
            **params)
        setResponseHeader('Content-Type', regionMime)
        setRawResponse()
        return regionData

    @describeRoute(
        Description('Remove a large image from this item.')
        .param('itemId', 'The ID of the item.', paramType='path')
    )
    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.WRITE)
    def deleteTiles(self, item, params):
        deleted = self.imageItemModel.delete(item)
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
        .param('frame', 'For multiframe images, the 0-based frame number.  '
               'This is ignored on non-multiframe images.', required=False,
               dataType='int')
        .param('encoding', 'Output image encoding.  TILED generates a tiled '
               'tiff without the upper limit on image size the other options '
               'have.  For geospatial sources, TILED will also have '
               'appropriate tagging.  Pickle emits python pickle data with an '
               'optional specific protocol', required=False,
               enum=EncodingTypes, default='JPEG')
        .param('contentDisposition', 'Specify the Content-Disposition response '
               'header disposition-type value.', required=False,
               enum=['inline', 'attachment'])
        .param('contentDispositionFilename', 'Specify the filename used in '
               'the Content-Disposition response header.', required=False)
        .produces(ImageMimeTypes)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.public(cookie=True, scope=TokenScope.DATA_READ)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def getTilesThumbnail(self, item, params):
        _adjustParams(params)
        params = self._parseParams(params, True, [
            ('width', int),
            ('height', int),
            ('fill', str),
            ('frame', int),
            ('jpegQuality', int),
            ('jpegSubsampling', int),
            ('tiffCompression', str),
            ('encoding', str),
            ('style', str),
            ('contentDisposition', str),
            ('contentDispositionFileName', str)
        ])
        _handleETag('getTilesThumbnail', item, params)
        pickle = _pickleParams(params)
        try:
            result = self.imageItemModel.getThumbnail(item, **params)
        except TileGeneralError as e:
            raise RestException(e.args[0])
        except ValueError as e:
            raise RestException('Value Error: %s' % e.args[0])
        if not isinstance(result, tuple):
            return result
        thumbData, thumbMime = result
        if pickle:
            thumbData, thumbMime = _pickleOutput(thumbData, pickle)
        self._setContentDisposition(
            item, params.get('contentDisposition'), thumbMime, 'thumbnail',
            params.get('contentDispositionFilename'))
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
        .param('frame', 'For multiframe images, the 0-based frame number.  '
               'This is ignored on non-multiframe images.', required=False,
               dataType='int')
        .param('encoding', 'Output image encoding.  TILED generates a tiled '
               'tiff without the upper limit on image size the other options '
               'have.  For geospatial sources, TILED will also have '
               'appropriate tagging.  Pickle emits python pickle data with an '
               'optional specific protocol', required=False,
               enum=EncodingTypes, default='JPEG')
        .param('jpegQuality', 'Quality used for generating JPEG images',
               required=False, dataType='int', default=95)
        .param('jpegSubsampling', 'Chroma subsampling used for generating '
               'JPEG images.  0, 1, and 2 are full, half, and quarter '
               'resolution chroma respectively.', required=False,
               enum=['0', '1', '2'], dataType='int', default='0')
        .param('tiffCompression', 'Compression method when storing a TIFF '
               'image', required=False,
               enum=['none', 'raw', 'lzw', 'tiff_lzw', 'jpeg', 'deflate',
                     'tiff_adobe_deflate'])
        .param('style', 'JSON-encoded style string', required=False)
        .param('resample', 'If false, an existing level of the image is used '
               'for the region.  If true, the internal values are '
               'interpolated to match the specified size as needed.  0-3 for '
               'a specific interpolation method (0-nearest, 1-lanczos, '
               '2-bilinear, 3-bicubic)', required=False,
               enum=['false', 'true', '0', '1', '2', '3'])
        .param('contentDisposition', 'Specify the Content-Disposition response '
               'header disposition-type value.', required=False,
               enum=['inline', 'attachment'])
        .param('contentDispositionFilename', 'Specify the filename used in '
               'the Content-Disposition response header.', required=False)
        .produces(ImageMimeTypes)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
        .errorResponse('Insufficient memory.')
    )
    @access.public(cookie=True, scope=TokenScope.DATA_READ)
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
            ('frame', int),
            ('encoding', str),
            ('jpegQuality', int),
            ('jpegSubsampling', int),
            ('tiffCompression', str),
            ('style', str),
            ('resample', 'boolOrInt'),
            ('contentDisposition', str),
            ('contentDispositionFileName', str)
        ])
        _handleETag('getTilesRegion', item, params)
        pickle = _pickleParams(params)
        setResponseTimeLimit(86400)
        try:
            regionData, regionMime = self.imageItemModel.getRegion(
                item, **params)
            if pickle:
                regionData, regionMime = _pickleOutput(regionData, pickle)
        except TileGeneralError as e:
            raise RestException(e.args[0])
        except ValueError as e:
            raise RestException('Value Error: %s' % e.args[0])
        self._setContentDisposition(
            item, params.get('contentDisposition'), regionMime, 'region',
            params.get('contentDispositionFilename'))
        setResponseHeader('Content-Type', regionMime)
        if isinstance(regionData, pathlib.Path):
            BUF_SIZE = 65536

            def stream():
                try:
                    with regionData.open('rb') as f:
                        while True:
                            data = f.read(BUF_SIZE)
                            if not data:
                                break
                            yield data
                finally:
                    regionData.unlink()
            return stream
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
        .param('frame', 'For multiframe images, the 0-based frame number.  '
               'This is ignored on non-multiframe images.', required=False,
               dataType='int')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.public(cookie=True, scope=TokenScope.DATA_READ)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def getTilesPixel(self, item, params):
        params = self._parseParams(params, True, [
            ('left', float, 'region', 'left'),
            ('top', float, 'region', 'top'),
            ('right', float, 'region', 'right'),
            ('bottom', float, 'region', 'bottom'),
            ('units', str, 'region', 'units'),
            ('frame', int),
        ])
        try:
            pixel = self.imageItemModel.getPixel(item, **params)
        except TileGeneralError as e:
            raise RestException(e.args[0])
        except ValueError as e:
            raise RestException('Value Error: %s' % e.args[0])
        return pixel

    @describeRoute(
        Description('Get a histogram for any region of a large image item.')
        .notes('This can take all of the parameters as the region endpoint, '
               'plus some histogram-specific parameters.  Only typically used '
               'parameters are listed.  The returned result is a list with '
               'one entry per channel (always one of L, LA, RGB, or RGBA '
               'colorspace).  Each entry has the histogram values, bin edges, '
               'minimum and maximum values for the channel, and number of '
               'samples (pixels) used in the computation.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param('width', 'The maximum width of the analyzed region in pixels.',
               default=2048, required=False, dataType='int')
        .param('height', 'The maximum height of the analyzed region in pixels.',
               default=2048, required=False, dataType='int')
        .param('resample', 'If false, an existing level of the image is used '
               'for the histogram.  If true, the internal values are '
               'interpolated to match the specified size as needed.  0-3 for '
               'a specific interpolation method (0-nearest, 1-lanczos, '
               '2-bilinear, 3-bicubic)', required=False,
               enum=['false', 'true', '0', '1', '2', '3'], default='false')
        .param('frame', 'For multiframe images, the 0-based frame number.  '
               'This is ignored on non-multiframe images.', required=False,
               dataType='int')
        .param('bins', 'The number of bins in the histogram.',
               default=256, required=False, dataType='int')
        .param('rangeMin', 'The minimum value in the histogram.  Defaults to '
               'the minimum value in the image.',
               required=False, dataType='float')
        .param('rangeMax', 'The maximum value in the histogram.  Defaults to '
               'the maximum value in the image.',
               required=False, dataType='float')
        .param('roundRange', 'If true and neither a minimum or maximum is '
               'specified for the range, round the bin edges and adjust the '
               'number of bins for integer data with smaller ranges.',
               required=False, dataType='boolean', default=False)
        .param('density', 'If true, scale the results by the number of '
               'samples.', required=False, dataType='boolean', default=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def getHistogram(self, item, params):
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
            ('frame', int),
            ('encoding', str),
            ('jpegQuality', int),
            ('jpegSubsampling', int),
            ('tiffCompression', str),
            ('style', str),
            ('resample', 'boolOrInt'),
            ('bins', int),
            ('rangeMin', int),
            ('rangeMax', int),
            ('roundRange', bool),
            ('density', bool),
        ])
        _handleETag('getHistogram', item, params)
        histRange = None
        if 'rangeMin' in params or 'rangeMax' in params:
            histRange = [params.pop('rangeMin', 0), params.pop('rangeMax', 256)]
        if params.get('roundRange'):
            if params.pop('roundRange', False) and histRange is None:
                histRange = 'round'
        result = self.imageItemModel.histogram(item, range=histRange, **params)
        result = result['histogram']
        # Cast everything to lists and floats so json with encode properly
        for entry in result:
            for key in {'bin_edges', 'hist', 'range'}:
                if key in entry:
                    entry[key] = [float(val) for val in list(entry[key])]
            for key in {'min', 'max', 'samples'}:
                if key in entry:
                    entry[key] = float(entry[key])
        return result

    @describeRoute(
        Description('Get band information for a large image item.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param('frame', 'For multiframe images, the 0-based frame number.  '
               'This is ignored on non-multiframe images.', required=False,
               dataType='int')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def getBandInformation(self, item, params):
        _adjustParams(params)
        params = self._parseParams(params, True, [
            ('frame', int),
        ])
        _handleETag('getBandInformation', item, params)
        result = self.imageItemModel.getBandInformation(item, **params)
        return result

    @describeRoute(
        Description('Get a list of additional images associated with a large image.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def getAssociatedImagesList(self, item, params):
        try:
            return self.imageItemModel.getAssociatedImagesList(item)
        except TileGeneralError as e:
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
        .param('contentDispositionFilename', 'Specify the filename used in '
               'the Content-Disposition response header.', required=False)
        .produces(ImageMimeTypes)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.public(cookie=True, scope=TokenScope.DATA_READ)
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
            ('style', str),
            ('contentDisposition', str),
            ('contentDispositionFileName', str)
        ])
        _handleETag('getAssociatedImage', item, image, params)
        try:
            result = self.imageItemModel.getAssociatedImage(item, image, **params)
        except TileGeneralError as e:
            raise RestException(e.args[0], code=400)
        if not isinstance(result, tuple):
            return result
        imageData, imageMime = result
        self._setContentDisposition(
            item, params.get('contentDisposition'), imageMime, image,
            params.get('contentDispositionFilename'))
        setResponseHeader('Content-Type', imageMime)
        setRawResponse()
        return imageData

    @autoDescribeRoute(
        Description('Get metadata for an image associated with a large image.')
        .modelParam('itemId', model=Item, level=AccessType.READ)
        .param('image', 'The key of the associated image.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.public(scope=TokenScope.DATA_READ)
    def getAssociatedImageMetadata(self, item, image, params):
        _handleETag('getAssociatedImageMetadata', item, image)
        tilesource = self.imageItemModel._loadTileSource(item, **params)
        pilImage = tilesource._getAssociatedImage(image)
        if pilImage is None:
            return {}
        result = {
            'sizeX': pilImage.width,
            'sizeY': pilImage.height,
            'mode': pilImage.mode,
        }
        if pilImage.format:
            result['format'] = pilImage.format
        if pilImage.info:
            result['info'] = pilImage.info
        return result

    _tileFramesParams = [
        ('framesAcross', int),
        ('frameList', str),
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
        ('frame', int),
        ('encoding', str),
        ('jpegQuality', int),
        ('jpegSubsampling', int),
        ('tiffCompression', str),
        ('style', str),
        ('resample', 'boolOrInt'),
        ('contentDisposition', str),
        ('contentDispositionFileName', str)
    ]

    @describeRoute(
        Description('Composite thumbnails of multiple frames into a single image.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param('framesAcross', 'How many frames across', required=False, dataType='int')
        .param('frameList', 'Comma-separated list of frames', required=False)
        .param('cache', 'Cache the results for future use', required=False,
               dataType='boolean', default=False)
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
        .param('frame', 'For multiframe images, the 0-based frame number.  '
               'This is ignored on non-multiframe images.', required=False,
               dataType='int')
        .param('encoding', 'Output image encoding.  TILED generates a tiled '
               'tiff without the upper limit on image size the other options '
               'have.  For geospatial sources, TILED will also have '
               'appropriate tagging.  Pickle emits python pickle data with an '
               'optional specific protocol', required=False,
               enum=EncodingTypes, default='JPEG')
        .param('jpegQuality', 'Quality used for generating JPEG images',
               required=False, dataType='int', default=95)
        .param('jpegSubsampling', 'Chroma subsampling used for generating '
               'JPEG images.  0, 1, and 2 are full, half, and quarter '
               'resolution chroma respectively.', required=False,
               enum=['0', '1', '2'], dataType='int', default='0')
        .param('tiffCompression', 'Compression method when storing a TIFF '
               'image', required=False,
               enum=['none', 'raw', 'lzw', 'tiff_lzw', 'jpeg', 'deflate',
                     'tiff_adobe_deflate'])
        .param('style', 'JSON-encoded style string', required=False)
        .param('resample', 'If false, an existing level of the image is used '
               'for the region.  If true, the internal values are '
               'interpolated to match the specified size as needed.  0-3 for '
               'a specific interpolation method (0-nearest, 1-lanczos, '
               '2-bilinear, 3-bicubic)', required=False,
               enum=['false', 'true', '0', '1', '2', '3'])
        .param('contentDisposition', 'Specify the Content-Disposition response '
               'header disposition-type value.', required=False,
               enum=['inline', 'attachment'])
        .param('contentDispositionFilename', 'Specify the filename used in '
               'the Content-Disposition response header.', required=False)
        .produces(ImageMimeTypes)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
        .errorResponse('Insufficient memory.')
    )
    @access.public(cookie=True, scope=TokenScope.DATA_READ)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def tileFrames(self, item, params):
        cache = params.pop('cache', False)
        checkAndCreate = False if cache else 'nosave'
        _adjustParams(params)

        params = self._parseParams(params, True, self._tileFramesParams)
        _handleETag('tileFrames', item, params)
        pickle = _pickleParams(params)
        if 'frameList' in params:
            params['frameList'] = [
                int(f.strip()) for f in str(params['frameList']).lstrip(
                    '[').rstrip(']').split(',')]
        setResponseTimeLimit(86400)
        try:
            result = self.imageItemModel.tileFrames(
                item, checkAndCreate=checkAndCreate, **params)
        except TileGeneralError as e:
            raise RestException(e.args[0])
        except ValueError as e:
            raise RestException('Value Error: %s' % e.args[0])
        if not isinstance(result, tuple):
            return result
        regionData, regionMime = result
        if pickle:
            regionData, regionMime = _pickleOutput(regionData, pickle)
        self._setContentDisposition(
            item, params.get('contentDisposition'), regionMime, 'tileframes',
            params.get('contentDispositionFilename'))
        setResponseHeader('Content-Type', regionMime)
        if isinstance(regionData, pathlib.Path):
            BUF_SIZE = 65536

            def stream():
                try:
                    with regionData.open('rb') as f:
                        while True:
                            data = f.read(BUF_SIZE)
                            if not data:
                                break
                            yield data
                finally:
                    regionData.unlink()
            return stream
        setRawResponse()
        return regionData

    @describeRoute(
        Description('Get parameters for using tile_frames as background sprite images.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param('format', 'Optional format parameters, such as "encoding=JPEG&'
               'jpegQuality=85&jpegSubsampling=1".  If specified, these '
               'replace the defaults.', required=False)
        .param('query', 'Addition query parameters that would be passed to '
               'tile endpoints, such as style.', required=False)
        .param('frameBase', 'Starting frame number (default 0).  If c/z/t/xy '
               'then step through values from 0 to number of that axis - 1.  '
               'The axis specification in only useful for cache reporting or '
               'scheduling',
               required=False, dataType='int')
        .param('frameStride', 'Only use every frameStride frame of the image '
               '(default 1).  c/z/t/xy to use the length of that axis',
               required=False, dataType='int')
        .param('frameGroup', 'Group frames when using multiple textures to '
               'keep boundaries at a multiple of the group size number.  '
               'c/z/t/xy to use the length of that axis.',
               required=False, dataType='int')
        .param('frameGroupFactor', 'Ignore grouping if the resultant images '
               'would be more than this factor smaller than without grouping '
               '(default 4)', required=False, dataType='int')
        .param('frameGroupStride', 'Reorder frames based on the to stride '
               '(default 1).  "auto" to use frameGroup / frameStride if that '
               'value is an integer.',
               required=False, dataType='int')
        .param('maxTextureSize', 'Maximum texture size in either dimension.  '
               'This should be the smaller of a desired value and of the '
               'intended graphics environment texture buffer (default 16384).',
               required=False, dataType='int')
        .param('maxTextures', 'Maximum number of textures to use (default 1).',
               required=False, dataType='int')
        .param('maxTotalTexturePixels', 'Limit the total area of all combined '
               'textures (default 2**30).',
               required=False, dataType='int')
        .param('alignment', 'Individual frame alignment within a texture.  '
               'Used to avoid jpeg artifacts from crossing frames (default '
               '16).',
               required=False, dataType='int')
        .param('maxFrameSize', 'If specified, frames will never be larger '
               'than this, even if the texture size allows it (default None).',
               required=False, dataType='int')
        .param('cache', 'Report on or request caching the resultant frames.  '
               'Scheduling creates a local job.',
               required=False,
               enum=['none', 'report', 'schedule'])
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.public(cookie=True, scope=TokenScope.DATA_READ)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def tileFramesQuadInfo(self, item, params):
        metadata = self.imageItemModel.getMetadata(item)
        options = self._parseParams(params, False, [
            ('format', str),
            ('query', str),
            ('frameBase', str),
            ('frameStride', str),
            ('frameGroup', str),
            ('frameGroupFactor', int),
            ('frameGroupStride', str),
            ('maxTextureSize', int),
            ('maxTextures', int),
            ('maxTotalTexturePixels', int),
            ('alignment', int),
            ('maxFrameSize', int),
        ])
        for key in {'format', 'query'}:
            if key in options:
                options[key] = dict(urllib.parse.parse_qsl(options[key]))
        result = large_image.tilesource.utilities.getTileFramesQuadInfo(metadata, options)
        if params.get('cache') in {'report', 'schedule'}:
            needed = []
            result['cached'] = []
            for src in result['src']:
                tfParams = self._parseParams(src, False, self._tileFramesParams)
                if 'frameList' in tfParams:
                    tfParams['frameList'] = [
                        int(f.strip()) for f in str(tfParams['frameList']).lstrip(
                            '[').rstrip(']').split(',')]
                result['cached'].append(self.imageItemModel.tileFrames(
                    item, checkAndCreate='check', **tfParams))
                if not result['cached'][-1]:
                    needed.append(tfParams)
            if params.get('cache') == 'schedule' and not all(result['cached']):
                result['scheduledJob'] = str(self.imageItemModel._scheduleTileFrames(
                    item, needed, self.getCurrentUser())['_id'])
        return result

    @autoDescribeRoute(
        Description('List all thumbnail and data files associated with a large_image item.')
        .modelParam('itemId', model=Item, level=AccessType.READ)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.admin(scope=TokenScope.DATA_READ)
    def listTilesThumbnails(self, item):
        return self.imageItemModel.removeThumbnailFiles(item, onlyList=True)

    @autoDescribeRoute(
        Description('Delete thumbnail and data files associated with a large_image item.')
        .modelParam('itemId', model=Item, level=AccessType.READ)
        .param('keep', 'Number of thumbnails to keep.', dataType='integer',
               required=False, default=10000)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.admin(scope=TokenScope.DATA_WRITE)
    def deleteTilesThumbnails(self, item, keep):
        return self.imageItemModel.removeThumbnailFiles(item, keep=keep or 0)
