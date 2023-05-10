import re
import sys

def string_generator( version, capitalised_name ):
    
    match = re.match( r'^\d+', version )
    
    if match:
        
        version_number = int( match.group() )
        
    else:
        
        version_number = version
        
    
    lower_name = capitalised_name.lower()
    
    return f'''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers=(0, {version_number}, 0, 0),
    prodvers=(0, {version_number}, 0, 0),
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x4,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '040904b0',
        [StringStruct('FileDescription', 'Hydrus Network {capitalised_name}'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('InternalName', 'Hydrus Network {capitalised_name}'),
        StringStruct('LegalCopyright', 'WTFPL'),
        StringStruct('OriginalFilename', 'hydrus_{lower_name}.exe'),
        StringStruct('ProductName', 'Hydrus Network {capitalised_name}'),
        StringStruct('ProductVersion', '{version}')])
      ]), 
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)'''

if __name__ == '__main__':
    
    version_with_v = sys.argv[1]
    
    if version_with_v.startswith( 'v' ):
        
        version = version_with_v[1:]
        
    else:
        
        version = version_with_v
        
    
    with open( 'client_file_version_info.txt', 'w', encoding = 'utf-8' ) as f:
        
        f.write( string_generator( version, 'Client' ) )
        
    
    with open( 'server_file_version_info.txt', 'w', encoding = 'utf-8' ) as f:
        
        f.write( string_generator( version, 'Server' ) )
        
    
