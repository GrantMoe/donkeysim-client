# Used as controller for donkey client. Takes image and makes predictions
# of steering and throttle with its model.
import csv
# import numpy as n

from numpy import array, asfarray
from pickle import load
from tensorflow.keras.models import load_model


from config import model_directory, model_history, scaler_directory

class Autopilot:

    def __init__(self, conf):
        data = model_paths(model_history, conf['model_number'])
        self.model = load_model(f"{model_directory}/{data['model_file']}", compile=False)
        if data['scaler_file']:
            self.scaler = load(open(f"{scaler_directory}/{data['scaler_file']}", 'rb'))
            print(f"{data['scaler_file'] = }")
        else:
            self.scaler = None
        self.telemetry_columns = data['telemetry_columns']


    def infer(self, inputs):
        # return 0.0, 1.0, 0.0
        img = asfarray(inputs[0])
        imu = array([inputs[1]])
        if self.scaler:
            imu_in = self.scaler.transform(imu)
        else:
            imu_in = imu
        img_in = img.reshape((1,)+img.shape)

        # grab inference
        pred = self.model([img_in, imu_in], training=False)
        
        if len(pred) == 1:
            st_pred = pred.numpy()[0][0]
            th_pred = 1.0
            br_pred = 0.0
#        checks if single or dual ouput based on return type
        elif isinstance(pred, list): # double output
            st_pred = pred[0].numpy()[0][0]
            th_pred = pred[1].numpy()[0][0]
            br_pred = 0.0
        else:
            st_pred = pred.numpy()[0][0]
            th_pred = pred.numpy()[0][1]
            if pred.shape[-1] == 3:
                br_pred = pred.numpy()[0][2]
            else:
                br_pred = 0.0
        return st_pred, th_pred, br_pred


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
