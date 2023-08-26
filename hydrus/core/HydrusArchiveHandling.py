import zipfile

def ExtractSingleFileFromZip( path_to_zip, filename_to_extract, extract_into_file_path ):
    
    with zipfile.ZipFile( path_to_zip ) as zip_handle:
        
        with zip_handle.open( filename_to_extract ) as reader:
            
            with open( extract_into_file_path, "wb" ) as writer:
                
                writer.write( reader.read() )
                
            
        
    

def ReadSingleFileFromZip( path_to_zip, filename_to_extract ):
    
    with zipfile.ZipFile( path_to_zip ) as zip_handle:
        
        with zip_handle.open( filename_to_extract ) as reader:
            
            return reader.read()
            
        
def GetZipAsPath( path_to_zip, path_in_zip="" ):

    return zipfile.Path( path_to_zip, at=path_in_zip )
