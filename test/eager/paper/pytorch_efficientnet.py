import torch
from torchvision.models import (efficientnet_b0, efficientnet_b1,
                                efficientnet_b2, efficientnet_b3,
                                efficientnet_b4, efficientnet_b5,
                                efficientnet_b6, efficientnet_b7)
from torchvision.models.efficientnet import (EfficientNet_B0_Weights,
                                             EfficientNet_B1_Weights,
                                             EfficientNet_B2_Weights,
                                             EfficientNet_B3_Weights,
                                             EfficientNet_B4_Weights,
                                             EfficientNet_B5_Weights,
                                             EfficientNet_B6_Weights,
                                             EfficientNet_B7_Weights)


def make_efficientnet_model(
    model_name: str = 'efficientnetb0',
    compile_model: bool = True,
    cuda_device: str = 'cuda:0',
):
    if model_name == 'efficientnetb0':
        model = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT)
    elif model_name == 'efficientnetb1':
        model = efficientnet_b1(weights=EfficientNet_B1_Weights.DEFAULT)
    elif model_name == 'efficientnetb2':
        model = efficientnet_b2(weights=EfficientNet_B2_Weights.DEFAULT)
    elif model_name == 'efficientnetb3':
        model = efficientnet_b3(weights=EfficientNet_B3_Weights.DEFAULT)
    elif model_name == 'efficientnetb4':
        model = efficientnet_b4(weights=EfficientNet_B4_Weights.DEFAULT)
    elif model_name == 'efficientnetb5':
        model = efficientnet_b5(weights=EfficientNet_B5_Weights.DEFAULT)
    elif model_name == 'efficientnetb6':
        model = efficientnet_b6(weights=EfficientNet_B6_Weights.DEFAULT)
    elif model_name == 'efficientnetb7':
        model = efficientnet_b7(weights=EfficientNet_B7_Weights.DEFAULT)

    # Set model to evaluation mode
    model.eval()

    model.to(cuda_device)

    # Compile model if needed
    if compile_model:
        torch.compiler.set_stance('force_eager')
        model = torch.compile(model)

    return model


if __name__ == '__main__':
    model = make_efficientnet_model()
    print(model.summary())
