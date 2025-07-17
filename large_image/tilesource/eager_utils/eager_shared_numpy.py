import os
from typing import Union
import multiprocessing.shared_memory
import operator
import functools

import numpy as np

class SharedArray:
    def __init__(self, shape: tuple, dtype: Union[np.dtype, 'torch.dtype'], is_torch: bool = False):
        """Init"""
        self.shape = shape        
        self.is_torch = is_torch
        self.dtype = dtype        
        
        if is_torch:
            import torch.multiprocessing
            self.shm_size = functools.reduce(operator.mul, shape, 1) * self.dtype().element_size()
            self.shm = multiprocessing.shared_memory.SharedMemory(create=True, size=self.shm_size)            
            self.buf = torch.frombuffer(self.shm.buf, dtype=self.dtype).reshape(self.shape)
        else:
            self.shm_size = functools.reduce(operator.mul, shape, 1) * self.dtype().itemsize
            self.shm = multiprocessing.shared_memory.SharedMemory(create=True, size=self.shm_size)
            self.buf = np.ndarray(self.shape, dtype=self.dtype, buffer=self.shm.buf)
        
        self.created = True

    def insert(self, arr: Union[np.ndarray, 'torch.Tensor'], i: int):
        """Insert a batch dimension slice."""
        self.buf[i] = arr

    def copy(self, arr: Union[np.ndarray, 'torch.Tensor']):
        self.shape = arr.shape
        if self.is_torch:
            import torch
            self.buf = torch.frombuffer(self.shm.buf, dtype=self.dtype).reshape(self.shape)
        else:
            self.buf = np.ndarray(self.shape, dtype=self.dtype, buffer=self.shm.buf)
        self.buf[:] = arr[:]

    def tobytes(self):
        return self.buf.tobytes()

    def view(self):
        if self.is_torch:
            import torch
            return torch.frombuffer(self.shm.buf, dtype=self.dtype).reshape(self.shape)
        else:
            return np.ndarray(self.shape, self.dtype, buffer=self.shm.buf)

    # If we want easier interoperability, we could, instead, forward a
    # whitelist of attributes to our underlying np.ndarray object; these could
    # be enumerated and done via __getattribute__
    def __getitem__(self, idx: int):
        return self.buf[idx]

    def __array__(self, dtype: Union[np.dtype, 'torch.dtype'] = None):
        return self.buf.copy().astype(dtype) if dtype is not None else self.buf.copy()

    def __getstate__(self):
        state = self.__dict__.copy()
        del state["shm"]
        state.pop("buf", None)
        state["created"] = False
        state["shm_name"] = self.shm.name
        return state

    def __setstate__(self, state: dict):
        state = state.copy()
        shm_name = state.pop("shm_name")
        self.__dict__.update(state)
        self.shm = multiprocessing.shared_memory.SharedMemory(shm_name)
        if self.is_torch:
            import torch
            self.buf = torch.frombuffer(self.shm.buf, dtype=self.dtype).reshape(self.shape)
        else:
            self.buf = np.ndarray(self.shape, dtype=self.dtype, buffer=self.shm.buf)

    def __del__(self):
        if hasattr(self, "shm"):
            self.shm.close()
            if getattr(self, "created", None) is True:
                # Fix for problem with linux when the shared memory is being created and destroyed too fast
                if os.path.exists('/dev/shm/{}'.format(self.shm.name)):
                    self.shm.unlink()