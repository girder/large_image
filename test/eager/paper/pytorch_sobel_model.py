import torch
import torch.nn as nn
import torch.nn.functional as F

class SobelFilter(nn.Module):
    def __init__(self):
        super(SobelFilter, self).__init__()
        # Define Sobel kernels
        sobel_x = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=torch.float32)
        sobel_y = torch.tensor([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=torch.float32)

        # Reshape kernels for conv2d: (out_channels, in_channels, kernel_height, kernel_width)
        # We assume single-channel input and single-channel output for each kernel
        self.sobel_x = sobel_x.unsqueeze(0).unsqueeze(0)
        self.sobel_y = sobel_y.unsqueeze(0).unsqueeze(0)

        # Register kernels as parameters (optional, but useful if you want to learn them)
        # For a fixed Sobel filter, it's better to register them as buffers
        self.register_buffer('kernel_x', self.sobel_x)
        self.register_buffer('kernel_y', self.sobel_y)

    def forward(self, x):
        # Apply convolution for horizontal and vertical gradients
        grad_x = F.conv2d(x, self.kernel_x, padding=1)
        grad_y = F.conv2d(x, self.kernel_y, padding=1)

        # Compute gradient magnitude
        magnitude = torch.sqrt(grad_x**2 + grad_y**2)
        return magnitude