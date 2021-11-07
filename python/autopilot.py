# Used as controller for donkey client. Takes image and makes predictions
# of steering and throttle with its model.
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array

class Autopilot:

    def __init__(self, model_path):
        self.model = load_model(model_path)

    ## Keeping this really simple for now
    def infer(self, img):
        return self.model(img.reshape((1,) + img.shape)[0])

