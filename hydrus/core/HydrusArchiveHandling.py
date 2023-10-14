import zipfile

from hydrus.core import HydrusConstants as HC

def ExtractSingleFileFromZip( path_to_zip, filename_to_extract, extract_into_file_path ):
    
    with zipfile.ZipFile( path_to_zip ) as zip_handle:
        
        with zip_handle.open( filename_to_extract ) as reader:
            
            with open( extract_into_file_path, "wb" ) as writer:
                
                writer.write( reader.read() )
    

def GetZipAsPath( path_to_zip, path_in_zip="" ):
    
    return zipfile.Path( path_to_zip, at=path_in_zip )
    

def MimeFromOpenDocument( path ):
    
    try:
        
        mimetype_data = GetZipAsPath( path, 'mimetype' ).read_text()
        
        filetype = HC.mime_enum_lookup.get(mimetype_data, None)

        return filetype if filetype in HC.OPEN_DOCUMENT_ZIPS else None
        
    except:
        
        return None
        
    
