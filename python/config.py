## File for holding configuration for donkey sim client
CONTROLLER_TYPE = 'xbox' 
CONTROLLER_PATH = '/dev/input/by-id/usb-Microsoft_Controller_3039363431313739383635393433-event-joystick'
MODEL_HISTORY_PATH = '/home/grant/projects/vrl/models/model_history.csv'
MODEL_DIRECTORY = '/home/grant/projects/vrl/models'
# scaler_directory = '/home/grant/projects/vrl/data/scalers' # before model 117
SCALER_DIRECTORY = '/home/grant/projects/vrl/scalers' 

AUTO_TIMEOUT = 25
# AUTO_TRAINING = False
START_DELAY = 3

RECORD_LAPS = False
HAS_TELEM = True
EXTENDED_TELEM = True

DEFAULT_TRACK = 'mountain_track'
DEFAULT_RECORD_FORMAT = 'CSV' # None, 'ASL', 'CSV', 'tub'
DEFAULT_IMAGE_FORMAT = 'PNG' # 'JPG', 'PNG', 'TGA'
<<<<<<< HEAD
DEFAULT_IMAGE_DEPTH = 1 # 1, 3
DEFAULT_DRIVE_MODE =  'auto_train' # 'auto', 'manual' 
DEFAULT_HOST = "127.0.0.1" #
=======
DEFAULT_IMAGE_DEPTH = 1 # 1: greyscale, 3: rgb
DEFAULT_DRIVE_MODE =  'manual' # 'auto', 'manual' 
DEFAULT_HOST = "127.0.0.1" # localhost 
>>>>>>> 17051b180094763bdcbdeb8ed99d4afda07fb3c6
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

# This is silly, and should probably be somewhere else
def msg_builder(config_dict):
    msg_string = "{"
    for key, value in config_dict.items():
        msg_string += f'"{key}" : "{value}", '
    msg_string += "}"
    return msg_string

<<<<<<< HEAD
# 0 is default
TRACKS = [
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
=======
tracks = ['generated_road', 'warehouse', 'sparkfun_avc', 'generated_track', 
    'roboracingleague_1', 'waveshare', 'mini_monaco', 'warren', 
    'circuit_launch', 'mountain_track']
>>>>>>> 17051b180094763bdcbdeb8ed99d4afda07fb3c6

RECORD_FORMATS = [
    None,
    'CSV',
    'tub', # Donkey Car
    'ASL', # openvslam
]

<<<<<<< HEAD
IMAGE_FORMATS = [
    'PNG', # default
    'JPG',
    'TGA'
]

IMAGE_DEPTHS = [
    1, #default
    3, # RGB'
]

DRIVE_MODES = [
    'manual', # default
    'auto',
    'auto_train',
    'telem_test',
]

# telemetry columns
# msg_type removed, lap added by me

EXTENDED_TELEMETRY_COLUMNS = [
=======
image_formats = ['JPG', 'PNG', 'TGA' ]
# 1 = BW, 3 = RGB
image_depths = [1, 3]

drive_modes = [ 'auto', 'manual', 'telem_test']

# telemetry columns
# msg_type removed, lap added by me
extended_cols = [
>>>>>>> 17051b180094763bdcbdeb8ed99d4afda07fb3c6
        'steering_angle', 'throttle', 'speed', 'image', 'hit', 
        'time', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 
        'gyro_y', 'gyro_z', 'gyro_w', 'pitch', 'yaw', 'roll', 
        'cte', 'activeNode', 'totalNodes', 'pos_x', 'pos_y', 
        'pos_z', 'vel_x', 'vel_y', 'vel_z', 'lap'
        ]

STANDARD_TELEMETRY_COLUMNS = [
        'steering_angle', 'throttle', 'speed', 'image', 'hit',
        'time', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 
        'gyro_y', 'gyro_z', 'gyro_w', 'pitch', 'yaw', 'roll',
        'activeNode', 'totalNodes', 'lap'
        ]