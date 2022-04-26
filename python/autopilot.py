# Used as controller for donkey client. Takes image and makes predictions
# of steering and throttle with its model.
import csv
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
import pickle
from collections import deque

from config import MODEL_DIRECTORY, MODEL_TYPE, SCALER_DIRECTORY

class Autopilot:

    def __init__(self, conf):
        self.model_number = conf['model_number']
        data = model_paths(conf['model_history'], conf['model_number'])
        self.model = load_model(f"{MODEL_DIRECTORY}/{data['model_file']}", compile=False)
        ## try to detect if prior image norming is required (currently broken)
        # print(self.model.get_layer(index=1).name)
        # self.norm_images = self.model.get_layer(index=1).name != 'rescaling'
        self.scaler = pickle.load(open(f"{SCALER_DIRECTORY}/{data['scaler_file']}", 'rb'))
        self.telemetry_columns = data['telemetry_columns']
        self.model_type = conf['model_type']
        self.image_depth = conf['image_depth']
        self.active = True
        print('autopilot initiated')

    # converts from 0-255 uint to expected 0.0-1.0 float
    def norm_image(self, img):
        img_array = img_to_array(img)
        return img_array / 255

    def infer(self, inputs):
        
        if self.model_number < 309:
            img = self.norm_image(inputs[0])
        else:
            img = img_to_array(inputs[0])
        if 982 <= self.model_number <= 993:
            img = img[40:120, 0:160]

        imu = np.array([inputs[1]])
        imu_in = self.scaler.transform(imu)
        img_in = img.reshape((1,)+img.shape)

        # grab inference
        pred = self.model([img_in, imu_in], training=False)
        
        # checks if single or dual ouput based on return type
        if isinstance(pred, list):
            st_pred = pred[0].numpy()[0][0]
            th_pred = pred[1].numpy()[0][0]
        else:
            st_pred = pred.numpy()[0][0]
            th_pred = pred.numpy()[0][1]
        return st_pred, th_pred

    # x'  = (b - a) * ( (x - x_min) / (x_max - x_min) ) + a
    # def norm(self, x, x_min=-.0, x_max=1.0, low=-0.64, high=0.64):
    #     return (high - low) * (x - x_min) / (x_max - x_min) + low

def model_paths(model_history_file, model_number):
    with open(model_history_file) as csv_file:
        csv_reader = csv.DictReader(csv_file)
        # print(f'model_number = {model_number}')
        # print(csv_reader[f'{model_number}'])
        for row in csv_reader:
            if int(row['model_index']) == model_number:
                return {
                    'model_file': row['model_file'], 
                    'scaler_file': row['scaler_file'], 
                    'telemetry_columns': eval(row['telemetry_columns'])  
                    }
