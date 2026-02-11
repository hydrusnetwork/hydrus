import os

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

INSTALL_STATIC_DIR = os.path.join( HC.BASE_DIR, 'static' )

USE_USER_STATIC_DIR = True

def GetStaticIconPath( name: str, force_install_dir = False, force_svg = False ) -> str:
    
    ( svg_path, was_userdir ) = GetStaticPathWithResult( name + '.svg', force_install_dir = force_install_dir )
    
    if not force_svg and not was_userdir:
        
        # a little ugly, but user png has preference over install svg
        ( png_path, was_userdir ) = GetStaticPathWithResult( name + '.png', force_install_dir = force_install_dir )
        
        if was_userdir:
            
            return png_path
            
        
    
    if os.path.exists( svg_path ):
        
        path = svg_path
        
    else:
        
        if force_svg:
            
            raise HydrusExceptions.NotFoundException( f'No SVG with the name "{name}"!' )
            
        else:
            
            png_path = GetStaticPath( name + '.png', force_install_dir = force_install_dir )
            
            path = png_path
            
        
    
    return path
    

def GetStaticPath( sub_path: str, force_install_dir = False ):
    
    ( path, was_userdir ) = GetStaticPathWithResult( sub_path, force_install_dir = force_install_dir )
    
    return path
    

def GetStaticPathWithResult( sub_path: str, force_install_dir = False ):
    
    if not force_install_dir and USE_USER_STATIC_DIR and HG.controller is not None:
        
        user_path = os.path.join( HG.controller.GetDBDir(), 'static', sub_path )
        
        if os.path.exists( user_path ):
            
            return ( user_path, True )
            
        
    
    return ( os.path.join( INSTALL_STATIC_DIR, sub_path ), False )
    

def GetRatingSVGPath( name ) -> str:
    
    name = os.path.join( HC.USERPATH_SVG_ICON, name )
    
    path = GetStaticIconPath( name, force_svg = True )
    
    if os.path.exists( path ):
        
        return path
        
    else:
        
        raise HydrusExceptions.NotFoundException( f'Did not have a rating SVG called "{name}"!' )
        
    

def ListStaticDirFilePaths( sub_dir_path: str ):
    
    user_path = GetStaticPath( sub_dir_path )
    install_path = GetStaticPath( sub_dir_path, force_install_dir = True )
    
    dirs_to_do = []
    
    if user_path != install_path:
        
        dirs_to_do.append( user_path )
        
    
    dirs_to_do.append( install_path )
    
    file_paths = []
    
    for dir_to_do in dirs_to_do:
        
        if not os.path.exists( dir_to_do ):
            
            continue
            
        
        for filename in list( os.listdir( dir_to_do ) ):
            
            path = os.path.join( dir_to_do, filename )
            
            if os.path.isfile( path ):
                
                if path in file_paths: # prefer user dir to overwrite
                    
                    continue
                    
                
                file_paths.append( path )
                
            
        
    
    return file_paths
    
