import os

from huggingface_hub import snapshot_download
from keras.models import load_model


def build_keras_breast_cancer_detector():
    # Download model from Hugging Face
    snapshot_download(repo_id='MUmairAB/Breast_Cancer_Detector',
                      local_dir='/scr/arosado/performance/keras_breast_cancer_detector')

    if os.path.exists(
            '/scr/arosado/performance/keras_breast_cancer_detector/Trained Model/CanDetect.keras'):
        # Load model
        model = load_model(
            '/scr/arosado/performance/keras_breast_cancer_detector/Trained Model/CanDetect.keras')

        return model
    return model


if __name__ == '__main__':
    model = build_keras_breast_cancer_detector()
    print(model)
