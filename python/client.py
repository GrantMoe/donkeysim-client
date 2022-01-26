# The structure of this program is based on the sdsandbox test client:
# https://github.com/tawnkramer/sdsandbox/blob/master/src/test_client.py 
# by tawnkramer (https://github.com/tawnkramer)

import argparse
import base64
import json
import os
import time
import logging

from config import *

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
        self.record_format = conf['record_format']
        self.car_loaded = False
        self.start_recording = False
        self.image_depth = conf['image_depth']
        self.image_format = conf['image_format']
        self.drive_mode = conf['drive_mode']
        self.extended_telem = conf['extended_telem']
        self.current_lap = 0
        self.lap_start = None
        self.sim_start = time.time()
        self.timer_start = time.time()
        self.driving = True
        self.lap_nodes = set()
        self.all_nodes = None
        self.pilot = None
        self.fresh_data = False
        self.recorder = None
        self.record_laps = conf['record_laps']
        self.refresh_sim = False

        if self.drive_mode in ('auto', 'auto_train'):
            self.driving = False
            self.current_image = None
            self.pilot = Autopilot(conf)
        self.ctr = Controller(ctr_type=conf['controller_type'], 
                                path=conf['controller_path'])
        if self.record_format:
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
            # self.send_config()
            self.car_loaded = True        

        if json_packet['msg_type'] == "collision_with_starting_line":
            # display time + resent progress if it was a full lap
            if len(self.all_nodes - self.lap_nodes) <= 10: # allow for skipped 
                lap_time = json_packet['timeStamp'] - self.lap_start
                print(f"Lap {self.current_lap}: {round(lap_time, 2)}")
                self.lap_nodes.clear()
            else: 
                # display '-' for time if not a complete lap
                print(f"Lap {self.current_lap}: -")
            # iterate lap
            self.lap_start = json_packet['timeStamp']
            self.timer_start = time.time()
            self.current_lap += 1
            # record laps if tracking thing separately
            if self.record_laps:
                self.lap_recorder.record(self.current_lap, json_packet['timeStamp'])

        if json_packet['msg_type'] == "telemetry":

            # check for crash/timeout if auto-training
            if self.lap_start:
                self.lap_elapsed = json_packet['time'] - self.lap_start
                lap_elapsed = time.time() - self.timer_start
                if self.drive_mode == 'auto_train' and lap_elapsed > AUTO_TIMEOUT:
                    print('Auto-training lap timeout')
                    self.reset_car()

            # track lap progress
            if not self.all_nodes:
                self.all_nodes = set(range(json_packet['totalNodes']))
            self.lap_nodes.add(json_packet['activeNode'])

            if self.drive_mode in ('auto', 'auto_train') and self.pilot:
                # don't try to start predicting without input
                if not self.current_image:
                    print('got first image')
                # decode image
                self.current_image = Image.open(
                    BytesIO(base64.b64decode(json_packet['image']))
                    ).getchannel(self.image_depth)

                # add telemetry from json. don't try to add dummy columns that don't exist
                self.current_telem = [json_packet[x] for x in self.pilot.telemetry_columns if not (x.startswith('activeNode_') or (x == 'first_lap'))]
                
                # mark first lap as such
                if 'first_lap' in self.pilot.telemetry_columns:
                    self.current_telem.append(self.current_lap == 1)
                
                # add activeNode dummy columns if necessary
                if 'activeNode_0' in self.pilot.telemetry_columns:
                    node_dummies = [0] * 250
                    node_dummies[json_packet['activeNode']] = 1
                    self.current_telem.extend(node_dummies)

            # Start recording when you first start moving
            if self.recorder and json_packet['throttle'] > 0.0:
                self.start_recording = True

            # record image/telemetry
            del json_packet['msg_type']
            if self.start_recording:
                json_packet['lap'] = self.current_lap # for sake o tub experiment
                self.recorder.record(json_packet)

            # indicate there is new data on which to make a prediction
            self.fresh_data = True    


    def send_config(self):
        # Racer
        msg = racer_config()
        self.send(msg)
        time.sleep(0.2)
        # Car
        msg = car_config()
        self.send(msg)
        time.sleep(0.2)
        # Camera
        msg = cam_config()
        self.send(msg)
        time.sleep(0.2)
        print('config sent!')


    def send_controls(self, steering, throttle):
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
        if HAS_TELEM:
            inputs = self.current_image, self.current_telem
        else:
            inputs = [self.current_image]
        steering, throttle = self.pilot.infer(inputs)
        return steering, throttle


    def manual_update(self, st_scale=1.0, th_scale=1.0):
        # get normed inputs from controller
        st = self.ctr.norm(ax='left_stick_horz', low=-1.0, high=1.0)
        # e-brake
        if self.ctr.button('a_button'):
            fw = 0.0
            rv = -1.0
        else:
            fw = self.ctr.norm(ax='right_trigger', low=0.0, high=1.0)
            rv = self.ctr.norm(ax='left_trigger', low=0.0, high=-1.0)
        if abs(st) < 0.05:
            st = 0.0
        return st*st_scale, (fw + rv)*th_scale

    def update(self):
        steering = 0.0
        throttle = 0.0
        self.ctr.update()
        if not self.driving:
            if self.ctr.button('start_button'):
                print('Driving started')
                self.driving = True
            elif self.drive_mode == 'auto_train':
                self.driving = time.time() - self.sim_start > START_DELAY
                if self.driving:
                    print('auto-training started')
        else:
            if self.ctr.button('select_button'):
                print('Driving stopped')
                self.driving = False
        if self.ctr.button('y_button'):
            self.reset_car()
        if self.drive_mode in ('auto', 'auto_train'):
            if not self.current_image:
                print("Waiting for first image")
                return 
            if self.driving and self.fresh_data:
                steering, throttle = self.auto_update()
                self.fresh_data = False
        elif self.drive_mode in ('manual', 'telem_test'):
            steering, throttle = self.manual_update()
        self.send_controls(steering, throttle)

        
    def reset_car(self):
        self.refresh_sim = True
        self.stop()
        # msg = '{ "msg_type" : "reset_car" }'
        # self.send(msg)
        #this sleep lets the SDClient thread poll our message and send it out.
        # time.sleep(self.poll_socket_sleep_sec)

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
        time.sleep(0.5)
        loaded = client.car_loaded           

    # doesn't work when this isn't here
    # Configure Car
    client.send_config()

    print('ready to drive')
    
    # Drive car
    run_sim = True
    refresh_sim = False
    while run_sim:
        try:
            client.update()
            if client.aborted:
                print("Client aborted, stopping driving.")
                if conf['drive_mode'] == 'auto_train':
                    refresh_sim = True
                run_sim = False
            if client.refresh_sim:
                print("Refreshing sim")
                refresh_sim = True
                run_sim = False
        except KeyboardInterrupt:
            run_sim = False
        time.sleep(0.1)

    # Exit Scene ## DON'T DO THIS IF YOU'RE ON THE SERVER
    if conf['host'] == "127.0.0.1":
        msg = '{ "msg_type" : "exit_scene" }'
        client.send(msg)
        time.sleep(0.2)

    # Close down client
    print("waiting for msg loop to stop")
    client.stop()
    # time.sleep(2)
    return refresh_sim


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="donkeysim_client")
    parser.add_argument("--host", 
                        type=str, 
                        default=DEFAULT_HOST, 
                        help="host to use for tcp",)
    parser.add_argument("--port", 
                        type=int, 
                        default=9091, 
                        help="port to use for tcp",)
    parser.add_argument("--track", 
                        type=str, 
                        default=DEFAULT_TRACK,
                        help="name of donkey sim environment", 
                        choices=TRACKS,)
    parser.add_argument("--record_format", 
                        type=str, 
                        default=DEFAULT_RECORD_FORMAT,
                        help="recording format", 
                        choices=RECORD_FORMATS) 
    parser.add_argument("--image_format", 
                        type=str, 
                        default=DEFAULT_IMAGE_FORMAT, 
                        help="image format", 
                        choices=IMAGE_FORMATS) 
    parser.add_argument("--image_channels", 
                        type=int, 
                        default=DEFAULT_IMAGE_DEPTH,
                        help="1 for greyscale, 3 for RGB", 
                        choices=IMAGE_DEPTHS,) 
    parser.add_argument("--drive_mode", 
                        type=str, 
                        default=DEFAULT_DRIVE_MODE, 
                        help="manual control or autopilot", 
                        choices=DRIVE_MODES,) 
    # parser.add_argument("--model_path", 
    #                     type=str, 
    #                     default=model_path,
    #                     help="path to model for inferencing",) 
    parser.add_argument("--model_number",
                        type=int,
                        default=None,
                        help='model_history index for model and scaler paths')
    args = parser.parse_args()
    conf = {
        "host": args.host,
        "port": args.port,
        "record_format": args.record_format,
        "image_format": args.image_format,
        "image_depth": args.image_channels,
        "drive_mode": args.drive_mode,
        "track": args.track,
        "controller_type": CONTROLLER_TYPE,
        "controller_path": CONTROLLER_PATH,
        "record_laps": RECORD_LAPS,
        "extended_telem": EXTENDED_TELEM,
        "model_number": args.model_number,
        "model_history": MODEL_HISTORY_PATH,
        # "auto_training": AUTO_TRAINING
    }
    while True: 
        refresh = run_client(conf)
        if not refresh:
            break
    print("client stopped")

