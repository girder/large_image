import torch
import torch.nn as nn
import torch.nn.functional as F

from torchvision import io

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
        if x.dim() != 4:
            raise ValueError(f"Expected input to be a 4D tensor, got shape {tuple(x.shape)}")

        channels = x.shape[1]
        kernel_x = self.kernel_x.to(device=x.device, dtype=x.dtype).repeat(channels, 1, 1, 1)
        kernel_y = self.kernel_y.to(device=x.device, dtype=x.dtype).repeat(channels, 1, 1, 1)

        grad_x = F.conv2d(x, kernel_x, padding=1, groups=channels)
        grad_y = F.conv2d(x, kernel_y, padding=1, groups=channels)

        # Compute gradient magnitude
        magnitude = torch.sqrt(grad_x**2 + grad_y**2)

        # Uncomment to visualize the magnitude output
        # for i in range(magnitude.shape[0]):
        #     image = magnitude[i].detach().cpu() * 255
        #     # make image uint8
        #     image = image.to(dtype=torch.uint8)
        #     io.write_png(image, f"test_sobel_{i}.png")
        #     pass
        return magnitude