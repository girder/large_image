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

    def close(self) -> None:
        """Attempt to release the shared memory segment.

        This removes our exported pointer first (self.buf), then closes the
        SharedMemory handle and unlinks it if we created it. If any exported
        pointers still exist elsewhere (e.g., arrays returned from view()),
        close() may raise BufferError; in that case we silently skip so the
        process can continue and rely on the OS to clean up at exit.
        """
        if not hasattr(self, "shm"):
            return
        try:
            # Drop our direct reference before closing to avoid BufferError
            if hasattr(self, "buf"):
                del self.buf
            self.shm.close()
        except (BufferError):
            # Other exported pointers still exist; cannot close now.
            return
        except Exception:
            # Ignore other shutdown-time issues
            return
        try:
            if getattr(self, "created", None) is True:
                shm_path = f"/dev/shm/{self.shm.name}"
                if os.path.exists(shm_path):
                    self.shm.unlink()
        except FileNotFoundError:
            pass
        except Exception:
            # Ignore unlink issues during interpreter shutdown
            pass

    def resize_shm(self, shape: Union[tuple, list]):
        '''
        Resize the shared memory to be appropriate for a new shape.
        This is used to adjust the shape of the shared memory to be appropriate for a new shape.
        This is necessary for pytorch because reshape requires the tensor to be contiguous and 
        expects a certain size based on the shape provided.
        '''
        self.shape = shape
        if self.is_torch:
            import torch.multiprocessing # type: ignore
            self.shm_size = functools.reduce(operator.mul, shape, 1) * self.dtype.itemsize            
        else:
            if callable(self.dtype):
                itemsize = self.dtype().itemsize
            else:
                itemsize = self.dtype.itemsize
            self.shm_size = functools.reduce(operator.mul, shape, 1) * itemsize

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
            self.buf = torch.frombuffer(self.shm.buf[:self.shm_size], dtype=self.dtype).reshape(self.shape)
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
        try:
            self.close()
        except Exception:
            # Suppress any shutdown-time exceptions
            pass