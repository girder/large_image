import os

import histomics_stream as hs
# import tensorflow as tf


def study(
        paths,
        t=(224, 224),
        overlap=(0, 0),
        chunk=(896, 896),
        objective=20.0,
        mask_threshold=0.01,
):
    """Convenience function for generating a histomics stream study for a single
    whole-slide image.

    Parameters
    ----------
    paths : string | (string, string)
        Path to the whole-slide image and optionally a foreground mask.
    t : tuple(int, int)
        Tile height and width (pixels) at the target magnification. Default is (224, 224).
    overlap : tuple(int, int)
        Vertical and horizontal tile overlap (pixels). Default value is (0, 0).
    chunk : (int, int)
        Size of region for grouping tiles (pixels) at the target magnification. Grouping
        tiles into a single read improves inference throughput. Default value is (896, 896).
        A value of `None` will leave tiles to be read individually.
    objective : float
        Objective magnification. If not available, the next highest magnification will be
        downsampled. Default value is 20. for 20X objective.
    mask_threshold : float
        Exclude tiles containing less than this minimum percent tissue area when a mask is provided.
        Range for this threshold is (0, 1]. Default value of 0.01 includes tiles with at least 1%
        positive mask pixels.

    Returns
    -------
    study : object
        A histomics_stream study object containing the slides defined in paths, and analysis
        plan defined by tile size, tile overlap, and magnification/reading parameters.
    """

    # wrap string or tuple inputs in list and check arguments
    if isinstance(paths, str):
        paths = [paths]
    elif isinstance(paths, tuple):
        paths = [paths]

    # extract names from lists
    names = []
    for path in paths:
        if isinstance(path, str):
            file = os.path.split(path)[1]
        elif isinstance(path, tuple):
            file = os.path.split(path[0])[1]
        else:
            raise ValueError("Invalid path type.")
        names.append(file)

    # fill basic study parameters
    study = {"version": "version-1", "tile_height": t[0], "tile_width": t[1]}
    slides = study["slides"] = {}

    # add slides to study
    for i, (name, path) in enumerate(zip(names, paths)):
        if isinstance(path, tuple):
            filename = path[0]
        else:
            filename = path
        slide_name = os.path.split(filename)[1]
        slides[name] = {
            "filename": filename,
            "slide_name": slide_name,
            "slide_group": name,
            "chunk_height": chunk[0],
            "chunk_width": chunk[1],
        }

    # apply settings to each slide
    for name, path in zip(names, paths):
        # generate resolution setting function
        find_resolution_for_slide = hs.configure.FindResolutionForSlide(
            study, target_magnification=objective, magnification_source="exact"
        )

        # generate gridding function
        if isinstance(path, tuple):
            tiles_by_grid_and_mask = hs.configure.TilesByGridAndMask(
                study,
                overlap_height=overlap[0],
                overlap_width=overlap[1],
                mask_filename=path[1],
                mask_threshold=mask_threshold,
            )
        else:
            tiles_by_grid_and_mask = hs.configure.TilesByGridAndMask(
                study,
                overlap_height=overlap[0],
                overlap_width=overlap[1],
            )

        # apply functions
        find_resolution_for_slide(study["slides"][name])
        tiles_by_grid_and_mask(study["slides"][name])

    # apply chunking
    if chunk is not None:
        hs.configure.ChunkLocations()(study)

    return study