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
from abc import abstractmethod

from gym_donkeycar.core.sim_client import SDClient

from autopilot import Autopilot
from controller import Controller
from sim_recorder import SimRecorder, LapRecorder

class Client(SDClient):

    def __init__(self, address, conf=None, poll_socket_sleep_time=0.01):
        super().__init__(*address, poll_socket_sleep_time=poll_socket_sleep_time)
        self.controller_type = conf['controller_type']
        self.controller_path = conf['controller_path']
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
        self.previous_node = None
        self.current_node = None
        self.max_node = None
        self.use_brakes = conf['use_brakes']
        self.brake_telem = None
        self.trial_laps = 10 # TODO: make this a conf thing
        self.printed_telem = False
        self.steering_scale = 1.0
        self.throttle_scale = 1.0

        if self.drive_mode in ('auto', 'auto_train'):
            self.driving = False
            self.current_image = None
            self.pilot = Autopilot(conf)
            self.trial_times = []
        self.ctr = Controller(self.controller_type, self.controller_path)
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
            print('collision_with_starting_line!')
            # # display time + resent progress if it was a full lap
            # if len(self.all_nodes - self.lap_nodes) <= 10: # allow for skipped 
            #     lap_time = json_packet['timeStamp'] - self.lap_start
            #     self.lap_sum += lap_time
            #     if self.current_lap > 1:
            #         self.later_lap_sum += lap_time 
            #     if self.drive_mode in ('auto', 'auto_train'):
            #         lap_avg = self.lap_sum / self.current_lap 
            #         later_lap_avg = 0.0 if self.later_lap_sum == 0 else self.later_lap_sum / (self.current_lap - 1)
            #         print(f"Lap {self.current_lap}: {lap_time:.2f} | avg : {lap_avg:.3f} / {later_lap_avg:.3f}")
            #     else:
            #         print(f"Lap {self.current_lap}: {lap_time:.2f}")
            #     self.lap_nodes.clear()
            # else: 
            #     # display '-' for time if not a complete lap
            #     print(f"Lap {self.current_lap}: -")
            # # iterate lap
            # self.lap_start = json_packet['timeStamp']
            # self.timer_start = time.time()
            # self.current_lap += 1
            # # record laps if tracking thing separately
            # if self.record_laps:
            #     self.lap_recorder.record(self.current_lap, json_packet['timeStamp'])

        if json_packet['msg_type'] == "telemetry":
            del json_packet['msg_type']

            if json_packet['hit'] != 'none':
                print(f"hit: {json_packet['hit']}")

            self.process_lap(json_packet)

            # check for crash/timeout if auto-training
            # TODO: switch to auto_train client
            if self.lap_start:
                self.lap_elapsed = json_packet['time'] - self.lap_start
                lap_elapsed = time.time() - self.timer_start
                if self.drive_mode == 'auto_train' and lap_elapsed > AUTO_TIMEOUT:
                    print('Auto-training lap timeout')
                    self.reset_car()

            telemetry_data = self.process_telemetry(json_packet=json_packet)

            # brakes (test)
            if self.brake_telem is not None: # brake_telem can be zero. ugh.
                telemetry_data['brake'] = self.brake_telem
                self.brake_telem = None

            # add lap
            telemetry_data['lap'] = self.current_lap
            
            # Start recording when you first start moving
            if self.recorder and json_packet['throttle'] > 0.0:
                self.start_recording = True
            # record image/telemetry
            if self.start_recording:
                self.recorder.record(telemetry_data)

            # indicate there is new data on which to make a prediction
            self.fresh_data = True    


    def print_trial_times(self):
        print('trial times: ', end='')
        for n, t in enumerate(self.trial_times):
            print(f'{t:.2f}' + (',' * (n < (len(self.trial_times) - 1))), end=' ')
        later_lap_avg = 0.0 if self.later_lap_sum == 0 else self.later_lap_sum / (self.current_lap - 1)
        print(f'| {later_lap_avg:.3f}')


    def process_lap(self, json_packet):
        # ==========================================================
        # starting line detection broke with v22.03.24
        # this restores lap timing by checking for rollover from maximum
        # node to node 0
        # ==========================================================

        # track lap progress
        if not self.all_nodes:
            self.all_nodes = set(range(json_packet['totalNodes']))
        self.lap_nodes.add(json_packet['activeNode'])
        
        if self.max_node is None:
            self.max_node = json_packet['totalNodes'] - 1
        self.current_node = json_packet['activeNode']
        if self.previous_node is not None and self.current_node != self.previous_node:
            if self.previous_node == self.max_node and self.current_node == 0:
                # display time + resent progress if it was a full lap
                if len(self.all_nodes - self.lap_nodes) <= 10: # allow for skipped 
                    lap_time = json_packet['time'] - self.lap_start
                    self.lap_sum += lap_time
                    if self.current_lap > 1:
                        self.later_lap_sum += lap_time 
                    if self.drive_mode in ('auto', 'auto_train'):
                        lap_avg = self.lap_sum / self.current_lap 
                        later_lap_avg = 0.0 if self.later_lap_sum == 0 else self.later_lap_sum / (self.current_lap - 1)
                        print(f"Lap {self.current_lap}: {lap_time:.2f} | avg : {lap_avg:.3f} | {later_lap_avg:.3f}")
                    else:
                        print(f"Lap {self.current_lap}: {lap_time:.2f}")
                    self.lap_nodes.clear()
                    # add lap time to trial lap times if auto-trialing
                    if self.drive_mode == 'auto':
                        if self.current_lap <= self.trial_laps:
                            self.trial_times.append(lap_time)
                            self.print_trial_times()
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

    
    def process_telemetry(self, json_packet):
        return json_packet

    def reset_car(self):
        self.refresh_sim = True
        self.stop()


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


    def send_controls(self, steering=0.0, throttle=0.0, brake=0.0):
        p = { "msg_type" : "control",
                "steering" : steering.__str__(),
                "throttle" : throttle.__str__(),
                "brake" : brake.__str__() } #"0.0" }
        msg = json.dumps(p)
        self.send(msg)
        #this sleep lets the SDClient thread poll our message and send it out.
        time.sleep(self.poll_socket_sleep_sec)


    def stop(self):
        print(f'Client stopping after {self.current_lap-1} laps.')
        super().stop()

    @ abstractmethod
    def update(self):
        pass

    def update_controller(self):
        try:
            self.ctr.update()
            return True
        except Exception as e:
            print(e)
            return False

    def update_driving_status(self):
        if not self.driving:
            if self.ctr.button('start_button'):
                print('Driving started')
                self.driving = True
        else:
            if self.ctr.button('select_button'):
                print('Driving stopped')
                self.driving = False


class Autonomous_Client(Client):

    def __init__(self, address, conf, poll_socket_sleep_time=0.01):
        super().__init__(address, conf=conf, poll_socket_sleep_time=poll_socket_sleep_time)

    def process_telemetry(self, json_packet):
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


    def update(self):
        # do brakes later
        steering, throttle, brake = 0.0, 0.0, 0.0
        # attempt to update controller
        controller_updated = self.update_controller()
        if not controller_updated:
            print('no controller update')
            self.aborted = True
            return
        # check reset
        if self.ctr.button('y_button'):
            self.reset_car()
            return
        # infer    
        if not self.current_image:
                print("Waiting for first image")
                self.driving = False
        else:
            self.update_driving_status()
            if HAS_TELEM:
                inputs = self.current_image, self.current_telem
            else:
                inputs = [self.current_image]
            steering, throttle = self.pilot.infer(inputs)
    
        if not self.driving:
            steering, throttle, brake = 0.0, 0.0, 1.0
        self.send_controls(steering, throttle, brake)


class Manual_Client(Client):

    def __init__(self, address, conf, poll_socket_sleep_time=0.01):
        super().__init__(address, conf=conf, poll_socket_sleep_time=poll_socket_sleep_time)

    def manual_steering(self):
        st = self.ctr.norm(ax='left_stick_horz', low=-1.0, high=1.0)
        if abs(st) < 0.05:
            st = 0.0
        return st * self.steering_scale

    def manual_throttle(self):
        if self.use_brakes:
            return self.brake_throttle()
        else:
            return self.brakeless_throttle(), 0.0

    def brake_throttle(self):
        th = self.ctr.norm(ax='right_trigger', low=0.0, high=1.0)
        br = self.ctr.norm(ax='left_trigger', low=0.0, high=1.0)
        # reverse
        if self.ctr.button('b_button'):
            th *= -1
        # e-brake
        if self.ctr.button('a_button'):
            br = 1.0
        if self.brake_telem == None:
            self.brake_telem = br
        return th, br

    def brakeless_throttle(self):
        # emergency "brake"
        fw, rv = 0.0, 0.0
        if self.ctr.button('a_button'):
            fw = 0.0
            rv = -1.0
        else:
            fw = self.ctr.norm(ax='right_trigger', low=0.0, high=1.0)
            rv = self.ctr.norm(ax='left_trigger', low=0.0, high=-1.0)
        return (fw + rv) * self.throttle_scale

    def update(self):
        steering, throttle, brake = 0.0, 0.0, 1.0
        # attempt to update controller
        controller_updated = self.update_controller()
        if controller_updated:
            # check reset
            if self.ctr.button('y_button'):
                self.reset_car()
                return
            self.update_driving_status()
            # get control inputs                     
            if self.driving:
                steering = self.manual_steering()
                throttle, brake = self.manual_throttle()
        else:
            print('no controller update')
            self.aborted = True
        self.send_controls(steering, throttle, brake)
