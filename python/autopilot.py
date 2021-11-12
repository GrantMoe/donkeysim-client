# Used as controller for donkey client. Takes image and makes predictions
# of steering and throttle with its model.
# import numpy as np
# import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.python.keras.backend import batch_dot
# import gc

class Autopilot:

    def __init__(self, model_path):
        # print(f'model path: {model_path}')
        # print(type(model_path))
        self.model = load_model(model_path)

    def convert_image(self, img):
        img_array = img_to_array(img)
        return img_array / 255

    def infer(self, img):
        arr = self.convert_image(img)
        outputs = self.model.predict(arr.reshape((1,)+arr.shape), 
                                   batch_size=1)
        return outputs[0][0], outputs[0][1]

class LineFollower:

    def __init__(self):
        # put PID stuff here.
        # self.steering_modifier = 1
        self.steering = 0
        self.throttle = 0
        self.previous_cte = 0

    def update(self, cte):
        # steering
        if cte < 0:
            self.steering = 1.0
        elif cte > 0:
            self.steering = -1.0
        else:
            self.steering = 0.0
        # throttle
        if abs(cte) > abs(self.previous_cte):
            self.throttle -= 0.01
        elif abs(cte) < abs(self.previous_cte):
            self.throttle += 0.01
        self.previous_cte = cte
        return self.steering, self.throttle
        

