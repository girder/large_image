import os
from typing import Union, List, Any
import multiprocessing.shared_memory
import operator
import functools

import numpy as np

# Ignore torch import errors given they aren't required for this module

class SharedArray:
    def __init__(self, shape: Union[tuple, list], dtype: Union[np.dtype, 'torch.dtype'], is_torch: bool = False): # type: ignore
        """Init"""
        self.shape = shape        
        self.is_torch = is_torch
        self.dtype = dtype        
        
        if is_torch:
            import torch.multiprocessing # type: ignore
            self.shm_size = functools.reduce(operator.mul, shape, 1) * self.dtype.itemsize
            self.shm = multiprocessing.shared_memory.SharedMemory(create=True, size=self.shm_size)            
            self.buf = torch.frombuffer(self.shm.buf, dtype=self.dtype).reshape(self.shape)
        else:
            if callable(self.dtype):
                self.shm_size = functools.reduce(operator.mul, shape, 1) * self.dtype().itemsize
            else:
                self.shm_size = functools.reduce(operator.mul, shape, 1) * self.dtype.itemsize
            self.shm = multiprocessing.shared_memory.SharedMemory(create=True, size=self.shm_size)
            self.buf = np.ndarray(self.shape, dtype=self.dtype, buffer=self.shm.buf)
        
        self.created = True

    def resize_shm(self, shape: Union[tuple, list]):
        '''
        Resize the shared memory to be appropriate for a new shape.
        This is used to adjust the shape of the shared memory to be appropriate for a new shape.
        This is necessary for pytorch because reshape requires the tensor to be contiguous and 
        expects a certain size based on the shape provided.
        '''
        self.shape = shape
        self.shm.close()
        self.shm.unlink()
        if self.is_torch:
            import torch.multiprocessing # type: ignore
            self.shm_size = functools.reduce(operator.mul, shape, 1) * self.dtype.itemsize
            self.shm = multiprocessing.shared_memory.SharedMemory(create=True, size=self.shm_size)            
            self.buf = torch.frombuffer(self.shm.buf, dtype=self.dtype).reshape(self.shape)
        else:
            self.shm_size = functools.reduce(operator.mul, shape, 1) * self.dtype.itemsize
            self.shm = multiprocessing.shared_memory.SharedMemory(create=True, size=self.shm_size)
            self.buf = np.ndarray(self.shape, dtype=self.dtype, buffer=self.shm.buf)

    def insert(self, arr: Union[np.ndarray, 'torch.Tensor'], i: int): # type: ignore
        """Insert a batch dimension slice."""
        self.buf[i] = arr

    def copy(self, arr: Union[np.ndarray, 'torch.Tensor']): # type: ignore
        self.shape = arr.shape
        if self.is_torch:
            import torch # type: ignore
            self.buf = torch.frombuffer(self.shm.buf, dtype=self.dtype).reshape(self.shape)
        else:
            self.buf = np.ndarray(self.shape, dtype=self.dtype, buffer=self.shm.buf)
        self.buf[:] = arr[:]

    def tobytes(self):
        return self.buf.tobytes()

    def view(self):
        if self.is_torch:
            import torch # type: ignore
            # self.buf = torch.frombuffer(self.shm.buf, dtype=self.dtype
            # if self.shape[0] != 64:
            #     pass
            self.buf = torch.frombuffer(self.shm.buf, dtype=self.dtype).reshape(self.shape)
            return self.buf
        else:
            return np.ndarray(self.shape, self.dtype, buffer=self.shm.buf)

    # If we want easier interoperability, we could, instead, forward a
    # whitelist of attributes to our underlying np.ndarray object; these could
    # be enumerated and done via __getattribute__
    def __getitem__(self, idx: int):
        return self.buf[idx]

    def __array__(self, dtype: Union[np.dtype, 'torch.dtype'] = None): # type: ignore
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
            import torch # type: ignore
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