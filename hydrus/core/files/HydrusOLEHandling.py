import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions

#                       :::!~!!!!!:.
#                   .xUHWH!! !!?M88WHX:.
#                 .X*#M@$!!  !X!M$$$$$$WWx:.
#                :!!!!!!?H! :!$!$$$$$$$$$$8X:
#               !!~  ~:~!! :~!$!#$$$$$$$$$$8X:
#              :!~::!H!<   ~.U$X!?R$$$$$$$$MM!
#              ~!~!!!!~~ .:XW$$$U!!?$$$$$$RMM!
#                !:~~~ .:!M"T#$$$$WX??#MRRMMM!
#                ~?WuxiW*`   `"#$$$$8!!!!??!!!
#              :X- M$$$$       `"T#$T~!8$WUXU~
#             :%`  ~#$$$m:        ~!~ ?$$$$$$
#           :!`.-   ~T$$$$8xx.  .xWW- ~""##*"
# .....   -~~:<` !    ~?T#$$@@W@*?$$      /`
# W$@@M!!! .!~~ !!     .:XUW$W!~ `"~:    :
# #"~~`.:x%`!!  !H:   !WM$$$$Ti.: .!WUn+!`
# :::~:!!`:X~ .: ?H.!u "$$$B$$$!W:U!T$$M~
# .~~   :X@!.-~   ?@WTWo("*$$$W$TH$! `
# Wi.~!X$?!-~    : ?$$$B$Wu("**$RM!
# $R@i.~~ !     :   ~$$$$$B$$en:``
# ?MXT@Wx.~    :     ~"##*$$$$M~


OLE_HEADER = b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'

# https://gitlab.freedesktop.org/xdg/shared-mime-info/-/blob/a342af1d8848a2916ced47c9775cab6ab48b1db2/data/freedesktop.org.xml.in#L897
# they got the byte order wrong
# See GUIDs here http://fileformats.archiveteam.org/wiki/Microsoft_Compound_File
# "Note that the CLSIDs are stored as GUIDs in little-endian binary format, so they have a strange byte order."
# and note the structure of a GUID is:
# typedef struct _GUID {
#   unsigned long  Data1;
#   unsigned short Data2;
#   unsigned short Data3;
#   unsigned char  Data4[8];
# } GUID

OLE_GUIDs = {
    b'\x00\x09\x02\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x00\x00\x00\x46': HC.APPLICATION_DOC,
    b'\x06\x09\x02\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x00\x00\x00\x46': HC.APPLICATION_DOC,
    b'\x10\x8d\x81\x64\x9b\x4f\xcf\x11\x86\xea\x00\xaa\x00\xb9\x29\xe8': HC.APPLICATION_PPT, # where is this from?
    b'\x70\xae\x7b\xea\x3b\xfb\xcd\x11\xa9\x03\x00\xaa\x00\x51\x0e\xa3': HC.APPLICATION_PPT,
    b'\x51\x48\x04\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x00\x00\x00\x46': HC.APPLICATION_PPT,
    b'\x10\x08\x02\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x00\x00\x00\x46': HC.APPLICATION_XLS,
    b'\x20\x08\x02\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x00\x00\x00\x46': HC.APPLICATION_XLS
}

OLE_signatures_items = OLE_GUIDs.items()

def isOLEFile(path: str):
    
    with open( path, 'rb' ) as f:
        
        file_bytes = f.read(8)
        
        return file_bytes[ :8 ] == OLE_HEADER
        
    
def MimeFromMicrosoftOLEFile(path: str):
    
    if not isOLEFile(path):
    
        return HC.APPLICATION_UNKNOWN
    
    print('ole')
    
    with open( path, 'rb' ) as f:
            
        file_bytes = f.read()
        
        for signature, mime in OLE_signatures_items:
            
            print('checking:')
            print(signature)
            
            if signature in file_bytes[ 592 : 8192 + len( signature ) ]:
                
                print('match!')
                
                return mime
                
            
        
    return HC.UNDETERMINED_OLE
    
