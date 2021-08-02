import os
import json
import time
from io import BytesIO
import base64

from PIL import Image
import numpy as np
from gym_donkeycar.core.sim_client import SDClient

from controller import Controller

###########################################

class SimpleClient(SDClient):

    def __init__(self, address, poll_socket_sleep_time=0.01):
        super().__init__(*address, poll_socket_sleep_time=poll_socket_sleep_time)
        # self.last_image = None
        self.car_loaded = False
        self.ctr = Controller()
        self.dir = f'{os.getcwd()}/../data/{time.strftime("%m_%d_%Y/%H_%M_%S")}'
        self.data_dir = f'{self.dir}/data'
        self.img_dir = f'{self.dir}/images'
        os.makedirs(self.data_dir)
        os.makedirs(self.img_dir)
        self.record_count = 0


    def on_msg_recv(self, json_packet):

        if json_packet['msg_type'] == "car_loaded":
            self.car_loaded = True

        if json_packet['msg_type'] == "telemetry":
            del json_packet['msg_type']                   
            if json_packet['speed'] > 0.1:
                imgString = json_packet['image']
                image = Image.open(BytesIO(base64.b64decode(imgString)))
                image.save(f'{self.img_dir}/frame_{self.record_count:04d}.jpg')
                # image.save(f'{self.img_dir}/frame_{self.record_count:04d}.png')

                with open(f'{self.data_dir}/data_{self.record_count:04d}', 'w') as outfile:
                    json.dump(json_packet, outfile)
                    self.record_count += 1 

            # don't have to, but to clean up the print, delete the image string.
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
        self.send_controls(st, fw + rv)



###########################################
## Create client and connect it with the simulator

def drive():
    # test params
    host = "127.0.0.1" # "trainmydonkey.com" for virtual racing server
    port = 9091

    # Start Client
    client = SimpleClient(address=(host, port))
    time.sleep(1)

    # Load Scene message
    #  Choices: 
    #           'generated_road'
    #           'generated_track'
    #           'mountain_track'
    #           'sparkfun_avc'
    #           'warehouse'
    msg = '{ "msg_type" : "load_scene", "scene_name" : "donkey-circuit-launch-track-v0" }'
    client.send(msg)

    # Wait briefly for the scene to load.
    loaded = False
    while(not loaded):
        time.sleep(1.0)
        loaded = client.car_loaded           
        
    # Car config
    # msg = '{ "msg_type" : "car_config", "body_style" : "bare", "body_r" : "255", "body_g" : "255", "body_b" : "255", "car_name" : "Grant", "font_size" : "50" }'
    msg = '{ "msg_type" : "car_config", "body_style" : "f1", "body_r" : "234", "body_g" : "21", "body_b" : "144", "car_name" : "Grant", "font_size" : "50" }'
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
    # msg = '{ "msg_type" : "cam_config", "fov" : "90", "fish_eye_x" : "0.0", "fish_eye_y" : "0.0", "img_w" : "160", "img_h" : "120", "img_d" : "3", "img_enc" : "PNG", "offset_x" : "0.0", "offset_y" : "1.0", "offset_z" : "1.0", "rot_x" : "15.0" }'
    msg = '{ "msg_type" : "cam_config", "fov" : "90", "fish_eye_x" : "0.0", "fish_eye_y" : "0.0", "img_w" : "251", "img_h" : "141", "img_d" : "3", "img_enc" : "PNG", "offset_x" : "0.0", "offset_y" : "4.0", "offset_z" : "1.0", "rot_x" : "0.0" }'
    client.send(msg)
    time.sleep(1)


    # Controller setup
    # events = [EV_ABS.ABS_X, EV_ABS.ABS_RZ, EV_ABS.ABS_Z] 

    # adjust steering dead zone. clunky
    # ctr.dev.absinfo[EV_ABS.ABS_X] = InputAbsInfo(flat=3000)

    # Drive car
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

