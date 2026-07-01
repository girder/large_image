import torch
import torch.nn as nn
import torch.nn.functional as F


def make_sobel_model(compile_model: bool = True, cuda_device: str = 'cuda:0'):
    model = SobelFilter()

    model.eval()

    model.to(cuda_device)

    # Compile model if needed
    if compile_model:
        model.compile()

    return model


class SobelFilter(nn.Module):
    def __init__(self_, max_channels: int = 3):
        super().__init__()
        # Define Sobel kernels
        sobel_x = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=torch.float32)
        sobel_y = torch.tensor([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=torch.float32)

        # Reshape kernels for conv2d: (out_channels, in_channels, kernel_height, kernel_width)
        # We assume single-channel input and single-channel output for each kernel
        self_.sobel_x = sobel_x.unsqueeze(0).unsqueeze(0).repeat(max_channels, 1, 1, 1)
        self_.sobel_y = sobel_y.unsqueeze(0).unsqueeze(0).repeat(max_channels, 1, 1, 1)

        # Register kernels as parameters (optional, but useful if you want to learn them)
        # For a fixed Sobel filter, it's better to register them as buffers
        self_.register_buffer('kernel_x', self_.sobel_x)
        self_.register_buffer('kernel_y', self_.sobel_y)
        self_.max_channels = max_channels

    def forward(self_, x):
        # Apply convolution for horizontal and vertical gradients
        if x.dim() != 4:
            msg = f'Expected input to be a 4D tensor, got shape {tuple(x.shape)}'
            raise ValueError(msg)

        channels = x.shape[1]
        if channels > self_.max_channels:
            msg = f'Expected input to have {self_.max_channels} channels, got {channels}'
            raise ValueError(
                msg,
            )

        kernel_x = self_.kernel_x[:channels]
        kernel_y = self_.kernel_y[:channels]

        grad_x = F.conv2d(x, kernel_x, padding=1, groups=channels)
        grad_y = F.conv2d(x, kernel_y, padding=1, groups=channels)

        # Compute gradient magnitude
        added = torch.add(torch.square(grad_x), torch.square(grad_y))
        magnitude = torch.sqrt(added)

        # Uncomment to visualize the magnitude output
        # for i in range(magnitude.shape[0]):
        #     image = magnitude[i].detach().cpu() * 255
        #     # make image uint8
        #     image = image.to(dtype=torch.uint8)
        #     io.write_png(image, f"test_sobel_{i}.png")
        #     pass
        return magnitude
