import json
import math

import large_image_source_tiff
import tifftools

import large_image

AperioHeader = 'Aperio Image Library v10.0.0\n'
FullHeaderStart = '{width}x{height} [0,0 {width}x{height}] ({tileSize}x{tileSize})'
LowHeaderChunk = ' -> {width}x{height}'
AssociatedHeader = '{name} {width}x{height}'
ThumbnailHeader = '-> {width}x{height} - |'


def adjust_params(geospatial, params, **kwargs):
    """
    Adjust options for aperio format.

    :param geospatial: True if the source is geospatial.
    :param params: the conversion options.  Possibly modified.
    :returns: suffix: the recommended suffix for the new file.
    """
    if geospatial:
        msg = 'Aperio format cannot be used with geospatial sources.'
        raise Exception(msg)
    if params.get('subifds') is None:
        params['subifds'] = False
    return '.svs'


def modify_vips_image_before_output(image, convertParams, **kwargs):
    """
    Make sure the vips image is either 1 or 3 bands.

    :param image: a vips image.
    :param convertParams: the parameters that will be used for compression.
    :returns: a vips image.
    """
    return image[:3 if image.bands >= 3 else 1]


def modify_tiled_ifd(info, ifd, idx, ifdIndices, lidata, liDesc, **kwargs):
    """
    Modify a tiled image to add aperio metadata and ensure tags are set
    appropriately.

    :param info: the tifftools info that will be written to the tiff tile;
        modified.
    :param ifd: the full resolution ifd as read by tifftools.
    :param idx: index of this ifd.
    :param ifdIndices: the 0-based index of the full resolution ifd of each
        frame followed by the ifd of the first associated image.
    :param lidata: large_image data including metadata and associated images.
    :param liDesc: the parsed json from the original large_image_converter
        description.
    """
    descStart = FullHeaderStart.format(
        width=ifd['tags'][tifftools.Tag.ImageWidth.value]['data'][0],
        height=ifd['tags'][tifftools.Tag.ImageHeight.value]['data'][0],
        tileSize=ifd['tags'][tifftools.Tag.TileWidth.value]['data'][0],
    )
    formatChunk = '-'
    if kwargs['compression'] == 'jpeg':
        formatChunk = 'JPEG/RGB Q=%s' % (kwargs.get('Q', 90))
    elif kwargs['compression'] == 'jp2k':
        formatChunk = 'J2K/YUV16 Q=%s' % (kwargs.get('psnr', kwargs.get('cratios', 0)))
    metadata = {
        'Converter': 'large_image_converter',
        'ConverterVersion': liDesc['large_image_converter']['version'],
        'ConverterEpoch': liDesc['large_image_converter']['conversion_epoch'],
        'MPP': (lidata['metadata']['mm_x'] * 1000
                if lidata and lidata['metadata'].get('mm_x') else None),
        'AppMag': (lidata['metadata']['magnification']
                   if lidata and lidata['metadata'].get('magnification') else None),
    }
    compressionTag = ifd['tags'][tifftools.Tag.Compression.value]
    if compressionTag['data'][0] == tifftools.constants.Compression.JP2000:
        compressionTag['data'][0] = tifftools.constants.Compression.JP2kRGB
    if len(ifdIndices) > 2:
        metadata['OffsetZ'] = idx
        metadata['TotalDepth'] = len(ifdIndices) - 1
        try:
            if metadata['IndexRange']['IndexZ'] == metadata['TotalDepth']:
                metadata['OffsetZ'] = lidata['metadata']['frames'][idx]['mm_z'] * 1000
                metadata['TotalDepth'] = (
                    lidata['metadata']['frames'][-1]['mm_z'] * 2 +
                    lidata['metadata']['frames'][-2]['mm_z'])
        except Exception:
            pass
    description = (
        f'{AperioHeader}{descStart} {formatChunk}|' +
        '|'.join(f'{k} = {v}' for k, v in sorted(metadata.items()) if v is not None))
    ifd['tags'][tifftools.Tag.ImageDescription.value] = {
        'data': description,
        'datatype': tifftools.Datatype.ASCII,
    }
    ifd['tags'][tifftools.Tag.NewSubfileType.value] = {
        'data': [0],
        'datatype': tifftools.Datatype.LONG,
    }
    if ifdIndices[idx + 1] == idx + 1:
        subifds = ifd['tags'][tifftools.Tag.SubIFD.value]['ifds']
    else:
        subifds = info['ifds'][ifdIndices[idx] + 1: ifdIndices[idx + 1]]
    for subifd in subifds:
        lowerDesc = LowHeaderChunk.format(
            width=subifd['tags'][tifftools.Tag.ImageWidth.value]['data'][0],
            height=subifd['tags'][tifftools.Tag.ImageHeight.value]['data'][0],
        )
        metadata['MPP'] = metadata['MPP'] * 2 if metadata['MPP'] else None
        metadata['AppMag'] = metadata['AppMag'] / 2 if metadata['AppMag'] else None
        description = (
            f'{AperioHeader}{descStart}{lowerDesc} {formatChunk}|' +
            '|'.join(f'{k} = {v}' for k, v in sorted(metadata.items()) if v is not None))
        subifd['tags'][tifftools.Tag.ImageDescription.value] = {
            'data': description,
            'datatype': tifftools.Datatype.ASCII,
        }
        subifd['tags'][tifftools.Tag.NewSubfileType.value] = {
            'data': [0],
            'datatype': tifftools.Datatype.LONG,
        }
        compressionTag = subifd['tags'][tifftools.Tag.Compression.value]
        if compressionTag['data'][0] == tifftools.constants.Compression.JP2000:
            compressionTag['data'][0] = tifftools.constants.Compression.JP2kRGB


def create_thumbnail_and_label(tempPath, info, ifdCount, needsLabel, labelPosition, **kwargs):
    """
    Create a thumbnail and, optionally, label image for the aperio file.

    :param tempPath: a temporary file in a temporary directory.
    :param info: the tifftools info that will be written to the tiff tile;
        modified.
    :param ifdCount: the number of ifds in the first tiled image.  This is 1 if
        there are subifds.
    :param needsLabel: true if a label image needs to be added.
    :param labelPosition: the position in the ifd list where a label image
        should be inserted.
    """
    thumbnailSize = 1024
    labelSize = 640
    maxLabelAspect = 1.5
    tileSize = info['ifds'][0]['tags'][tifftools.Tag.TileWidth.value]['data'][0]
    levels = int(math.ceil(math.log(max(thumbnailSize, labelSize) / tileSize) / math.log(2))) + 1

    neededList = ['thumbnail']
    if needsLabel:
        neededList[0:0] = ['label']
    tiledPath = tempPath + '-overview.tiff'
    firstFrameIfds = info['ifds'][max(0, ifdCount - levels):ifdCount]
    tifftools.write_tiff(firstFrameIfds, tiledPath)
    ts = large_image_source_tiff.open(tiledPath)
    for subImage in neededList:
        if subImage == 'label':
            x = max(0, (ts.sizeX - min(ts.sizeX, ts.sizeY) * maxLabelAspect) // 2)
            y = max(0, (ts.sizeY - min(ts.sizeX, ts.sizeY) * maxLabelAspect) // 2)
            regionParams = {
                'output': dict(maxWidth=labelSize, maxHeight=labelSize),
                'region': dict(left=x, right=ts.sizeX - x, top=y, bottom=ts.sizeY - y),
            }
        else:
            regionParams = {'output': dict(maxWidth=thumbnailSize, maxHeight=thumbnailSize)}
        image, _ = ts.getRegion(
            format=large_image.constants.TILE_FORMAT_PIL, **regionParams)
        if image.mode not in {'RGB', 'L'}:
            image = image.convert('RGB')
        if subImage == 'label':
            image = image.rotate(90, expand=True)
        imagePath = tempPath + '-image_%s.tiff' % subImage
        image.save(
            imagePath, 'TIFF', compression='tiff_jpeg',
            quality=int(kwargs.get('quality', 90)))
        imageInfo = tifftools.read_tiff(imagePath)
        ifd = imageInfo['ifds'][0]
        if subImage == 'label':
            ifd['tags'][tifftools.Tag.Orientation.value] = {
                'data': [tifftools.constants.Orientation.RightTop.value],
                'datatype': tifftools.Datatype.LONG,
            }
            description = AperioHeader + AssociatedHeader.format(
                name='label',
                width=ifd['tags'][tifftools.Tag.ImageWidth.value]['data'][0],
                height=ifd['tags'][tifftools.Tag.ImageHeight.value]['data'][0],
            )
            ifd['tags'][tifftools.Tag.ImageDescription.value] = {
                'data': description,
                'datatype': tifftools.Datatype.ASCII,
            }
            ifd['tags'][tifftools.Tag.NewSubfileType.value] = {
                'data': [
                    tifftools.constants.NewSubfileType.ReducedImage.value,
                ],
                'datatype': tifftools.Datatype.LONG,
            }
            info['ifds'][labelPosition:labelPosition] = imageInfo['ifds']
        else:
            fullDesc = info['ifds'][0]['tags'][tifftools.Tag.ImageDescription.value]['data']
            description = fullDesc.split('[', 1)[0] + ThumbnailHeader.format(
                width=ifd['tags'][tifftools.Tag.ImageWidth.value]['data'][0],
                height=ifd['tags'][tifftools.Tag.ImageHeight.value]['data'][0],
            ) + fullDesc.split('|', 1)[1]
            ifd['tags'][tifftools.Tag.ImageDescription.value] = {
                'data': description,
                'datatype': tifftools.Datatype.ASCII,
            }
            info['ifds'][1:1] = imageInfo['ifds']


def modify_tiff_before_write(info, ifdIndices, tempPath, lidata, **kwargs):
    """
    Adjust the metadata and ifds for a tiff file to make it compatible with
    Aperio (svs).

    Aperio files are tiff files which are stored without subifds in the order
    full res, optional thumbnail, half res, quarter res, ..., full res, half
    res, quarter res, ..., label, macro.  All ifds have an ImageDescription
    that start with an aperio header followed by some dimension information and
    then an option key-.value list

    :param info: the tifftools info that will be written to the tiff tile;
        modified.
    :param ifdIndices: the 0-based index of the full resolution ifd of each
        frame followed by the ifd of the first associated image.
    :param tempPath: a temporary file in a temporary directory.
    :param lidata: large_image data including metadata and associated images.
    """
    liDesc = json.loads(info['ifds'][0]['tags'][tifftools.Tag.ImageDescription.value]['data'])
    # Adjust tiled images
    for idx, ifdIndex in enumerate(ifdIndices[:-1]):
        ifd = info['ifds'][ifdIndex]
        modify_tiled_ifd(info, ifd, idx, ifdIndices, lidata, liDesc, **kwargs)
    # Remove all but macro and label image, keeping track if either is present
    assocKeys = set()
    for idx in range(len(info['ifds']) - 1, ifdIndices[-1] - 1, -1):
        ifd = info['ifds'][idx]
        try:
            assocKey = ifd['tags'][tifftools.Tag.ImageDescription.value]['data']
        except Exception:
            assocKey = 'none'
        if assocKey not in {'label', 'macro'}:
            info['ifds'][idx: idx + 1] = []
        description = AssociatedHeader.format(
            name=assocKey,
            width=ifd['tags'][tifftools.Tag.ImageWidth.value]['data'][0],
            height=ifd['tags'][tifftools.Tag.ImageHeight.value]['data'][0],
        )
        ifd['tags'][tifftools.Tag.ImageDescription.value] = {
            'data': description,
            'datatype': tifftools.Datatype.ASCII,
        }
        ifd['tags'][tifftools.Tag.NewSubfileType.value] = {
            'data': [
                tifftools.constants.NewSubfileType.ReducedImage.value if assocKey == 'label' else
                (tifftools.constants.NewSubfileType.ReducedImage.value |
                 tifftools.constants.NewSubfileType.Macro.value),
            ],
            'datatype': tifftools.Datatype.LONG,
        }
        assocKeys.add(assocKey)
    create_thumbnail_and_label(
        tempPath, info, ifdIndices[1], 'label' not in assocKeys, ifdIndices[-1], **kwargs)
