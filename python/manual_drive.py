import argparse
import time

from client import Client
from controller import Controller
from sim_recorder import SimRecorder

class ManualClient(Client):

    def __init__(self, address, conf, poll_socket_sleep_time=0.01):
        super().__init__(address, conf=conf, poll_socket_sleep_time=poll_socket_sleep_time)
        self.recorder = None
        self.start_recording = False
        self.track = conf['track']
        self.ctr = Controller()
        self.recorder = SimRecorder()
        self.driving = True

    def on_telemetry(self, data):
        self.check_progress(data)
        data['track'] = self.track
        data['lap'] = self.current_lap
        self.recorder.record(data)

    def update(self):
        steering, throttle, brake = 0.0, 0.0, 0.0
        # attempt to update controller
        controller_updated = self.update_controller()
        if not controller_updated:
            print('no controller update')
            self.aborted = True
            return
        # check reset
        if self.ctr.button('y_button'):
            self.reset_car = True
            self.stop()
        self.update_driving_status()
        steering, throttle = self.get_controls()
        if not self.driving:
            steering, throttle, brake = 0.0, 0.0, 1.0
        self.send_controls(steering, throttle, brake)

    def get_controls(self):
        steering = self.manual_steering()
        throttle = self.manual_throttle()
        return steering, throttle

    def manual_steering(self):
        st = self.ctr.norm(ax='left_stick_horz', low=-1.0, high=1.0)
        if abs(st) < 0.05:
            st = 0.0
        return st * self.steering_scale

    def manual_throttle(self):
        # emergency "brake"
        fw, rv = 0.0, 0.0
        if self.ctr.button('a_button'):
            fw = 0.0
            rv = -1.0
        else:
            fw = self.ctr.norm(ax='right_trigger', low=0.0, high=1.0)
            rv = self.ctr.norm(ax='left_trigger', low=0.0, high=-1.0)
        return (fw + rv) * self.throttle_scale

    def update_driving_status(self):
        if not self.driving:
            if self.ctr.button('start_button'):
                print('Driving started')
                self.driving = True
        else:
            if self.ctr.button('select_button'):
                print('Driving stopped')
                self.driving = False

    def update_controller(self):
        try:
            self.ctr.update()
            return True
        except Exception as e:
            print(e)
            return False


# Create client and connect it with the simulator
def run_client(conf):
    host = conf["host"]
    port = conf["port"]
    client = ManualClient(address=(host, port), conf=conf,)

    # Load Track
    msg = f'{{"msg_type" : "load_scene", "scene_name" : "{conf["track"]}"}}'
    client.send(msg)
    time.sleep(1.0)
    # doesn't work when this isn't here
    # Configure Car
    client.send_config()

    # Drive car
    run_sim = True
    refresh_sim = False
    while run_sim:
        try:
            client.update()
            if client.aborted:
                print("Client aborted, stopping driving.")
                run_sim = False
            if client.reset_car:
                print("Refreshing sim")
                refresh_sim = True
                run_sim = False
        except KeyboardInterrupt:
            run_sim = False
        time.sleep(0.1)

    msg = '{ "msg_type" : "exit_scene" }'
    client.send(msg)
    time.sleep(0.2)

    # Close down client
    print("waiting for msg loop to stop")
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

    args = parser.parse_args()
    conf = {
        "host": args.host,
        "port": args.port,
        "track": args.track,
    }

    while True: 
        refresh = run_client(conf)
        if not refresh:
            break
    print("client stopped")
