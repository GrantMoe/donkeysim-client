import argparse
import base64
import time
from io import BytesIO
from PIL import Image

from config import auto_timeout, image_depth, trial_laps
from pilot import Autopilot
from client import Client
from sim_recorder import SimRecorder


class AutoClient(Client):

    def __init__(self, address, conf, poll_socket_sleep_time=0.01):
        self.pilot = Autopilot(conf)
        self.mode = conf['mode']
        self.current_image = None
        self.current_telem = None
        self.fresh_data = False
        self.later_lap_sum = 0

        # give time for the autopilot to start up
        # time.sleep(1)

        super().__init__(address, conf=conf, poll_socket_sleep_time=poll_socket_sleep_time)
        if self.mode == 'train':
            self.recorder = SimRecorder(conf)
            self.braking = 0.0
        if self.mode == 'trial':
            self.trial_times = []

        # time.sleep(1)

        # only holds at the starting line if there's a race
        self.driving = self.mode in ['train', 'trial']

        # keep from rolling forward while setting up
        self.send_controls(0.0, 0.0, 1.0)

    def on_telemetry(self, data):
        self.check_progress(data)
        self.update_telemetry(data)
        if self.mode == 'train':
            data['brake'] = self.braking
            data['lap'] = self.current_lap
            self.recorder.record(data)

    def update_telemetry(self, data):
        # decode image
        self.current_image = Image.open(
            BytesIO(base64.b64decode(data['image']))).getchannel(image_depth)
        # add specified telemetry from json
        if 'first_lap' in self.pilot.telemetry_columns:
            data['first_lap'] = self.current_lap == 1
        self.current_telem = [data[x] for x in self.pilot.telemetry_columns]
        self.fresh_data = True
        if self.mode == 'train':
            self.check_reset(data['time'], data['hit'])
    
    def check_reset(self, time, hit):
        if self.lap_start:
            lap_elapsed = time - self.lap_start
            timed_out = lap_elapsed > auto_timeout
            crashed = hit != 'none'
            if timed_out or crashed:
                print(f"{'Auto timeout' * timed_out}{'Crashed!' * crashed}")
                self.reset_car = True
                # self.stop()

    def update(self):
        steering, throttle, brake = 0.0, 0.0, 0.0
        if not self.current_image:
            print("Waiting for first image")
            self.driving = False
            # return
        if self.fresh_data:
            inputs = self.current_image, self.current_telem
            steering, throttle, brake = self.pilot.infer(inputs)
            if brake < 0.01:
                brake = 0
            self.fresh_data = False
        if not self.driving:
            steering, throttle, brake = 0.0, 0.0, 1.0
        if self.mode == 'train':
            self.braking = brake
        self.send_controls(steering, throttle, brake)

    def on_full_lap(self, lap_time):
        dirty_lap = self.hit_count > 0
        print(f"Lap {self.current_lap}: {lap_time:.2f}", end="")
        if self.hit_count > 0:
            print('*', end="")
        if self.current_lap > 1:
            self.later_lap_sum += lap_time
            later_lap_avg = self.later_lap_sum / (self.current_lap - 1)
            print(f" | avg: {later_lap_avg:.3f}", end="")        
        self.print_fastest_lap(lap_time)
        if self.mode == 'trial' and self.current_lap <= trial_laps:
            self.trial_times.append(lap_time)
            if self.current_lap > 1:
                self.print_trial_times(dirty_lap)

    def print_trial_times(self, dirty_lap):
        print('trial times: ', end='')
        for n, t in enumerate(self.trial_times):
            print(f'{t:.2f}' + ('*' * dirty_lap) + (',' * (n < (len(self.trial_times) - 1))), end=' ')
        trial_avg = sum(self.trial_times[1:])/(len(self.trial_times)-1)
        print(f'| {trial_avg:.3f}')

# Create client and connect it with the simulator
def run_client(conf):
    host = conf["host"]
    port = conf["port"]
    client = AutoClient(address=(host, port), conf=conf,)


    # msg = '{ "msg_type" : "exit_scene" }'
    # client.send(msg)
    # time.sleep(0.5)

    # time.sleep(2)

    # Load Track
    msg = f'{{"msg_type" : "load_scene", "scene_name" : "{conf["track"]}"}}'
    client.send(msg)
    time.sleep(1.0)
    # doesn't work when this isn't here
    # Configure Car
    client.send_config()
    time.sleep(1.0)

    # Drive car
    run_sim = True
    refresh_sim = False
    while run_sim:
        try:
            client.update()
            if client.aborted:
                # print("Client aborted, stopping driving.")
                run_sim = False
            if client.reset_car:
                # print("Refreshing sim")
                refresh_sim = True
                run_sim = False
            if not client.driving:
                _ = input('press Enter to start driving')
                client.driving = True
        except KeyboardInterrupt:
            run_sim = False
        time.sleep(0.1)

    # msg = '{ "msg_type" : "exit_scene" }'
    # client.send(msg)
    # time.sleep(0.5)

    # Close down client
    # print("waiting for msg loop to stop")
    client.stop()
    return refresh_sim

if __name__ == "__main__":

    track_list = [
        'generated_road', 
        'warehouse', 
        'sparkfun_avc', 
        'generated_track', 
        'roboracingleague_1', 
        'waveshare', 
        'mini_monaco', 
        'warren', 
        'circuit_launch',
        'mountain_track'
        ]

    parser = argparse.ArgumentParser(description="donkeysim_client")
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
                        default="mountain_track",
                        help="name of donkey sim environment", 
                        choices=track_list,)
    parser.add_argument("--model_number",
                        type=int,
                        default=None,
                        help='model number for pilot')
    parser.add_argument("--mode",
                        type=str,
                        default="trial",
                        help="autonomous driving mode",
                        choices=['race', 'train', 'trial']
                        )

    args = parser.parse_args()
    conf = {
        "host": args.host,
        "port": args.port,
        "mode": args.mode,
        "track": args.track,
        "model_number": args.model_number,
        "record_format": 'CSV', # None, 'CSV', 'tub' (Donkey Car), 'ASL' (openvslam)
        "image_format": 'PNG', # 'JPG', 'PNG', 'TGA'
        "image_depth": 1, # 1:'grayscale', 3:'rgb'
        "telem_type": 'donkey_extended_brake' # 'donkey_basic', 'donkey_extended_brake', 'gym'
    }
    while True: 
        refresh = run_client(conf)
        if not refresh:
            break
        # time.sleep(3)
    print("client stopped")
