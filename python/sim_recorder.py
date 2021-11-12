import os
import time
import csv
import json
import shutil
import base64

from io import BytesIO
from PIL import Image


class ASLRecorder:

    def __init__(self):
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


    def record(self, json_packet):
        time_stamp= str(time.time_ns())
        image = Image.open(
                    BytesIO(base64.b64decode(json_packet['image']))
                    ).getchannel(self.image_depth)
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



class CSVRecorder:

    csv_cols = [
            'steering_angle', 'throttle', 'speed', 'image', 'hit', 
            'time', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 
            'gyro_y', 'gyro_z', 'gyro_w', 'pitch', 'yaw', 'roll', 
            'cte', 'activeNode', 'totalNodes', 'pos_x', 'pos_y', 
            'pos_z', 'vel_x', 'vel_y', 'vel_z', 'on_road', 
            'progress_on_shortest_path', 'lap'
            ]

    def __init__(self, image_format, image_depth):
        time_str = time.strftime("%m_%d_%Y/%H_%M_%S")
        self.dir = f'{os.getcwd()}/../data/{time_str}'
        os.makedirs(self.dir, exist_ok=True)
        self.img_dir = f'{self.dir}/images'
        os.makedirs(self.img_dir, exist_ok=True)
        self.csv_file_path = f'{self.dir}/data.csv'
        with open(self.csv_file_path, 'w', newline='') as csv_outfile:
            row_writer = csv.writer(csv_outfile)
            row_writer.writerow(self.csv_cols)
        self.image_format = image_format
        self.image_depth = image_depth

    def record(self, json_packet, current_lap):
        image = Image.open(
                    BytesIO(base64.b64decode(json_packet['image']))
                    ).getchannel(self.image_depth)
        image.save(f"{self.img_dir}/{json_packet['time']}.{self.image_format}")
        json_packet['image'] = f"{json_packet['time']}.{self.image_format}"
        json_packet['lap'] = current_lap
        del json_packet['msg_type']
        with open(self.csv_file_path, 'a', newline='') as csv_outfile:
            row_writer = csv.writer(csv_outfile)
            row_writer.writerow(value for value in json_packet.values())


class TubRecorder:

    def __init__(self, image_format, image_depth):
        time_str = time.strftime("%m_%d_%Y/%H_%M_%S")
        self.dir = f'{os.getcwd()}/../data/{time_str}'
        self.data_dir = f'{self.dir}/tub_data'
        os.makedirs(self.data_dir, exist_ok=True)
        self.img_dir = f'{self.dir}/images'
        os.makedirs(self.img_dir, exist_ok=True)
        self.image_format = image_format
        self.image_depth = image_depth
        self.record_count = 0
    
    def record(self, json_packet, image):
        image = Image.open(
            BytesIO(base64.b64decode(json_packet['image']))
            ).getchannel(self.image_depth)
        image.save(f'{self.img_dir}/frame_{self.record_count:04d}.png')
        del json_packet['image']
        with open(f'{self.data_dir}/data_{self.record_count:04d}', 'w') as outfile:
            json.dump(json_packet, outfile)
        self.record_count += 1 