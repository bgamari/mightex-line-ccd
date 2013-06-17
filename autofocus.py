#!/usr/bin/python

import numpy as np
from numpy import exp, sqrt, pi
import matplotlib.pyplot as pl
from camera import *
import microscope

#m = Microscope()
#print 'Connected to microscope: %s' % m.get_unit()
#m.enable_buttons()

c = LineCamera()
print('Firmware version', c.get_firmware_ver())
print('Device version', c.get_device_info())
c.set_work_mode(WorkMode.NORMAL)
c.set_exposure_time(0x0015)

def read_frame():
    try: frame = c.get_frame()
    except: return None
    if frame is not None:
        return frame[1] - np.mean(frame[0])
    else:
        return None
    
print('move the lens to have only the background on the camera')    
raw_input('press ENTER')

background = None
while background is None:
    background = read_frame()


print('move the lens to have the maximum of signal')
print('you are set on the focus position')
raw_input('press ENTER')

fig = pl.figure()
ax = fig.add_subplot(211)
curve, = ax.plot([], [])
ax.set_ylim(-10, 0xffff+10)
ax.set_xlim(0, 3648)
ax.axvline(x=1824, color='r')

ax = fig.add_subplot(212)
maxima = []
setpoint=read_frame()-background
max_curve, = ax.plot(maxima)
ax.set_xlim(0,2000)
ax.set_ylim(1000,2000)

window_sz = 10
kernel = exp(-np.arange(4*window_sz)**2 / window_sz**2) / sqrt(2*pi) / window_sz

image_sz = 3609
oversamples = 10
images = np.zeros((image_sz, oversamples))
image_n = 0


def update():
    global maxima, image_n, images
    data = read_frame() - background
    data = np.convolve(data, kernel, 'valid')
    images[:,image_n] = data
    data = np.mean(images, axis=1)
    image_n = (image_n + 1) % oversamples
    if data is None: return True
    x = np.arange(len(data))
    curve.set_data(x, data)

    max_x = np.argmax(data)
    maxima.append(max_x)
    maxima = maxima[:1000]
    n = len(maxima)
    max_curve.set_data(np.arange(n), maxima)
    ax.relim()
    ax.autoscale_view(scaley=False)

    fig.canvas.draw()   
    
read_frame()
timer = fig.canvas.new_timer(interval=100)
timer.add_callback(update)
timer.start()
pl.show()

