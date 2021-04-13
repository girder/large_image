import os

import pooch

registry = {
    # netcdf file for testing mapnik source
    # Source: 04091217_ruc.nc
    '04091217_ruc.nc': 'sha512:3380c8de64afc46a5cfe764921e0fd5582380b1065754a6e6c4fa506625ee26edb1637aeda59c1d2a2dc245364b191563d8572488c32dcafe9e706e208fd9939',  # noqa
    # OME Tiff with non-tiled layout
    # Source: DDX58_AXL_EGFR_well2_XY01.ome.tif
    'DDX58_AXL_EGFR_well2_XY01.ome.tif': 'sha512:d9f7b733fd758f13540a7416d1e22469e8e28a434a1acb7a50a5da0398eaa93cb5b00cc1d0bd02216da8ab9b648e82cfcb4c4bc084bd08216f6cb3c5f485f1b6',  # noqa
    # Power of three tiles
    # Source: G10-3_pelvis_crop-powers-of-3.tif
    'G10-3_pelvis_crop-powers-of-3.tif': 'sha512:56ca89f25b0857960518c417393633029d5592376c8d94bc867662b7bff684fb2a4fe40f7dd3eeeb9abe9c8c3105b9bf89868a79a883b32e1207acd2ff59af21',  # noqa
    # Zeiss file
    # Source: HENormalN801.czi
    'HENormalN801.czi': 'sha512:ca0704401d7e1b75b5b3830bc4316e4f453a1428538d54415671d3048786c7d88d3b0774a67a5f8071c4e91213657ad6ee3f866f4a631cd3f2b477bdae4b17a7',  # noqa
    # Nikon file
    # Source: ITGA3Hi_export_crop2.nd2
    'ITGA3Hi_export_crop2.nd2': 'sha512:9c1f412468025e53c632c2d45a77ac73d6c100750304ad0db6311de22348a4052f97828fde78ca3ccd61ace17bd007c2d8a1bb1406ec19748029a308f60a1725',  # noqa
    # JPEG2000 File with associated images
    # Source: JK-kidney_B-gal_H3_4C_1-500sec.jp2
    'JK-kidney_B-gal_H3_4C_1-500sec.jp2': 'sha512:38912884b07a626d61a61dfede497abc31e407772bf300a553de737cb2289cb55aa94b059d4a304269900a5a267170912fa95d3b8260571bdffc14b311d5ec61',  # noqa
    # Multiple tiles; some not part of the main sequence
    # Source: JK-kidney_H3_4C_1-500sec.tif
    'JK-kidney_H3_4C_1-500sec.tif': 'sha512:9d94deb45acd1af86dedd26e261e788bad6364e0243712cd9ac37ad6862b3ec7db1554bf9392b88dc2748a1d2147baaf1a8b00d5ab39c04aa1dfbc4218362550',  # noqa
    # RGB JPEG compression
    # Source: TCGA-AA-A02O-11A-01-BS1.8b76f05c-4a8b-44ba-b581-6b8b4f437367.svs
    'TCGA-AA-A02O-11A-01-BS1.8b76f05c-4a8b-44ba-b581-6b8b4f437367.svs': 'sha512:1b75a4ec911017aef5c885760a3c6575dacf5f8efb59fb0e011108dce85b1f4e97b8d358f3363c1f5ea6f1c3698f037554aec1620bbdd4cac54e3d5c9c1da1fd',  # noqa
    # Tiff with floating point pixels
    # Source: d042-353.crop.small.float32.tif
    'd042-353.crop.small.float32.tif': 'sha512:ae05dbe6f3330c912893b203b55db27b0fdf3222a0e7f626d372c09668334494d07dc1d35533670cfac51b588d2292eeee7431317741fdb4cbb281c28a289115',  # noqa
    # Tiff with JP2k compression
    # Source: huron.image2_jpeg2k.tif
    'huron.image2_jpeg2k.tif': 'sha512:eaba877079c86f0603b2a636a44d57832cdafe6d43a449121f575f0d43f69b8a17fa619301b066ece1c11050b41d687400b27407c404d827fd2c132d99e669ae',  # noqa
    # Thematic landcover sample
    # Source: landcover_sample_1000.tif
    'landcover_sample_1000.tif': 'sha512:0a1e8c4cf29174b19ddece9a2deb7230a31e819ee78b5ec264feda6356abf60d63763106f1ddad9dd04106d383fd0867bf2db55be0552c30f38ffb530bf72dec',  # noqa
    # Geospatial image defined by GCP
    # Source: extracted from a public landsat image
    'region_gcp.tiff': 'sha512:b49d753c0a04888882da60917a6578707ad2d6f5a8f1de3b21b2ae498ad6140ee8a1779a4690cc24fa7b1cbae46e86c3529d2fbd88f392a344fbe549b4447f23',  # noqa
    # Multiframe OME tif
    # Source: sample.ome.tif
    'sample.ome.tif': 'sha512:a65ad3d67bbc8f56eb3aa7c7d6a43326e50fdef7c0a0c7ace2b477c2dfda2e810c1acc148be2ee2da9a9aa7b0195032938f36da4117a7c3f46302d4fbb1e8173',  # noqa
    # Multiframe OME tif with lower resolutions in subifds
    # Source: sample.subifd.ome.tif
    'sample.subifd.ome.tif': 'sha512:35ec252c94b1ad0b9d5bd42c89c1d15c83065d6734100d6f596237ff36e8d4495bcfed2c9ea24ab0b4a35aef59871da429dbd48faf0232219dc4391215ba59ce',  # noqa
    # Used for testing tile redirects
    # Source: sample_Easy1.jpeg
    'sample_Easy1.jpeg': 'sha512:528a3625f6565450292da605264aefbdb29fd0ca7991f6e86dff85c2e7f3093715e7cc8b5664c2168b513c37c3b43ecd537404a2d3b7f902c2ad0a66b3f5d3c8',  # noqa
    # Small PNG
    # Source: sample_Easy1.png
    'sample_Easy1.png': 'sha512:feaf2b24c4ab3123caf1aa35f51acb1d8b83b34941b28d130f878702fd3be4ae9bf46176209f7511d1213da511d414c2b4b7738ad567b089224de9d6c189e664',  # noqa
    # Small JPEG2000 image
    # Source: sample_image.jp2
    'sample_image.jp2': 'sha512:82f1dc64435ab959532ea845c93c28a1e05ed85999300bccf0e7196c91652d014d2a571c324d83279da4cabcd42cf4ed6d732e304ffa71e8b9f7ae3a1390f4c5',  # noqa
    # Pyramidal tiff file (Phillips format)
    # Source: sample_image.ptif
    'sample_image.ptif': 'sha512:ec0ec688537080e4ec2abb3978c14577df87250a2c0af42beaadc8f00f0baba210997d5d2fe7cfeeceb841885b6adad0c9f607e35eddcc479eb487bd3c1e28ac',  # noqa
    # Aperio file with JPEG2000 compression requiring a newer openjpeg library
    # Source: sample_jp2k_33003_TCGA-CV-7242-11A-01-TS1.1838afb1-9eee-4a70-9ae3-50e3ab45e242.svs
    'sample_jp2k_33003_TCGA-CV-7242-11A-01-TS1.1838afb1-9eee-4a70-9ae3-50e3ab45e242.svs': 'sha512:9a4312bc720e81ef4496cc33c71c122b82226f72bc4944b0192cc83a93b9ed7f69612d3f4369279c2ec41183e3f684cca7e068208b7d0a42bdca26cbdc3b9aac',  # noqa
    # Leica file
    # Source: sample_leica.scn
    'sample_leica.scn': 'sha512:954953c1562d9b91445287cc2066d252e821e807d5b6f60a575892f6434ecf3db7fa40371c0d07cedc0c3e8a8eb8666f40b7e027e04051afc609f55ce596f588',  # noqa
    # Typical SVS file with 240x240 tiles
    # Source: sample_svs_image.TCGA-DU-6399-01A-01-TS1.e8eb65de-d63e-42db-af6f-14fefbbdf7bd.svs
    'sample_svs_image.TCGA-DU-6399-01A-01-TS1.e8eb65de-d63e-42db-af6f-14fefbbdf7bd.svs': 'sha512:5580c2b5a5360d279d102f1eb5b0e646a4943e362ec1d47f2db01f8e9e52b302e51692171198d0d35c7fa9ec9f5b8e445ef91fa7ea0bdb05ead31ab49e0118f9',  # noqa
}


class DKCPooch(pooch.Pooch):
    def get_url(self, fname):
        self._assert_file_in_registry(fname)
        algo, hashvalue = self.registry[fname].split(':')
        return self.base_url.format(algo=algo, hashvalue=hashvalue)


datastore = DKCPooch(
    path=pooch.utils.cache_location(
        os.path.join(os.environ.get('TOX_WORK_DIR', pooch.utils.os_cache('pooch')), 'externaldata')
    ),
    base_url='https://data.kitware.com/api/v1/file/hashsum/{algo}/{hashvalue}/download',
    registry=registry,
    retry_if_failed=10,
)
