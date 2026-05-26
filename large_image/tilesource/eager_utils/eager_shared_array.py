"""Shared-memory array wrapper used by eager worker processes."""

import contextlib
import functools
import multiprocessing.shared_memory
import operator
import weakref
from typing import TYPE_CHECKING, Any, Union, cast

import numpy as np

# Ignore torch import errors given they aren't required for this module
if TYPE_CHECKING:
    import torch


class SharedArray:
    """Shared-memory array wrapper used by eager worker processes."""

    def __init__(
        self,
        shape: Union[tuple, list],
        dtype: Any,
        is_torch: bool = False,
        enable_mm: bool = False,
    ):
        """Create a shared-memory array.

        :param shape: Shape of the image batch buffer.
        :param dtype: Numpy or torch dtype stored by the buffer.
        :param is_torch: If True, expose the buffer as a torch tensor.
        :param enable_mm: If True, create a second shared buffer for mm scale metadata.
        :returns: None.
        """
        self.shape = shape
        self.is_torch = is_torch
        self.dtype = dtype
        self.buf: Any
        self.enable_mm = enable_mm
        self.mm_dtype = np.float32
        # Per-item runtime scale metadata in [mm_y, mm_x] order
        self.mm_shape = (shape[0], 2)

        if is_torch:
            import torch.multiprocessing

            self.shm_size = functools.reduce(operator.mul, shape, 1) * self.dtype.itemsize
            self.shm_array = multiprocessing.shared_memory.SharedMemory(
                create=True, size=self.shm_size,
            )
            self.buf = torch.frombuffer(
                self.shm_array.buf, dtype=self.dtype,
            ).reshape(self.shape)
        else:
            if callable(self.dtype):
                self.shm_size = functools.reduce(operator.mul, shape, 1) * self.dtype().itemsize
            else:
                self.shm_size = functools.reduce(operator.mul, shape, 1) * self.dtype.itemsize
            self.shm_array = multiprocessing.shared_memory.SharedMemory(
                create=True, size=self.shm_size,
            )
            self.buf = np.ndarray(self.shape, dtype=self.dtype, buffer=self.shm_array.buf)

        if self.enable_mm:
            # Shared 2D buffer aligned with batch index for runtime scale metadata
            mm_size = (
                functools.reduce(operator.mul, self.mm_shape, 1) * np.dtype(self.mm_dtype).itemsize
            )
            self.mm_shm_array = multiprocessing.shared_memory.SharedMemory(
                create=True, size=mm_size,
            )
            self.mm_buf = np.ndarray(
                self.mm_shape, dtype=self.mm_dtype, buffer=self.mm_shm_array.buf,
            )

        self.created = True
        self._closed = False

    def close(self) -> None:
        """Release the shared-memory resources owned by this array.

        :returns: None.
        """
        if self._closed or not hasattr(self, 'shm_array'):
            return

        self._release_buffer('buf')
        if self.enable_mm:
            self._release_buffer('mm_buf')
        if not self._close_shared_memory_handles():
            return
        try:
            self._unlink_shared_memory_handles()
        except FileNotFoundError:
            # Already cleaned up
            pass
        except Exception:
            # Ignore unlink issues during interpreter shutdown
            pass
        finally:
            self._closed = True

    def _release_buffer(self, attr_name: str) -> None:
        """Release an exported local buffer reference if present.

        :param attr_name: Buffer attribute name to remove.
        :returns: None.
        """
        try:
            if hasattr(self, attr_name):
                delattr(self, attr_name)
        except Exception:
            pass

    def _close_shared_memory_handles(self) -> bool:
        """Close shared-memory handles after local buffers are released.

        :returns: True when all relevant handles close successfully.
        """
        try:
            self.shm_array.close()
        except BufferError:
            # Other exported pointers still exist; cannot close now.
            # This is expected when user code still holds references to view() results.
            return False
        except Exception:
            # Ignore other shutdown-time issues.
            return False
        return self._close_mm_shared_memory_handle()

    def _close_mm_shared_memory_handle(self) -> bool:
        """Close the optional mm metadata shared-memory handle.

        :returns: True when no mm handle is enabled or the handle closes successfully.
        """
        if not self.enable_mm:
            return True
        try:
            if hasattr(self, 'mm_shm_array'):
                self.mm_shm_array.close()
        except BufferError:
            return False
        except Exception:
            return False
        return True

    def _unlink_shared_memory_handles(self) -> None:
        """Unlink shared-memory handles created by this process.

        :returns: None.
        """
        if getattr(self, 'created', None) is not True:
            return
        self.shm_array.unlink()
        if self.enable_mm:
            self.mm_shm_array.unlink()

    def resize_shm(self, shape: Union[tuple, list]):
        """Update the logical shape and byte size for the shared buffer.

        :param shape: New shape for the shared image batch buffer.
        :returns: None.
        """
        self.shape = shape
        self.mm_shape = (shape[0], 2)
        if self.is_torch:
            self.shm_size = functools.reduce(operator.mul, shape, 1) * self.dtype.itemsize
        else:
            itemsize = self.dtype().itemsize if callable(self.dtype) else self.dtype.itemsize
            self.shm_size = functools.reduce(operator.mul, shape, 1) * itemsize
        self.mm_shm_size = (
            functools.reduce(operator.mul, self.mm_shape, 1) * np.dtype(self.mm_dtype).itemsize
        )

    def insert(self, arr: Union[np.ndarray, 'torch.Tensor'], i: int):
        """Insert an array into a batch slot.

        :param arr: Numpy array or torch tensor to insert.
        :param i: Batch index to update.
        :returns: None.
        """
        self.buf[i] = arr

    def insert_mm(self, mm_x: float, mm_y: float, i: int):
        """Insert per-item mm scale metadata into a batch slot.

        :param mm_x: Horizontal pixel size in millimeters.
        :param mm_y: Vertical pixel size in millimeters.
        :param i: Batch index to update.
        :returns: None.
        """
        if not self.enable_mm:
            msg = 'SharedArray mm metadata not enabled.'
            raise RuntimeError(msg)
        self.mm_buf[i, 0] = mm_y
        self.mm_buf[i, 1] = mm_x

    def copy(self, arr: Union[np.ndarray, 'torch.Tensor']):
        """Copy an array into the shared-memory buffer.

        :param arr: Numpy array or torch tensor to copy.
        :returns: None.
        """
        self.shape = arr.shape
        if self.is_torch:
            import torch

            self.buf = torch.frombuffer(self.shm_array.buf, dtype=self.dtype).reshape(self.shape)
        else:
            self.buf = np.ndarray(self.shape, dtype=self.dtype, buffer=self.shm_array.buf)
        self.buf[:] = arr[:]

    def tobytes(self):
        """Return the shared-memory contents as bytes.

        :returns: The byte representation of the current image buffer.
        """
        return self.buf.tobytes()

    def view(self):
        """Return an array or tensor view of the shared image buffer.

        :returns: A numpy array or torch tensor backed by shared memory.
        """
        if self.is_torch:
            import torch

            shm_buf = cast(Any, self.shm_array.buf)
            view_buf = torch.frombuffer(
                shm_buf[: self.shm_size], dtype=self.dtype,
            ).reshape(self.shape)
            return view_buf
        # copy bytes for view
        np_view_buf = np.ndarray(self.shape, self.dtype, buffer=self.shm_array.buf)
        return np_view_buf

    def mm_view(self):
        """Return a view of the shared mm scale metadata buffer.

        :returns: A numpy array with [mm_y, mm_x] columns.
        """
        if not self.enable_mm:
            msg = 'SharedArray mm metadata not enabled for this iterator.'
            raise RuntimeError(msg)
        return np.ndarray(self.mm_shape, self.mm_dtype, buffer=self.mm_shm_array.buf)

    # If we want easier interoperability, we could, instead, forward a
    # whitelist of attributes to our underlying np.ndarray object; these could
    # be enumerated and done via __getattribute__
    def __getitem__(self, idx: int):
        """Return an item from the shared image buffer.

        :param idx: Index or slice to retrieve.
        :returns: The selected item from the shared image buffer.
        """
        return self.buf[idx]

    def __array__(self, dtype: Any = None):
        """Return a numpy copy of the shared image buffer.

        :param dtype: Optional dtype for the returned numpy array.
        :returns: A numpy array copy of the shared image buffer.
        """
        return self.buf.copy().astype(dtype) if dtype is not None else self.buf.copy()

    def __getstate__(self):
        """Return pickle state for passing this object to worker processes.

        :returns: A state dictionary with shared-memory names instead of buffer views.
        """
        state = self.__dict__.copy()
        state.pop('shm', None)
        state.pop('buf', None)
        state.pop('mm_buf', None)
        state['created'] = False
        state['shm_name'] = self.shm_array.name
        state['mm_shm_name'] = self.mm_shm_array.name if self.enable_mm else None
        return state

    def __setstate__(self, state: dict):
        """Restore shared-memory handles from pickle state.

        :param state: State dictionary produced by __getstate__.
        :returns: None.
        """
        state = state.copy()
        shm_name = state.pop('shm_name')
        mm_shm_name = state.pop('mm_shm_name')
        self.__dict__.update(state)
        self._closed = False  # Reset closed state when unpickling
        self._exported_refs: weakref.WeakSet[Any] = weakref.WeakSet()
        self.shm_array = multiprocessing.shared_memory.SharedMemory(shm_name)
        if self.enable_mm:
            self.mm_shm_array = multiprocessing.shared_memory.SharedMemory(mm_shm_name)

        if self.is_torch:
            import torch

            self.buf = torch.frombuffer(self.shm_array.buf, dtype=self.dtype).reshape(self.shape)
        else:
            self.buf = np.ndarray(self.shape, dtype=self.dtype, buffer=self.shm_array.buf)
        if self.enable_mm:
            self.mm_buf = np.ndarray(
                self.mm_shape, dtype=self.mm_dtype, buffer=self.mm_shm_array.buf,
            )

    def __del__(self):
        """Release shared-memory resources during object destruction.

        :returns: None.
        """
        with contextlib.suppress(Exception):
            self.close()
