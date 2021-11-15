# Used as controller for donkey client. Takes image and makes predictions
# of steering and throttle with its model.
import numpy as np
# import tensorflow as tf
import sklearn
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
import pickle
# from sklearn.preprocessing import StandardScaler
# from tensorflow.python.keras.backend import batch_dot
# import time
# import gc

class Autopilot:

    def __init__(self, conf):
        self.model = load_model(conf['model_path'])
        self.scaler = pickle.load(open(conf['scaler_path'], 'rb'))
        self.dual_output = conf['dual_output']

    def convert_image(self, img):
        img_array = img_to_array(img)
        return img_array / 255

    def infer(self, inputs):
        img = self.convert_image(inputs[0])
        imu = np.array([inputs[1]])
        imu_in = self.scaler.transform(imu)
        img_in = img.reshape((1,)+img.shape)
        # imu_in = imu.reshape((1,)+imu.shape)
        pred = self.model([img_in, imu_in])
        if self.dual_output:
            st_pred = pred[0].numpy()[0][0]
            th_pred = pred[1].numpy()[0][0]
        else:
            st_pred = pred.numpy()[0][0]
            th_pred = pred.numpy()[0][1]
        return st_pred, th_pred

    # def infer(self, inputs):
    #     if len(inputs) > 1:
    #         return self.vimu_infer(inputs)
    #     img = self.convert_image(inputs[0])
    #     img_in = img.reshape((1,)+img.shape)
    #     pred = self.model(img_in)
    #     st_pred = pred[0].numpy()[0][0]
    #     th_pred = pred[1].numpy()[0][0]
    #     return st_pred, th_pred


