# -*- coding: utf-8 -*-

from large_image.tilesource import nearPowerOfTwo


def testNearPowerOfTwo():
    assert nearPowerOfTwo(45808, 11456)
    assert nearPowerOfTwo(45808, 11450)
    assert not nearPowerOfTwo(45808, 11200)
    assert nearPowerOfTwo(45808, 11400)
    assert not nearPowerOfTwo(45808, 11400, 0.005)
    assert nearPowerOfTwo(45808, 11500)
    assert not nearPowerOfTwo(45808, 11500, 0.005)
