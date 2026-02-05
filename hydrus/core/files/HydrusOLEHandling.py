from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions

try:
    
    import olefile

    OLEFILE_OK = True
    
except Exception as e:
    
    OLEFILE_OK = False
    

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

# This is a classic example of a good time to just let some third party library do it for you.

# Historical record of attempting to just search for signatures:

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

# OLE_GUIDs = {
#     b'\x00\x09\x02\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x00\x00\x00\x46': HC.APPLICATION_DOC,
#     b'\x06\x09\x02\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x00\x00\x00\x46': HC.APPLICATION_DOC,
#     b'\x10\x8d\x81\x64\x9b\x4f\xcf\x11\x86\xea\x00\xaa\x00\xb9\x29\xe8': HC.APPLICATION_PPT, # where is this from?
#     b'\x70\xae\x7b\xea\x3b\xfb\xcd\x11\xa9\x03\x00\xaa\x00\x51\x0e\xa3': HC.APPLICATION_PPT,
#     b'\x51\x48\x04\ x00\x00\x00\x00\x00\xc0\x00\x00\x00\x00\x00\x00\x46': HC.APPLICATION_PPT,
#     b'\x10\x08\x02\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x00\x00\x00\x46': HC.APPLICATION_XLS,
#     b'\x20\x08\x02\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x00\x00\x00\x46': HC.APPLICATION_XLS
# }

# Now using the proper `olefile` library:

# http://fileformats.archiveteam.org/wiki/Microsoft_Compound_File 
# https://wikileaks.org/ciav7p1/cms/page_13762814.html
# https://raw.githubusercontent.com/decalage2/oletools/master/oletools/common/clsid.py


# These need to be uppercase
GUID_MIMES = {
    '00020900-0000-0000-C000-000000000046': HC.APPLICATION_DOC, # Word 6.0-7.0 Document (Word.Document.6)
    '00020906-0000-0000-C000-000000000046': HC.APPLICATION_DOC, # Word 97-2003 Document (Word.Document.8)
    '00030003-0000-0000-C000-000000000046': HC.APPLICATION_DOC, # Word 2.0 Document
    'F4754C9B-64F5-4B40-8AF4-679732AC0607': HC.APPLICATION_DOC, # (Word.Document.12)
    '00044851-0000-0000-C000-000000000046': HC.APPLICATION_PPT, # PowerPoint 4.0 PPT
    '64818D10-4F9B-11CF-86EA-00AA00B929E8': HC.APPLICATION_PPT, # PPT (Microsoft Powerpoint.Show.8)
    'EA7BAE70-FB3B-11CD-A903-00AA00510EA3': HC.APPLICATION_PPT, # PowerPoint 95 PPT
    'CF4F55F4-8F87-4D47-80BB-5808164BB3F8': HC.APPLICATION_PPT, # (Microsoft Powerpoint.Show.12)
    '00020810-0000-0000-C000-000000000046': HC.APPLICATION_XLS, # Excel 5-95 XLS (Microsoft Excel.Sheet.5)
    '00020820-0000-0000-C000-000000000046': HC.APPLICATION_XLS, # Excel 97-2003 Worksheet (Excel.Sheet.8)
    '00020830-0000-0000-C000-000000000046': HC.APPLICATION_XLS, # (Microsoft Excel.Sheet.12)
}

# GUID_MIMES =  {k.upper(): v for k, v in GUID_MIMES.items()}


OLE_HEADER = b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'
    
def isOleFile(path: str):
    
    if OLEFILE_OK:
        
        return olefile.isOleFile(path)
        
    else:
        
        with open( path, 'rb' ) as f:
            
            file_bytes = f.read(8)
            
            return file_bytes[ :8 ] == OLE_HEADER
            
        
    

def MimeFromOLEFile(path: str):
    
    if not isOleFile( path ):
        
        return HC.APPLICATION_UNKNOWN
        
    
    if not OLEFILE_OK:
        
        return HC.UNDETERMINED_OLE
    
    try:
        
        with olefile.OleFileIO(path) as ole:
        
            rootCLSID = ole.root.clsid
            
            if rootCLSID in GUID_MIMES:
                
                return GUID_MIMES[rootCLSID]
            
            # only call this once!
            metadata = ole.get_metadata()
            
            # noinspection PyUnresolvedReferences
            creating_application = metadata.creating_application
            
            if creating_application is not None:
                
                if creating_application.startswith(b'Microsoft Word'):
                    
                    return HC.APPLICATION_DOC
                
                if creating_application.startswith(b'Microsoft PowerPoint'):
                    
                    return HC.APPLICATION_PPT
                
                if creating_application.startswith(b'Microsoft Excel'):
                    
                    return HC.APPLICATION_XLS
                    
                
            return HC.UNDETERMINED_OLE
            
    except Exception as e:
        
        return HC.UNDETERMINED_OLE
        
    

def OfficeOLEDocumentWordCount( path: str ):
    
    # Not all legacy office files are OLE
    if not isOleFile( path ):
        
        raise HydrusExceptions.LimitedSupportFileException('File is not OLE!')
        
    
    if not OLEFILE_OK:
        
        raise HydrusExceptions.NoThumbnailFileException('olefile is not available')
        
    
    try:
        
        with olefile.OleFileIO( path ) as ole:
            
            # noinspection PyUnresolvedReferences
            num_words = ole.get_metadata().num_words
            
        
    except Exception as e:
        
        num_words = None
        
    
    return num_words
    
