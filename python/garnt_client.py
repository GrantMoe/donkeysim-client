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
import csv

class SimpleClient(SDClient):

    def __init__(self, type, address, poll_socket_sleep_time=0.01):
        super().__init__(*address, poll_socket_sleep_time=poll_socket_sleep_time)
        self.type = type
        self.car_loaded = False
        self.ctr = Controller()
        timeStr = time.strftime("%m_%d_%Y/%H_%M_%S")
        self.dir = f'{os.getcwd()}/../data/{timeStr}'
        self.data_dir = self.dir #f'{self.dir}/data'
        self.img_dir = f'{self.dir}/data' #f'{self.dir}/images'
        os.makedirs(self.data_dir)
        os.makedirs(self.img_dir)
        self.record_count = 0
        self.start_recording = False
        if type == 'ASL':
            self.stamp_file = 'timestamps.txt'
            self.csv_file = "data.csv"
            with open(f'{self.data_dir}/{self.stamp_file}', 'w', newline='') as stampfile:
                pass
            with open(f'{self.data_dir}/{self.csv_file}', 'w', newline='') as csvfile:
                row_writer = csv.writer(csvfile)
                row_writer.writerow(['#timestamp [ns]', 'filename'])


    def on_msg_recv(self, json_packet):
        if json_packet['msg_type'] == "car_loaded":
            self.car_loaded = True
            # if not self.prev_frame:
                # self.prev_frame = time.time()
        
        if json_packet['msg_type'] == "telemetry":
            if json_packet['throttle'] > 0.0:
                self.start_recording = True
            if self.start_recording:
                imgString = json_packet['image']
                del json_packet['image']
                image = Image.open(BytesIO(base64.b64decode(imgString)))
                if self.type == "raw":                  
                    image.save(f'{self.img_dir}/frame_{self.record_count:04d}.png')
                    with open(f'{self.data_dir}/data_{self.record_count:04d}', 'w') as outfile:
                        json.dump(json_packet, outfile)
                        self.record_count += 1 
                if self.type == "ASL":
                    time_stamp= str(time.time_ns())
                    image.save(f'{self.img_dir}/{time_stamp}.png')
                    with open(f'{self.data_dir}/{self.stamp_file}', 'a') as stampfile:
                        stampfile.write(time_stamp+'\n')
                    with open(f'{self.data_dir}/{self.csv_file}', 'a', newline='') as csvfile:
                        row_writer = csv.writer(csvfile)
                        row_writer.writerow([time_stamp, time_stamp+'.png'])

        if json_packet['msg_type'] != "telemetry":     
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

    def update(self, st_scale=1.0, th_scale=0.5):
        # get normed inputs
        self.ctr.update()
        st = self.ctr.norm('left_stick_horz', -1.0, 1.0)
        fw = self.ctr.norm('right_trigger', 0.0, 1.0)
        rv = self.ctr.norm('left_trigger', 0.0, -1.0)
        if abs(st) < 0.07:
            st = 0.0
        self.send_controls(st*st_scale, (fw + rv)*th_scale)


# Create client and connect it with the simulator
def run_client(env_name, conf):
    host = conf["host"] # "trainmydonkey.com" for virtual racing
    port = conf["port"]
    data_type = conf["data_type"]
    client = SimpleClient(data_type, address=(host, port))

    time.sleep(1)

    # # test
    # msg = '{ "msg_type" : "get_scene_names" }'
    # client.send(msg)
    # time.sleep(1) 


    msg = f'{{ "msg_type" : "load_scene", "scene_name" : "{env_name}" }}'
    client.send(msg)
    loaded = False
    while(not loaded):
        time.sleep(1.0)
        loaded = client.car_loaded           
        


    # Car config
    msg = f'{{ "msg_type" : "car_config", "body_style" : "{conf["body_style"]}", "body_r" : "{conf["body_rgb"][0]}", "body_g" : "{conf["body_rgb"][1]}", "body_b" : "{conf["body_rgb"][2]}", "car_name" : "{conf["car_name"]}", "font_size" : "{conf["font_size"]}" }}'
    client.send(msg)
    time.sleep(1)

    # Camera config
    # set any field to Zero to get the default camera setting.
    # the offset_x moves camera left/right
    # the offset_y moves camera up/down
    # the offset_z moves camera forward/back
    # with fish_eye_x/y == 0.0 then you get no distortion
    # img_enc can be one of JPG|PNG|TGA
    msg = '{ "msg_type" : "cam_config", "fov" : "90", "fish_eye_x" : "0.0", "fish_eye_y" : "0.0", "img_w" : "1280", "img_h" : "960", "img_d" : "1", "img_enc" : "PNG", "offset_x" : "0.0", "offset_y" : "0.0", "offset_z" : "0.0", "rot_x" : "0.0" }'
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

    # Initialize the donkey environment
    # where env_name one of:
    env_list = [
        "generated_road", 
        "warehouse", 
        "sparkfun_avc", 
        "generated_track", 
        "roboracingleague_1", 
        "waveshare", 
        "mini_monaco", 
        "warren", 
        "circuit_launch"
        ]

    format_list = [
        "raw",
        "ASL"
    ]

    parser = argparse.ArgumentParser(description="garnt_client")
    parser.add_argument(
        "--sim",
        type=str,
        default="sim_path",
        help="path to unity simulator. maybe be left at default if you would like to start the sim on your own.",
    )
    parser.add_argument("--host", type=str, default="127.0.0.1", help="host to use for tcp")
    parser.add_argument("--port", type=int, default=9091, help="port to use for tcp")
    parser.add_argument(
        "--env_name", type=str, default="circuit_launch", help="name of donkey sim environment", choices=env_list
    )
    parser.add_argument("--data_type", type=str, default="ASL", help="recording format", choices=format_list) 

    args = parser.parse_args()

    conf = {
        "exe_path": args.sim,
        "host": args.host,
        "port": args.port,
        "data_type": args.data_type,
        "body_style": "bare", # donkey, bare, car01, cybertruck, f1
        "body_rgb": (234, 21, 144),
        "car_name": "",
        "font_size": 10,
        "racer_name": "Grant",
        "country": "California",
        "bio": "custom client",
        "guid": str(uuid.uuid4()),
        "start_delay": 1,
    }

    run_client(args.env_name, conf)
