# Copyright 2005 Alexey Bobyakov <claymore.ws@gmail.com>, Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# Based on quodlibet/formats/mpc.py by Joe Wreschnig, Michael Urman

import gst
import tempfile
from formats._audio import AudioFile

try:
    import ctypes
    _mp4v2 = ctypes.cdll.LoadLibrary("libmp4v2.so.0")
except: extensions = []
else:
    _mp4v2.MP4Read.restype = ctypes.c_void_p
    _mp4v2.MP4GetTrackType.restype = ctypes.c_char_p
    _mp4v2.MP4GetTrackDuration.restype = ctypes.c_ulonglong
    _mp4v2.MP4ConvertFromTrackDuration.restype = ctypes.c_ulonglong
    if gst.element_factory_make("faad"): extensions = ['.mp4', '.m4a']
    else: extensions = []

def GetAACTrack(infile):
    numtracks = _mp4v2.MP4GetNumberOfTracks(infile, None, 0)
    for i in range(numtracks):
        trackid = _mp4v2.MP4FindTrackId(infile, i, None, 0)
        tracktype = _mp4v2.MP4GetTrackType(infile, trackid)
        if tracktype == "soun": return trackid
    else: return -1

class MP4File(AudioFile):
    format = "MPEG-4 AAC"

    def __init__(self, filename):
        try:
            f = _mp4v2.MP4Read(filename, 0)
            if not f: raise IOError("%s not an MP4 file" % filename)
            track = GetAACTrack(f)
            if track == -1: raise IOError("%s has no audio track")
            duration = _mp4v2.MP4GetTrackDuration(f, track)
            length = _mp4v2.MP4ConvertFromTrackDuration(
                f, track, ctypes.c_ulonglong(duration), 1)
            self["~#length"] = int(length)

            self.__fill_metadata(f)
            self.sanitize(filename)
        finally:
            _mp4v2.MP4Close(f)

    def __fill_metadata(self, f):
        from ctypes import byref
        for key, function in [
            ("title", _mp4v2.MP4GetMetadataName),
            ("artist", _mp4v2.MP4GetMetadataArtist),
            ("composer", _mp4v2.MP4GetMetadataWriter),
            ("comment", _mp4v2.MP4GetMetadataComment),
            ("date", _mp4v2.MP4GetMetadataYear),
            ("album", _mp4v2.MP4GetMetadataAlbum),
            ("encoder", _mp4v2.MP4GetMetadataTool),
            ("genre", _mp4v2.MP4GetMetadataGenre)]:
            value = ctypes.c_char_p()
            if function(f, byref(value)):
                self[key] = value.value.decode('utf-8')

        cur, total = ctypes.c_short(), ctypes.c_short()
        if _mp4v2.MP4GetMetadataTrack(f, byref(cur), byref(total)):
            self["tracknumber"] = "%d/%d" % (cur.value, total.value)
        if _mp4v2.MP4GetMetadataDisk(f, byref(cur), byref(total)):
            self["discnumber"] = "%d/%d" % (cur.value, total.value)
        

    def can_change(self, key=None):
        if key is None: return []
        else: return False

    def write(self):
        raise NotImplementedError
    
    def get_format_cover(self):
        try:
            from ctypes import byref
            value = ctypes.c_char_p()
            size = ctypes.c_int()
            f = _mp4v2.MP4Read(filename, 0)
            if _mpv4v2.MP4GetMetadataCoverArt(f, byref(value), byref(size)):
                fn = tempfile.NamedTemporaryFile()
                fn.write(value.value)
                fn.flush()
                fn.seek(0, 0)
                return fn
        finally:
            _mp4v2.MP4Close(f)

info = MP4File
