import collections
import re
import zipfile

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions

def ExtractSingleFileFromZip( path_to_zip, filename_to_extract, extract_into_file_path ):
    
    with zipfile.ZipFile( path_to_zip ) as zip_handle:
        
        with zip_handle.open( filename_to_extract ) as reader:
            
            with open( extract_into_file_path, "wb" ) as writer:
                
                writer.write( reader.read() )
                
            
        
    

def ExtractCoverPage( path_to_zip, extract_path ):
    
    with zipfile.ZipFile( path_to_zip ) as zip_handle:
        
        path = GetCoverPagePath( zip_handle )
        
        with zip_handle.open( path ) as reader:
            
            with open( extract_path, 'wb' ) as writer:
                
                writer.write( reader.read() )
                
            
        
    

def GetCoverPagePath( zip_handle: zipfile.ZipFile ):
    
    # this probably depth-first fails with a crazy multiple-nested-subdirectory structure, but we'll cross that bridge when we come to it
    all_file_paths = [ zip_info.filename for zip_info in zip_handle.infolist() if not zip_info.is_dir() ]
    
    HydrusData.HumanTextSort( all_file_paths )
    
    for path in all_file_paths:
        
        if '.' in path:
            
            ext_with_dot = '.' + path.split( '.' )[-1]
            
            if ext_with_dot in HC.IMAGE_FILE_EXTS:
                
                return path
                
            
        
    
    raise HydrusExceptions.DamagedOrUnusualFileException( 'Sorry, could not find an image file in there!' )
    

def GetSingleFileFromZipBytes( path_to_zip, path_in_zip ):
    
    return GetZipAsPath( path_to_zip, path_in_zip = path_in_zip ).read_bytes()
    

def GetZipAsPath( path_to_zip, path_in_zip="" ):
    
    return zipfile.Path( path_to_zip, at=path_in_zip )
    

def IsEncryptedZip( path_to_zip ):
    
    ENCRYPTED_FLAG = 0x1
    
    try:
        
        with zipfile.ZipFile( path_to_zip ) as zip_handle:
            
            zip_infos = zip_handle.infolist()
            
            for zip_info in zip_infos:
                
                is_encrypted = zip_info.flag_bits & ENCRYPTED_FLAG
                
                if is_encrypted:
                    
                    return True
                    
                
            
            return False
            
        
    except:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Could not open this zip at all!' )
        
    

def filename_has_image_ext( filename: str ):
    
    if '.' in filename:
        
        ext_with_dot = '.' + filename.split( '.' )[-1]
        
        if ext_with_dot in HC.IMAGE_FILE_EXTS:
            
            return True
            
        
    
    return False
    

def filename_has_video_ext( filename: str ):
    
    if '.' in filename:
        
        ext_with_dot = '.' + filename.split( '.' )[-1]
        
        if ext_with_dot in HC.VIDEO_FILE_EXTS:
            
            return True
            
        
    
    return False
    

def ZipLooksLikeCBZ( path_to_zip ):
    
    # TODO: we should probably wangle this away from 'zip' and towards 'archive', but it is fine as a first step
    
    # what does a Comic Book Archive look like? it is ad-hoc, not rigorous, so be forgiving
    # it is a list of images
    # they may be flat in the base, or they may be in one or more subfolders
    # they may be accompanied by extra metadata files like: md5sum, .sfv/.SFV, .nfo, comicbook.xml, metadata.txt
    # they _cannot_ be accompanied by .exe, .zip, .unitypackage, .psd, or other gubbins
    # nothing else
    
    directories_to_image_filenames = collections.defaultdict( set )
    
    directories_with_stuff_in = set()
    num_weird_files = 0
    num_images = 0
    num_images_with_numbers = 0
    num_weird_files_allowed_per_directory = 5
    num_images_needed_per_directory = 1
    totally_ok_weird_filenames = { 'md5sum', 'comicbook.xml', 'metadata.txt', 'info.txt' }
    weird_filename_extension_whitelist = { '.sfv', '.nfo', '.txt', '.xml', '.json' }
    
    with zipfile.ZipFile( path_to_zip ) as zip_handle:
        
        for zip_info in zip_handle.infolist():
            
            if zip_info.is_dir():
                
                continue
                
            
            filename = zip_info.filename
            
            if '/' in filename:
                
                directory_path = '/'.join( filename.split( '/' )[:-1] )
                
                filename = filename.split( '/' )[-1]
                
            else:
                
                directory_path = ''
                
            
            directories_with_stuff_in.add( directory_path )
            
            filename = filename.lower()
            
            if filename in totally_ok_weird_filenames:
                
                continue
                
            
            if filename_has_image_ext( filename ):
                
                num_images += 1
                
                if re.search( r'\d', filename ) is not None:
                    
                    num_images_with_numbers += 1
                    
                
                directories_to_image_filenames[ directory_path ].add( filename )
                
                continue
                
            else:
                
                if '.' in filename:
                    
                    ext_with_dot = '.' + filename.split( '.' )[-1]
                    
                    if ext_with_dot in weird_filename_extension_whitelist:
                        
                        num_weird_files += 1
                        
                    else:
                        
                        # we got ourselves a .mp4 or .unitypackage or whatever. not a cbz!
                        return False
                        
                    
                else:
                    
                    # we out here with a 'gonk' file. not a cbz!
                    return False
                    
                
            
        
        # although we want to broadly check there are files with numbers, we don't want tempt ourselves into searching for 0 or 1. some 'chapters' start at page 55
        # a two-paged comic is the minimum permissible
        if num_images_with_numbers <= 1:
            
            return False
            
        
        try:
            
            path = GetCoverPagePath( zip_handle )
            
            with zip_handle.open( path ) as reader:
                
                reader.read()
                
            
        except:
            
            return False
            
        
    
    if len( directories_to_image_filenames ) > 0:
        
        directories_to_looks_good_scores = {}
        
        for ( directory_path, image_filenames ) in directories_to_image_filenames.items():
            
            # ok, so a zip that has fifteen different filename styles is not a cbz
            # one that is all "Coolguy Adventures-c4-p001.jpg" however is!
            
            # so let's take all the numbers and figure out how commonly the image filenames are templated
            
            unique_numberless_filenames = { re.sub( r'\d', '', filename ) for filename in image_filenames }
            
            magical_uniqueness_percentage = ( len( unique_numberless_filenames ) - 1 ) / len( image_filenames )
            
            directories_to_looks_good_scores[ directory_path ] = magical_uniqueness_percentage
            
        
        all_percentages = list( directories_to_looks_good_scores.values() )
        
        average_directory_good = sum( all_percentages ) / len( all_percentages )
        
        # experimentally, I haven't seen this go above 0.103 on a legit cbz
        if average_directory_good > 0.2:
            
            return False
            
        
    
    if num_weird_files * len( directories_with_stuff_in ) > num_weird_files_allowed_per_directory:
        
        return False
        
    
    if num_images * len( directories_with_stuff_in ) < num_images_needed_per_directory:
        
        return False
        
    
    return True
    

def MimeFromOpenDocument( path ):
    
    try:
        
        mimetype_data = GetZipAsPath( path, 'mimetype' ).read_text()
        
        filetype = HC.mime_enum_lookup.get(mimetype_data, None)

        return filetype if filetype in HC.OPEN_DOCUMENT_ZIPS else None
        
    except:
        
        return None
        
    
