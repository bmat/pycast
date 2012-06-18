#-*- coding: utf-8 -*-
#
# pyvericast - A Python interface to Vericast
# Copyright (C) 2012 BMAT
# Based in pylast (Amr Hassan)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import os
import urllib
import urllib2
from xml.dom import minidom
from hashlib import md5
import datetime


__name__ = 'pycast'
__version__ = '0.0.1'
__doc__ = 'A Python interface to Vericast'
__author__ = 'BMAT developers'
__copyright__ = 'Copyright (C) 2012 BMAT'
__license__ = 'gpl'
__email__ = 'vericast-support@bmat.com'


WS_SERVER = "localhost:8080"


__cache_dir = None
__cache_enabled = None


class ServiceException(Exception):
    """Exception related to the Vericast web service"""

    def __init__(self, code, message):
        self._code = code
        self._message = message

    def __str__(self):
        return self._message

    def get_id(self):
        return self.code


class _Request(object):
    """Representing an abstract web service operation."""

    def __init__(self, method_name, params, username, api_key):
        self.params = params
        self.params['user'] = username
        self.params['api'] = api_key
        self.params['method'] = method_name

    def _download_response(self):
        """Returns a response body string from the server"""
        data = []
        for name in self.params.keys():
            value = self.params[name]
            if isinstance(value, unicode):
                value = value.encode('utf8')
            data.append('='.join((name, urllib.quote_plus(str(value)))))
        data = '&'.join(data)

        headers = {
            'Content-type': 'application/x-www-form-urlencoded',
            'Accept-Charset': 'utf-8',
            'User-Agent': __name__ + '/' + __version__
        }
        request = urllib2.Request(
                'http://' + WS_SERVER + '?' + data, None, headers)
        response = urllib2.urlopen(request).read()
        self._check_response_for_errors(response)
        return response

    def execute(self, cacheable=False):
        """Returns the XML DOM response from the server"""
        if is_caching_enabled() and cacheable:
            response = self._get_cached_response()
        else:
            response = self._download_response()
        return minidom.parseString(response)

    def _get_cache_key(self):
        """Cache key"""
        keys = list(self.params.keys())
        keys.sort()
        cache_key = str()
        for key in keys:
            cache_key += key + str(self.params[key])
        return get_md5(cache_key)

    def _is_cached(self):
        """Returns True if the request is available in the cache."""
        return os.path.exists(
                os.path.join(_get_cache_dir(), self._get_cache_key()))

    def _get_cached_response(self):
        """Returns a file object of the cached response."""
        print 'get_cached_response'
        if not self._is_cached():
            print 'set cache'
            response = self._download_response()
            response_file = open(
                os.path.join(_get_cache_dir(), self._get_cache_key()), "w")
            response_file.write(response)
            response_file.close()
        print 'get_cache'
        return open(
            os.path.join(_get_cache_dir(), self._get_cache_key()), "r").read()

    def _check_response_for_errors(self, response):
        """Checks the response for errors and raises one if any exists."""
        doc = minidom.parseString(response)
        e = doc.getElementsByTagName('vct')[0]
        if e.getAttribute('status') != "ok":
            e = doc.getElementsByTagName('error')[0]
            status = e.getAttribute('code')
            details = e.firstChild.data.strip()
            raise ServiceException(status, details)


class _BaseObject(object):
    """An abstract webservices object."""

    def __init__(self, username, api_key):
        self.username = username
        self.api_key = api_key

    def _request(self, method_name, cacheable=False, params=None):
        if not params:
            params = self._get_params()
        req = _Request(method_name, params, self.username, self.api_key)
        return req.execute(cacheable)

    def _get_params(self):
        return dict()


class Artist(_BaseObject):
    """ A Vericast artist """

    def __init__(self, name, username, api_key):
        """Create an artist object.
        #Parametres:
          * name str: The artist's name.
        """
        _BaseObject.__init__(self, username, api_key)
        self.name = name

    def __repr__(self):
        return unicode(self.get_name())

    def _get_params(self):
        return {'artist': self.get_name()}

    def get_name(self):
        """Returns the name of the artist."""
        return self.name

    def get_top_tracks(self, start, end):
        """Return a list of the top tracks starting from the
           start value to the end value
        """
        params = self._get_params()
        params['start'] = _date(start)
        params['end'] = _date(end)
        doc = self._request('artist.GetTopTracks', False, params)
        tracks = []
        for track in doc.getElementsByTagName('track'):
            title = _extract(track, 'name')
            artist = _extract(track, 'name', 1)
            playcount = _number(_extract(track, 'playcount'))
            tracks.append(TopItem(
                Track(artist, title, self.username, self.api_key),
                playcount))
        return tracks

    def get_top_channels(self, start, end):
        """Return a list of the top channels starting from the
           start value to the end value
        """
        params = self._get_params()
        params['start'] = _date(start)
        params['end'] = _date(end)
        doc = self._request('artist.GetTopChannels', False, params)
        channels = []
        for track in doc.getElementsByTagName('channel'):
            keyname = _extract(track, 'keyname')
            playcount = _number(_extract(track, 'playcount'))
            channels.append(TopItem(
                Channel(keyname, self.username, self.api_key),
                playcount))
        return channels

    def get_matches(self, start, end, page=1, limit=50):
        """Return a list of matches starting from the start value
           to the end value order by date
        """
        params = self._get_params()
        params['start'] = _date(start)
        params['end'] = _date(end)
        params['page'] = _number(page)
        params['limit'] = _number(limit)
        doc = self._request('artist.GetMatches', False, params)
        matches = []
        for match in doc.getElementsByTagName('match'):
            id = _extract(match, 'id')
            matches.append(Match(id, self.username, self.api_key))
        return matches


class Track(_BaseObject):
    """A Vericast track"""

    def __init__(self, artist, title, username, api_key, **kwargs):
        _BaseObject.__init__(self, username, api_key, **kwargs)

        if isinstance(artist, Artist):
            self.artist = artist
        else:
            self.artist = Artist(artist, username, api_key)
        self.title = title

    def __repr__(self):
        return self.get_artist().get_name() + ' - ' + self.get_title()

    def _get_params(self):
        return {'artist': self.get_artist().get_name(),
                'track': self.get_title()}

    def get_artist(self):
        """Returns the associated Artist object."""
        return self.artist

    def get_title(self):
        """Returns the track title."""
        return self.title

    def get_top_channels(self, start, end):
        """Return a list of the top channels starting from
           the start value to end value
        """
        params = self._get_params()
        params['start'] = _date(start)
        params['end'] = _date(end)
        doc = self._request('track.GetTopChannels', False, params)
        channels = []
        for track in doc.getElementsByTagName('channel'):
            keyname = _extract(track, 'keyname')
            playcount = _number(_extract(track, 'playcount'))
            channels.append(TopItem(
                Channel(keyname, self.username, self.api_key), playcount))
        return channels

    def get_matches(self, start, end, page=1, limit=50):
        """Return a list of matches starting from the start value
           to the end value order by date
        """
        params = self._get_params()
        params['start'] = _date(start)
        params['end'] = _date(end)
        params['page'] = _number(page)
        params['limit'] = _number(limit)
        doc = self._request('track.GetMatches', False, params)
        matches = []
        for match in doc.getElementsByTagName('match'):
            id = _extract(match, 'id')
            matches.append(Match(id, self.username, self.api_key))
        return matches


class Channel(_BaseObject):
    """A Vericat channel"""

    def __init__(self, keyname, username, api_key):
        _BaseObject.__init__(self, username, api_key)
        self.keyname = keyname

    def __repr__(self):
        return self.keyname

    def _get_params(self):
        return {'channel': self.get_keyname()}

    def get_keyname(self):
        return self.keyname

    def get_top_artists(self, start, end):
        """Return a list of the top artists starting
           from start value to the end value
        """
        params = self._get_params()
        params['start'] = _date(start)
        params['end'] = _date(end)
        doc = self._request('charts.GetTopArtists', False, params)
        artists = []
        for artist in doc.getElementsByTagName('artist'):
            name = _extract(artist, 'name')
            playcount = _extract(artist, 'playcount')
            artists.append(TopItem(
                Artist(name, self.username, self.api_key), playcount))
        return artists

    def get_top_tracks(self, start, end):
        """Return a list of the top tracks starting from the
           start value to the end value
        """
        params = self._get_params()
        params['start'] = _date(start)
        params['end'] = _date(end)
        doc = self._request('channel.GetTopTracks', False, params)
        tracks = []
        for track in doc.getElementsByTagName('track'):
            title = _extract(track, 'name')
            artist = _extract(track, 'name', 1)
            playcount = _number(_extract(track, 'playcount'))
            tracks.append(TopItem(
                Track(artist, title, self.username, self.api_key),
                playcount))
        return tracks

    def get_top_labels(self, start, end):
        """Return a list of the top labels starting from the
           start value to the end value
        """
        params = self._get_params()
        params['start'] = _date(start)
        params['end'] = _date(end)
        doc = self._request('channel.GetTopLabels', False, params)
        labels = []
        for label in doc.getElementsByTagName('label'):
            name = _extract(label, 'name')
            playcount = _extract(label, 'playcount')
            labels.append(TopItem(
                Label(name, self.username, self.api_key), playcount))
        return labels

    def get_matches(self, start, end, page=1, limit=50):
        """Return a list of matches starting from the start value
           to the end value order by date
        """
        params = self._get_params()
        params['start'] = _date(start)
        params['end'] = _date(end)
        params['page'] = _number(page)
        params['limit'] = _number(limit)
        doc = self._request('channel.GetMatches', False, params)
        matches = []
        for match in doc.getElementsByTagName('match'):
            id = _extract(match, 'id')
            matches.append(Match(id, self.username, self.api_key))
        return matches


class Label(_BaseObject):
    """A Vericast label"""

    def __init__(self, name, username, api_key):
        _BaseObject.__init__(self, username, api_key)
        self.name = name

    def __repr__(self):
        return self.name

    def _get_params(self):
        return {'label': self.get_name()}

    def get_name(self):
        return self.name

    def get_top_artists(self, start, end):
        """Return a list of the top artists starting
           from start value to the end value
        """
        params = self._get_params()
        params['start'] = _date(start)
        params['end'] = _date(end)
        doc = self._request('label.GetTopArtists', False, params)
        artists = []
        for artist in doc.getElementsByTagName('artist'):
            name = _extract(artist, 'name')
            playcount = _extract(artist, 'playcount')
            artists.append(TopItem(
                Artist(name, self.username, self.api_key), playcount))
        return artists

    def get_top_tracks(self, start, end):
        """Return a list of the top tracks starting from the
           start value to the end value
        """
        params = self._get_params()
        params['start'] = _date(start)
        params['end'] = _date(end)
        doc = self._request('label.GetTopTracks', False, params)
        tracks = []
        for track in doc.getElementsByTagName('track'):
            title = _extract(track, 'name')
            artist = _extract(track, 'name', 1)
            playcount = _number(_extract(track, 'playcount'))
            tracks.append(TopItem(
                Track(artist, title, self.username, self.api_key),
                playcount))
        return tracks

    def get_top_channels(self, start, end):
        """Return a list of the top channels starting from
           the start value to end value
        """
        params = self._get_params()
        params['start'] = _date(start)
        params['end'] = _date(end)
        doc = self._request('label.GetTopChannels', False, params)
        channels = []
        for track in doc.getElementsByTagName('channel'):
            keyname = _extract(track, 'keyname')
            playcount = _number(_extract(track, 'playcount'))
            channels.append(TopItem(
                Channel(keyname, self.username, self.api_key), playcount))
        return channels

    def get_matches(self, start, end, page=1, limit=50):
        """Return a list of matches starting from the start value
           to the end value order by date
        """
        params = self._get_params()
        params['start'] = _date(start)
        params['end'] = _date(end)
        params['page'] = _number(page)
        params['limit'] = _number(limit)
        doc = self._request('label.GetMatches', False, params)
        matches = []
        for match in doc.getElementsByTagName('match'):
            id = _extract(match, 'id')
            matches.append(Match(id, self.username, self.api_key))
        return matches


class Match(_BaseObject):
    """A match"""

    id = None

    def __init__(self, id, username, api_key):
        _BaseObject.__init__(self, username, api_key)
        self.id = id

    def __repr__(self):
        return "pycast.Match(%s)" % self.id

    def _get_params(self):
        return {'match': self.id}

    def get_id(self):
        return id

    def get_datetime(self):
        """Returns the date when the track has matched"""
        doc = self._request('match.GetInfo', True)
        dt = _extract(doc, 'datetime')
        return datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')

    def get_channel(self):
        """Returns the channel of the match"""
        doc = self._request('match.GetInfo', True)
        keyname = _extract(doc, 'channel')
        return Channel(keyname, self.username, self.api_key)

    def get_duration(self):
        """Returns the duration of the match"""
        doc = self._request('match.GetInfo', True)
        duration = _extract(doc, 'duration')
        return _number(duration)

    def get_track(self):
        """Returns the track of the match"""
        doc = self._request('match.GetInfo', True)
        track = _extract(doc, 'name')
        artist = _extract(doc, 'name', 1)
        return Track(artist, track, self.username, self.api_key)


class Chart(_BaseObject):
    """A Vericast chart"""

    def __init__(self, start, end, username, api_key):
        """Create a chart object starting from the start value
           to the end value
           #Parametres:
            * start date: Start date
            * end date: End date
        """
        _BaseObject.__init__(self, username, api_key)
        self.start = start
        self.end = end

    def __repr__(self):
        return "pycast.Chart('%s', '%s')" % (
                _date(self.start), _date(self.end))

    def _get_params(self):
        return {'start': _date(self.start),
                'end': _date(self.end)}

    def get_start_date(self):
        return self.start

    def get_end_date(self):
        return self.end

    def get_top_artists(self):
        """Return a list of the top artists starting"""
        doc = self._request('charts.GetTopArtists')
        artists = []
        for artist in doc.getElementsByTagName('artist'):
            name = _extract(artist, 'name')
            playcount = _extract(artist, 'playcount')
            artists.append(TopItem(
                Artist(name, self.username, self.api_key), playcount))
        return artists

    def get_top_tracks(self):
        """Return a list of the top tracks starting from the value
        """
        doc = self._request('charts.GetTopTracks')
        tracks = []
        for track in doc.getElementsByTagName('track'):
            title = _extract(track, 'name')
            artist = _extract(track, 'name', 1)
            playcount = _number(_extract(track, 'playcount'))
            tracks.append(TopItem(
                Track(artist, title, self.username, self.api_key, playcount)))
        return tracks

    def get_top_labels(self):
        """Return a list of the top labels"""
        doc = self._request('charts.GetTopLabels')
        labels = []
        for label in doc.getElementsByTagName('label'):
            name = _extract(label, 'name')
            playcount = _extract(label, 'playcount')
            labels.append(TopItem(
                Label(name, self.username, self.api_key), playcount))
        return labels


class TopItem(object):

    def __init__(self, item, weight):
        self.item = item
        self.weight = _number(weight)

    def __repr__(self):
        return ("Item: " + self.get_item().__repr__() +
                ", Weight: " + str(self.get_weight()))

    def get_item(self):
        """Return the item"""
        return self.item

    def get_weight(self):
        """Return the weight of the item in the list"""
        return self.weight


def _extract(node, name, index=0):
    """Extracts a value from the xml string"""
    nodes = node.getElementsByTagName(name)
    if len(nodes) and nodes[index].firstChild:
        return nodes[index].firstChild.data.strip()


def _number(string):
    """Extracts an int from a string.
    Returns a 0 if None or an empty string was passed."""
    if not string or string == '':
        return 0
    else:
        return int(string)


def _date(date):
    return date.strftime('%Y%m%d')


def enable_caching(cache_dir=None):
    global __cache_dir
    global __cache_enabled

    if cache_dir == None:
        import tempfile
        __cache_dir = tempfile.mkdtemp()
    else:
        if not os.path.exists(cache_dir):
            os.mkdir(cache_dir)
        __cache_dir = cache_dir
    __cache_enabled = True


def disable_caching():
    global __cache_enabled
    __cache_enabled = False


def is_caching_enabled():
    """Returns True if caching is enabled."""
    global __cache_enabled
    return __cache_enabled


def _get_cache_dir():
    """Returns the directory in which cache files are saved."""
    global __cache_dir
    global __cache_enabled
    return __cache_dir


def get_md5(text):
    """Returns the md5 hash of a string."""
    hash = md5()
    hash.update(text.encode('utf8'))
    return hash.hexdigest()
