'''

'''
import os
import math

def setEncoderDesc(config, level=''):
    config['max_keyframe_distance'] = int(config['gop'] * config['framerate'])
    # get svc bitrate
    if level:
        config['bitrate'] = config['bitrate' + level]
    #
    # vp8/vp9
    if config['codec'] in ['vp8', 'vp9']:
        config['cpu_count'] = os.cpu_count()
        config['video_rtppay_options'] = 'picture-id-mode=2'
        config['token_partitions'] = min(math.ceil(math.sqrt(config['cpu_count'])), 8)
        # hardware encoder
        if config['hw'] == 'vaapi' and (not level or level == '_2'):
            config['video_encoder_desc' + level] = 'vaapi%(codec)senc \
                bitrate=%(bitrate)d \
                rate-control=cbr \
                keyframe-period=%(max_keyframe_distance)d \
                quality-level=7' %config
        # software encoder
        else:
            config['video_encoder_desc' + level] = '''%(codec)senc \
                lag-in-frames=0 \
                error-resilient=default \
                deadline=1 \
                cpu-used=-5 \
                end-usage=cbr \
                target-bitrate=%(bitrate)d000 \
                min-quantizer=5 \
                max-quantizer=56 \
                undershoot=100 \
                overshoot=15 \
                dropframe-threshold=50 \
                resize-allowed=false \
                buffer-initial-size=500 \
                buffer-optimal-size=600 \
                buffer-size=1000 \
                max-intra-bitrate=100 \
                keyframe-mode=auto \
                keyframe-max-dist=%(max_keyframe_distance)d \
                token-partitions=%(token_partitions)d \
                threads=%(cpu_count)d \
                static-threshold=1 \
                noise-sensitivity=1''' %config
    # h264
    else:
        config['video_rtppay_options'] = ''
        # vaapi hardware encoder
        if config['hw'] == 'vaapi' and (not level or level == '_2'):
            config['video_encoder_desc' + level] = 'vaapi%(codec)senc \
                bitrate=%(bitrate)d \
                rate-control=cbr \
                keyframe-period=%(max_keyframe_distance)d \
                quality-level=7 \
                ! video/x-%(codec)s,profile=high' %config
        # nv hardware encoder
        elif config['hw'] == 'nv': # and (not level or level == '_2'):
            config['video_encoder_desc' + level] = 'nvh264enc \
                preset=low-latency \
                bitrate=%(bitrate)d \
                rc-mode=cbr \
                gop-size=%(max_keyframe_distance)d \
                ! h264parse \
                ! video/x-h264,stream-format=avc' %config
        # software encoder
        elif config['codec'] == 'h264':
            config['video_encoder_desc' + level] = 'x264enc \
                pass=cbr \
                bitrate=%(bitrate)d \
                key-int-max=%(max_keyframe_distance)d \
                speed-preset=veryfast \
                tune=zerolatency \
                vbv-buf-capacity=0 \
                ! video/x-h264,profile=high' %config #option-string="no-sliced-threads"
        elif config['codec'] == 'h265':
            config['video_encoder_desc' + level] = 'x265enc \
                pass=cbr \
                bitrate=%(bitrate)d \
                key-int-max=%(max_keyframe_distance)d \
                speed-preset=veryfast \
                tune=zerolatency \
                vbv-buf-capacity=0' %config #option-string="no-sliced-threads"
    #
    if config.get('text_overlay', ''):
        config['font_size'] = 20
        s = '''textoverlay 
            font-desc="Mono %(font_size)d" \
            text="%(text_overlay)s" \
            halignment=left \
            valignment=top \
            shaded-background=true \
            xpad=0 \
            ypad=0 \
            auto-resize=false ! ''' %config
        config['video_encoder_desc' + level] = s + config['video_encoder_desc' + level]
    if config.get('time_overlay', ''):
        config['font_size'] = 20
        s = '''timeoverlay \
            font-desc="Mono %(font_size)d" \
            halignment=right \
            valignment=top \
            shaded-background=true \
            xpad=0 \
            ypad=0 \
            auto-resize=false ! ''' %config
        config['video_encoder_desc' + level] = s + config['video_encoder_desc' + level]
    if config.get('clock_overlay', ''):
        config['font_size'] = config['height'] / 10
        s = '''textoverlay \
            name=clock_overlay \
            font-desc="Mono %(font_size)d" \
            halignment=left \
            valignment=bottom \
            shaded-background=true \
            xpad=5 \
            ypad=5 \
            auto-resize=false ! ''' %config
        config['video_encoder_desc' + level] = s + config['video_encoder_desc' + level]

def getProducerPipelineDesc(config):
    if config['kind'] == 'audio':
        return '''
rtpbin name=rtpbin latency=200 rtp-profile=avpf

audioconvert name=src
    ! audioresample
    ! audiorate
    ! audio/x-raw,format=S16LE,rate=48000,channels=2
    ! %(codec)senc bitrate=%(bitrate)d000 inband-fec=1
    ! rtp%(codec)spay ssrc=%(ssrc)d pt=%(pt)d mtu=1400
    ! rtprtxqueue name=rtprtxqueue max-size-time=400 max-size-packets=0
    ! rtpbin.send_rtp_sink_0

rtpbin.send_rtp_src_0
    ! udpsink name=rtp_udpsink host=%(ip)s port=%(rtpPort)d

rtpbin.send_rtcp_src_0
    ! udpsink name=rtcp_udpsink host=%(ip)s port=%(rtcpPort)d sync=false async=false
''' %config
    else:
        if config.get('simulcast', False):
            setEncoderDesc(config, '_0')
            setEncoderDesc(config, '_1')
            setEncoderDesc(config, '_2')
            return '''
rtpbin name=rtpbin latency=200 rtp-profile=avpf

videoconvert name=src
    ! tee name=tee

funnel name=rtp_funnell
    ! udpsink name=rtp_udpsink host=%(ip)s port=%(rtpPort)d

funnel name=rtcp_funnell
    ! udpsink name=rtcp_udpsink host=%(ip)s port=%(rtcpPort)d sync=false async=false

tee.
    ! videoscale
    ! video/x-raw,width=%(width_0)d,height=%(height_0)d
    ! %(video_encoder_desc_0)s
    ! rtp%(codec)spay ssrc=%(ssrc_0)d pt=%(pt)d %(video_rtppay_options)s mtu=1400
    ! rtprtxqueue name=rtprtxqueue_0 max-size-time=1000 max-size-packets=0
    ! rtpbin.send_rtp_sink_0

rtpbin.send_rtp_src_0
    ! rtp_funnell.sink_0

rtpbin.send_rtcp_src_0
    ! rtcp_funnell.sink_0

tee.
    ! videoscale
    ! video/x-raw,width=%(width_1)d,height=%(height_1)d
    ! %(video_encoder_desc_1)s
    ! rtp%(codec)spay ssrc=%(ssrc_1)d pt=%(pt)d %(video_rtppay_options)s mtu=1400
    ! rtprtxqueue name=rtprtxqueue_1 max-size-time=1000 max-size-packets=0
    ! rtpbin.send_rtp_sink_1

rtpbin.send_rtp_src_1
    ! rtp_funnell.sink_1
    
rtpbin.send_rtcp_src_1
    ! rtcp_funnell.sink_1

tee.
    ! videoscale
    ! video/x-raw,width=%(width_2)d,height=%(height_2)d
    ! %(video_encoder_desc_2)s
    ! rtp%(codec)spay ssrc=%(ssrc_2)d pt=%(pt)d %(video_rtppay_options)s mtu=1400
    ! rtprtxqueue name=rtprtxqueue_2 max-size-time=1000 max-size-packets=0
    ! rtpbin.send_rtp_sink_2

rtpbin.send_rtp_src_2
    ! rtp_funnell.sink_2
    
rtpbin.send_rtcp_src_2
    ! rtcp_funnell.sink_2

''' %config

        else:
            setEncoderDesc(config)
            return '''
rtpbin name=rtpbin latency=200 rtp-profile=avpf

videoconvert name=src
    ! %(video_encoder_desc)s
    ! rtp%(codec)spay ssrc=%(ssrc)d pt=%(pt)d %(video_rtppay_options)s mtu=1400
    ! rtprtxqueue name=rtprtxqueue max-size-time=1000 max-size-packets=0
    ! rtpbin.send_rtp_sink_0

rtpbin.send_rtp_src_0
    ! udpsink name=rtp_udpsink host=%(ip)s port=%(rtpPort)d

rtpbin.send_rtcp_src_0
    ! udpsink name=rtcp_udpsink host=%(ip)s port=%(rtcpPort)d sync=false async=false
''' %config

def getConsumerPipelineDesc(config):
    if config['codec'] == 'h264':
        config['decoder'] = 'avdec_h264'
    else:
        config['decoder'] = config['codec'] + 'dec'
    return '''
rtpbin name=rtpbin latency=200 rtp-profile=avpf do-retransmission=true

udpsrc name=rtp_udpsrc caps=application/x-rtp,media=%(kind)s,clock-rate=%(clockRate)d,encoding-name=%(encoding_name)s,payload=%(pt)d
    ! rtpbin.recv_rtp_sink_0

rtpbin.
    ! rtp%(codec)sdepay 
    ! %(decoder)s name=sink

rtpbin.send_rtcp_src_0 
    ! udpsink name=rtcp_udpsink host=%(ip)s port=%(rtcpPort)d sync=false async=false 

udpsrc name=rtcp_udpsrc 
    ! rtpbin.recv_rtcp_sink_0 
''' %config
