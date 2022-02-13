"""
file: robocar_gym.py
author: Grant Moe
date: 12 February 2022
notes: This tests controller input and image/telemetry recording.
        based on: github.com/tawnkramer/gym-donkeycar/examples/gym_test.py
"""
import argparse
import uuid

import gym

import gym_donkeycar

from controller import Controller


def test_track(env_name, conf):


    env = gym.make(env_name, conf=conf)

    # make sure you have no track loaded
    exit_scene(env)

    simulate(env, conf=conf)

    # exit the scene and close the env
    exit_scene(env)
    env.close()

def simulate(env, conf):

    # Create the controller
    ctr = Controller(ctr_type=conf['controller_type'], 
                            path=conf['controller_path'])

    # Reset the environment
    obv = env.reset()

    lap_time = 0.0
    lap_count = 0

    # t = 0
    while True:
        try:
            # get action
            ctr.update()
            st = ctr.norm(ax='left_stick_horz', low=-1.0, high=1.0)
            # e-brake
            if ctr.button('a_button'):
                fw = 0.0
                rv = -1.0
            else:
                fw = ctr.norm(ax='right_trigger', low=0.0, high=1.0)
                rv = ctr.norm(ax='left_trigger', low=0.0, high=-1.0)
            if abs(st) < 0.05:
                st = 0.0
            th = (fw + rv)

            action = [st, th]

            # execute the action
            obv, reward, done, info = env.step(action)

            # t = t + 1
            # if t % 30 == 0:
            #     print(
            #         "TIMESTEP",
            #         t,
            #         "/ ACTION",
            #         action,
            #         "/ REWARD",
            #         info,
            #             )
            if info["last_lap_time"] != lap_time:
                lap_count += 1
                lap_time = info["last_lap_time"]
                print(f"Lap {lap_count}: {round(lap_time, 3)}" )

        # if done:
            # print("done w test.", info)
            # break
        except KeyboardInterrupt:
            print("done w test.", info)
            break

def exit_scene(env):
    env.viewer.exit_scene()

def get_controls(self, st_scale=1.0, th_scale=1.0):
    # get normed inputs from controller
    st = self.ctr.norm(ax='left_stick_horz', low=-1.0, high=1.0)
    # e-brake
    if self.ctr.button('a_button'):
        fw = 0.0
        rv = -1.0
    else:
        fw = self.ctr.norm(ax='right_trigger', low=0.0, high=1.0)
        rv = self.ctr.norm(ax='left_trigger', low=0.0, high=-1.0)
    if abs(st) < 0.05:
        st = 0.0
    return st*st_scale, (fw + rv)*th_scale


if __name__ == "__main__":

    # Initialize the donkey environment
    # where env_name one of:
    env_list = [
        "donkey-warehouse-v0",
        "donkey-generated-roads-v0",
        "donkey-avc-sparkfun-v0",
        "donkey-generated-track-v0",
        "donkey-roboracingleague-track-v0",
        "donkey-waveshare-v0",
        "donkey-minimonaco-track-v0",
        "donkey-mountain-track-v0",
        "donkey-warren-track-v0",
        "donkey-thunderhill-track-v0",
        "donkey-circuit-launch-track-v0",
    ]

    parser = argparse.ArgumentParser(description="gym_test")
    parser.add_argument(
        "--sim",
        type=str,
        default="sim_path",
        help="path to unity simulator. maybe be left at default if you would like to start the sim on your own.",
    )
    parser.add_argument("--host", type=str, default="127.0.0.1", help="host to use for tcp")
    parser.add_argument("--port", type=int, default=9091, help="port to use for tcp")
    parser.add_argument(
        "--env_name", type=str, default="donkey-circuit-launch-track-v0", help="name of donkey sim environment", choices=env_list + ["all"]
    )

    args = parser.parse_args()

    conf = {
        "exe_path": args.sim,
        "host": args.host,
        "port": args.port,
        "body_style": "car01",
        "body_rgb": (234, 21, 144),
        "car_name": "",
        "font_size": 50,
        "start_delay": 1,
        "max_cte": 100,
        "cam_resolution": (1280, 720, 3),
        "controller_type": "xbox",
        "controller_path": "/dev/input/by-id/usb-Microsoft_Controller_3039363431313739383635393433-event-joystick",
        # "lidar_config": {
        #     "degPerSweepInc": 2.0,
        #     "degAngDown": 0.0,
        #     "degAngDelta": -1.0,
        #     "numSweepsLevels": 1,
        #     "maxRange": 50.0,
        #     "noise": 0.4,
        #     "offset_x": 0.0,
        #     "offset_y": 0.5,
        #     "offset_z": 0.5,
        #     "rot_x": 0.0,
        # },
    }

    if args.env_name == "all":
        for env_name in env_list:
            test_track(env_name, conf)

    else:
        test_track(args.env_name, conf)

    print("test finished")
