# Used as controller for donkey client. Takes image and makes predictions
# of steering and throttle with its model.
import csv
# import numpy as n

from numpy import array, asfarray
from pickle import load
from tensorflow.keras.models import load_model


from conf import model_directory, model_history, scaler_directory

class Autopilot:

    def __init__(self, conf):
        data = model_paths(model_history, conf['model_number'])
        self.model = load_model(f"{model_directory}/{data['model_file']}", compile=False)
        self.scaler = load(open(f"{scaler_directory}/{data['scaler_file']}", 'rb'))
        self.telemetry_columns = data['telemetry_columns']


    def infer(self, inputs):
        img = asfarray(inputs[0])
        imu = array([inputs[1]])
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


def model_paths(model_history_file, model_number):
    with open(model_history_file) as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            if int(row['model_index']) == model_number:
                return {
                    'model_file': row['model_file'], 
                    'scaler_file': row['scaler_file'], 
                    'telemetry_columns': eval(row['telemetry_columns'])  
                    }
