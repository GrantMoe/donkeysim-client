model_history = '/home/grant/projects/vrl/models/model_history.csv'
model_directory = '/home/grant/projects/vrl/models'
scaler_directory = '/home/grant/projects/vrl/scalers'

record_format = 'CSV' # None, 'CSV', 'tub' (Donkey Car), 'ASL' (openvslam)
image_format = 'PNG' # 'JPG', 'PNG', 'TGA'
image_depth = 1 # 1:'grayscale', 3:'rgb'
# telem_type = 'donkey_extended' # 'donkey_basic', 'donkey_extended', 'gym'
trial_laps = 10
auto_timeout = 35

# y = a*X^3 + (1-a)*X
expo_a = 0.8

racer_conf = {
    'msg_type' : 'racer_info',
    'racer_name' : 'Grant',
    'car_name' : 'Grant',
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
    'body_style': 'donkey', # donkey, bare, car01, cybertruck, f1
    'body_r': 234, # orange=255, pink=234
    'body_g' : 21, # orange=72, pink=21 
    'body_b' : 144, # orange=0, pink=144 
    'car_name' : 'Grant', #'A 1985 Toyota Camry', ' ∅ ', # 
    # 'car_name' : '', #'A 1985 Toyota Camry', ' ∅ ', # 
    'font_size' : 32,
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
    'img_w' : 160, # 1280, # 64, 
    'img_h' : 120, # 720, # 64, 
    'img_d' : 1, 
    'img_enc' : 'PNG', 
    'offset_x' : 0.0, 
    'offset_y' : 0.0, 
    'offset_z' : 0.0, 
    'rot_x' : 0.0 
}

# telemetry columns
# msg_type removed, lap added by me

TELEMETRY_COLUMNS = {
    'donkey_basic': [
        'steering_angle', 'throttle', 'speed', 'image', 'hit',
        'time', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 
        'gyro_y', 'gyro_z', 'pitch', 'yaw', 'roll',
        'activeNode', 'totalNodes', 'lap'
        ],
    'donkey_extended': [
        'steering_angle', 'throttle', 'speed', 'image', 'hit', 
        'time', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 
        'gyro_y', 'gyro_z', 'pitch', 'yaw', 'roll', 
        'cte', 'activeNode', 'totalNodes', 'pos_x', 'pos_y', 
        'pos_z', 'vel_x', 'vel_y', 'vel_z', 'lap'
        ],
    'donkey_extended_brake': [
        'steering_angle', 'throttle', 'speed', 'image', 'hit', 
        'time', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 
        'gyro_y', 'gyro_z', 'pitch', 'yaw', 'roll', 
        'cte', 'activeNode', 'totalNodes', 'pos_x', 'pos_y', 
        'pos_z', 'vel_x', 'vel_y', 'vel_z', 'brake', 'lap'
        ],
    'gym': [
        'pos', 'cte', 'speed', 'hit', 'gyro', 'accel', 'vel', 'lidar', 
        'car', 'last_lap_time', 'lap_count', 'timestep', 'time'
        ]
}

