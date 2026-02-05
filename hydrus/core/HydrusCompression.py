import zlib

LZ4_OK = False

try:
    
    import lz4
    import lz4.block
    
    LZ4_OK = True
    
except Exception as e: # ImportError wasn't enough here as Linux went up the shoot with a __version__ doesn't exist bs
    
    pass # this is no big deal
    

def CompressBytesToBytes( obj_bytes: bytes ) -> bytes:
    
    return zlib.compress( obj_bytes, 9 )
    
def CompressFastBytesToBytes( obj_bytes: bytes ) -> bytes:
    
    if LZ4_OK:
        
        return lz4.block.compress( obj_bytes )
        
    else:
        
        return obj_bytes
        
    
def CompressStringToBytes( obj_string: str ) -> bytes:
    
    obj_bytes = bytes( obj_string, 'utf-8' )
    
    return CompressBytesToBytes( obj_bytes )
    
def DecompressBytesToBytes( compressed_bytes: bytes ) -> bytes:
    
    try:
        
        obj_bytes = zlib.decompress( compressed_bytes )
        
    except zlib.error:
        
        if LZ4_OK:
            
            obj_bytes = lz4.block.decompress( compressed_bytes )
            
        else:
            
            raise
            
        
    
    return obj_bytes
    
def DecompressBytesToString( compressed_bytes: bytes ) -> str:
    
    obj_bytes = DecompressBytesToBytes( compressed_bytes )
    
    obj_string = str( obj_bytes, 'utf-8' )
    
    return obj_string
    
def DecompressFastBytesToBytes( compressed_bytes: bytes ) -> bytes:
    
    if LZ4_OK:
        
        return lz4.block.decompress( compressed_bytes )
        
    else:
        
        return compressed_bytes
        
    
