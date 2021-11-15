# Used as controller for donkey client. Takes image and makes predictions
# of steering and throttle with its model.
import numpy as np
# import tensorflow as tf
import pickle
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
# from tensorflow.python.keras.backend import batch_dot
# import time
# import gc

class Autopilot:

    def __init__(self, conf):
        self.model = load_model(conf['model_path'])
        self.scaler = pickle.load(conf['scaler_path'])

    def convert_image(self, img):
        img_array = img_to_array(img)
        return img_array / 255

    def infer(self, inputs):
        img = self.convert_image(inputs[0])
        imu = self.scaler.transform(np.array(inputs[1]))
        img_in = img.reshape((1,)+img.shape)
        imu_in = imu.reshape((1,)+imu.shape)
        pred = self.model([img_in, imu_in])
        # st_pred = pred[0].numpy()[0][0]
        # th_pred = pred[1].numpy()[0][0]
        st_pred = pred.numpy()[0][0]
        th_pred = pred.numpy()[0][1]
        return st_pred, th_pred
