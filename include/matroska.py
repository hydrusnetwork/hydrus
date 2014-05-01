# EBML/Matroska parser
# Copyright (C) 2010  Johannes Sasongko <sasongko@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
#
# The developers of the Exaile media player hereby grant permission
# for non-GPL compatible GStreamer and Exaile plugins to be used and
# distributed together with GStreamer and Exaile. This permission is
# above and beyond the permissions granted by the GPL license by which
# Exaile is covered. If you modify this code, you may extend this
# exception to your version of the code, but you are not obligated to
# do so. If you do not wish to do so, delete this exception statement
# from your version.


# This code is heavily based on public domain code by "Omion" (from the
# Hydrogenaudio forums), as obtained from Matroska's Subversion repository at
# revision 858 (2004-10-03), under "/trunk/Perl.Parser/MatroskaParser.pm".


import sys
from struct import unpack

SINT, UINT, FLOAT, STRING, UTF8, DATE, MASTER, BINARY = range(8)

class EbmlException(Exception): pass

class BinaryData(str): pass
class UnknownData: pass

class Ebml:
    """EBML parser.

    Usage: Ebml(location, tags).parse()
    tags is a dictionary of the form { id: (name, type) }.
    """

    ## Constructor and destructor

    def __init__(self, location, tags):
        self.tags = tags
        self.open(location)

    def __del__(self):
        self.close()

    ## File access.
    ## These can be overridden to provide network support.

    def open(self, location):
        """Open a location and set self.size."""
        self.file = f = open(location, 'rb')
        f = self.file
        f.seek(0, 2)
        self.size = f.tell()
        f.seek(0, 0)

    def seek(self, offset, mode):
        self.file.seek(offset, mode)

    def tell(self):
        return self.file.tell()

    def read(self, length):
        return self.file.read(length)

    def close(self):
        self.file.close()

    ## Element reading

    def readSize(self):
        b1 = self.read(1)
        b1b = ord(b1)
        if b1b & 0x80:
            # 1 byte
            return b1b & 0x7f
        elif b1b & 0x40:
            # 2 bytes
            # JS: BE-ushort
            return unpack(">H", chr(0x40 ^ b1b) + self.read(1))[0]
        elif b1b & 0x20:
            # 3 bytes
            # JS: BE-ulong
            return unpack(">L", "\0" + chr(0x20 ^ b1b) + self.read(2))[0]
        elif b1b & 0x10:
            # 4 bytes
            # JS: BE-ulong
            return unpack(">L", chr(0x10 ^ b1b) + self.read(3))[0]
        elif b1b & 0x08:
            # 5 bytes
            # JS: uchar BE-ulong. We change this to BE uchar ulong.
            high, low = unpack(">BL", chr(0x08 ^ b1b) + self.read(4))
            return high * 4294967296 + low
        elif b1b & 0x04:
            # 6 bytes
            # JS: BE-slong BE-ulong
            high, low = unpack(">HL", chr(0x04 ^ b1b) + self.read(5))
            return high * 4294967296 + low
        elif b1b & 0x02:
            # 7 bytes
            # JS: BE-ulong BE-ulong
            high, low = unpack(">LL",
                    "\0" + chr(0x02 ^ b1b) + self.read(6))
            return high * 4294967296 + low
        elif b1b & 0x01:
            # 8 bytes
            # JS: BE-ulong BE-ulong
            high, low = unpack(">LL", chr(0x01 ^ b1b) + self.read(7))
            return high * 4294967296 + low
        else:
            raise EbmlException(
                    "invalid element size with leading byte 0x%X" % b1b)

    def readInteger(self, length):
        if length == 1:
            # 1 byte
            return ord(self.read(1))
        elif length == 2:
            # 2 bytes
            return unpack(">H", self.read(2))[0]
        elif length == 3:
            # 3 bytes
            return unpack(">L", "\0" + self.read(3))[0]
        elif length == 4:
            # 4 bytes
            return unpack(">L", self.read(4))[0]
        elif length == 5:
            # 5 bytes
            high, low = unpack(">BL", self.read(5))
            return high * 4294967296 + low
        elif length == 6:
            # 6 bytes
            high, low = unpack(">HL", self.read(6))
            return high * 4294967296 + low
        elif length == 7:
            # 7 bytes
            high, low = unpack(">LL", "\0" + (self.read(7)))
            return high * 4294967296 + low
        elif length == 8:
            # 8 bytes
            high, low = unpack(">LL", self.read(8))
            return high * 4294967296 + low
        else:
            raise EbmlException(
                    "don't know how to read %r-byte integer" % length)

    def readFloat(self, length):
        # Need to reverse the bytes for little-endian machines
        if length == 4:
            # single
            return unpack('@f', self.read(4)[::-1])[0]
        elif length == 8:
            # double
            return unpack('@d', self.read(8)[::-1])[0]
        elif length == 10:
            # extended (don't know how to handle it)
            return 'EXTENDED'
        else:
            raise EbmlException("don't know how to read %r-byte float" % length)

    def readID(self):
        b1 = self.read(1)
        b1b = ord(b1)
        if b1b & 0x80:
            # 1 byte
            return b1b & 0x7f
        elif b1b & 0x40:
            # 2 bytes
            return unpack(">H", chr(0x40 ^ b1b) + self.read(1))[0]
        elif b1b & 0x20:
            # 3 bytes
            return unpack(">L", "\0" + chr(0x20 ^ b1b) + self.read(2))[0]
        elif b1b & 0x10:
            # 4 bytes
            return unpack(">L", chr(0x10 ^ b1b) + self.read(3))[0]
        else:
            raise EbmlException(
                    "invalid element ID with leading byte 0x%X" % b1b)

    ## Parsing

    def parse(self, from_=0, to=None):
        """Parses EBML from `from_` to `to`.

        Note that not all streams support seeking backwards, so prepare to handle
        an exception if you try to parse from arbitrary position.
        """
        if to is None:
            to = self.size
        self.seek(from_, 0)
        node = {}
        # Iterate over current node's children.
        while self.tell() < to:
            try:
                id = self.readID()
            except EbmlException, e:
                # Invalid EBML header. We can't reliably get any more data from
                # this level, so just return anything we have.
                print >>sys.stderr, "ERROR:", e
                return node
            size = self.readSize()
            try:
                key, type_ = self.tags[id]
            except KeyError:
                self.seek(size, 1)
            else:
                try:
                    if type_ is MASTER:
                        tell = self.tell()
                        value = self.parse(tell, tell + size)
                    elif type_ in (SINT, UINT, DATE):
                        value = self.readInteger(size)
                    elif type_ is FLOAT:
                        value = self.readFloat(size)
                    elif type_ is STRING:
                        value = unicode(self.read(size), 'ascii')
                    elif type_ is UTF8:
                        value = unicode(self.read(size), 'utf-8')
                    elif type_ is BINARY:
                        value = BinaryData(self.read(size))
                    else:
                        assert False
                except (EbmlException, UnicodeDecodeError), e:
                    print >>sys.stderr, "WARNING:", e
                try:
                    parentval = node[key]
                except KeyError:
                    parentval = node[key] = []
                parentval.append(value)
        return node

'''Hydrus Dev deleted this!
## GIO-specific code

import gio

class GioEbml(Ebml):
    # NOTE: All seeks are faked using InputStream.skip because we need to use
    # BufferedInputStream but it does not implement Seekable.

    def open(self, location):
        f = gio.File(location)
        self.buffer = gio.BufferedInputStream(f.read())
        self._tell = 0

        self.size = f.query_info('standard::size').get_size()

    def seek(self, offset, mode):
        if mode == 0:
            skip = offset - self._tell
        elif mode == 1:
            skip = offset
        elif mode == 2:
            skip = self.size - self._tell + offset
        else:
            raise ValueError("invalid seek mode: %r" % offset)
        if skip < 0:
            raise gio.Error("cannot seek backwards from %d" % self._tell)
        self._tell += skip
        self.buffer.skip(skip)

    def tell(self):
        return self._tell

    def read(self, length):
        result = self.buffer.read(length)
        self._tell += len(result)
        return result

    def close(self):
        self.buffer.close()
'''

## Matroska-specific code

# Interesting Matroska tags.
# Tags not defined here are skipped while parsing.
MatroskaTags = {
    0xa45dfa3: ('EBML', MASTER ),
    0x0282: ('DocType', STRING), # hydrus dev added this
    # Segment
    0x08538067: ('Segment', MASTER),
    # Segment Information
    0x0549A966: ('Info', MASTER),
    0x3384: ('SegmentFilename', UTF8),
    0x0AD7B1: ('TimecodeScale', UINT),
    0x0489: ('Duration', FLOAT),
    0x0461: ('DateUTC', DATE),
    0x3BA9: ('Title', UTF8),
    0x0D80: ('MuxingApp', UTF8),
    0x1741: ('WritingApp', UTF8),
    # Track
    0x0654AE6B: ('Tracks', MASTER),
    0x2E: ('TrackEntry', MASTER),
    0x57: ('TrackNumber', UINT),
    0x03: ('TrackType', UINT),
    0x29: ('FlagEnabled', UINT),
    0x08: ('FlagDefault', UINT),
    0x03E383: ('DefaultDuration', UINT),
    0x03314F: ('TrackTimecodeScale', FLOAT),
    0x137F: ('TrackOffset', SINT),
    0x136E: ('Name', UTF8),
    0x02B59C: ('Language', STRING),
    0x06: ('CodecID', STRING),
    0x058688: ('CodecName', UTF8),
    0x1A9697: ('CodecSettings', UTF8),
    0x1B4040: ('CodecInfoURL', STRING),
    0x06B240: ('CodecDownloadURL', STRING),
    0x2A: ('CodecDecodeAll', UINT),
    0x2FAB: ('TrackOverlay', UINT),
    # Video
    0x60: ('Video', MASTER),
    0x30: ('PixelWidth', UINT), # hydrus dev added this
    0x3A: ('PixelHeight', UINT), # hydrus dev added this
    # Audio
    0x61: ('Audio', MASTER),
    0x35: ('SamplingFrequency', UINT),
    0x38B5: ('OutputSamplingFrequency', UINT),
    0x1F: ('Channels', UINT),
    0x3D7B: ('ChannelPositions', BINARY),
    0x2264: ('BitDepth', UINT),
    # Content Encoding
    0x2D80: ('ContentEncodings', MASTER),
    0x2240: ('ContentEncoding', MASTER),
    0x1031: ('ContentEncodingOrder', UINT),
    0x1032: ('ContentEncodingScope', UINT),
    0x1033: ('ContentEncodingType', UINT),
    0x1034: ('ContentCompression', MASTER),
    0x0254: ('ContentCompAlgo', UINT),
    0x0255: ('ContentCompSettings', BINARY),
    # Chapters
    0x0043A770: ('Chapters', MASTER),
    0x05B9: ('EditionEntry', MASTER),
    0x05BC: ('EditionUID', UINT),
    0x05BD: ('EditionFlagHidden', UINT),
    0x05DB: ('EditionFlagDefault', UINT),
    0x05DD: ('EditionManaged', UINT),
    0x36: ('ChapterAtom', MASTER),
    0x33C4: ('ChapterUID', UINT),
    0x11: ('ChapterTimeStart', UINT),
    0x12: ('ChapterTimeEnd', UINT),
    0x18: ('ChapterFlagHidden', UINT),
    0x0598: ('ChapterFlagEnabled', UINT),
    0x23C3: ('ChapterPhysicalEquiv', UINT),
    0x0F: ('ChapterTrack', MASTER),
    0x09: ('ChapterTrackNumber', UINT),
    0x00: ('ChapterDisplay', MASTER),
    0x05: ('ChapString', UTF8),
    0x037C: ('ChapLanguage', STRING),
    0x037E: ('ChapCountry', STRING),
    # Tagging
    0x0254C367: ('Tags', MASTER),
    0x3373: ('Tag', MASTER),
    0x23C0: ('Targets', MASTER),
    0x28CA: ('TargetTypevalue', UINT),
    0x23CA: ('TargetType', STRING),
    0x23C9: ('EditionUID', UINT),
    0x23C4: ('ChapterUID', UINT),
    0x23C5: ('TrackUID', UINT),
    0x23C6: ('AttachmentUID', UINT),
    0x27C8: ('SimpleTag', MASTER),
    0x05A3: ('TagName', UTF8),
    0x047A: ('TagLanguage', STRING),
    0x0484: ('TagDefault', UINT),
    0x0487: ('TagString', UTF8),
    0x0485: ('TagBinary', BINARY),
}

def parse(location):
    return Ebml(location, MatroskaTags).parse()

def dump(location):
    from pprint import pprint
    pprint(parse(location))

def dump_tags(location):
    from pprint import pprint
    mka = parse(location)
    segment = mka['Segment'][0]
    info = segment['Info'][0]
    length = info['Duration'][0] * info['TimecodeScale'][0] / 1e9
    print "Length = %f seconds" % length
    pprint(segment['Tags'][0]['Tag'])

if __name__ == '__main__':
    import sys
    location = sys.argv[1]
    if sys.platform == 'win32' and '://' not in location:
        # XXX: This is most likely a bug in the Win32 GIO port; it converts
        # paths into UTF-8 and requires them to be specified in UTF-8 as well.
        # Here we decode the path according to the FS encoding to get the
        # Unicode representation first. If the path is in a different encoding,
        # this step will fail.
        location = location.decode(sys.getfilesystemencoding()).encode('utf-8')
    dump_tags(location)


# vi: et sts=4 sw=4 ts=4
