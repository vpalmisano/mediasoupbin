'''

'''
import os, sys
import math
import json
from datetime import datetime

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
gi.require_version('GstBase', '1.0')
from gi.repository import GstBase
from gi.repository import GObject, GLib, Gio

Gst.init(None)

#
from lib.mediasoup import MediaSoup
from lib.pipelines import getProducerPipelineDesc, getConsumerPipelineDesc
from lib.signaling import DefaultSignaling

DEFAULT_AUDIO_CONFIG = {
    'codec': 'opus',
    'bitrate': 128,
    'pt': 96,
}

DEFAULT_VIDEO_CONFIG = {
    'codec': 'vp8',
    'bitrate': 2000,
    'hw': '',
    'gop': 9999,
    'pt': 97,
}

class MediaSoupBin(Gst.Bin):
    __name__ = 'MediaSoupBin'

    __gstmetadata__ = ('MediaSoupBin', 'Bin', 'MediaSoupBin', 'Vittorio Palmisano <vpalmisano@gmail.com>')

    __gsttemplates__ = (
        Gst.PadTemplate.new(
            'audio_sink',
            Gst.PadDirection.SINK,
            Gst.PadPresence.REQUEST,
            Gst.Caps.new_empty_simple('audio/x-raw'),
        ),
        Gst.PadTemplate.new(
            'video_sink',
            Gst.PadDirection.SINK,
            Gst.PadPresence.REQUEST,
            Gst.Caps.new_empty_simple('video/x-raw'),
        ),
        Gst.PadTemplate.new(
            'audio_src',
            Gst.PadDirection.SRC,
            Gst.PadPresence.REQUEST,
            Gst.Caps.new_empty_simple('audio/x-raw'),
        ),
        Gst.PadTemplate.new(
            'video_src',
            Gst.PadDirection.SRC,
            Gst.PadPresence.REQUEST,
            Gst.Caps.new_empty_simple('video/x-raw'),
        ),
    )

    signaling = GObject.Property(type=object, blurb='Signaling object')

    app_data = GObject.Property(type=str, blurb='appData in JSON format', default='{}')

    # producer
    server_ip = GObject.Property(type=str, blurb='force server ip', 
        default='')
    audio_codec = GObject.Property(type=str, blurb='producer audio codec', 
        default=DEFAULT_AUDIO_CONFIG['codec'])
    audio_bitrate = GObject.Property(type=int, blurb='producer audio bitrate (kbps)', 
        default=DEFAULT_AUDIO_CONFIG['bitrate'], minimum=16, maximum=256)

    video_codec = GObject.Property(type=str, blurb='producer video codec', 
        default=DEFAULT_VIDEO_CONFIG['codec'])
    video_bitrate = GObject.Property(type=int, blurb='producer video bitrate (kbps)', 
        default=DEFAULT_VIDEO_CONFIG['bitrate'], minimum=128, maximum=20000)
    hw = GObject.Property(type=str, blurb='use hardware encoder for producer ("vaapi"|"nv")', default='')
    gop = GObject.Property(type=float, blurb='producer video GOP size (s)', 
        default=DEFAULT_VIDEO_CONFIG['gop'], minimum=0.01, maximum=999999.)
    simulcast = GObject.Property(type=bool, blurb='enable simulcast', default=False)

    text_overlay = GObject.Property(type=str, blurb='text overlay', default='')
    time_overlay = GObject.Property(type=bool, blurb='time overlay', default=False)
    clock_overlay = GObject.Property(type=bool, blurb='clock overlay', default=False)
    
    # consumer
    local_ip = GObject.Property(type=str, blurb='local ip address', default='127.0.0.1')

    __gsignals__ = {
        'producer-added': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
        'consumer-added': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
    }

    def __init__(self):
        GObject.__init__(self)
        Gst.Bin.__init__(self)
        #
        self.signaling = None
        self.mediasoup = None

    def do_request_new_pad(self, templ, name, caps):
        Gst.info('%s do_request_new_pad name_template=%s direction=%d name=%s caps=%s' %(
            self.name, templ.name_template, templ.direction, name, caps))
        # create a default signaling
        if not self.signaling:
            try:
                self.signaling = DefaultSignaling()
            except Exception as e:
                Gst.error('DefaultSignaling error: %s' %e)
                sys.exit(-1)
        # create MediaSoup instance
        if not self.mediasoup:
            self.mediasoup = MediaSoup(self.signaling)
        # create tmp pad
        pad = Gst.Pad.new_from_template(templ, templ.name_template+'_tmp')
        self.add_pad(pad)
        # create ghost pad
        ghostPad = Gst.GhostPad.new_from_template(templ.name_template, pad, templ)
        ghostPad.set_active(True)
        self.add_pad(ghostPad)
        # producer
        if templ.direction == Gst.PadDirection.SINK:
            # connect tmp pad chain
            def chain_function(pad, parent, buf):
                Gst.debug('%s chain_function caps: %s pts: %f' %(pad.name, pad.get_current_caps(), buf.pts*1e-9))
                caps = pad.get_current_caps()
                if caps:
                    structure = caps.get_structure(0)
                    Gst.info('%s event_function caps=%s' %(pad.name, caps))
                    kind = structure.get_name().split('/')[0]
                    appData = json.loads(self.app_data)
                    # producer
                    config = {
                        'kind': kind,
                        'producerId': structure.get_string('producer-id'),
                        'text_overlay': self.text_overlay,
                        'time_overlay': self.time_overlay,
                        'clock_overlay': self.clock_overlay,
                    }
                    if kind == 'audio':
                        config.update(DEFAULT_AUDIO_CONFIG)
                        config['codec'] = self.audio_codec
                        config['bitrate'] = self.audio_bitrate
                    else:
                        config.update(DEFAULT_VIDEO_CONFIG)
                        config['server_ip'] = self.server_ip
                        config['codec'] = self.video_codec
                        config['bitrate'] = self.video_bitrate
                        config['hw'] = self.hw
                        config['gop'] = self.gop
                        config['simulcast'] = self.simulcast
                        config['width'] = structure['width']
                        config['height'] = structure['height']
                        config['framerate'] = structure['framerate'].num or 30
                        appData['width'] = config['width']
                        appData['height'] = config['height']
                        appData['framerate'] = config['framerate']
                    appData['maxBitrate'] = config['bitrate']
                    self.mediasoup.produce(config, appData, self._produce_done, self._on_error, self._on_producer_removed, ghostPad)
                return Gst.FlowReturn.OK
            pad.set_chain_function_full(chain_function)
        # consumer
        elif templ.direction == Gst.PadDirection.SRC:
            # use the peer caps
            def on_pad_linked(pad, peer):
                caps = pad.peer_query_caps()
                structure = caps.get_structure(0)
                Gst.info('%s on_pad_linked %s' %(pad.name, caps))
                # create listen rtp/rtcp sockets
                recv_rtp_socket = Gio.Socket.new(Gio.SocketFamily.IPV4, 
                    Gio.SocketType.DATAGRAM, Gio.SocketProtocol.UDP)
                rtp_socket_address = Gio.InetSocketAddress.new_from_string(self.local_ip, 0)
                recv_rtp_socket.bind(rtp_socket_address, False)
                #
                recv_rtcp_socket = Gio.Socket.new(Gio.SocketFamily.IPV4, 
                    Gio.SocketType.DATAGRAM, Gio.SocketProtocol.UDP)
                rtcp_socket_address = Gio.InetSocketAddress.new_from_string(self.local_ip, 0)
                recv_rtcp_socket.bind(rtcp_socket_address, False)
                #
                config = {
                    'producerId': structure.get_string('producer-id'),
                    'local_ip': self.local_ip,
                    'local_rtpPort': recv_rtp_socket.get_local_address().get_port(),
                    'local_rtcpPort': recv_rtcp_socket.get_local_address().get_port(),
                }
                appData = json.loads(self.app_data)
                self.mediasoup.consume(config, appData, self._consume_done, self._on_error, self._on_producer_removed,
                    ghostPad, recv_rtp_socket, recv_rtcp_socket)
            ghostPad.connect('linked', on_pad_linked)
        #
        return ghostPad

    def do_state_changed(self, oldstate, newstate, pending):
        Gst.debug('%s do_state_changed oldstate=%s newstate=%s pending=%s' %(self.name, oldstate, newstate, pending))
        if oldstate in (Gst.State.READY, Gst.State.PAUSED) and newstate == Gst.State.NULL:
            if self.mediasoup:
                self.mediasoup.stop()
                self.mediasoup = None
            if self.signaling:
                self.signaling.stop()
                self.signaling = None

    def _on_producer_removed(self, removedProducer):
        Gst.error('%s producer %s removed' %(self.name, removedProducer))
        err = 'Producer %s removed' %(removedProducer['id'])
        self.bus.post(Gst.Message.new_error(self, GLib.Error(err), err))

    def _on_error(self, err, *args):
        Gst.error('%s error %s' %(self.name, err))
        self.bus.post(Gst.Message.new_error(self, GLib.Error(err), err))

    #
    def _produce_done(self, config, ghostPad):
        Gst.info('%s _produce_done %s' %(self.name, config))
        #
        desc = getProducerPipelineDesc(config)
        Gst.info('%s _produce_done desc=%s' %(self.name, desc))
        bin = Gst.parse_bin_from_description(desc, False)
        self.add(bin)
        #
        # handle time display
        if self.clock_overlay:
            clock_overlay = bin.get_by_name('clock_overlay')
            def on_v_encoder_buffer(pad, info):
                clock_overlay.set_property('text', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f UTC'))
                return Gst.PadProbeReturn.OK
            clock_overlay.get_static_pad('video_sink').add_probe(Gst.PadProbeType.BUFFER, on_v_encoder_buffer)
        #
        bin.set_state(Gst.State.PAUSED)
        # create a udpsrc element with the same rtcp_udpsink socket
        rtcp_socket = bin.get_by_name('rtcp_udpsink').get_property('used-socket')
        rtcp_udpsrc = Gst.ElementFactory.make('udpsrc')
        rtcp_udpsrc.set_property('name', 'rtcp_udpsrc')
        rtcp_udpsrc.set_property('socket', rtcp_socket)
        bin.add(rtcp_udpsrc)
        #recv_rtcp_sink_0 = rtpbin.get_request_pad('recv_rtcp_sink_0')
        #rtcp_udpsrc.get_static_pad('src').link(recv_rtcp_sink_0)
        #                        
        # rtcp_udpsrc -> tee --recv_rtcp_sink_0
        #                    `-recv_rtcp_sink_1
        #                    `-recv_rtcp_sink_2
        rtcp_udpsrc_tee = Gst.ElementFactory.make('tee')
        bin.add(rtcp_udpsrc_tee)
        rtcp_udpsrc.link(rtcp_udpsrc_tee)
        #
        rtpbin = bin.get_by_name('rtpbin')
        recv_rtcp_sink_0 = rtpbin.get_request_pad('recv_rtcp_sink_0')
        rtcp_udpsrc_tee.get_request_pad('src_0').link(recv_rtcp_sink_0)
        if config.get('simulcast', False):
            recv_rtcp_sink_1 = rtpbin.get_request_pad('recv_rtcp_sink_1')
            rtcp_udpsrc_tee.get_request_pad('src_1').link(recv_rtcp_sink_1)
            recv_rtcp_sink_2 = rtpbin.get_request_pad('recv_rtcp_sink_2')
            rtcp_udpsrc_tee.get_request_pad('src_2').link(recv_rtcp_sink_2)
        # link source ghost pad
        sink_pad = bin.get_by_name('src').get_static_pad('sink')
        tmp_pad = ghostPad.get_target()
        ghostPad.set_target(sink_pad)
        self.remove_pad(tmp_pad)
        #
        bin.set_state(Gst.State.PLAYING)
        #
        self.emit('producer-added', config['producerId'])

    #
    def _consume_done(self, config, ghostPad, recv_rtp_socket, recv_rtcp_socket):
        Gst.info('%s _consume_done %s' %(self.name, config))
        #
        desc = getConsumerPipelineDesc(config)
        Gst.debug('%s _produce_done desc=%s' %(self.name, desc))
        bin = Gst.parse_bin_from_description(desc, False)
        self.add(bin)
        rtpbin = bin.get_by_name('rtpbin')
        # setup sockets
        bin.get_by_name('rtp_udpsrc').set_property('socket', recv_rtp_socket)
        bin.get_by_name('rtcp_udpsrc').set_property('socket', recv_rtcp_socket)
        #
        # bin.set_state(Gst.State.PAUSED)
        # link ghost pad
        src_pad = bin.get_by_name('sink').get_static_pad('src')
        tmp_pad = ghostPad.get_target()
        ghostPad.set_target(src_pad)
        self.remove_pad(tmp_pad)
        #
        bin.set_state(Gst.State.PLAYING)
        #
        self.emit('consumer-added', config['consumerId'])
        #
        self.mediasoup.resumeConsumer(config['transportId'], config['consumerId'], 
            self._resume_consumer_done, self._on_error, config)
    
    def _resume_consumer_done(self, config):
        Gst.info('%s _resume_consumer_done' %(self.name))

GObject.type_register(MediaSoupBin)
__gstelementfactory__ = ('mediasoupbin_py', Gst.Rank.NONE, MediaSoupBin)
