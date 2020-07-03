
#!/usr/bin/env python3
import fcntl
import os
import sys
import libevdev


class XBox:
    
    axes = {
        'ABS_X': 0, 
        'ABS_Y': 0, 
        'ABS_Z': 0, 
        'ABS_RX': 0, 
        'ABS_RY': 0, 
        'ABS_RZ': 0, 
        'ABS_HAT0X': 0, 
        'ABS_HAT0Y': 0,
    }

    buttons = {
        'BTN_SOUTH': 0,
        'BTN_EAST': 0,
        'BTN_NORTH': 0,
        'BTN_WEST': 0,
        'BTN_TL': 0,
        'BTN_TR': 0,
        'BTN_SELECT': 0,
        'BTN_START': 0,
        'BTN_MODE': 0,
        'BTN_THUMBL': 0,
        'BTN_THUMBR': 0,
    }

    axis_info = {}

    def __init__(self, path='/dev/input/by-id/usb-Microsoft_Controller_3039363431313739383635393433-event-joystick'):
        try:
            self.fd_ = open(path, 'rb')
            fcntl.fcntl(self.fd_, fcntl.F_SETFL, os.O_NONBLOCK)
            self.dev_ = libevdev.Device(self.fd_)
            for e in self.dev_.evbits[libevdev.EV_ABS]:
                self.axis_info[e.name] = self.dev_.absinfo[e]

        except IOError as e:
            import errno
            if e.errno == errno.EACCES:
                print("Insufficient permissions to access {}".format(path))
            elif e.errno == errno.ENOENT:
                print("Device {} does not exist".format(path))
            else:
                raise e

    def update_deadzone(self, val):
        ai = libevdev.InputAbsInfo(flat=val)
        self.dev_.absinfo[libevdev.EV_ABS.ABS_X] = ai


    def poll(self):
        try:
            for event in self.dev_.events():
                if event.matches(libevdev.EV_ABS):
                    self.axes[event.code.name] = event.value
                elif event.matches(libevdev.EV_KEY):
                    self.buttons[event.code.name] = event.value
        except libevdev.EventsDroppedException:
            print('synching')
            for sync_event in self.dev_.sync():
                if sync_event.matches(libevdev.EV_ABS):
                    self.axes[sync_event.code.name] = sync_event.value
                if sync_event.matches(libevdev.EV_KEY):
                    self.buttons[sync_event.code.name] = sync_event.value
        except:
            raise Exception('polling failure')

    # to get x' in [a, b],
    # x'  = (b - a) * ( (x - x_min) / (x_max - x_min) ) + a
    def steer(self, low=-1, high=1):
        x_val = self.axes['ABS_X']
        x_flat = self.dev_.absinfo[libevdev.EV_ABS.ABS_X].flat
        x_min = self.dev_.absinfo[libevdev.EV_ABS.ABS_X].minimum
        x_max = self.dev_.absinfo[libevdev.EV_ABS.ABS_X].maximum

        return (high - low) * (x_val - x_min) / (x_max - x_min) + low

    def throttle(self, low=-1, high=1):
        f_val = self.axes['ABS_RZ']
        f_min = self.dev_.absinfo[libevdev.EV_ABS.ABS_RZ].minimum
        f_max = self.dev_.absinfo[libevdev.EV_ABS.ABS_RZ].maximum

        r_val = self.axes['ABS_Z']
        r_min = self.dev_.absinfo[libevdev.EV_ABS.ABS_Z].minimum
        r_max = self.dev_.absinfo[libevdev.EV_ABS.ABS_Z].maximum

        f = (high - 0) * (f_val - f_min) / (f_max - f_min) + low
        r = (0 - low) * (r_val - r_min) / (r_max - r_min) + low

        return f - r


def main():
    xbox = XBox()


if __name__ == "__main__":
    main()