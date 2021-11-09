# Used as controller for donkey client. Takes image and makes predictions
# of steering and throttle with its model.
# import numpy as np
# import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array

class Autopilot:

    def __init__(self, model_path):
        print(f'model path: {model_path}')
        print(type(model_path))
        # self.model = load_model(model_path)
        self.model = load_model(model_path)


    def convert_image(self, img):
        img_array = img_to_array(img)
        return img_array / 255

    def infer(self, img):
        arr = self.convert_image(img)
        outputs = self.model.predict(arr.reshape((1,) + arr.shape))
        return outputs[0][0], outputs[0][1]
