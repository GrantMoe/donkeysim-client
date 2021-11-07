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
import csv
import shutil


class SimpleClient(SDClient):


    def __init__(self, address, conf=None, poll_socket_sleep_time=0.01):
        super().__init__(*address, poll_socket_sleep_time=poll_socket_sleep_time)
        self.data_format = conf['data_type']
        self.car_loaded = False
        self.start_recording = False
        self.ctr = Controller()
        self.image_depth = conf['image_depth']
        self.image_format = conf['image_format']
        if self.data_format in ('csv', 'raw'):
            time_str = time.strftime("%m_%d_%Y/%H_%M_%S")
            self.dir = f'{os.getcwd()}/../data/{time_str}'
            os.makedirs(self.dir, exist_ok=True)
        if self.data_format == 'raw':
            self.data_dir = f'{self.dir}/{self.data_format}_data'
            os.makedirs(self.data_dir, exist_ok=True)
            self.img_dir = f'{self.dir}/images'
            os.makedirs(self.img_dir, exist_ok=True)
            self.record_count = 0
        if self.data_format == 'csv':
            self.img_dir = f'{self.dir}/images'
            os.makedirs(self.img_dir, exist_ok=True)
            self.csv_cols = [
                'steering_angle', 'throttle', 'speed', 'image', 'hit', 
                'time', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 
                'gyro_y', 'gyro_z', 'gyro_w', 'pitch', 'yaw', 'roll', 
                'cte', 'activeNode', 'totalNodes', 'pos_x', 'pos_y', 
                'pos_z', 'vel_x', 'vel_y', 'vel_z', 'on_road', 
                'progress_on_shortest_path', 'lap'
                ]
            self.csv_file_path = f'{self.dir}/data.csv'
            with open(self.csv_file_path, 'w', newline='') as csv_outfile:
                row_writer = csv.writer(csv_outfile)
                row_writer.writerow(self.csv_cols)
            self.current_lap = 0
        if self.data_format == 'ASL':
            asl_dir = f'{os.getcwd()}/../data/asl'
            dir_num = 1
            dir_str = f'DS{dir_num:02}'
            self.dir = f'{asl_dir}/{dir_str}'
            while os.path.isdir(self.dir):
                dir_num += 1
                dir_str = f'DS{dir_num:02}'
                self.dir = f'{os.getcwd()}/../data/asl/{dir_str}'
            os.makedirs(self.dir)
            # add entry to example .sh file
            sh_file = '/home/grant/projects/ORB_SLAM3/Examples/sim_examples.sh'
            sh_str = (
                f'./Monocular-Inertial/mono_inertial_euroc'
                f' ../Vocabulary/ORBvoc.txt'
                f' "$pathDatasetDonkeySim"/Monocular-Inertial/DonkeySim.yaml'
                f' "$pathDatasetDonkeySim"/{dir_str}'
                f' "$pathDatasetDonkeySim"/Monocular-Inertial/DonkeySim_Timestamps/{dir_str}.txt'
                f' dataset-{dir_str}_monoi'
            )
            with open(sh_file, 'a') as f:
                f.write(f'\n\necho "Launching {dir_str} with Monocular-Inertial sensor"')
                f.write(f'\n{sh_str}')
            self.mav_dir = f'{self.dir}/mav0'
            self.cam_dir = f'{self.mav_dir}/cam0'
            self.imu_dir = f'{self.mav_dir}/imu0'
            self.img_dir = f'{self.cam_dir}/data'
            os.makedirs(self.mav_dir)
            os.makedirs(self.cam_dir)
            os.makedirs(self.imu_dir)
            os.makedirs(self.img_dir)
            # copy yaml files
            shutil.copy(f'{asl_dir}/body.yaml', self.mav_dir)
            shutil.copy(f'{asl_dir}/cam_sensor.yaml', f'{self.cam_dir}/sensor.yaml')
            shutil.copy(f'{asl_dir}/imu_sensor.yaml', f'{self.imu_dir}/sensor.yaml')
            # create cam and imu data.csv files
            self.cam_csv = f'{self.cam_dir}/data.csv'
            self.imu_csv = f'{self.imu_dir}/data.csv'
            with open(self.cam_csv, 'w', newline='') as csvfile:
                row_writer = csv.writer(csvfile)
                row_writer.writerow(['#timestamp [ns]', 'filename'])
            with open(self.imu_csv, 'w', newline='') as csvfile:
                row_writer = csv.writer(csvfile)
                row_writer.writerow(['#timestamp [ns]', 
                                    'w_RS_S_x [rad s^-1]', 
                                    'w_RS_S_y [rad s^-1]', 
                                    'w_RS_S_z [rad s^-1]', 
                                    'a_RS_S_x [m s^-2]', 
                                    'a_RS_S_y [m s^-2]',
                                    'a_RS_S_z [m s^-2]'
                                    ])
            # create timestamp files
            cam_ts_dir = f'{asl_dir}/Monocular-Inertial/DonkeySim_Timestamps'
            self.cam_ts_file = f'{cam_ts_dir}/{dir_str}.txt'
            with open(self.cam_ts_file, 'w') as stampfile:
                pass
            imu_ts_dir = f'{asl_dir}/Monocular-Inertial/DonkeySim_IMU'
            self.imu_ts_file = f'{imu_ts_dir}/{dir_str}.txt'
            with open(self.imu_ts_file, 'w', newline='') as stampfile:
                stampfile.write('#timestamp [ns],w_RS_S_x [rad s^-1],'
                                'w_RS_S_y [rad s^-1],w_RS_S_z [rad s^-1],'
                                'a_RS_S_x [m s^-2],a_RS_S_y [m s^-2],'
                                'a_RS_S_z [m s^-2]\n')


    def on_msg_recv(self, json_packet):

        if json_packet['msg_type'] != "telemetry":     
            print("got:", json_packet)

        if json_packet['msg_type'] == "car_loaded":
            self.car_loaded = True

        if json_packet['msg_type'] == "collision_with_starting_line":
            self.current_lap += 1

        if json_packet['msg_type'] == "telemetry":
            if json_packet['throttle'] > 0.0:
                self.start_recording = True
            if self.start_recording:
                if self.data_format == "raw":
                    imgString = json_packet['image']
                    image = Image.open(BytesIO(base64.b64decode(imgString)))
                    image.save(f'{self.img_dir}/frame_{self.record_count:04d}.png')
                    del json_packet['image']
                    with open(f'{self.data_dir}/data_{self.record_count:04d}', 'w') as outfile:
                        json.dump(json_packet, outfile)
                    self.record_count += 1 
                if self.data_format == 'csv':
                    imgString = json_packet['image']
                    image = Image.open(BytesIO(base64.b64decode(imgString))).getchannel(self.image_depth)
                    image.save(f"{self.img_dir}/{json_packet['time']}.{self.image_format}")
                    json_packet['image'] = f"{json_packet['time']}.{self.image_format}"
                    json_packet['lap'] = self.current_lap
                    del json_packet['msg_type']
                    with open(self.csv_file_path, 'a', newline='') as csv_outfile:
                        row_writer = csv.writer(csv_outfile)
                        row_writer.writerow(value for value in json_packet.values())
                if self.data_format == "ASL":
                    time_stamp= str(time.time_ns())
                    # image
                    image.save(f'{self.img_dir}/{time_stamp}.png')
                    with open(self.cam_ts_file, 'a') as stampfile:
                        stampfile.write(time_stamp+'\n')
                    with open(self.cam_csv, 'a', newline='') as csvfile:
                        row_writer = csv.writer(csvfile)
                        row_writer.writerow([time_stamp, time_stamp+'.png'])
                    # imu
                    imu_stamp = (
                        f"{time_stamp},"
                        f"{json_packet['gyro_x']},"
                        f"{json_packet['gyro_y']},"
                        f"{json_packet['gyro_z']},"
                        f"{json_packet['accel_x']},"
                        f"{json_packet['accel_y']},"
                        f"{json_packet['accel_z']}\n"
                    )
                    with open(self.imu_ts_file, 'a') as stampfile:
                        stampfile.write(imu_stamp)
                    imu_data = [
                        time_stamp,
                        float(json_packet['gyro_x']),
                        float(json_packet['gyro_y']),
                        float(json_packet['gyro_z']),
                        float(json_packet['accel_x']),
                        float(json_packet['accel_y']),
                        float(json_packet['accel_z'])
                    ]
                    with open(self.imu_csv, 'a', newline='') as csvfile:
                        row_writer = csv.writer(csvfile)
                        row_writer.writerow(imu_data)


    def send_controls(self, steering, throttle):
        p = { "msg_type" : "control",
                "steering" : steering.__str__(),
                "throttle" : throttle.__str__(),
                "brake" : "0.0" }
        msg = json.dumps(p)
        self.send(msg)
        #this sleep lets the SDClient thread poll our message and send it out.
        time.sleep(self.poll_socket_sleep_sec)


    def update(self, st_scale=1.0, th_scale=1.0):
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
    client = SimpleClient(address=(host, port), conf=conf,)

    time.sleep(1)


    # # Uncomment to get track names
    # get_tracks = '{"msg_type" : "get_scene_names"}'
    # client.send(get_tracks)
    # time.sleep(1)
    
    # env_list = [
    # "generated_road", 
    # "warehouse", 
    # "sparkfun_avc", 
    # "generated_track", 
    # "roboracingleague_1", 
    # "waveshare", 
    # "mini_monaco", 
    # "warren", 
    # "circuit_launch"
    # ]

    msg = f'{{"msg_type" : "load_scene", "scene_name" : "{env_name}"}}'
    client.send(msg)
    loaded = False
    while(not loaded):
        time.sleep(1.0)
        loaded = client.car_loaded           



    # Car config
    car_config = (f'{{ "msg_type" : "car_config", ' 
        f'"body_style" : "{str(conf["body_style"])}", ' 
        f'"body_r" : "{str(conf["body_rgb"][0])}", ' 
        f'"body_g" : "{str(conf["body_rgb"][1])}", ' 
        f'"body_b" : "{str(conf["body_rgb"][2])}", ' 
        f'"car_name" : "{str(conf["car_name"])}", ' 
        f'"font_size" : "{str(conf["font_size"])}"}}')
    msg = car_config
    client.send(car_config)
    time.sleep(1)



    # Camera config
    # set any field to Zero to get the default camera setting.
    # the offset_x moves camera left/right
    # the offset_y moves camera up/down
    # the offset_z moves camera forward/back
    # with fish_eye_x/y == 0.0 then you get no distortion
    # img_enc can be one of JPG|PNG|TGA
    msg = '{ "msg_type" : "cam_config", "fov" : "0", "fish_eye_x" : "0.0", "fish_eye_y" : "0.0", "img_w" : "32", "img_h" : "32", "img_d" : "1", "img_enc" : "PNG", "offset_x" : "0.0", "offset_y" : "0.0", "offset_z" : "0.0", "rot_x" : "0.0" }'
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

    data_format_list = [
        "csv",
        "raw",
        "ASL"
    ]

    image_format_list = [
        'PNG',
        'JPG',
        'TGA'
    ]

    color_list = [
        "1 (greyscale)",
        "3 (RGB)"
    ]

    parser = argparse.ArgumentParser(description="garnt_client")
    parser.add_argument(
        "--sim",
        type=str,
        default="sim_path",
        help="path to unity simulator",
    )
    parser.add_argument("--host", 
                        type=str, 
                        default="127.0.0.1", 
                        help="host to use for tcp")
    parser.add_argument("--port", 
                        type=int, 
                        default=9091, 
                        help="port to use for tcp")
    parser.add_argument("--env_name", 
                        type=str, 
                        default="mini_monaco", 
                        help="name of donkey sim environment", 
                        choices=env_list)
    parser.add_argument("--data_type", 
                        type=str, 
                        default="csv", 
                        help="recording format", 
                        choices=data_format_list) 
    parser.add_argument("--image_format", 
                        type=str, 
                        default="PNG", 
                        help="image format", 
                        choices=image_format_list) 
    parser.add_argument("--image_channels", 
                        type=int, 
                        default=1, 
                        help="image channels", 
                        choices=color_list) 


    args = parser.parse_args()

    conf = {
        "exe_path": args.sim,
        "host": args.host,
        "port": args.port,
        "data_type": args.data_type,
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
    }

    run_client(args.env_name, conf)
