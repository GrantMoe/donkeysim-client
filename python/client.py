# The structure of this program is based on the sdsandbox test client:
# https://github.com/tawnkramer/sdsandbox/blob/master/src/test_client.py 
# by tawnkramer (https://github.com/tawnkramer)

import argparse
import base64
import json
import os
import time
import logging

import config

from io import BytesIO
from re import T
from PIL import Image

from gym_donkeycar.core.sim_client import SDClient

from autopilot import Autopilot
from controller import Controller
from sim_recorder import SimRecorder, LapRecorder

class SimpleClient(SDClient):

    def __init__(self, address, conf=None, poll_socket_sleep_time=0.01):
        super().__init__(*address, poll_socket_sleep_time=poll_socket_sleep_time)
        self.data_format = conf['data_format']
        self.car_loaded = False
        self.start_recording = False
        self.image_depth = conf['image_depth']
        self.image_format = conf['image_format']
        self.drive_mode = conf['drive_mode']
        self.extended_telem = conf['extended_telem']
        self.current_lap = 0
        self.lap_start = None
        self.update_delay = 1.0
        self.last_update = time.time()
        self.cte = 0 
        self.st_ctl = 0
        self.th_ctl = 0

        self.frames_this_second = 0
        self.frame_count = 0

        self.fps_index = 0
        self.fps_list = [0,0,0,0,0,0,0,0,0,0]

        self.driving = False
        self.current_node = 0

        self.lap_nodes = set()
        self.all_nodes = None
        # self.x = 0
        # self.y = 0
        # self.z = 0
        # self.node = 0

        self.fresh_data = False
        self.recorder = None
        self.record_laps = conf['record_laps']

        if self.drive_mode == 'auto':
            self.current_image = None
            self.pilot = Autopilot(conf)
        # elif self.drive_mode in ('manual', 'telem_test'):
        # no longer either-or
        self.ctr = Controller(ctr_type=conf['controller_type'], 
                                path=conf['controller_path'])
            # if self.drive_mode == 'telem_test':
            #     self.update_delay = 1.0
            #     self.prev_node = None
            #     self.last_update = time.time()

        if self.data_format:
            self.recorder = SimRecorder(self)
        if self.record_laps:
            self.lap_recorder = LapRecorder(conf)


    def on_msg_recv(self, json_packet):

        # telemetry will flood the output, starting line is redundant with below checks
        if json_packet['msg_type'] not in ["telemetry", "collision_with_starting_line"]:
            print("got:", json_packet)

        if json_packet['msg_type'] == "need_car_config":
            self.send_config()

        if json_packet['msg_type'] == "car_loaded":
            self.send_config()
            self.car_loaded = True        

        if json_packet['msg_type'] == "collision_with_starting_line":
            # display time + resent progress if it was a full lap
            if len(self.all_nodes - self.lap_nodes) <= 10: # allow for skipped 
                lap_time = json_packet['timeStamp'] - self.lap_start
                print(f"Lap: {self.current_lap}: {round(lap_time, 2)}")
                self.lap_nodes.clear()
            else: 
                # display '-' for time if not a complete lap
                print(f"Lap: {self.current_lap}: -")
            # iterate lap
            self.lap_start = json_packet['timeStamp']
            self.current_lap += 1
            # record laps if tracking thing separately
            if self.record_laps:
                self.lap_recorder.record(self.current_lap, json_packet['timeStamp'])

        if json_packet['msg_type'] == "telemetry":

            # track lap progress
            if not self.all_nodes:
                self.all_nodes = set(range(json_packet['totalNodes']))
            self.lap_nodes.add(json_packet['activeNode'])

            if self.drive_mode == "auto":
                # don't try to start predicting without an image
                if not self.current_image:
                    print('got first image')
                # decode image
                self.current_image = Image.open(
                    BytesIO(base64.b64decode(json_packet['image']))
                    ).getchannel(self.image_depth)
                # handle telemetry
                json_packet['first_lap'] = (self.current_lap == 1) * 1
                # add telemetry from json
                self.current_telem = [json_packet[x] for x in self.pilot.telemetry_columns if not x.startswith('activeNode_')]
                # add activeNode dummy columns if necessary
                if 'activeNode_0' in self.pilot.telemetry_columns:
                    node_dummies = [0] * 250
                    node_dummies[json_packet['activeNode']] = 1
                    self.current_telem.extend(node_dummies)

            # Don't record if you haven't started yet.
            if self.recorder and json_packet['throttle'] > 0.0:
                self.start_recording = True

            # record image/telemetry
            del json_packet['msg_type']
            if self.start_recording:
                json_packet['lap'] = self.current_lap
                self.recorder.record(json_packet)

            self.fresh_data = True    

    def send_config(self):
        # Racer
        msg = config.racer_config()
        self.send(msg)
        time.sleep(0.2)
        # Car
        msg = config.car_config()
        self.send(msg)
        time.sleep(0.2)
        # Camera
        msg = config.cam_config()
        self.send(msg)
        time.sleep(0.2)
        print('config sent!')


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
        if config.HAS_TELEM:
            inputs = self.current_image, self.current_telem
        else:
            inputs = [self.current_image]
        steering, throttle = self.pilot.infer(inputs)
        return steering, throttle


    def manual_update(self, st_scale=1.0, th_scale=1.0):
        # get normed inputs from controller
        # self.ctr.update()
        st = self.ctr.norm(ax='left_stick_horz', low=-1.0, high=1.0)
        # "e brake"
        if self.ctr.button('a_button'):
            fw = 0.0
            rv = -1.0
        else:
            fw = self.ctr.norm(ax='right_trigger', low=0.0, high=1.0)
            rv = self.ctr.norm(ax='left_trigger', low=0.0, high=-1.0)
        if abs(st) < 0.07:
            st = 0.0
        return st*st_scale, (fw + rv)*th_scale

    def update(self):
        self.ctr.update()
        # print(self.driving)
        if not self.driving:
            if self.ctr.button('start_button'):
                print('Driving started')
                self.driving = True
        else:
            if self.ctr.button('select_button'):
                print('Driving stopped')
                self.driving = False
        
        if self.ctr.button('y_button'):
            self.reset_car()
            # self.driving = False

        if self.drive_mode == 'auto':
            if not self.current_image:
                print("Waiting for first image")
                return 
            if self.fresh_data:
                steering, throttle = self.auto_update()
                self.fresh_data = False
        elif self.drive_mode in ('manual', 'telem_test'):
            steering, throttle = self.manual_update()
        self.st_ctl = steering
        self.th_ctl = throttle

        if self.driving:
            self.send_controls(steering, throttle)

        # current_time = time.time()
        # if current_time - self.last_update >= self.update_delay:
        #     os.system('clear')
        #     print('===========================')
        #     print(f'str: {steering:.3f}')
        #     print(f'thr: {throttle:.3f}')
        #     print(f'lap: {self.current_lap}')
        #     print('===========================')
        #     self.last_update = current_time
        # if self.fresh_data:
        # self.send_controls(steering, throttle)
        
    def reset_car(self):
        msg = '{ "msg_type" : "reset_car" }'
        self.send(msg)
        #this sleep lets the SDClient thread poll our message and send it out.
        time.sleep(self.poll_socket_sleep_sec)

    def stop(self):
        print(f'Client stopping after {self.current_lap-1} laps.')
        super().stop()


# Create client and connect it with the simulator
def run_client(conf):
    # logging.basicConfig(level=logging.DEBUG)

    host = conf["host"] # "trainmydonkey.com" for virtual racing
    port = conf["port"]
    client = SimpleClient(address=(host, port), conf=conf,)

    # Load Track
    msg = f'{{"msg_type" : "load_scene", "scene_name" : "{conf["track"]}"}}'
    client.send(msg)
    loaded = False
    while(not loaded):
        time.sleep(1.0)
        loaded = client.car_loaded           
    # time.sleep(1)

    # doesn't work when this isn't here
    # Configure Car
    client.send_config()

    # Drive car
    run_sim = True
    while run_sim:
        try:
            client.update()
            # if client.driving:
                # client.send_controls(client.st_ctl, client.th_ctl)
            if client.aborted:
                print("Client aborted, stopping driving.")
                run_sim = False
        except KeyboardInterrupt:
            run_sim = False
        time.sleep(0.1)
    
    # time.sleep(1.0)

    # Exit Scene ## DON'T DO THIS IF YOU'RE ON THE SERVER
    if conf['host'] == "127.0.0.1":
        msg = '{ "msg_type" : "exit_scene" }'
        client.send(msg)
        time.sleep(1.0)
    # Close down client
    print("waiting for msg loop to stop")
    client.stop()
    print("client stopped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="donkeysim_client")
    parser.add_argument("--host", 
                        type=str, 
                        default=config.DEFAULT_HOST, 
                        help="host to use for tcp",)
    parser.add_argument("--port", 
                        type=int, 
                        default=9091, 
                        help="port to use for tcp",)
    parser.add_argument("--track", 
                        type=str, 
                        default=config.DEFAULT_TRACK,
                        help="name of donkey sim environment", 
                        choices=config.tracks,)
    parser.add_argument("--data_format", 
                        type=str, 
                        default=config.DEFAULT_DATA_FORMAT,
                        help="recording format", 
                        choices=config.data_formats) 
    parser.add_argument("--image_format", 
                        type=str, 
                        default=config.DEFAULT_IMAGE_FORMAT, 
                        help="image format", 
                        choices=config.image_formats[0]) 
    parser.add_argument("--image_channels", 
                        type=int, 
                        default=config.DEFAULT_IMAGE_DEPTH,
                        help="1 for greyscale, 3 for RGB", 
                        choices=config.image_depths,) 
    parser.add_argument("--drive_mode", 
                        type=str, 
                        default=config.DEFAULT_DRIVE_MODE, 
                        help="manual control or autopilot", 
                        choices=config.drive_modes,) 
    # parser.add_argument("--model_path", 
    #                     type=str, 
    #                     default=config.model_path,
    #                     help="path to model for inferencing",) 
    parser.add_argument("--model_number",
                        type=int,
                        default=None,
                        help='model_history index for model and scaler paths')
    args = parser.parse_args()
    conf = {
        "host": args.host,
        "port": args.port,
        "data_format": args.data_format,
        "start_delay": 1,
        "image_format": args.image_format,
        "image_depth": args.image_channels,
        "drive_mode": args.drive_mode,
        # "model_path": args.model_path,
        "track": args.track,
        "controller_type": config.ctr_type,
        "controller_path": config.ctr_path,
        # "scaler_path": config.scaler_path,
        "record_laps": config.RECORD_LAPS,
        "extended_telem": config.EXTENDED_TELEM,
        "model_number": args.model_number,
        "model_history": config.model_history_path,
    }
    run_client(conf)
