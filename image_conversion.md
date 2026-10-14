# Image Conversion

The `large_image` library can read a variety of images with the various tile source modules.  Some image files that cannot be read directly can be converted into a format that can be read by the `large_image` library.  Additionally, some images that can be read are very slow to handle because they are stored inefficiently, and converting them will make a equivalent file that is more efficient.

## Python Usage

The `large_image_converter` module can be used as a Python package. See [large_image_converter](_build/large_image_converter/modules.md) for details.

## Command Line Usage

Installing the `large-image-converter` module adds a `large_image_converter` command to the local environment.  Running `large_image_converter --help` displays the various options.

```default
usage: large_image_converter [-h] [--version] [--verbose] [--silent]
                             [--overwrite] [--tile TILESIZE] [--no-subifds]
                             [--subifds] [--frame ONLYFRAME]
                             [--format {tiff,aperio}]
                             [--compression {,jpeg,deflate,zip,lzw,zstd,packbits,jbig,lzma,webp,jp2k,none}]
                             [--quality QUALITY] [--level LEVEL]
                             [--predictor {,none,horizontal,float,yes}]
                             [--psnr PSNR] [--cr CR]
                             [--shrink-mode {mean,median,mode,max,min,nearest,default}]
                             [--only-associated _KEEP_ASSOCIATED]
                             [--exclude-associated _EXCLUDE_ASSOCIATED]
                             [--concurrency _CONCURRENCY] [--stats]
                             [--stats-full]
                             source [dest]

Convert files for use with Large Image. Output files are written as tiled tiff
files. For geospatial files, these conform to the cloud-optimized geospatial
tiff format (COG). For non-geospatial, the output image will be either 8- or
16-bits per sample per channel. Some compression formats are always 8-bits per
sample (webp, jpeg), even if that format could support more and the original
image is higher bit depth.

positional arguments:
  source                Path to source image
  dest                  Output path

options:
  -h, --help            show this help message and exit
  --version             Report version
  --verbose, -v         Increase verbosity
  --silent, -s          Decrease verbosity
  --overwrite, -w, -y   Overwrite an existing output file
  --tile TILESIZE, --tile-size TILESIZE, --tilesize TILESIZE, --tileSize TILESIZE, -t TILESIZE
                        Tile size. Default is 256.
  --no-subifds          When writing multiframe files, do not use subifds.
  --subifds             When writing multiframe files, use subifds.
  --frame ONLYFRAME     When handling a multiframe file, only output a single
                        frame. This is the zero-based frame number.
  --format {tiff,aperio}
                        Output format. The default is a standardized pyramidal
                        tiff or COG geotiff. Other formats may not be
                        available for all input options and will change some
                        defaults. Aperio (svs) defaults to no-subifds. If
                        there is no label image, a cropped nearly square
                        thumbnail is used in its place if the source image can
                        be read by any of the known tile sources.
  --compression {,jpeg,deflate,zip,lzw,zstd,packbits,jbig,lzma,webp,jp2k,none}, -c {,jpeg,deflate,zip,lzw,zstd,packbits,jbig,lzma,webp,jp2k,none}
                        Internal compression. Default will use jpeg if the
                        source appears to be lossy or lzw if lossless. lzw is
                        the most compatible lossless mode. jpeg is the most
                        compatible lossy mode. jbig and lzma may not be
                        available. jp2k will first write the file with no
                        compression and then rewrite it with jp2k the
                        specified psnr or compression ratio.
  --quality QUALITY, -q QUALITY
                        JPEG or webp compression quality. For webp, specify 0
                        for lossless. Default is 90.
  --level LEVEL, -l LEVEL
                        General compression level. Used for deflate (zip)
                        (1-9), zstd (1-22), and some others.
  --predictor {,none,horizontal,float,yes}, -p {,none,horizontal,float,yes}
                        Predictor for some compressions. Default is horizontal
                        for non-geospatial data and yes for geospatial.
  --psnr PSNR           JP2K peak signal to noise ratio. 0 for lossless.
  --cr CR               JP2K compression ratio. 1 for lossless.
  --shrink-mode {mean,median,mode,max,min,nearest,default}, --shrink {mean,median,mode,max,min,nearest,default}, --reduce {mean,median,mode,max,min,nearest,default}
                        When producing lower resolution images, use this
                        method for computing pixels. This defaults to median
                        for lossy images and nearest for lossless images.
  --only-associated _KEEP_ASSOCIATED
                        Only keep associated images with the specified keys.
                        The value is used as a matching regex.
  --exclude-associated _EXCLUDE_ASSOCIATED
                        Exclude associated images with the specified keys. The
                        value is used as a matching regex. If a key is
                        specified for both exclusion and inclusion, it will be
                        excluded.
  --concurrency _CONCURRENCY, -j _CONCURRENCY
                        Maximum processor concurrency. Some conversion tasks
                        can use multiple processors. A value <= 0 will use the
                        number of logical processors less that number. This is
                        a recommendation and is not strict. Default is 0.
  --stats               Add conversion stats (time and size) to the
                        ImageDescription of the output file. This involves
                        writing the file an extra time; the stats do not
                        include the extra write.
  --stats-full, --full-stats
                        Add conversion stats, including noise metrics (PSNR,
                        etc.) to the output file. This takes more time and
                        temporary disk space.
```
