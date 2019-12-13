'''

'''
import os
import requests
import json
from random import randint

from lib.custom_log import getLogger
logger = getLogger('Signaling')

class DefaultSignaling:
    def __init__(self):
        self.serverUrl = os.environ.get('SERVER_URL', 'https://localhost:4443')
        self.roomId = os.environ.get('ROOM_ID', 'test')
        self.broadcasterId = os.environ.get('BROADCASTER_ID', 'b%d' %randint(1, 99999999))
        logger.info('__init__ serverUrl=%s roomId=%s broadcasterId=%s' %(self.serverUrl, self.roomId, self.broadcasterId))
        # check room
        r = requests.get(self.serverUrl + '/rooms/' + self.roomId, verify=False)
        r.raise_for_status()
        # logger.debug('room: %s', r.json())
        # create broadcaster
        r = requests.post(self.serverUrl + '/rooms/' + self.roomId + '/broadcasters', json={
            'id': self.broadcasterId,
            'displayName': 'Broadcaster %s' %self.broadcasterId,
            'device': { "name": "GStreamer" },
        }, verify=False)
        r.raise_for_status()
        logger.info('room: %s', r.json())

    def stop(self):
        logger.info('stop')
        r = requests.delete(self.serverUrl + '/rooms/' + self.roomId + '/broadcasters/' + self.broadcasterId, verify=False)
        r.raise_for_status()

    def request(self, name, data, cb):
        logger.info('request %s', name)
        f = getattr(self, 'do_'+name)
        if not f:
            raise Exception('Handler not found: %s' %name)
        return f(data, cb)

    def on(self, name, cb):
        logger.info('on %s', name)

    #
    def do_createPlainRtpTransport(self, data, cb):
        logger.info('do_createPlainRtpTransport %s', data)
        r = requests.post(self.serverUrl + '/rooms/' + self.roomId + '/broadcasters/' + self.broadcasterId + '/transports', 
                json=data, verify=False)
        try:
            r.raise_for_status()
        except Exception as e:
            cb(str(e))
        else:
            cb(None, r.json())

    def do_transportProduce(self, data, cb):
        logger.info('do_transportProduce %s', data)
        r = requests.post(self.serverUrl + '/rooms/' + self.roomId + '/broadcasters/' + self.broadcasterId 
                + '/transports/' + data['transportId'] + '/producers', 
                json=data, verify=False)
        try:
            r.raise_for_status()
        except Exception as e:
            cb(str(e))
        else:
            cb(None, r.json())
    
    def do_plainRtpTransportConnect(self, data, cb):
        logger.info('do_plainRtpTransportConnect %s', data)
        logger.info('do_transportProduce %s', data)
        r = requests.post(self.serverUrl + '/rooms/' + self.roomId + '/broadcasters/' + self.broadcasterId 
                + '/transports/' + data['transportId'] + '/connect', 
                json=data, verify=False)
        try:
            r.raise_for_status()
        except Exception as e:
            cb(str(e))
        else:
            cb(None, {})

    def do_transportConsume(self, data, cb):
        logger.info('do_transportConsume %s', data)
        r = requests.post(self.serverUrl + '/rooms/' + self.roomId + '/broadcasters/' + self.broadcasterId 
                + '/transports/' + data['transportId'] + '/consume', 
                json=data, verify=False)
        try:
            r.raise_for_status()
        except Exception as e:
            cb(str(e))
        else:
            cb(None, r.json())

    def do_consumerResume(self, data, cb):
        logger.info('do_consumerResume %s', data)
        r = requests.post(self.serverUrl + '/rooms/' + self.roomId + '/broadcasters/' + self.broadcasterId 
                + '/transports/' + data['transportId'] + '/resume', 
                json=data, verify=False)
        try:
            r.raise_for_status()
        except Exception as e:
            cb(str(e))
        else:
            cb(None, {})
