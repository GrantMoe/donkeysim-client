import time
from controller import XBox 

def steer(c):
    return c.steer()
    
def throttle(c):
    return c.throttle()


def main():
    ctr = XBox()
    ctr.update_deadzone(2000)

    # limit = 1000
    # for i in range(limit):
    while True:
        # print(f'step {i} of {limit}')

        ctr.poll()
        print(f'steering: {steer(ctr)}')
        print(f'throttle: {throttle(ctr)}')

        time.sleep(0.25)


if __name__ == "__main__":
    main()