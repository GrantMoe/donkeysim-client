# The structure of this program is based on the sdsandbox test client:
# https://github.com/tawnkramer/sdsandbox/blob/master/src/test_client.py 
# by tawnkramer (https://github.com/tawnkramer)

import json
import time

from abc import abstractmethod

from gym_donkeycar.core.sim_client import SDClient

from conf import cam_conf, car_conf, racer_conf

class Client(SDClient):

    def __init__(self, address, conf=None, poll_socket_sleep_time=0.01):
        super().__init__(*address, poll_socket_sleep_time=poll_socket_sleep_time)
        self.car_loaded = False
        self.reset_car = False
        self.current_lap = 0
        self.lap_start = None
        self.driving = False
        self.lap_nodes = set()
        self.all_nodes = None
        self.previous_node = None
        self.steering_scale = 1.0
        self.throttle_scale = 1.0
        self.fastest_time = None
        self.fastest_laps = 0

    def config_builder(self, config_dict):
        msg_string = "{"
        for key, value in config_dict.items():
            msg_string += f'"{key}" : "{value}", '
        msg_string += "}"
        return msg_string

    def on_msg_recv(self, json_packet):

        # telemetry will flood the output, starting line is redundant with below checks
        if json_packet['msg_type'] not in ["telemetry", "collision_with_starting_line"]:
            print("got:", json_packet)

        if json_packet['msg_type'] == "need_car_config":
            print('got config request')
            self.send_config()

        if json_packet['msg_type'] == "car_loaded":
            # self.send_config()
            self.car_loaded = True        

        if json_packet['msg_type'] == "collision_with_starting_line":
            print('collision_with_starting_line!')
            self.on_finish_line(json_packet['timeStamp'])

        if json_packet['msg_type'] == "telemetry":
            del json_packet['msg_type']
            if json_packet['hit'] != 'none':
                print(f" * hit: {json_packet['hit']} *")
            self.on_telemetry(json_packet)
    
    @ abstractmethod
    def on_telemetry(self, json_packet):
        pass

    # TODO: report bug: activeNode can only increment, never decrement
    #       this opens the possibility of backwards progress going 
    #       undetected. bah.
    def check_progress(self, json_packet):
        # ==========================================================
        # starting line detection broke with v22.03.24
        # this restores lap timing by checking for rollover from maximum
        # node to node 0
        # ==========================================================
        # track lap progress
        if not self.all_nodes:
            self.all_nodes = set(range(json_packet['totalNodes']))
        self.lap_nodes.add(json_packet['activeNode'])
        if self.previous_node is None:
            self.previous_node = json_packet['activeNode']
        if (json_packet['activeNode'] == 1 and json_packet['activeNode'] != self.previous_node):
            self.on_finish_line(json_packet['time'])
        self.previous_node = json_packet['activeNode']

    def on_finish_line(self, time_crossed):
        # check if there has been a full lap
        # somewhat redundant without "real" finish line alerts
        if len(self.all_nodes - self.lap_nodes) <= 10:
            self.on_full_lap(round(time_crossed - self.lap_start, 2))
        else:
            print(f"Lap {self.current_lap}: -")
        self.lap_nodes.clear()
        self.lap_start = time_crossed
        self.current_lap += 1      

    def on_full_lap(self, lap_time):
        print(f"Lap {self.current_lap}: {lap_time:.2f}", end="")
        self.print_fastest_lap(lap_time)

    def print_fastest_lap(self, lap_time):
        if self.fastest_time is None:
            self.fastest_time = lap_time
        if lap_time < self.fastest_time:
            self.fastest_time = lap_time
            self.fastest_laps = 0
        if lap_time == self.fastest_time:
            self.fastest_laps += 1
            print(f" | fastest: {self.fastest_time:.2f} ({self.fastest_laps})")
        else:
            print("")

    def send_config(self):
        # Racer
        msg = self.config_builder(racer_conf)
        self.send(msg)
        time.sleep(0.2)
        # Car
        msg = self.config_builder(car_conf)
        self.send(msg)
        time.sleep(0.2)
        # Camera
        msg = self.config_builder(cam_conf)
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

    def stop(self):
        print(f'Client stopping after {self.current_lap-1} laps.')
        super().stop()

    @ abstractmethod
    def update(self):
        pass
