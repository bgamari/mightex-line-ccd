#!/usr/bin/python

import numpy as np
from numpy import exp, sqrt, pi
from camera import *
from microscope import ButtonfulMicroscope
import wx
from matplotlib.backends.backend_wx import _load_bitmap
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.backends.backend_wxagg import NavigationToolbar2Wx as Toolbar
from matplotlib.figure import Figure

class FeedbackLoop(object):
    def get_response(self, err):
        raise UnimplementedError()

class PLoop(FeedbackLoop):
    def __init__(self, gain, max_error, dy):
        self.gain = gain
        self.max_error = max_error
        self.dy = dy
        
    def get_response(self, err):
        if err > self.max_error:
            return self.gain * err
        else:
            return 0

class PILoop(FeedbackLoop):
    def __init__(self, p, i, n=100):
        self.p = p
        self.i = i
        self.history = []
        self.n = n

    def get_response(self, err):
        self.history.append(err)
        self.history = self.history[-self.n:]
        return -self.p * err - self.i * np.mean(self.history)
        
class PlotPanel(wx.Panel):
    ON_START_STOP = wx.NewId()
    ON_ACQUIRE_BACKGROUND = wx.NewId()
    ON_CLEAR_BACKGROUND = wx.NewId()
    ON_SETPOINT = wx.NewId()
    
    def __init__(self, parent, camera, microscope, fb_loop):
        wx.Panel.__init__(self, parent, -1)

        self.fig = Figure((5,4), 75)
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        self.toolbar = Toolbar(self.canvas)
        
        self.toolbar.AddSimpleTool(self.ON_START_STOP,
                                   _load_bitmap('stock_left.xpm'),
                                   'Start/stop', 'Start/stop feedback')
        wx.EVT_TOOL(self.toolbar, self.ON_START_STOP, self.OnStartStop)

        self.toolbar.AddSimpleTool(self.ON_ACQUIRE_BACKGROUND,
                                   _load_bitmap('stock_right.xpm'),
                                   'Acquire background', 'Acquire background')
        wx.EVT_TOOL(self.toolbar, self.ON_ACQUIRE_BACKGROUND, self.OnAcquireBackground)
        
        self.toolbar.AddSimpleTool(self.ON_CLEAR_BACKGROUND,
                                   _load_bitmap('stock_right.xpm'),
                                   'Clear background', 'Clear background')
        wx.EVT_TOOL(self.toolbar, self.ON_CLEAR_BACKGROUND, self.OnClearBackground)

        self.toolbar.AddSimpleTool(self.ON_SETPOINT,
                                   _load_bitmap('stock_left.xpm'),
                                   'setpoint', 'Set setpoint')
        wx.EVT_TOOL(self.toolbar, self.ON_SETPOINT, self.OnSetSetpoint)
        
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)
        self.SetSizer(sizer)
        self.Fit()        

        self.camera = camera
        self.microscope = microscope
        
        im = self.read_frame()
        self.image_sz = len(im)
        self.background = np.zeros(self.image_sz)

        self.feedback_period = 200 # milliseconds
        self.fb_loop = fb_loop
        self.oversamples = 10
        self.image_n = 0
        self.set_smoothing_window(0)
        self.init_plot_data()

        self.update_timer = wx.PyTimer(self.update)
        self.update_timer.Start(100, False)

        self.feedback_timer = wx.PyTimer(self.feedback)

    def set_smoothing_window(self, sigma):
        window_size = 4*sigma
        convolved_size = self.image_sz-window_size+1
        if sigma == 0:
            self.kernel = None
            convolved_size = self.image_sz
        else:
            self.kernel = exp(-np.arange(window_size)**2 / sigma**2) / sqrt(2*pi) / sigma
        self.images = np.zeros((convolved_size, self.oversamples))

    def read_frame(self):
        frame = None
        for i in range(5): # Try five times to get frame
            try: frame = self.camera.get_frame()
            except: pass
        if frame is None:
            raise RuntimeError('Failed to acquire frame')
        return frame[1] - np.mean(frame[0])
        
    def init_plot_data(self):
        self.read_frame()
        
        self.ax1 = self.fig.add_subplot(211)
        self.curve, = self.ax1.plot([], [])
        self.ax1.set_ylim(-10, 0xffff+10)
        self.ax1.set_xlim(0, 3648)
        self.setpoint_line = self.ax1.axvline(x=0, color='r')
        self.max_line = self.ax1.axvline(x=0, color='k')

        self.ax2 = self.fig.add_subplot(212)
        self.maxima = []
        self.max_curve, = self.ax2.plot(self.maxima)
        self.ax2.set_xlim(0,2000)
        self.ax2.set_ylim(1000,2000)

    def update(self):
        data = self.read_frame() - self.background
        if self.kernel is not None:
            data = np.convolve(data, self.kernel, 'valid')
        self.images[:,self.image_n] = data
        data = np.mean(self.images, axis=1)
        self.image_n = (self.image_n + 1) % self.oversamples
        x = np.arange(len(data))
        self.curve.set_data(x, data)

        max_x = np.argmax(data)
        self.maxima.append(max_x)
        self.maxima = self.maxima[:1000]
        n = len(self.maxima)
        self.max_curve.set_data(np.arange(n), self.maxima)
        self.ax2.relim()
        self.ax2.autoscale_view(scaley=False)

        self.fig.canvas.draw()   

    def feedback(self):
        max_x = self.maxima[-1]
        self.max_line.set_xdata([max_x, max_x])
        error = max_x - self.setpoint
        resp = self.fb_loop.get_response(error)
        print 'moving', resp
        self.microscope.move(resp)
        
    def GetToolBar(self):
        return self.toolbar

    def OnStartStop(self, evt):
        if self.feedback_timer.IsRunning():
            print 'stop'
            self.feedback_timer.Stop()
        else:
            print 'start'
            self.feedback_timer.Start(self.feedback_period)

    def OnAcquireBackground(self, evt):
        print 'acquire background'
        self.background = self.read_frame()

    def OnSetSetpoint(self, evt):
        self.setpoint = self.maxima[-1]
        self.setpoint_line.set_xdata([self.setpoint, self.setpoint])
        print 'setpoint'

    def OnClearBackground(self, evt):
        print 'clear background'
        self.background[:] = 0
        
    def onEraseBackground(self, evt):
        pass

m = ButtonfulMicroscope()
print 'Connected to microscope: %s' % m.get_unit()

c = LineCamera()
print('Firmware version', c.get_firmware_ver())
print('Device version', c.get_device_info())
c.set_work_mode(WorkMode.NORMAL)
c.set_exposure_time(10)

fb_loop = PILoop(0.2, 0)

if __name__ == '__main__':
    app = wx.PySimpleApp()
    frame = wx.Frame(None, -1, 'Autofocus')
    plotter = PlotPanel(frame, c, m, fb_loop)
    frame.Show()
    app.MainLoop()


