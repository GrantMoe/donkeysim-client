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
        if self.model_type == 'lstm':
            self.sequence_length = conf['sequence_length']
            # using maxlen will take care of 'popping'
            self.img_seq = deque(maxlen=self.sequence_length)
            self.tel_seq = deque(maxlen=self.sequence_length)
        self.image_depth = conf['image_depth']
        self.active = True
        print('autopilot initiated')

    # converts from 0-255 uint to expected 0.0-1.0 float
    def norm_image(self, img):
        img_array = img_to_array(img)
        return img_array / 255

    # load up sequence queues and shape accordingly
    def process_lstm(self, img, tel):

        # if the queues are empty, fill them with first image
        while len(self.img_seq) < self.sequence_length:
            self.img_seq.append(img)
        while len(self.tel_seq) < self.sequence_length:
            self.tel_seq.append(tel)
        
         # add newest input
        self.img_seq.append(img)
        self.tel_seq.append(tel)
        
        # shape as expected by model
        img_array = np.array(self.img_seq).reshape(-2, 3, 120, 160, 1)
        tel_array = np.array(self.tel_seq).reshape(-1, 3, 5, 1)
        
        return img_array, tel_array

    def infer(self, inputs):
        
        if self.model_type == 'lstm':
            img = self.norm_image(inputs[0])
            imu = self.scaler.transform(np.array([inputs[1]]))
            img_in, imu_in = self.process_lstm(img, imu)
        else: # self.model_ty[e == 'vimu':
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
