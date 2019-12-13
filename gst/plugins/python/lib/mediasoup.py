
'''

'''

from lib.custom_log import getLogger
logger = getLogger('MediaSoup')
from random import randint

def getProducerRtpParameters(config):
    if config['kind'] == 'audio':
        config['ssrc'] = randint(10000000, 99999999)
        return {
            'codecs': [{
                'name': config.get('codec', 'opus').upper(),
                'mimeType': 'audio/'+config.get('codec', 'opus').upper(),
                'clockRate': 48000,
                'payloadType': config.get('pt', 96),
                'channels': 2,
                'rtcpFeedback': [
                    { 'type': 'nack' },
                ],
                'parameters': {
                    'useinbandfec': 1,
                    'sprop-stereo': 1
                }
            }],
            'encodings': [{ 'ssrc': config['ssrc'] }],
        }
    else:
        if config.get('simulcast', False):
            ssrc = randint(10000000, 99999997)
            config['ssrc_0'] = ssrc
            config['ssrc_1'] = ssrc + 1
            config['ssrc_2'] = ssrc + 2
            config['bitrate_0'] = int(config.get('bitrate', 3000) / 4)
            config['bitrate_1'] = int(config.get('bitrate', 3000) / 2)
            config['bitrate_2'] = int(config.get('bitrate', 3000) / 1)
            config['width_0'] = int(config['width'] / 4)
            config['width_1'] = int(config['width'] / 2)
            config['width_2'] = int(config['width'])
            config['height_0'] = int(config['height'] / 4)
            config['height_1'] = int(config['height'] / 2)
            config['height_2'] = int(config['height'])
            #
            encodings = [
                { 
                    'ssrc': config['ssrc_0'],
                    'active': True,
                    'maxBitrate': config['bitrate_0'] * 1000,
                    'scaleResolutionDownBy': 4,
                    'scalabilityMode': 'S1T1',
                },
                { 
                    'ssrc': config['ssrc_1'],
                    'active': True,
                    'maxBitrate': config['bitrate_1'] * 1000,
                    'scaleResolutionDownBy': 2,
                    'scalabilityMode': 'S1T1',
                },
                { 
                    'ssrc': config['ssrc_2'],
                    'active': True,
                    'maxBitrate': config['bitrate_2'] * 1000,
                    'scaleResolutionDownBy': 1,
                    'scalabilityMode': 'S1T1',
                },
            ]
        else:
            config['ssrc'] = randint(10000000, 99999999)
            encodings = [{ 'ssrc': config['ssrc'] }]
        return {
            'codecs': [{
                'name': config.get('codec', 'vp8').upper(),
                'mimeType': 'video/'+config.get('codec', 'vp8').upper(),
                'clockRate': 90000,
                'payloadType': config.get('pt', 97),
                'rtcpFeedback': [
                    #{ 'type': 'goog-remb' },
                    { 'type': 'nack' },
                    { 'type': 'nack', 'parameter': 'pli' },
                    { 'type': 'ccm', 'parameter': 'fir' }
                ],
                'parameters': {
                    'vp8': None,
                    'vp9': None,
                    'h264': {
                        'packetization-mode': 1,
                        'profile-level-id': '42e01f',
                        'level-asymmetry-allowed': 1,
                    },
                    'h265': None,
                }[config.get('codec', 'vp8')]
            }],
            'encodings': encodings,
        }

def getConsumerRtpCapabilities():
    return {
        'codecs': [
            {
                'mimeType': 'audio/opus',
                'clockRate': 48000,
                'kind': 'audio',
                'preferredPayloadType': 100,
                'channels': 2,
                'parameters': { 'useinbandfec': 1 },
                'rtcpFeedback': []
            },
            {
                'mimeType': 'video/VP8',
                'clockRate': 90000,
                'kind': 'video',
                'preferredPayloadType': 101,
                'parameters': {},
                'rtcpFeedback': [{ 'type': 'nack' }]
            },
            {
                'mimeType': 'video/VP9',
                'clockRate': 90000,
                'kind': 'video',
                'preferredPayloadType': 103,
                'parameters': {},
                'rtcpFeedback': [{ 'type': 'nack' }]
            },
            {
                'mimeType': 'video/H264',
                'clockRate': 90000,
                'kind': 'video',
                'preferredPayloadType': 107,
                'parameters': { 'packetization-mode': 1, 'profile-level-id': '42e01f', 'level-asymmetry-allowed': 1 },
                'rtcpFeedback': [{ 'type': 'nack' }]
            },
            {
                'mimeType': 'video/H265',
                'clockRate': 90000,
                'kind': 'video',
                'preferredPayloadType': 109,
                'parameters': {},
                'rtcpFeedback': [{ 'type': 'nack' }]
            }
        ]
    }

class MediaSoup:
    def __init__(self, signaling):
        self.signaling = signaling

    def stop(self):
        logger.info('stop')
        self.signaling = None

    def produce(self, config, appData, done_cb, error_cb, removed_cb, *done_cb_args):
        logger.info('produce %s', config)
        #
        def createPlainRtpTransport():
            self.signaling.request('createPlainRtpTransport', {
                'type': 'plain',
                'comedia': True,
                'rtcpMux': False,
                'enableSctp': False,
                'appData': {}
            }, createPlainRtpTransport_done)
        #
        def createPlainRtpTransport_done(error, transport=None):
            if error:
                logger.error('produce createPlainRtpTransport error: %s', error)
                error_cb(error, *done_cb_args)
                return
            logger.info('produce createPlainRtpTransport_done %s', transport)
            #
            config['transportId'] = transport['id']
            if config.get('server_ip'):
                config['ip'] = config['server_ip']
            else:
                config['ip'] = transport['ip']
            config['rtpPort'] = transport['port']
            config['rtcpPort'] = transport['rtcpPort']
            #
            data = {
                'transportId': transport['id'],
                'kind': config['kind'],
                'rtpParameters': getProducerRtpParameters(config),
                'appData': appData,
            }
            if config['producerId']:
                data['id'] = config['producerId']
            self.signaling.request('transportProduce', data, transportProduce_done)
        #
        def transportProduce_done(error, producer=None):
            if error:
                logger.error('produce transportProduce error: %s', error)
                error_cb(error, *done_cb_args)
                return
            logger.info('produce transportProduce %s', producer)
            config['producerId'] = producer['id']
            #
            def _on_producer_removed(removedProducer):
                if removedProducer['id'] == producer['id']:
                    logger.info('_on_producer_removed %s', removedProducer)
                    removed_cb(removedProducer)
            self.signaling.on('producer:remove', _on_producer_removed)
            #
            done_cb(config, *done_cb_args)
        #
        createPlainRtpTransport()

    def consume(self, config, appData, done_cb, error_cb, removed_cb, *done_cb_args):
        logger.info('consume %s', config)
        #
        def createPlainRtpTransport():
            self.signaling.request('createPlainRtpTransport', {
                'type': 'plain',
                'comedia': False,
                'rtcpMux': False,
                'enableSctp': False,
                'appData': {},
            }, createPlainRtpTransport_done)
        #
        def createPlainRtpTransport_done(error, transport=None):
            if error:
                logger.error('consume createPlainRtpTransport error: %s', error)
                error_cb(error, *done_cb_args)
                return
            logger.info('consume createPlainRtpTransport %s', transport)
            #
            config['transportId'] = transport['id']
            config['ip'] = transport['ip']
            config['rtpPort'] = transport['port']
            config['rtcpPort'] = transport['rtcpPort']
            config['sctpParameters'] = transport.get('sctpParameters')
            #
            data = {
                'transportId': transport['id'],
                'ip': config['local_ip'],
                'port': config['local_rtpPort'],
                'rtcpPort': config['local_rtcpPort'],
            }
            self.signaling.request('plainRtpTransportConnect', data, plainRtpTransportConnect_done)
        #
        def plainRtpTransportConnect_done(error, data=None):
            if error:
                logger.error('consume plainRtpTransportConnect error: %s', error)
                error_cb(error, *done_cb_args)
                return
            logger.info('consume plainRtpTransportConnect %s', data)
            #
            data = {
                'producerId': config['producerId'],
                'transportId': config['transportId'],
                'paused': True,
                'rtpCapabilities': getConsumerRtpCapabilities(),
            }
            self.signaling.request('transportConsume', data, transportConsume_done)
        #
        def transportConsume_done(error, consumer=None):
            if error:
                logger.error('consume transportConsume error: %s', error)
                error_cb(error, *done_cb_args)
                return
            logger.info('consume transportConsume %s', consumer)
            config['kind'] = consumer['kind']
            config['consumerId'] = consumer['id']
            codecs = consumer['rtpParameters']['codecs'][0]
            config['encoding_name'] = codecs['mimeType'].split('/')[1].upper()
            config['codec'] = config['encoding_name'].lower()
            config['clockRate'] = codecs['clockRate']
            config['pt'] = codecs['payloadType']
            config['ssrc'] = consumer['rtpParameters']['encodings'][0]['ssrc']
            if config['kind'] == 'audio':
                config['channels'] = codecs['channels']
            #
            def _on_producer_removed(removedProducer):
                if removedProducer['id'] == config['producerId']:
                    logger.info('_on_producer_removed %s', removedProducer)
                    removed_cb(removedProducer)
            self.signaling.on('producer:remove', _on_producer_removed)
            #
            done_cb(config, *done_cb_args)
        #
        createPlainRtpTransport()

    def resumeConsumer(self, transportId, consumerId, done_cb, error_cb, *done_cb_args):
        logger.info('resumeConsumer %s %s', transportId, consumerId)
        #
        def resumeConsumer_done(error, res=None):
            if error:
                logger.error('consume resumeConsumer error: %s', error)
                error_cb(error, *done_cb_args)
                return
            done_cb(*done_cb_args)
        #
        self.signaling.request('consumerResume', { 
            'transportId': transportId,
            'consumerId': consumerId,
        }, resumeConsumer_done)
