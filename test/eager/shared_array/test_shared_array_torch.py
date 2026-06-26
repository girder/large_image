import pytest


def test_torch_shared_array():
    pytest.importorskip('pykdtree.kdtree', reason='eager read planning requires pykdtree')
    torch = pytest.importorskip('torch')
    from large_image.tilesource.eager_utils.eager_shared_array import SharedArray

    shared_array = SharedArray((256, 256, 3), torch.uint8, is_torch=True)
    view = shared_array.view()

    assert tuple(view.shape) == (256, 256, 3)
    assert view.dtype == torch.uint8
    assert view.is_contiguous()

    shared_array.close()
