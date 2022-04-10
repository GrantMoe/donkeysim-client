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
from client import Manual_Client


# Create client and connect it with the simulator
def run_client(conf):
    # logging.basicConfig(level=logging.DEBUG)

    host = conf["host"] # "trainmydonkey.com" for virtual racing
    port = conf["port"]
    client = Manual_Client(address=(host, port), conf=conf,)
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
    # parser.add_argument("--drive_mode", 
    #                     type=str, 
    #                     default=DEFAULT_DRIVE_MODE, 
    #                     help="manual control or autopilot", 
    #                     choices=DRIVE_MODES,) 
    # parser.add_argument("--model_number",
    #                     type=int,
    #                     default=None,
    #                     help='model_history index for model and scaler paths')
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
        "drive_mode": 'manual',
        "track": args.track,
        "controller_type": CONTROLLER_TYPE,
        "controller_path": CONTROLLER_PATH,
        "record_laps": RECORD_LAPS,
        "telem_type": DEFAULT_TELEM,
        # "model_number": args.model_number,
        # "model_history": MODEL_HISTORY_PATH,
        # "model_type":  MODEL_TYPE,
        # "sequence_length": SEQUENCE_LENGTH,
        "use_brakes": USE_BRAKES,
        # "auto_training": AUTO_TRAINING
    }
    while True: 
        refresh = run_client(conf)
        if not refresh:
            break
    print("client stopped")
