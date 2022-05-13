import os
import time
import csv
import json
import shutil
import base64

from io import BytesIO
from PIL import Image

# from conf import TELEMETRY_COLUMNS
import config as config


class GymRecorder:

    def __init__(self, conf):
        telem_type = 'gym'
        image_format = 'png'
        image_depth = conf['cam_resolution'][2]
        self.recorder = CSVRecorder(image_format, image_depth, telem_type)

    def record(self, json_packet):
        self.recorder.record(json_packet)


class SimRecorder:

    def __init__(self, conf):
        record_format = config.record_format 
        image_format = config.image_format
        image_depth = config.image_depth
        # telem_type = conf['telem_type']
        if record_format == 'tub':
            self.recorder = TubRecorder(image_format, image_depth)
        elif record_format == 'CSV':
            self.recorder = CSVRecorder(conf)
        elif record_format == 'ASL':
            self.recorder = ASLRecorder(image_format, image_depth)
        else:
            self.recorder = None

    def record(self, json_packet):
        self.recorder.record(json_packet)

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

class LapRecorder:

    def __init__(self, model_path):
        model_str = model_path.split('/')[-1][:-3]
        day_str = time.strftime("%m_%d_%Y")
        time_str = time.strftime("%H_%M")
        self.dir = f'{os.getcwd()}/../data/{model_str}/{day_str}'
        os.makedirs(self.dir, exist_ok=True)
        self.csv_file_path = f'{self.dir}/{time_str}.csv'
        with open(self.csv_file_path, 'w', newline='') as csv_outfile:
            row_writer = csv.writer(csv_outfile)
            row_writer.writerow(('lap','time'))

    def record(self, lap, time):
        with open(self.csv_file_path, 'a', newline='') as csv_outfile:
            row_writer = csv.writer(csv_outfile)
            row_writer.writerow((lap, time))

class CSVRecorder:

    def __init__(self, conf):
        time_str = time.strftime("%m_%d_%Y/%H_%M_%S")
        self.dir = f'{os.getcwd()}/../data/{time_str}'
        self.img_dir = f'{self.dir}/images'
        os.makedirs(self.dir, exist_ok=True)
        os.makedirs(self.img_dir, exist_ok=True)
        self.csv_file_path = f'{self.dir}/data.csv'
        self.telem_cols = config.TELEMETRY_COLUMNS[conf['telem_type']]
        with open(f'{self.dir}/conf', 'x') as conf_file:
            conf_file.write(json.dumps(conf))
        with open(self.csv_file_path, 'w', newline='') as csv_outfile:
            row_writer = csv.writer(csv_outfile)
            row_writer.writerow(self.telem_cols)
        self.image_format = conf['image_format'] # 'PNG' # conf.image_format
        self.image_depth = conf['image_depth'] # 1 # conf.image_depth
        print(f"DATA FILE: {self.csv_file_path}")

    def record(self, json_packet):
        image_file = f"{str(json_packet['time']).replace('.','_')}.{self.image_format.lower()}"
        image = Image.open(BytesIO(base64.b64decode(json_packet['image']))).getchannel(self.image_depth)
        image.save(f"{self.img_dir}/{image_file}")
        json_packet['image'] = f"{image_file}" 
        with open(self.csv_file_path, 'a', newline='') as csv_outfile:
            row_writer = csv.writer(csv_outfile)
            # row_writer.writerow(value for value in json_packet.values())
            row_writer.writerow(json_packet[col] for col in self.telem_cols)




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
    
    def record(self, json_packet):
        image = Image.open(
            BytesIO(base64.b64decode(json_packet['image']))
            ).getchannel(self.image_depth)
        image.save(f'{self.img_dir}/frame_{self.record_count:04d}.png')
        del json_packet['image']
        with open(f'{self.data_dir}/data_{self.record_count:04d}', 'w') as outfile:
            json.dump(json_packet, outfile)
        self.record_count += 1 
