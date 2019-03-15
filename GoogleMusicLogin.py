import utils, xbmc, xbmcgui
from gmusicapi import Mobileclient

class GoogleMusicLogin():
    def __init__(self):
        self.gmusicapi = Mobileclient(debug_logging=False, validate=False, verify_ssl=True)

    def checkCookie(self):
        # Remove cookie data if it is older then 7 days
        if utils.addon.getSetting('cookie-time'):
            import time
            if time.time() - float(utils.addon.getSetting('cookie-time')) > 3600*24*7:
                self.clearCookie()

    def checkCredentials(self):
        if not utils.addon.getSetting('username'):
            utils.addon.openSettings()
        if utils.addon.getSetting('password') and utils.addon.getSetting('password') != '**encoded**':
            import base64
            utils.addon.setSetting('encpassword',base64.b64encode(utils.addon.getSetting('password')))
            utils.addon.setSetting('password','**encoded**')

    def getApi(self):
        return self.gmusicapi

    def getStreamUrl(self, song_id, session_token, wentry_id):
        # retrieve registered device
        device_id = self.getDevice()
        # retrieve stream quality from settings
        quality = { '0':'hi','1':'med','2':'low' } [utils.addon.getSetting('quality')]
        utils.log("getStreamUrl songid: %s device: %s quality: %s"%(song_id, device_id, quality))

        stream_url = ''
        if wentry_id:
            stream_url = self.gmusicapi.get_station_track_stream_url(song_id, wentry_id, session_token, quality)
        else:
            stream_url = self.gmusicapi.get_stream_url(song_id, device_id, quality)
        return stream_url

    def getDevice(self):
        return utils.addon.getSetting('device_id')

    def initDevice(self):
        device_id = self.getDevice()

        if not device_id:
            utils.log('Trying to fetch the device_id')
            self.login()
            try:
                devices = self.gmusicapi.get_registered_devices()
                if len(devices) == 10:
                    utils.log("WARNING: 10 devices already registered!")
                utils.log('Devices: '+repr(devices))
                for device in devices:
                    if device["type"] in ("ANDROID","PHONE","IOS"):
                        device_id = str(device["id"])
                        break
            except Exception as e:
                utils.log("ERROR: "+repr(e))

            if device_id:
                if device_id.lower().startswith('0x'): device_id = device_id[2:]
                utils.addon.setSetting('device_id', device_id)
                utils.log('Found device_id: '+device_id)
            else:
                utils.log('No Android device found in account')

    def clearCookie(self):
        utils.addon.setSetting('logged_in-mobile', "")
        utils.addon.setSetting('authtoken-mobile', "")
        utils.addon.setSetting('device_id', "")
        utils.addon.setSetting('subscriber', "0")

    def logout(self):
        self.gmusicapi.logout()

    def login(self, nocache=False):
        if not utils.addon.getSetting('logged_in-mobile') or nocache:
            import base64

            utils.log('Logging in')
            self.checkCredentials()
            username = utils.addon.getSetting('username')
            password = base64.b64decode(utils.addon.getSetting('encpassword'))

            try:
                self.gmusicapi.login(username, password, self.getDevice() )
            except Exception as e:
                utils.log("ERROR: "+repr(e))
                if 'Your valid device IDs are:' in str(e):
                    self.gmusicapi.login(username, password, str(e).split('*')[1].strip() )
                if not self.gmusicapi.is_authenticated():
                try:
                    utils.log("Login in with device_id failed, trying with MAC")
                    self.gmusicapi.login(username, password, Mobileclient.FROM_MAC_ADDRESS)
            except Exception as e:
                    utils.log("ERROR: "+repr(e))

            if not self.gmusicapi.is_authenticated():
                utils.log("Login failed")
                utils.addon.setSetting('logged_in-mobile', "")
                self.language = utils.addon.getLocalizedString
                dialog = xbmcgui.Dialog()
                dialog.ok(self.language(30101), self.language(30102))
                raise
            else:
                utils.log("Login succeeded. Device id: "+self.gmusicapi.android_id)
                utils.addon.setSetting('device_id', self.gmusicapi.android_id)
                utils.addon.setSetting('logged_in-mobile', "1")
                utils.addon.setSetting('authtoken-mobile', self.gmusicapi.session._authtoken)
                import time
                utils.addon.setSetting('cookie-time', str(time.time()))
                utils.addon.setSetting('subscriber','1' if self.gmusicapi.is_subscribed else '0')

        else:

            utils.log("Loading auth from cache")
            self.gmusicapi.session._authtoken = utils.addon.getSetting('authtoken-mobile')
            self.gmusicapi.session.is_authenticated = True
