# Used as controller for donkey client. Takes image and makes predictions
# of steering and throttle with its model.
import numpy as np
# import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.python.keras.backend import batch_dot
import time
# import gc

class Autopilot:

    def __init__(self, model_path):
        # print(f'model path: {model_path}')
        # print(type(model_path))
        self.model = load_model(model_path)

    def convert_image(self, img):
        img_array = img_to_array(img)
        return img_array / 255

    def infer(self, inputs):
        img = self.convert_image(inputs[0])
        imu = np.array(inputs[1])
        img_in = img.reshape((1,)+img.shape)
        imu_in = imu.reshape((1,)+imu.shape)
        pred = self.model([img_in, imu_in])
        # st_pred = pred[0].numpy()[0][0]
        # th_pred = pred[1].numpy()[0][0]
        st_pred = pred.numpy()[0][0]
        th_pred = pred.numpy()[0][1]
        return st_pred, th_pred

class LineFollower:

    def __init__(self):
        # put PID stuff here.
        # self.steering_modifier = 1
        self.steering_P = 0.75
        self.steering_D = 0.5
        self.throttle_P = 2
        # self.throttle_D = 2
        self.steering_max = 0.64
        self.steering = 0
        self.throttle = 0
        self.previous_e = 0
        # self.current_time = time.time()
        self.previous_time = time.time()

    def update(self, cte):
        self.current_time = time.time()
        e = self.norm(cte, -4, 4)
        d = e - self.previous_e
        steering = ((e * self.steering_P) + (d * self.steering_D)) * -1
        throttle = 0.5 - (e * self.throttle_P)
        max_steer = self.steering_P + self.steering_D
        min_steer = max_steer * -1
        steering = self.norm(steering, min_steer, max_steer)
        throttle = self.norm(throttle, -4, 4)
        self.previous_cte = e 
        return steering, throttle
        

    def norm(self, x, minimum, maximum, low=-1.0, high=1.0):
        v_val = x
        v_min = minimum
        v_max = maximum
        return (high - low) * (v_val - v_min) / (v_max - v_min) + low