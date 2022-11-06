import sys
import gi
import threading
import ctypes
import time
gi.require_version('Gst', '1.0')
from gi.repository import Gst

class RTSP_pipeline:
    def __init__(self,rtspsrc):
        Gst.init(sys.argv)
        self.pipeline = None
        self.bus = None
        self.rtspsrc = rtspsrc

    def on_error(self,bus,msg):
        err, dbg = msg.parse_error()
        print("ERROR:", msg.src.get_name(), " ", err.message)
        if dbg:
            print("debugging info:", dbg)
        self.pipeline.set_state(Gst.State.NULL)

    def on_eos(self,bus,msg):
        print("End-Of-Stream reached")
        self.pipeline.set_state(Gst.State.READY)

    def on_state_changed(self,bus,msg):
        # we are only interested in STATE_CHANGED messages from
        # the pipeline
        if msg.src == self.pipeline:
            old_state, new_state, pending_state = msg.parse_state_changed()
            print("Pipeline state changed from {0:s} to {1:s}".format(
                Gst.Element.state_get_name(old_state),
                Gst.Element.state_get_name(new_state)))

    def on_pad_added(self,src, new_pad):
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

    def initElements(self):
        #create empty pipeline
        self.pipeline = Gst.Pipeline.new("rtsp-pipeline")

        # Make elements
        self.source = Gst.ElementFactory.make("rtspsrc", "source")
        self.depay = Gst.ElementFactory.make("rtph264depay", "depay")
        self.parser = Gst.ElementFactory.make("h264parse", "parse")
        self.decoder = Gst.ElementFactory.make("avdec_h264", "decoder")
        self.video_convert = Gst.ElementFactory.make("videoconvert", "converter")
        self.sink = Gst.ElementFactory.make("autovideosink","sink")

        #check Elements
        if not self.source or not self.depay or not self.parser\
            or not self.decoder or not self.video_convert or not self.sink:
            print("ERROR: Could not create all elements")
            sys.exit(1)

        #build the pipeline
        self.pipeline.add(self.source)
        self.pipeline.add(self.depay)
        self.pipeline.add(self.parser)
        self.pipeline.add(self.decoder)
        self.pipeline.add(self.video_convert)
        self.pipeline.add(self.sink)

        #create bus
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::error",self.on_error)
        bus.connect("message::eos",self.on_eos)
        bus.connect("message::state_changed",self.on_state_changed)

    def linkElements(self):
        #link elements
        ret = self.depay.link(self.parser)
        ret = ret and self.parser.link(self.decoder)
        ret = ret and self.decoder.link(self.video_convert)
        ret = ret and self.video_convert.link(self.sink)

        if not ret:
            print("link failed")
            sys.exit(1)

        #set property of pipeline elements
        self.source.set_property("location",self.rtspsrc)
        self.source.connect("pad-added",self.on_pad_added)

        #start playing
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("ERROR: Unable to set the pipeline to the playing state")
            sys.exit(1)


    def start(self):
        if not self.pipeline:
            self.initElements()
            self.linkElements()
        else:
            current_state = self.pipeline.get_state(Gst.CLOCK_TIME_NONE).state
            if current_state == Gst.State.PLAYING:
                raise Exception("ALREADY PLAYING")
            elif current_state == Gst.State.READY:
                ret = self.pipeline.set_state(Gst.State.PLAYING)
                if (ret != Gst.StateChangeReturn.SUCCESS):
                    raise Exception("FAIL TO PLAY: {}".format(current_state))


    def stop(self):
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)

class Gstreamer_thread1(threading.Thread):
    def __init__(self,port):
        threading.Thread.__init__(self)
        self.testGst = RTSP_pipeline(port)

    def run(self):
        self.testGst.start()

    def get_id(self):
        # returns id of the respective thread
        if hasattr(self, '_thread_id'):
            return self._thread_id
        for id, thread in threading._active.items():
            if thread is self:
                return id

    def terminate_thread(self):
        self.testGst.stop()
        thread_id = self.get_id()
        response = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, \
                                                              ctypes.py_object(SystemExit))
        if response > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
            print("Exit failed")


if __name__ == "__main__":
    #rtsp 주소 전체를 parameter로 준다고 가정

    test_rtspsrc = "rtsp://admin:mdcl7726@192.168.2.4:554/Streaming/Channels/101/"

    test123 = Gstreamer_thread1(test_rtspsrc)
    test123.start()
    time.sleep(10)      #종료조건은 일단, 10초 후 종료한다고 가정
    test123.terminate_thread()
    test123.join()
