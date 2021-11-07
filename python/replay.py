# This acts a controller feeding back in input data recorded from the
# donkey simulator, manual or auto
import pandas as pd

class Replay:

    def __init__(self, csv_path):
        self.input_df = pd.read_csv(csv_path, usecols=['steering_angle', 'throttle', 'time'])
        self.index = 0

    def next_record(self, current_time):
        while current_time < self.input_df.loc[self.index, 'time']:
            self.index -= 1
        self.index += 1
        return self.input_df.loc[self.index, ['steering_angle', 'throttle']] 



