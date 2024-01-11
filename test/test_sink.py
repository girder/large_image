import large_image_source_test
import large_image_source_zarr


def testImageCopy():
    sink = large_image_source_zarr.new()
    source = large_image_source_test.TestTileSource(
        fractal=True,
        maxLevel=4,
        tileWidth=128,
        tileHeight=128,
        sizeX=512,
        sizeY=1024,
        frames='c=2,z=3',
        # bands="red=400-12000,green=0-65535,blue=800-4000,
        # ir1=200-24000,ir2=200-22000,gray=100-10000,other=0-65535"
    )

    metadata = source.getMetadata()
    for frame in metadata.get('frames', []):
        num_tiles = source.getSingleTile(frame=frame['Frame'])['iterator_range'][
            'position'
        ]
        print(f'Copying {num_tiles} tiles for frame {frame}')
        for tile in source.tileIterator(frame=frame['Frame'], format='numpy'):
            t = tile['tile']
            x, y = tile['x'], tile['y']
            kwargs = {
                'z': frame['IndexZ'],
                'c': frame['IndexC'],
            }
            sink.addTile(t, x=x, y=y, axes='zcyxs', **kwargs)

    sink._validateZarr()
    print('Final shape:', sink.getRegion(format='numpy')[0].shape)

    # sink.write('temp.tiff')
    # sink.write('temp.sqlite')
    sink.write('temp.zip')
    # sink.write('temp.zarr')
    # sink.write('temp.dz')
    # sink.write('temp.szi')
    # sink.write('temp.svs')


if __name__ == '__main__':
    testImageCopy()
