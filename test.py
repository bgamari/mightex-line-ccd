import matplotlib
matplotlib.use('gtkagg')
import matplotlib.pyplot as pl
import gobject
from camera import *

c = LineCamera()
print(c.get_firmware_ver())
print(c.get_device_info())
c.set_work_mode(WorkMode.NORMAL)
c.set_exposure_time(0x0004)

def read_frame():
    try: frame = c.get_frame()
    except: return None
    if frame is None: return
    return frame[1] - np.mean(frame[0])

fig = pl.figure()
ax = fig.add_subplot(111)
curve, = ax.plot([], [])
ax.set_ylim(-10, 0xffff+10)
#ax.set_xlim(0, 3648)
ax.set_xlim(0, 7680/2)

def on_idle():
    data = read_frame()
    if data is None: return True
    x = np.arange(len(data))
    curve.set_data(x, data)
    fig.canvas.draw()
    return True
    
read_frame()
gobject.idle_add(on_idle)
pl.show()

