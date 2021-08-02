#!/usr/bin/env python3
import fcntl
import os
import sys
import libevdev
from libevdev import *

ev_map = {
    'xbox': {
        'axis': {
            'left_stick_horz': EV_ABS.ABS_X,
            'left_stick_vert': EV_ABS.ABS_Y,
            'left_trigger': EV_ABS.ABS_Z,
            'right_stick_horz': EV_ABS.ABS_RX,
            'right_stick_vert': EV_ABS.ABS_RY,
            'right_trigger': EV_ABS.ABS_RZ,
            'dpad_horz': EV_ABS.ABS_HAT0X,
            'dpad_vert': EV_ABS.ABS_HAT0Y,
        },
        'button': {
            'a_button': EV_KEY.BTN_SOUTH,
            'b_button': EV_KEY.BTN_EAST,
            'y_button': EV_KEY.BTN_NORTH,
            'x_button': EV_KEY.BTN_WEST,
            'left_shoulder': EV_KEY.BTN_TL,
            'right_shoulder': EV_KEY.BTN_TR,
            'select_button': EV_KEY.BTN_SELECT,
            'start_button': EV_KEY.BTN_START,
            'mode_button': EV_KEY.BTN_MODE,
            'left_thumb': EV_KEY.BTN_THUMBL,
            'right_thumb': EV_KEY.BTN_THUMBR,
        }
    }
}
class Controller:

    def __init__(self, ctr_type='xbox', path='/dev/input/by-id/usb-Microsoft_Controller_3039363431313739383635393433-event-joystick'):
        try:
            self.fd_ = open(path, 'rb')
            fcntl.fcntl(self.fd_, fcntl.F_SETFL, os.O_NONBLOCK)
            self.dev_ = Device(self.fd_)
        except IOError as e:
            import errno
            if e.errno == errno.EACCES:
                print("Insufficient permissions to access {}".format(path))
            elif e.errno == errno.ENOENT:
                print("Device {} does not exist".format(path))
            else:
                raise e

        self.map_ = ev_map[ctr_type]
        self.dev_.absinfo[EV_ABS.ABS_X] = InputAbsInfo(flat=3000)


    def steering_deadzone(self, val):
        if val is None:
            return self.dev_.absinfo[EV_ABS.ABS_X].flat
        else:
            ai = InputAbsInfo(flat=val)
            self.dev_.absinfo[EV_ABS.ABS_X] = ai

    # see if this counts as enough work to actually refresh
    def update(self):
        try:
            for event in self.dev_.events():
                if event.matches(EV_ABS):
                    continue
                elif event.matches(EV_KEY):
                    continue
        except EventsDroppedException:
            for sync_event in self.dev_.sync():
                if sync_event.matches(EV_ABS):
                    continue
                if sync_event.matches(EV_KEY):
                    continue
        except:
            raise Exception('polling failure')

    # to get x' in [a, b],
    # x'  = (b - a) * ( (x - x_min) / (x_max - x_min) ) + a
    def norm(self, ax, low=-1.0, high=1.0):
        ev = self.map_['axis'][ax]
        v_val = self.dev_.value[ev]
        v_min = self.dev_.absinfo[ev].minimum
        v_max = self.dev_.absinfo[ev].maximum
        return (high - low) * (v_val - v_min) / (v_max - v_min) + low

    def button(self, btn):
        return self.dev_.value[self.map_['button'][btn]]



def main():
    ctr = Controller()
    while True:
        ctr.update()
        st = ctr.norm('left_stick_horz', -1.0, 1.0)
        fw = ctr.norm('right_trigger', 0.0, 1.0)
        rv = ctr.norm('left_trigger', 0.0, -1.0)
        if abs(st) < 0.07:
            st = 0.0
        print("st: {}, th: {}".format(st, (fw+rv)))
        # self.send_controls(st * 0.5, 0.5 * (fw + rv))

if __name__ == "__main__":
    main()