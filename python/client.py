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
        self.telem_type = conf['telem_type']
        self.current_lap = 0
        self.lap_start = None
        self.lap_sum = 0
        self.later_lap_sum = 0
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
        self.previous_node = 0
        self.current_node = 0
        self.max_node = None
        self.use_brakes = conf['use_brakes']
        self.brake_telem = None

        self.printed_telem = False

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
        if json_packet['msg_type'] not in ["telemetry"]: #, "collision_with_starting_line"]:
            print("got:", json_packet)

        if json_packet['msg_type'] == "need_car_config":
            self.send_config()

        if json_packet['msg_type'] == "car_loaded":
            # self.send_config()
            self.car_loaded = True        

        if json_packet['msg_type'] == "collision_with_starting_line":
            print('starting line!')
            # display time + resent progress if it was a full lap
            if len(self.all_nodes - self.lap_nodes) <= 10: # allow for skipped 
                lap_time = json_packet['timeStamp'] - self.lap_start
                self.lap_sum += lap_time
                if self.current_lap > 1:
                    self.later_lap_sum += lap_time 
                if self.drive_mode in ('auto', 'auto_train'):
                    lap_avg = self.lap_sum / self.current_lap 
                    later_lap_avg = 0.0 if self.later_lap_sum == 0 else self.later_lap_sum / (self.current_lap - 1)
                    print(f"Lap {self.current_lap}: {lap_time:.2f} | avg : {lap_avg:.3f} / {later_lap_avg:.3f}")
                else:
                    print(f"Lap {self.current_lap}: {lap_time:.2f}")
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

            # track lap progress
            if not self.all_nodes:
                self.all_nodes = set(range(json_packet['totalNodes']))
            self.lap_nodes.add(json_packet['activeNode'])
            
            # ==========================================================
            # startin line detection broke with v22.03.24
            # this restores lap timing by checking for rollover from maximum
            # node to node 0
            # ==========================================================
            if self.max_node is None:
                self.max_node = json_packet['totalNodes'] - 1
            self.current_node = json_packet['activeNode']
            if self.current_node != self.previous_node:
                if self.previous_node == self.max_node and self.current_node == 0:
                    # print('starting line!')
                    # display time + resent progress if it was a full lap
                    if len(self.all_nodes - self.lap_nodes) <= 10: # allow for skipped 
                        lap_time = json_packet['time'] - self.lap_start
                        self.lap_sum += lap_time
                        if self.current_lap > 1:
                            self.later_lap_sum += lap_time 
                        if self.drive_mode in ('auto', 'auto_train'):
                            lap_avg = self.lap_sum / self.current_lap 
                            later_lap_avg = 0.0 if self.later_lap_sum == 0 else self.later_lap_sum / (self.current_lap - 1)
                            print(f"Lap {self.current_lap}: {lap_time:.2f} | avg : {lap_avg:.3f} / {later_lap_avg:.3f}")
                        else:
                            print(f"Lap {self.current_lap}: {lap_time:.2f}")
                        self.lap_nodes.clear()
                    else: 
                        # display '-' for time if not a complete lap
                        print(f"Lap {self.current_lap}: -")
                    # iterate lap
                    self.lap_start = json_packet['time']
                    self.timer_start = time.time()
                    self.current_lap += 1
                    # record laps if tracking thing separately
                    if self.record_laps:
                        self.lap_recorder.record(self.current_lap, json_packet['time'])
            self.previous_node = self.current_node

            # check for crash/timeout if auto-training
            if self.lap_start:
                self.lap_elapsed = json_packet['time'] - self.lap_start
                lap_elapsed = time.time() - self.timer_start
                if self.drive_mode == 'auto_train' and lap_elapsed > AUTO_TIMEOUT:
                    print('Auto-training lap timeout')
                    self.reset_car()

            # this makes sure that at least one image has been received before
            # attempting inference
            if self.drive_mode in ('auto', 'auto_train') and self.pilot:
                # don't try to start predicting without input
                if not self.current_image:
                    print('got first image')
                # decode image
                self.current_image = Image.open(
                    BytesIO(base64.b64decode(json_packet['image']))).getchannel(self.image_depth)
                lap_telem = [
                    'first_lap', 
                    'first_lap_speed', 
                    'first_lap_yaw',
                    'later_lap_speed',
                    'later_lap_yaw',
                    'lap_type_first',
                    'lap_type_later'
                    ]
                if not self.printed_telem:
                    print([x for x in self.pilot.telemetry_columns if not (x.startswith('activeNode_') or (x in lap_telem))])
                    if len([tc for tc in self.pilot.telemetry_columns if tc in lap_telem]) > 0:
                        print([tc for tc in self.pilot.telemetry_columns if tc in lap_telem])
                    self.printed_telem = True
                # add telemetry from json. don't try to add dummy columns that don't exist
                self.current_telem = [json_packet[x] for x in self.pilot.telemetry_columns if not (x.startswith('activeNode_') or (x in lap_telem))]
                first_lap = int(self.current_lap == 1)
                later_lap = int(not first_lap)
                # engineered features
                for lt in [tc for tc in self.pilot.telemetry_columns if tc in lap_telem]:
                    if lt in ['first_lap', 'lap_type_first']:
                        self.current_telem.append(first_lap)
                    elif lt == 'lap_type_later':
                        self.current_telem.append(later_lap)
                    else:
                        lt_split = lt.split('_')
                        if lt_split[0] == 'first':
                            self.current_telem.append(first_lap * json_packet[lt_split[-1]])
                        if lt_split[0] == 'later':
                            self.current_telem.append(later_lap * json_packet[lt_split[-1]])
                # add activeNode dummy columns if necessary
                if 'activeNode_0' in self.pilot.telemetry_columns:
                    node_dummies = [0] * 250
                    node_dummies[json_packet['activeNode']] = 1
                    self.current_telem.extend(node_dummies)

            # brakes (test)
            if self.brake_telem is not None: # brake_telem can be zero. ugh.
                json_packet['brake'] = self.brake_telem
                self.brake_telem = None
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


    def send_controls(self, steering=0.0, throttle=0.0, brake=1.0):
        p = { "msg_type" : "control",
                "steering" : steering.__str__(),
                "throttle" : throttle.__str__(),
                "brake" : brake.__str__() } #"0.0" }
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
        if abs(st) < 0.05:
            st = 0.0
        # e-brake
        if self.ctr.button('a_button'):
            fw = 0.0
            rv = -1.0
        else:
            fw = self.ctr.norm(ax='right_trigger', low=0.0, high=1.0)
            rv = self.ctr.norm(ax='left_trigger', low=0.0, high=-1.0)
        return st*st_scale, (fw + rv)*th_scale, 0.0
        # th = self.ctr.norm(ax='right_trigger', low=0.0, high=1.0)
        # br = self.ctr.norm(ax='left_trigger', low=0.0, high=1.0)
        # reverse (when brakes)
        # if self.ctr.button('b_button'):d
            # th *= -1
        # if self.ctr.button('a_button'):
        #     br = 1.0
        # if self.brake_telem == None:
        #     self.brake_telem = br
        # return st*st_scale, th, br

    def update(self):
        steering = 0.0
        throttle = 0.0
        brake = 0.0
        try:
            self.ctr.update()
        except Exception as e:
            if self.drive_mode == 'manual':
                self.driving = False
            print(e)
            print('attemping to reconnect')
            try:
                self.ctr = Controller(ctr_type=conf['controller_type'], 
                                path=conf['controller_path'])
            except:
                print("couldn't reconnect controller")
        if not self.driving:
            brake = 1.0
            if self.ctr.button('start_button'):
                print('Driving started')
                self.driving = True
            elif self.drive_mode == 'auto_train':
                self.driving = time.time() - self.sim_start > START_DELAY
                if self.driving:
                    print('auto-training started')
        else:
            if self.drive_mode in ('auto', 'auto_train'):
                if not self.current_image:
                    print("Waiting for first image")
                    return 
                if self.fresh_data:
                    steering, throttle = self.auto_update()
                    self.fresh_data = False
            elif self.drive_mode in ('manual', 'telem_test'):
                steering, throttle, brake = self.manual_update()
                brake = max(brake, (not self.driving) * 1.0)
            if self.ctr.button('select_button'):
                print('Driving stopped')
                self.driving = False
                self.send_controls(0.0, 0.0, 1.0)
        if self.ctr.button('y_button'):
            self.reset_car()
        
        self.send_controls(steering, throttle, brake)

        
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

    # print('ready to drive')

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
    parser.add_argument("--image_depth", 
                        type=int, 
                        default=DEFAULT_IMAGE_DEPTH,
                        help="image channels", 
                        choices=IMAGE_DEPTHS,) 
    parser.add_argument("--drive_mode", 
                        type=str, 
                        default=DEFAULT_DRIVE_MODE, 
                        help="manual control or autopilot", 
                        choices=DRIVE_MODES,) 
    parser.add_argument("--model_number",
                        type=int,
                        default=None,
                        help='model_history index for model and scaler paths')
    parser.add_argument("--telem_type",
                        type=str,
                        default=DEFAULT_TELEM,
                        help='type of telemetry provided by sim',
                        choices=TELEM_TYPES)

    args = parser.parse_args()
    conf = {
        "host": args.host,
        "port": args.port,
        "record_format": args.record_format,
        "image_format": args.image_format,
        "image_depth": args.image_depth,
        "drive_mode": args.drive_mode,
        "track": args.track,
        "controller_type": CONTROLLER_TYPE,
        "controller_path": CONTROLLER_PATH,
        "record_laps": RECORD_LAPS,
        "telem_type": DEFAULT_TELEM,
        "model_number": args.model_number,
        "model_history": MODEL_HISTORY_PATH,
        "model_type":  MODEL_TYPE,
        "sequence_length": SEQUENCE_LENGTH,
        "use_brakes": USE_BRAKES,
        # "auto_training": AUTO_TRAINING
    }
    while True: 
        refresh = run_client(conf)
        if not refresh:
            break
    print("client stopped")

