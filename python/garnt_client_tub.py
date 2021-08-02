import os
import json
import time
from io import BytesIO
import base64
import math

from PIL import Image
import numpy as np
from gym_donkeycar.core.sim_client import SDClient

from controller import Controller

###########################################

class SimpleClient(SDClient):

    def __init__(self, address, poll_socket_sleep_time=0.01):
        super().__init__(*address, poll_socket_sleep_time=poll_socket_sleep_time)
        self.last_image = None
        self.car_loaded = False
        self.ctr = Controller()

        date_count = 0
        self.data_dir = f'{os.getcwd()}/../data/tub_{date_count}_{time.strftime("%y-%m-%d")}'
        while os.path.isdir(self.data_dir):
            date_count += 1
            self.data_dir = f'{os.getcwd()}/../data/tub_{date_count}_{time.strftime("%y-%m-%d")}'
        os.makedirs(self.data_dir)
        self.start_time = time.time()
        meta_tub = {
            "inputs": [
               "cam/image_array", "user/angle",
               "user/throttle", "user/mode",
            ], 
            "types": [
               "image_array", "float", "float", "str",
            ],
            "start": f'{time.time()}',
            # "start": self.start_time,
            
        }
        with open(f'{self.data_dir}/meta.json', 'w') as outfile:
            json.dump(meta_tub, outfile)
        self.record_count = 0


    def on_msg_recv(self, json_packet):

        if json_packet['msg_type'] == "car_loaded":
            self.car_loaded = True

        if json_packet['msg_type'] == "telemetry":
            # del json_packet['msg_type']
            if json_packet['throttle'] > 0.0:
                record_msec = 1000 * math.floor(time.time() - self.start_time)
                with open(f'{self.data_dir}/record_{self.record_count}.json', 'w') as outfile:
                    imgString = json_packet["image"]
                    imgName = f'{self.record_count}_cam-image-array_.jpg'
                    image = Image.open(BytesIO(base64.b64decode(imgString)))
                    temp_json = {
                        "cam/image_array": imgName,
                        "user/angle": json_packet['steering_angle'],
                        "user/throttle": json_packet['throttle'],
                        "user/mode": "user",
                        "milliseconds": record_msec,
                    }
                    json.dump(temp_json, outfile)
                    image.save(f'{self.data_dir}/{imgName}')
                    self.record_count += 1 

            #don't have to, but to clean up the print, delete the image string.
            del json_packet['image']

        print("got:", json_packet)


    def send_controls(self, steering, throttle):
        p = { "msg_type" : "control",
                "steering" : steering.__str__(),
                "throttle" : throttle.__str__(),
                "brake" : "0.0" }
        msg = json.dumps(p)
        self.send(msg)

        #this sleep lets the SDClient thread poll our message and send it out.
        time.sleep(self.poll_socket_sleep_sec)

    def update(self):
        # get normed inputs
        self.ctr.update()
        st = self.ctr.norm('left_stick_horz', -1.0, 1.0)
        fw = self.ctr.norm('right_trigger', 0.0, 1.0)
        rv = self.ctr.norm('left_trigger', 0.0, -1.0)
        if abs(st) < 0.07:
            st = 0.0
        self.send_controls(st * 0.5, 0.5 * (fw + rv))



###########################################
## Create client and connect it with the simulator

def drive():
    # test params
    host = "127.0.0.1" # "trainmydonkey.com" for virtual racing server
    port = 9091

    # Start Client
    client = SimpleClient(address=(host, port))
    time.sleep(1)
    

#    From gym_test.py
    env_list = [
        "donkey-warehouse-v0",
        "donkey-generated-roads-v0",
        "donkey-avc-sparkfun-v0",
        "donkey-generated-track-v0",
        "donkey-roboracingleague-track-v0",
        "donkey-waveshare-v0",
        "donkey-minimonaco-track-v0",
        "donkey-warren-track-v0",
        "donkey-thunderhill-track-v0",
        "donkey-circuit-launch-track-v0",
    ]
    msg = '{ "msg_type" : "load_scene", "scene_name" : "donkey-circuit-launch-track-v0" }'

    # Load Scene message
    #  Choices: 
    #           'generated_road'
    #           'generated_track'
    #           'mountain_track'
    #           'sparkfun_avc'
    #           'warehouse'
    # msg = '{ "msg_type" : "load_scene", "scene_name" : "mountain_track" }'
    
    
    client.send(msg)

    # Wait briefly for the scene to load.
    loaded = False
    while(not loaded):
        time.sleep(1.0)
        loaded = client.car_loaded           
        
    # Car config
    msg = '{ "msg_type" : "car_config", "body_style" : "bare", "body_r" : "255", "body_g" : "255", "body_b" : "255", "car_name" : "Grant", "font_size" : "50" }'
    # msg = '{ "msg_type" : "car_config", "body_style" : "car01", "body_r" : "234", "body_g" : "21", "body_b" : "144", "car_name" : "Grant", "font_size" : "50" }'
    client.send(msg)
    time.sleep(1)

    # Camera config
    # set any field to Zero to get the default camera setting.
    # this will position the camera right above the car, with max fisheye and wide fov
    # this also changes the img output to 255x255x1 ( actually 255x255x3 just all three channels have same value)
    # the offset_x moves camera left/right
    # the offset_y moves camera up/down
    # the offset_z moves camera forward/back
    # with fish_eye_x/y == 0.0 then you get no distortion
    # img_enc can be one of JPG|PNG|TGA
    # msg = '{ "msg_type" : "cam_config", "fov" : "170", "fish_eye_x" : "1.0", "fish_eye_y" : "1.0", "img_w" : "255", "img_h" : "255", "img_d" : "3", "img_enc" : "JPG", "offset_x" : "0.0", "offset_y" : "3.0", "offset_z" : "0.0", "rot_x" : "90.0" }'
    msg = '{ "msg_type" : "cam_config", "fov" : "90", "fish_eye_x" : "0.0", "fish_eye_y" : "0.0", "img_w" : "160", "img_h" : "120", "img_d" : "3", "img_enc" : "JPG", "offset_x" : "0.0", "offset_y" : "1.0", "offset_z" : "1.0", "rot_x" : "0.0" }'
    # msg = '{ "msg_type" : "cam_config", "fov" : "90", "fish_eye_x" : "0.0", "fish_eye_y" : "0.0", "img_w" : "251", "img_h" : "141", "img_d" : "3", "img_enc" : "PNG", "offset_x" : "0.0", "offset_y" : "4.0", "offset_z" : "1.0", "rot_x" : "0.0" }'
    client.send(msg)
    time.sleep(1)


    # Controller setup
    # events = [EV_ABS.ABS_X, EV_ABS.ABS_RZ, EV_ABS.ABS_Z] 

    # adjust steering dead zone. clunky
    # ctr.dev.absinfo[EV_ABS.ABS_X] = InputAbsInfo(flat=3000)

    # Send random driving controls
    do_drive = True
    while do_drive:
        try:
            client.update()
            if client.aborted:
                print("Client socket problem, stopping driving.")
                do_drive = False
        except KeyboardInterrupt:
            do_drive = False


    time.sleep(1.0)

    # Exit Scene
    msg = '{ "msg_type" : "exit_scene" }'
    client.send(msg)

    time.sleep(1.0)

    # Close down clients
    print("waiting for msg loop to stop")
    client.stop()

    print("client stopped")



if __name__ == "__main__":
    drive()

