# The structure of this program is based on the sdsandbox test client:
# https://github.com/tawnkramer/sdsandbox/blob/master/src/test_client.py 
# by tawnkramer (https://github.com/tawnkramer)

import argparse
from re import T
import uuid
import os
import json
import time
from io import BytesIO
import base64
from PIL import Image
from gym_donkeycar.core.sim_client import SDClient
from controller import Controller
from autopilot import Autopilot, LineFollower
import config
from sim_recorder import ASLRecorder, CSVRecorder, TubRecorder

class SimpleClient(SDClient):

    def __init__(self, address, conf=None, poll_socket_sleep_time=0.01):
        super().__init__(*address, poll_socket_sleep_time=poll_socket_sleep_time)
        self.data_format = conf['data_format']
        self.car_loaded = False
        self.start_recording = False
        self.image_depth = conf['image_depth']
        self.image_format = conf['image_format']
        self.drive_mode = conf['drive_mode']
        self.current_lap = 0

        self.update_delay = 1.0
        self.last_update = time.time()
        self.cte = 0 
        self.max_cte = 0
        self.min_cte = 0
        self.st_ctl = 0
        self.th_ctl = 0
        # self.st_angle = 0
        # self.th_data = 0
        self.recorder = None

        if self.drive_mode == 'auto':
            self.current_image = None
            self.ctr = Autopilot(conf['model_path'])
        if self.drive_mode == 'linefollow':
            self.ctr = LineFollower()
            self.cte = 0
        elif self.drive_mode in ('manual', 'telem_test'):
            self.ctr = Controller(ctr_type=conf['controller_type'], 
                                  path=conf['controller_path'])
            if self.drive_mode == 'telem_test':
                self.update_delay = 1.0
                self.prev_node = None
                self.last_update = time.time()
        if self.data_format == 'tub':
            self.recorder = TubRecorder(self.image_format, self.image_depth)
        elif self.data_format == 'CSV':
            self.recorder = CSVRecorder(self.image_format, self.image_depth)
        elif self.data_format == 'ASL':
            self.recorder = ASLRecorder(self.image_format, self.image_depth)
        else:
            self.recorder = None


    def on_msg_recv(self, json_packet):
        if json_packet['msg_type'] != "telemetry":     
            print("got:", json_packet)
        if json_packet['msg_type'] == "car_loaded":
            self.car_loaded = True
        if json_packet['msg_type'] == "collision_with_starting_line":
            self.current_lap += 1
        if json_packet['msg_type'] == "telemetry":
            del json_packet['msg_type']
            # if json_packet['cte'] > self.max_cte:
            #     self.max_cte = json_packet['cte']
            # if json_packet['cte'] < self.min_cte:
            #     self.min_cte = json_packet['cte']
            if self.drive_mode == "auto":
                if not self.current_image:
                    print('got first image')
                self.current_image = Image.open(
                    BytesIO(base64.b64decode(json_packet['image']))
                    ).getchannel(self.image_depth)
                self.current_imu = [json_packet[sensor] for sensor in config.IMU_SENSORS]
            if self.drive_mode == 'linefollow':
                self.cte = json_packet['cte']
            if self.recorder and json_packet['throttle'] > 0.0:
                self.start_recording = True
            if self.start_recording:
                json_packet['lap'] = self.current_lap
                self.recorder.record(json_packet)
            if self.drive_mode == 'telem_test':
                ## report a bunch of stuff I'm curious about
                # json_keys = ['speed',' vel_x', 'vel_y', 'vel_z', 
                #     'accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y',
                #     'gyro_z','gyro_w', 'pitch', 'yaw', 'roll',]
                # json_keys = ['steering_angle', 'cte']
                current_time = time.time()
                json_keys = ['steering_angle', 'throttle']
                if current_time - self.last_update >= self.update_delay:
                    os.system('clear')
                    print('===========================')
                    j = json_packet
                    del j['image']
                    print(f'st_ctl: {self.st_ctl}')
                    print(f'st_ang: {j["steering_angle"]}')
                    ratio = 0
                    if self.st_ctl != 0:
                        ratio = self.st_angle / self.st_ctl
                    print(f'ratio: {ratio}')
                    print('===========================')
                    self.last_update = current_time


    def send_controls(self, steering, throttle):
        # print(f'{steering}, {throttle}')
        p = { "msg_type" : "control",
                "steering" : steering.__str__(),
                "throttle" : throttle.__str__(),
                "brake" : "0.0" }
        msg = json.dumps(p)
        self.send(msg)
        #this sleep lets the SDClient thread poll our message and send it out.
        time.sleep(self.poll_socket_sleep_sec)


    def auto_update(self):
        # get inferences from autopilot
        inputs = self.current_image, self.current_imu
        steering, throttle = self.ctr.infer(inputs)
        # if throttle > 0.5:
            # throttle = 0.5
        return steering, throttle

    def linefollow_update(self):
        steering, throttle = self.ctr.update(self.cte)
        if throttle < 0.1:
            throttle = 0.1
        if throttle > 1.0:
            throttle = 1.0
        current_time = time.time()
        if current_time - self.last_update >= self.update_delay:
            os.system('clear')
            print('===========================')
            print(f'steering: {steering}')
            print(f'throttle: {throttle}')
            print(f'cte: {self.cte}')
            print(f'rat: {self.cte/4.0}')
            print('===========================')
            self.last_update = current_time
        return steering, throttle

    def manual_update(self, st_scale=1.0, th_scale=1.0):
        # get normed inputs from controller
        self.ctr.update()
        # st = self.ctr.norm('left_stick_horz', -1.0, 1.0)
        # anything lower and higher than +-0.64 are treated as +-0.64
        st = self.ctr.norm('left_stick_horz', -0.64, 0.64) 
        fw = self.ctr.norm('right_trigger', 0.0, 1.0)
        rv = self.ctr.norm('left_trigger', 0.0, -1.0)
        if abs(st) < 0.07:
            st = 0.0
        return st*st_scale, (fw + rv)*th_scale

    def update(self):
        if self.drive_mode == 'auto':
            if not self.current_image:
                print("Waiting for first image")
                return 
            steering, throttle = self.auto_update()
        elif self.drive_mode == 'linefollow':
            steering, throttle = self.linefollow_update()
        elif self.drive_mode in ('manual', 'telem_test'):
            steering, throttle = self.manual_update()
        self.st_ctl = steering
        self.th_ctl = throttle
        current_time = time.time()
        if current_time - self.last_update >= self.update_delay:
            os.system('clear')
            print('===========================')
            print(f'str: {steering}')
            print(f'thr: {throttle}')
            print(f'lap: {self.current_lap}')
            print(f'cte: {self.cte}')
            print(f'min: {self.min_cte}')
            print(f'max: {self.max_cte}')
            print('===========================')
            self.last_update = current_time
        self.send_controls(steering, throttle)

    def stop(self):
        print(f'Client stopping after {self.current_lap-1} laps.')
        super().stop()


# Create client and connect it with the simulator
def run_client(conf):
    host = conf["host"] # "trainmydonkey.com" for virtual racing
    port = conf["port"]
    client = SimpleClient(address=(host, port), conf=conf,)

    time.sleep(1)

    # Load Track
    msg = f'{{"msg_type" : "load_scene", "scene_name" : "{conf["track"]}"}}'
    client.send(msg)
    loaded = False
    while(not loaded):
        time.sleep(1.0)
        loaded = client.car_loaded           
    
    # Configure Car
    msg = config.car_config()
    client.send(msg)
    time.sleep(1)
    # Configure Camera
    msg = config.cam_config()
    client.send(msg)
    time.sleep(1)

    # Drive car
    do_drive = True
    while do_drive:
        try:
            client.update()
            if client.aborted:
                print("Client aborted, stopping driving.")
                do_drive = False
        except KeyboardInterrupt:
            do_drive = False
        # time.sleep(0.05)
    time.sleep(1.0)
    # Exit Scene
    msg = '{ "msg_type" : "exit_scene" }'
    client.send(msg)
    time.sleep(1.0)
    # Close down client
    print("waiting for msg loop to stop")
    client.stop()
    print("client stopped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="garnt_client")
    parser.add_argument("--sim",
                        type=str,
                        default="sim_path",
                        help="path to unity simulator",)
    parser.add_argument("--host", 
                        type=str, 
                        default="127.0.0.1", 
                        help="host to use for tcp",)
    parser.add_argument("--port", 
                        type=int, 
                        default=9091, 
                        help="port to use for tcp",)
    parser.add_argument("--track", 
                        type=str, 
                        default=config.tracks[0],
                        help="name of donkey sim environment", 
                        choices=config.tracks,)
    parser.add_argument("--data_format", 
                        type=str, 
                        default=config.data_formats[0],
                        help="recording format", 
                        choices=config.data_formats) 
    parser.add_argument("--image_format", 
                        type=str, 
                        default=config.image_formats[0], 
                        help="image format", 
                        choices=config.image_formats[0]) 
    parser.add_argument("--image_channels", 
                        type=int, 
                        default=config.image_depths[0], 
                        help="1 for greyscale, 3 for RGB", 
                        choices=config.image_depths,) 
    parser.add_argument("--drive_mode", 
                        type=str, 
                        default=config.drive_modes[0], 
                        help="manual control or autopilot", 
                        choices=config.drive_modes,) 
    parser.add_argument("--model_path", 
                        type=str, 
                        help="path to model for inferencing",) 
    args = parser.parse_args()
    conf = {
        "exe_path": args.sim,
        "host": args.host,
        "port": args.port,
        "data_format": args.data_format,
        "body_style": "donkey", # donkey, bare, car01, cybertruck, f1
        "body_rgb": (255, 72, 0), # orange # pink: (234, 21, 144),
        "car_name": "",
        "font_size": 10,
        "racer_name": "Grant",
        "country": "California",
        "bio": "custom client",
        "guid": str(uuid.uuid4()),
        "start_delay": 1,
        "image_format": args.image_format,
        "image_depth": args.image_channels,
        "drive_mode": args.drive_mode,
        "model_path": args.model_path,
        "track": args.track,
        "controller_type": config.ctr_type,
        "controller_path": config.ctr_path,
    }
    run_client(conf)
