import torch
import timm

def make_huggingface_uni2_model(compile_model: bool = True, cuda_device: str = 'cuda:0'):
    # pretrained=True needed to load UNI2-h weights (and download weights for the first time)
    timm_kwargs = {
                'img_size': 224, 
                'patch_size': 14, 
                'depth': 24,
                'num_heads': 24,
                'init_values': 1e-5, 
                'embed_dim': 1536,
                'mlp_ratio': 2.66667*2,
                'num_classes': 0, 
                'no_embed_class': True,
                'mlp_layer': timm.layers.SwiGLUPacked, 
                'act_layer': torch.nn.SiLU, 
                'reg_tokens': 8, 
                'dynamic_img_size': True
            }

    # def wrap_dinov2_model(model):
    #     from torch import nn
    #     from transformers.models.dinov2.modeling_dinov2 import Dinov2PatchEmbeddings
    #     from transformers.utils import torch_int
    #     import math

    #     def patch_embeddings_forward(self, pixel_values: torch.Tensor) -> torch.Tensor:
    #         # Dont check the channel dimension
    #         # num_channels = pixel_values.shape[1]
    #         # if num_channels != self.num_channels:
    #         #     raise ValueError(
    #         #         "Make sure that the channel dimension of the pixel values match with the one set in the configuration."
    #         #         f" Expected {self.num_channels} but got {num_channels}."
    #         #     )
    #         embeddings = self.projection(pixel_values).flatten(2).transpose(1, 2)
    #         return embeddings

    #     def interpolate_pos_encoding(self, embeddings: torch.Tensor, height: int, width: int) -> torch.Tensor:
    #         """
    #         This method allows to interpolate the pre-trained position encodings, to be able to use the model on higher resolution
    #         images. This method is also adapted to support torch.jit tracing and interpolation at torch.float32 precision.

    #         Adapted from:
    #         - https://github.com/facebookresearch/dino/blob/de9ee3df6cf39fac952ab558447af1fa1365362a/vision_transformer.py#L174-L194, and
    #         - https://github.com/facebookresearch/dinov2/blob/e1277af2ba9496fbadf7aec6eba56e8d882d1e35/dinov2/models/vision_transformer.py#L179-L211
    #         """

    #         num_patches = embeddings.shape[1] - 1
    #         num_positions = self.position_embeddings.shape[1] - 1

    #         # always interpolate when tracing to ensure the exported model works for dynamic input shapes
    #         # if not torch.jit.is_tracing() and num_patches == num_positions and height == width:
    #         #     return self.position_embeddings

    #         class_pos_embed = self.position_embeddings[:, :1]
    #         patch_pos_embed = self.position_embeddings[:, 1:]

    #         dim = embeddings.shape[-1]

    #         new_height = height // self.patch_size
    #         new_width = width // self.patch_size

    #         # Updated to use math.floor and math.sqrt to be compatible with proxy for tracing
    #         sqrt_num_positions = math.floor(math.sqrt(num_positions))
    #         patch_pos_embed = patch_pos_embed.reshape(1, sqrt_num_positions, sqrt_num_positions, dim)
    #         patch_pos_embed = patch_pos_embed.permute(0, 3, 1, 2)
    #         target_dtype = patch_pos_embed.dtype
    #         patch_pos_embed = nn.functional.interpolate(
    #             patch_pos_embed.to(torch.float32),
    #             size=(new_height, new_width),
    #             mode="bicubic",
    #             align_corners=False,
    #         ).to(dtype=target_dtype)

    #         patch_pos_embed = patch_pos_embed.permute(0, 2, 3, 1).view(1, -1, dim)

    #         return torch.cat((class_pos_embed, patch_pos_embed), dim=1)

    #     class WrappedDinoV2(nn.Module):
    #         def __init__(self, model):
    #             super().__init__()
    #             self.model = model
    #             # self.model.config._attn_implementation = 'eager'
    #             patch_embeddings_func_type = type(self.model.embeddings.patch_embeddings.forward)
    #             interpolate_pos_encoding_func_type = type(self.model.embeddings.interpolate_pos_encoding)
    #             self.model.embeddings.patch_embeddings.forward = patch_embeddings_func_type(patch_embeddings_forward, self.model.embeddings.patch_embeddings)
    #             self.model.embeddings.interpolate_pos_encoding = interpolate_pos_encoding_func_type(interpolate_pos_encoding, self.model.embeddings)
            
    #         def forward(self, x):           
    #             return self.model.forward(x) 

    #     return WrappedDinoV2(model)

    model = timm.create_model("hf-hub:MahmoodLab/UNI2-h", pretrained=True, **timm_kwargs)

    from timm.layers.patch_embed import PatchEmbed
    from timm.models import VisionTransformer
    named_modules = list(model.named_modules())
    for name, module in named_modules:
        if isinstance(module, PatchEmbed):
            # Make the image size strict
            setattr(module, 'strict_img_size', True)
            # Make the image size non-dynamic
            setattr(module, 'dynamic_img_pad', False)
        if isinstance(module, VisionTransformer):
            # Make the image size non-dynamic
            setattr(module, 'dynamic_img_size', False)
            # Pos embed is not needed for a static image size
            setattr(module, 'pos_embed', None)

    # model = wrap_dinov2_model(model)
    
    model.eval()

    model.to(cuda_device)

    # Compile model if needed
    if compile_model:
        model.compile()

    return model