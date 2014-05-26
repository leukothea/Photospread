import urllib, urllib2, urlparse
import django.utils.simplejson as json
import re, hashlib, os.path

"""
This will use API version 1.2.2
"""

""" Constants """
EMAIL='linhchan1205@gmail.com'
PASSWORD='iloverockclimbing'
API_KEY='PIA0bSs4qxvzwsNUUvGt1hNeGQhZoE3K'
API_VERSION='1.2.2'
API_URL='https://api.smugmug.com/services/api/json/1.2.2/' # Assume SSL is used
UPLOAD_URL='http://upload.smugmug.com/photos/xmlrawadd.mg'

su_cookie = None

class SmugmugClient(object):
    def __init__(self, api_key= API_KEY, api_version='1.2.2'):
        self.api_key = api_key
        self.use_ssl = True
        self.api_version = api_version

    @staticmethod
    def _smugmug_request(method, params):
        global su_cookie
        paramstrings = [urllib.quote(key)+'='+urllib.quote(params[key]) for key in params]
        paramstrings += ['method=' + method]
        url = urlparse.urljoin(API_URL, '?' + '&'.join(paramstrings))
        request = urllib2.Request(url)
        # if _su cookie present, add to header
        if su_cookie:
            request.add_header('Cookie', su_cookie)

        response = urllib2.urlopen(request)
        result = json.loads(response.read())

        meta = response.info()
        if meta.has_key('set-cookie'):
            match = re.search('(_su=\S+);', meta['set-cookie'])
            if match and match.group(1) != "_su=deleted":
                su_cookie = match.group(1)
        if result['stat'] != 'ok' : raise Exception('Bad result code')

        return result

    def login(self, method):
        params = {'APIKey' : API_KEY,'EmailAddress' : EMAIL, 'Password': PASSWORD}
        result = self._smugmug_request(method, params)
        return result

    def getalbumid(self,session,album_name): 
        params = {'SessionID' : session}
        result = self._smugmug_request('smugmug.albums.get', params)
        for album in result['Albums'] :
            if album['Title'] == album_name :
                album_id = album['id']
                break
        if album_id is None :
            print 'Album not existing.'
        return album_id

    def uploadtoalbum(self,filename,session,album_id):
        global su_cookie
        #filename = "/Users/linhchan/P-O-U-master/mysite/media/images/work3.png"
        params = {'Content-Length' : len(open(filename,'rb').read()), 
                  'Content-MD5' : hashlib.md5(open(filename,'rb').read()).hexdigest(),
                  'Content-Type': 'none',
                  'X-Smug-SessionID': session,
                  'X-Smug-Version'  : API_VERSION,
                  'X-Smug-ResponseType' : 'JSON',
                  'X-Smug-AlbumID'  : album_id,
                  'X-Smug-FileName' : os.path.basename(filename) }
        request = urllib2.Request(UPLOAD_URL, open(filename,'rb').read(), params)
        # if _su cookie present, add to header
        if su_cookie:
            request.add_header('Cookie', su_cookie)
        response = urllib2.urlopen(request)
        result = json.loads(response.read())
        meta = response.info()
        if meta.has_key('set-cookie'):
            match = re.search('(_su=\S+);', meta['set-cookie'])
            if match and match.group(1) != "_su=deleted":
                su_cookie = match.group(1)
                #if result['stat'] != 'ok' : raise Exception('Bad result code']
        return result
        
if __name__ == '__main__':
    pass      

