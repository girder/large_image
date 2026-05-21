import functools
import multiprocessing.shared_memory
import operator
import weakref
from typing import TYPE_CHECKING, Union

import numpy as np

# Ignore torch import errors given they aren't required for this module
if TYPE_CHECKING:
    import torch


class SharedArray:
    def __init__(
        self,
        shape: Union[tuple, list],
        dtype: Union[np.dtype, 'torch.dtype'],
        is_torch: bool = False,
        enable_mm: bool = False,
    ):  # type: ignore
        """Init"""
        self.shape = shape
        self.is_torch = is_torch
        self.dtype = dtype
        self.enable_mm = enable_mm
        self.mm_dtype = np.float32
        # Per-item runtime scale metadata in [mm_y, mm_x] order
        self.mm_shape = (shape[0], 2)

        if is_torch:
            import torch.multiprocessing  # type: ignore
            self.shm_size = functools.reduce(operator.mul, shape, 1) * self.dtype.itemsize
            self.shm_array = multiprocessing.shared_memory.SharedMemory(
                create=True, size=self.shm_size)
            self.buf = torch.frombuffer(self.shm_array.buf, dtype=self.dtype).reshape(self.shape)
        else:
            if callable(self.dtype):
                self.shm_size = functools.reduce(operator.mul, shape, 1) * self.dtype().itemsize
            else:
                self.shm_size = functools.reduce(operator.mul, shape, 1) * self.dtype.itemsize
            self.shm_array = multiprocessing.shared_memory.SharedMemory(
                create=True, size=self.shm_size)
            self.buf = np.ndarray(self.shape, dtype=self.dtype, buffer=self.shm_array.buf)

        if self.enable_mm:
            # Shared 2D buffer aligned with batch index for runtime scale metadata
            mm_size = functools.reduce(operator.mul, self.mm_shape, 1) * \
                np.dtype(self.mm_dtype).itemsize
            self.mm_shm_array = multiprocessing.shared_memory.SharedMemory(
                create=True, size=mm_size)
            self.mm_buf = np.ndarray(
                self.mm_shape,
                dtype=self.mm_dtype,
                buffer=self.mm_shm_array.buf)

        self.created = True
        self._closed = False

    def close(self) -> None:
        """Attempt to release the shared memory segment.

        This removes our exported pointer first (self.buf), then closes the
        SharedMemory handle and unlinks it if we created it. If any exported
        pointers still exist elsewhere (e.g., arrays returned from view()),
        close() may raise BufferError; in that case we silently skip so the
        process can continue and rely on the OS to clean up at exit.
        """
        if self._closed or not hasattr(self, 'shm_array'):
            return

        # Release our direct exported pointers before closing SharedMemory.
        # If user code still holds view() results, close can still BufferError.
        try:
            if hasattr(self, 'buf'):
                del self.buf
        except Exception:
            pass

        if self.enable_mm:
            try:
                if hasattr(self, 'mm_buf'):
                    del self.mm_buf
            except Exception:
                pass

        try:
            if hasattr(self, 'shm_array'):
                self.shm_array.close()
        except BufferError:
            # Other exported pointers still exist; cannot close now.
            # This is expected when user code still holds references to view() results
            return
        except Exception:
            # Ignore other shutdown-time issues
            return

        if self.enable_mm:
            try:
                if hasattr(self, 'mm_shm_array'):
                    self.mm_shm_array.close()
            except BufferError:
                return
            except Exception:
                return

        # Only attempt to unlink if close() succeeded
        try:
            if getattr(self, 'created', None) is True:
                self.shm_array.unlink()
                if self.enable_mm:
                    self.mm_shm_array.unlink()
        except FileNotFoundError:
            # Already cleaned up
            pass
        except Exception:
            # Ignore unlink issues during interpreter shutdown
            pass
        finally:
            self._closed = True

    def resize_shm(self, shape: Union[tuple, list]):
        """
        Resize the shared memory to be appropriate for a new shape.
        This is used to adjust the shape of the shared memory to be appropriate for a new shape.
        This is necessary for pytorch because reshape requires the tensor to be contiguous and
        expects a certain size based on the shape provided.
        """
        self.shape = shape
        self.mm_shape = (shape[0], 2)
        if self.is_torch:
            self.shm_size = functools.reduce(operator.mul, shape, 1) * self.dtype.itemsize
        else:
            if callable(self.dtype):
                itemsize = self.dtype().itemsize
            else:
                itemsize = self.dtype.itemsize
            self.shm_size = functools.reduce(operator.mul, shape, 1) * itemsize
        self.mm_shm_size = functools.reduce(
            operator.mul, self.mm_shape, 1) * np.dtype(self.mm_dtype).itemsize

    def insert(self, arr: Union[np.ndarray, 'torch.Tensor'], i: int):  # type: ignore
        """Insert a batch dimension slice."""
        self.buf[i] = arr

    def insert_mm(self, mm_x: float, mm_y: float, i: int):
        """Insert mm scale metadata as [mm_y, mm_x] for a batch index."""
        if not self.enable_mm:
            raise RuntimeError('SharedArray mm metadata not enabled.')
        self.mm_buf[i, 0] = mm_y
        self.mm_buf[i, 1] = mm_x

    def copy(self, arr: Union[np.ndarray, 'torch.Tensor']):  # type: ignore
        """Copy an array into the shared memory."""
        self.shape = arr.shape
        if self.is_torch:
            import torch  # type: ignore
            self.buf = torch.frombuffer(self.shm_array.buf, dtype=self.dtype).reshape(self.shape)
        else:
            self.buf = np.ndarray(self.shape, dtype=self.dtype, buffer=self.shm_array.buf)
        self.buf[:] = arr[:]

    def tobytes(self):
        """Convert the shared memory to bytes."""
        return self.buf.tobytes()

    def view(self):
        """View the shared memory."""
        if self.is_torch:
            import torch  # type: ignore
            view_buf = torch.frombuffer(
                self.shm_array.buf[:self.shm_size], dtype=self.dtype).reshape(self.shape)
            return view_buf
        # copy bytes for view
        view_buf = np.ndarray(self.shape, self.dtype, buffer=self.shm_array.buf)
        return view_buf

    def mm_view(self):
        """View consolidated mm shared memory buffer with [mm_y, mm_x] columns."""
        if not self.enable_mm:
            raise RuntimeError('SharedArray mm metadata not enabled for this iterator.')
        return np.ndarray(self.mm_shape, self.mm_dtype, buffer=self.mm_shm_array.buf)

    # If we want easier interoperability, we could, instead, forward a
    # whitelist of attributes to our underlying np.ndarray object; these could
    # be enumerated and done via __getattribute__
    def __getitem__(self, idx: int):
        """Get an item from the shared memory."""
        return self.buf[idx]

    def __array__(self, dtype: Union[np.dtype, 'torch.dtype'] = None):  # type: ignore
        """Convert the shared memory to an array."""
        return self.buf.copy().astype(dtype) if dtype is not None else self.buf.copy()

    def __getstate__(self):
        """Get the state of the shared memory."""
        state = self.__dict__.copy()
        state.pop('shm', None)
        state.pop('buf', None)
        state.pop('mm_buf', None)
        state['created'] = False
        state['shm_name'] = self.shm_array.name
        state['mm_shm_name'] = self.mm_shm_array.name if self.enable_mm else None
        return state

    def __setstate__(self, state: dict):
        """Set the state of the shared memory."""
        state = state.copy()
        shm_name = state.pop('shm_name')
        mm_shm_name = state.pop('mm_shm_name')
        self.__dict__.update(state)
        self._closed = False  # Reset closed state when unpickling
        self._exported_refs = weakref.WeakSet()  # Initialize reference tracking
        self.shm_array = multiprocessing.shared_memory.SharedMemory(shm_name)
        if self.enable_mm:
            self.mm_shm_array = multiprocessing.shared_memory.SharedMemory(mm_shm_name)

        if self.is_torch:
            import torch  # type: ignore
            self.buf = torch.frombuffer(self.shm_array.buf, dtype=self.dtype).reshape(self.shape)
        else:
            self.buf = np.ndarray(self.shape, dtype=self.dtype, buffer=self.shm_array.buf)
        if self.enable_mm:
            self.mm_buf = np.ndarray(
                self.mm_shape,
                dtype=self.mm_dtype,
                buffer=self.mm_shm_array.buf)

    def __del__(self):
        """Delete the shared memory."""
        try:
            self.close()
        except Exception:
            # Suppress any shutdown-time exceptions
            pass
