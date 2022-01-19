## File for holding configuration for donkey sim client
ctr_type = 'xbox' 
ctr_path = '/dev/input/by-id/usb-Microsoft_Controller_3039363431313739383635393433-event-joystick'
model_history_path = '/home/grant/projects/vrl/models/model_history.csv'
model_directory = '/home/grant/projects/vrl/models'
scaler_directory = '/home/grant/projects/vrl/data/scalers'

# model_number = 28
# model_path = f'/home/grant/projects/vrl/models/model_{model_number}.h5'
# model_directory = '/home/grant/projects/vrl/models'
# scaler_directory = '/home/grant/projects/vrl/data/scalers'


# 0-3:      ss_scaler_01_14_20_10
# 4-7:      ss_scaler_01_14_23_31
# 8:        ss_scaler_01_15_00_38
# 9-12:     ss_scaler_01_15_01_46
# 13-15:    ss_scaler_01_15_18_19
# 16:       ss_scaler_01_15_19_58
# 17-20:    ss_scaler_01_16_00_26
# 21-23     ss_scaler_01_16_01_28
# 24-27:    ss_scaler_01_17_16_00
# 28-31:    ss_scaler_01_17_16_56
# 32-34:    ss_scaler_01_17_17_39

# scaler_name = 'ss_scaler_01_17_16_56'
# scaler_path = f'/home/grant/projects/vrl/data/scalers/{scaler_name}.pkl'


RECORD_LAPS = False
HAS_TELEM = True
EXTENDED_TELEM = False

DEFAULT_TRACK = 'mountain_track'
DEFAULT_DATA_FORMAT = None #'CSV'
DEFAULT_IMAGE_FORMAT = 'png'
DEFAULT_IMAGE_DEPTH = 1
DEFAULT_DRIVE_MODE = 'auto' # 'manual'
DEFAULT_HOST = "127.0.0.1" #
# DEFAULT_HOST = "donkey-sim.roboticist.dev" # twitch server

racer_conf = {
    'msg_type' : 'racer_info',
    'racer_name' : 'Grant',
    # 'car_name' : 'Grant',
    'bio' : '¯\_(ツ)_/¯',
    'country' : 'California',
    'guid' : "8675309"
}

# Car config
# body_style = "donkey" | "bare" | "car01" | "cybertruck" | "f1"  choice of string
# body_rgb  = (128, 128, 128) tuple of ints
# car_name = "string less than 64 char"
car_conf = {
    'msg_type': 'car_config',
    'body_style': 'car01', # donkey, bare, car01, cybertruck, f1
    'body_r': 234, # orange=255, pink=234
    'body_g' : 21, # orange=72, pink=21 
    'body_b' : 144, # orange=0, pink=144 
    'car_name' : '', #'Grant', #'A 1985 Toyota Camry', ' ∅ ', # 
    'font_size' : 50,
}

# Camera config
# set any field to Zero to get the default camera setting.
# this will position the camera right above the car, with max fisheye and wide fov
# this also changes the img output to 255x255x1 ( actually 255x255x3 just all three channels have same value)
# the offset_x moves camera left/right
# the offset_y moves camera up/down
# the offset_z moves camera forward/back
# with fish_eye_x/y == 0.0 then you get no distortion
# img_enc can be one of JPG|PNG|TGA        
cam_conf = {
    'msg_type' : 'cam_config', 
    'fov' : 0, 
    'fish_eye_x' : 0.0, 
    'fish_eye_y' : 0.0, 
    # 'img_w' : 64, 
    # 'img_h' : 64, 
    'img_d' : 3, 
    'img_enc' : 'PNG', 
    'offset_x' : 0.0, 
    'offset_y' : 0.0, 
    'offset_z' : 0.0, 
    'rot_x' : 0.0 
}

def cam_config():
    return msg_builder(cam_conf)

def car_config():
    return msg_builder(car_conf)

def racer_config():
    return msg_builder(racer_conf)


# This is silly
def msg_builder(config_dict):
    msg_string = "{"
    for key, value in config_dict.items():
        msg_string += f'"{key}" : "{value}", '
    msg_string += "}"
    return msg_string


# telem_data = [
    # 'speed',
    # 'pitch', 
    # 'yaw',
    # 'roll',
    # 'activeNode',
    # 'pos_x',
    # 'pos_z',
    # 'accel_x',
    # 'accel_y',
    # 'accel_z',
    # 'gyro_x',
    # 'gyro_y',
    # 'gyro_z',
    # 'gyro_w',
    # 'vel_x',
    # 'vel_y',
    # 'vel_z',
# ]

# 0 is default
tracks = [
    'generated_road', 
    'warehouse', 
    'sparkfun_avc', 
    'generated_track', 
    'roboracingleague_1', 
    'waveshare', 
    'mini_monaco', 
    'warren', 
    'circuit_launch',
    'mountain_track'
    ]

data_formats = [
    None,
    'None', # default
    'CSV', # capstone
    'tub', # Donkey Car
    'ASL', # Slam
]

image_formats = [
    'PNG', # default
    'JPG',
    'TGA'
]

image_depths = [
    1, #default
    3, # RGB'
]

drive_modes = [
    'manual', # default
    'auto',
    'telem_test',
]

# telemetry columns
# msg_type removed, lap added by me

extended_cols = [
        'steering_angle', 'throttle', 'speed', 'image', 'hit', 
        'time', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 
        'gyro_y', 'gyro_z', 'gyro_w', 'pitch', 'yaw', 'roll', 
        'cte', 'activeNode', 'totalNodes', 'pos_x', 'pos_y', 
        'pos_z', 'vel_x', 'vel_y', 'vel_z', 'lap'
        ]

standard_cols = [
        'steering_angle', 'throttle', 'speed', 'image', 'hit',
        'time', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 
        'gyro_y', 'gyro_z', 'gyro_w', 'pitch', 'yaw', 'roll',
        'activeNode', 'totalNodes', 'lap'
        ]