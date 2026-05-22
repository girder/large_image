"""Context manager for temporarily limiting PyTorch thread counts."""

# Ignore torch import errors given they aren't required for this module


class _PyTorchThreadingContext:
    """Context manager to temporarily set PyTorch threading to 1 thread per process."""

    def __init__(self):
        """Initialize saved PyTorch threading state.

        :returns: None.
        """
        self.original_num_threads = None
        self.original_interop_threads = None
        self.torch_available = False

    def __enter__(self):
        """Limit PyTorch to one intra-op thread while inside the context.

        :returns: This context manager instance.
        """
        try:
            import torch  # type: ignore

            self.torch_available = True
            # Save current settings
            self.original_num_threads = torch.get_num_threads()
            # Set to single thread
            torch.set_num_threads(1)
        except ImportError:
            self.torch_available = False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore the PyTorch thread count when leaving the context.

        :param exc_type: Exception type raised inside the context, if any.
        :param exc_val: Exception value raised inside the context, if any.
        :param exc_tb: Traceback raised inside the context, if any.
        :returns: None.
        """
        if self.torch_available:
            try:
                import torch  # type: ignore

                # Restore original settings
                if self.original_num_threads is not None:
                    torch.set_num_threads(self.original_num_threads)
                # if self.original_interop_threads is not None:
                #     torch.set_num_interop_threads(self.original_interop_threads)
            except ImportError:
                pass
