# Ignore torch import errors given they aren't required for this module

class _PyTorchThreadingContext:
    """Context manager to temporarily set PyTorch threading to 1 thread per process."""
    
    def __init__(self):
        self.original_num_threads = None
        self.original_interop_threads = None
        self.torch_available = False
        
    def __enter__(self):
        try:
            import torch # type: ignore
            self.torch_available = True
            # Save current settings
            self.original_num_threads = torch.get_num_threads()
            # self.original_interop_threads = torch.get_num_interop_threads()
            # Set to single thread
            torch.set_num_threads(1)
            # torch.set_num_interop_threads(1)
        except ImportError:
            self.torch_available = False
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.torch_available:
            try:
                import torch # type: ignore
                # Restore original settings
                if self.original_num_threads is not None:
                    torch.set_num_threads(self.original_num_threads)
                # if self.original_interop_threads is not None:
                #     torch.set_num_interop_threads(self.original_interop_threads)
            except ImportError:
                pass