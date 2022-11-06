import sys
import numpy as np
import copy
import threading
import ctypes
import time
import cv2
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')
from gi.repository import Gst


# 이것은 클라우드 서버에서 작동되는 것.




class RTSP_image(object):
    def __init__(self, rtsp_src):
        # initialize GStreamer
        Gst.init(sys.argv)

        # image from opencv
        self.opencv_image = None

        self.rtsp_src = rtsp_src
        self.pipeline = None  # Gstreamer pipeline

    def initElements(self):
        # create empty pipeline
        self.pipeline = Gst.Pipeline.new("rtsp-pipeline")

        # Make elements
        self.source = Gst.ElementFactory.make("rtspsrc", "source")
        self.depay = Gst.ElementFactory.make("rtph264depay", "depay")
        self.parser = Gst.ElementFactory.make("h264parse", "parse")
        self.decoder = Gst.ElementFactory.make("avdec_h264", "decoder")
        self.video_convert = Gst.ElementFactory.make("videoconvert", "converter")

        # Set property
        self.source.set_property("latency", 0)

        # Get Sample
        def gst_to_opencv(sample):
            gst_buffer = sample.get_buffer()
            caps = sample.get_caps()
            # gst_buffer size = 1280 * 720 * 3 = 2,764,800
            # gst_buffer size = 1920 * 1080 * 3 = 6,220,800
            image = np.ndarray((caps.get_structure(0).get_value('height'),
                                caps.get_structure(0).get_value('width'), 3),
                               buffer=gst_buffer.extract_dup(0, gst_buffer.get_size()), dtype=np.uint8)
            return image

        def new_buffer(sink, data):
            sample = sink.emit("pull-sample")
            image = gst_to_opencv(sample)
            self.opencv_image = image
            return Gst.FlowReturn.OK

        self.sink = Gst.ElementFactory.make("appsink", "sink")
        caps = Gst.caps_from_string("video/x-raw,format=(string) BGR")
        self.sink.set_property("caps", caps)
        self.sink.set_property("emit-signals", True)
        self.sink.connect("new-sample", new_buffer, self.sink)

        # check Elements
        if (not self.pipeline or not self.source or not self.depay \
                or not self.parser or not self.decoder or not self.video_convert \
                or not self.sink):
            print("ERROR: Could not create all elements")
            sys.exit(1)

        # build the pipeline. we are NOT linking the source at this point.
        # will do it later
        self.pipeline.add(self.source)
        self.pipeline.add(self.depay)
        self.pipeline.add(self.parser)
        self.pipeline.add(self.decoder)
        self.pipeline.add(self.video_convert)
        self.pipeline.add(self.sink)

        # create bus
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message::error", self.on_error)
        self.bus.connect("message::eos", self.on_eos)
        self.bus.connect("message::state_changed", self.on_state_changed)

    def on_error(self, bus, msg):
        err, dbg = msg.parse_error()
        print("ERROR:", msg.src.get_name(), " ", err.message)
        if dbg:
            print("debugging info:", dbg)

    def on_eos(self, bus, msg):
        print("End-Of-Stream reached")
        self.pipeline.set_state(Gst.State.READY)

    def on_state_changed(self, bus, msg):
        # we are only interested in STATE_CHANGED messages from
        # the pipeline
        if msg.src == self.pipeline:
            old_state, new_state, pending_state = msg.parse_state_changed()
            print("Pipeline state changed from {0:s} to {1:s}".format(
                Gst.Element.state_get_name(old_state),
                Gst.Element.state_get_name(new_state)))

    def linkElements(self):
        # link elements
        ret = self.depay.link(self.parser)
        ret = ret and self.parser.link(self.decoder)
        ret = ret and self.decoder.link(self.video_convert)
        ret = ret and self.video_convert.link(self.sink)

        if not ret:
            print("link failed")
            sys.exit(1)

        # set the Location to play
        self.source.set_property("location", self.rtsp_src)

        # connect to the pad-added signal
        self.source.connect("pad-added", self.on_pad_added)

        # start playing
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("ERROR: Unable to set the pipeline to the playing state")
            sys.exit(1)

    def playpipeline(self):
        self.initElements()
        self.linkElements()

    def start(self):
        if not self.pipeline:
            self.playpipeline()
        else:
            current_state = self.pipeline.get_state(Gst.CLOCK_TIME_NONE).state
            if current_state == Gst.State.PLAYING:
                raise Exception("ALREADY PLAYING")
            elif current_state == Gst.State.READY:
                ret = self.pipeline.set_state(Gst.State.PLAYING)
                if (ret != Gst.StateChangeReturn.SUCCESS):
                    raise Exception("FAIL TO PLAY: {}".format(current_state))
            else:
                self.playpipeline()

    def pause(self):
        if self.pipeline:
            current_state = self.pipeline.get_state(Gst.CLOCK_TIME_NONE).state
            if current_state == Gst.State.NULL:
                raise Exception("FAIL TO PAUSE: {}".format(current_state))
            ret = self.pipeline.set_state(Gst.State.PAUSED)
            if ret == Gst.StateChangeReturn.FAILURE:
                raise Exception("FAIL TO PAUSE: {}".format(current_state))

    def stop(self):
        print("STOP STREAMING")
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            self.opencv_image = None



    # handler for the pad-added signal
    def on_pad_added(self, src, new_pad):
        print(
            "Received new pad '{0:s}' from '{1:s}'".format(
                new_pad.get_name(),
                src.get_name()))

        # check the new pad's type
        new_pad_caps = new_pad.get_current_caps()
        new_pad_struct = new_pad_caps.get_structure(0)
        new_pad_type = new_pad_struct.get_name()

        if new_pad_type.startswith("application/x-rtp"):
            sink_pad = self.depay.get_static_pad("sink")
        else:
            print("It has type '{0:s}' which is not rtp video. Ignoring.".format(new_pad_type))
            return

        # if our converter is already linked, we have nothing to do here
        if (sink_pad.is_linked()):
            print("We are already linked. Ignoring.")
            return

        # attempt the link
        ret = new_pad.link(sink_pad)

        if not ret == Gst.PadLinkReturn.OK:
            print("Type is '{0:s}' but link failed".format(new_pad_type))
        else:
            print("Link succeeded (type '{0:s}')".format(new_pad_type))

        return

class Gstreamer_thread2(threading.Thread):
    def __init__(self, rtsp):
        threading.Thread.__init__(self)
        self.gst_thread = RTSP_image(rtsp)

    def run(self):
        self.gst_thread.start()

    def get_snapshot(self):
        snapshot = copy.deepcopy(self.gst_thread.opencv_image)
        return snapshot

    def get_id(self):
        # returns id of the respective thread
        if hasattr(self, '_thread_id'):
            return self._thread_id
        for id, thread in threading._active.items():
            if thread is self:
                return id

    def terminate_thread(self):
        self.gst_thread.stop()
        thread_id = self.get_id()
        response = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, \
                                                              ctypes.py_object(SystemExit))
        if response > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
            print("Exit failed")

if __name__ == "__main__":
    #rtsp 주소 전체를 parameter로 준다고 가정
    test_rtspsrc = "rtsp://admin:mdcl7726@192.168.2.4:554/Streaming/Channels/101/"

    test123 = Gstreamer_thread2(test_rtspsrc)
    test123.start()
    time.sleep(2)
    temp = test123.get_snapshot()
    time.sleep(10)      #종료조건은 일단, 10초 후 종료한다고 가정
    test123.terminate_thread()
    test123.join()

    cv2.imshow("test",temp)
    cv2.imwrite("test.jpeg",temp)