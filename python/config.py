## File for holding configuration for donkey sim client

ctr_type = 'xbox' 
ctr_path = '/dev/input/by-id/usb-Microsoft_Controller_3039363431313739383635393433-event-joystick'
scaler_path = '/home/grant/projects/capstone/data/11_12_2021/19_28_18/ss_scaler_11_19_01_16.pkl'
model_path = '/home/grant/projects/capstone/models/11_12_2021/19_28_18/model_178.h5'
RECORD_LAPS = False

racer_conf = {
    'msg_type' : 'racer_info',
    'racer_name' : 'Grant',
    'car_name' : 'Garnt',
    'bio' : 'cargo cultist',
    'country' : 'California',
    'guid' : "GUID"
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
    'car_name' : '', 
    'font_size' : 10,
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
    'img_w' : 64, 
    'img_h' : 64, 
    'img_d' : 1, 
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


HAS_TELEM = True
telem_data = [
    'speed',
    'pitch', 
    'yaw',
    'roll',
    'activeNode',
    'pos_x',
    'pos_z',
    'accel_x',
    'accel_y',
    'accel_z',
    'gyro_x',
    'gyro_y',
    'gyro_z',
    'gyro_w',
    'vel_x',
    'vel_y',
    'vel_z',
]

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

