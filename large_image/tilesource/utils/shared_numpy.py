import os
import platform
import multiprocessing.shared_memory
import operator
import functools

import numpy as np

class SharedNumpyArray:
    def __init__(self, shape, dtype):
        """Init"""
        self.shape = shape
        self.dtype = np.dtype(dtype)
        self.shm_size = functools.reduce(operator.mul, shape, 1) * self.dtype.itemsize
        self.shm = multiprocessing.shared_memory.SharedMemory(
            create=True, size=self.shm_size
        )
        self.buf = np.ndarray(self.shape, dtype=self.dtype, buffer=self.shm.buf)
        self.created = True

    def insert(self, arr, i):
        """Insert a batch dimension slice."""
        self.buf[i] = arr

    def copy(self, arr):
        self.shape = arr.shape
        self.buf = np.ndarray(self.shape, dtype=self.dtype, buffer=self.shm.buf)
        self.buf[:] = arr[:]

    def tobytes(self):
        return self.buf.tobytes()

    def view(self):
        return np.ndarray(self.shape, self.dtype, buffer=self.shm.buf)

    # If we want easier interoperability, we could, instead, forward a
    # whitelist of attributes to our underlying np.ndarray object; these could
    # be enumerated and done via __getattribute__
    def __getitem__(self, idx):
        return self.buf[idx]

    def __array__(self, dtype=None):
        return self.buf.copy().astype(dtype) if dtype is not None else self.buf.copy()

    def __getstate__(self):
        state = self.__dict__.copy()
        del state["shm"]
        state.pop("buf", None)
        state["created"] = False
        state["shm_name"] = self.shm.name
        return state

    def __setstate__(self, state):
        state = state.copy()
        shm_name = state.pop("shm_name")
        self.__dict__.update(state)
        self.shm = multiprocessing.shared_memory.SharedMemory(shm_name)
        self.buf = np.ndarray(self.shape, dtype=self.dtype, buffer=self.shm.buf)

    def __del__(self):
        if hasattr(self, "shm"):
            self.shm.close()
            if getattr(self, "created", None) is True:
                # Fix for problem with linux when the shared memory is being created and destroyed too fast
                if os.path.exists('/dev/shm/{}'.format(self.shm.name)):
                    self.shm.unlink()