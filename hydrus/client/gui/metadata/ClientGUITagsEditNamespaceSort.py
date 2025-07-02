import re

from qtpy import QtWidgets as QW

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTags

from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.metadata import ClientTags

def EditNamespaceSort( win: QW.QWidget, sort_data ):
    
    ( namespaces, tag_display_type ) = sort_data
    
    # users might want to add a namespace with a hyphen in it, so in lieu of a nice list to edit we'll just escape for now mate
    correct_char = '-'
    escaped_char = '\\-'
    
    escaped_namespaces = [ namespace.replace( correct_char, escaped_char ) for namespace in namespaces ]
    
    edit_string = '-'.join( escaped_namespaces )
    
    message = 'Write the namespaces you would like to sort by here, separated by hyphens. Any namespace in any of your sort definitions will be added to the collect-by menu.'
    message += '\n' * 2
    message += 'If the namespace you want to add has a hyphen, like \'creator-id\', instead type it with a backslash escape, like \'creator\\-id-page\'.'
    
    try:
        
        edited_string = ClientGUIDialogsQuick.EnterText( win, message, allow_blank = False, default = edit_string )
        
    except HydrusExceptions.CancelledException:
        
        raise
        
    
    edited_escaped_namespaces = re.split( r'(?<!\\)-', edited_string )
    
    edited_namespaces = [ namespace.replace( escaped_char, correct_char ) for namespace in edited_escaped_namespaces ]
    
    edited_namespaces = [ HydrusTags.CleanTag( namespace ) for namespace in edited_namespaces if HydrusTags.TagOK( namespace ) ]
    
    if len( edited_namespaces ) > 0:
        
        if CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            available_types = [
                ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL,
                ClientTags.TAG_DISPLAY_SELECTION_LIST,
                ClientTags.TAG_DISPLAY_SINGLE_MEDIA
            ]
            
            choice_tuples = [ ( ClientTags.tag_display_str_lookup[ tag_display_type ], tag_display_type, ClientTags.tag_display_str_lookup[ tag_display_type ] ) for tag_display_type in available_types ]
            
            message = 'If you filter your different tag views (e.g. hiding the PTR\'s title tags), sorting on those views may give a different order. If you are not sure on this, set \'display tags\'.'
            
            try:
                
                tag_display_type = ClientGUIDialogsQuick.SelectFromListButtons( win, 'select tag view to sort on', choice_tuples = choice_tuples, message = message )
                
            except HydrusExceptions.CancelledException:
                
                raise HydrusExceptions.VetoException()
                
            
        else:
            
            tag_display_type = ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL
            
        
        return ( tuple( edited_namespaces ), tag_display_type )
        
    
    raise HydrusExceptions.VetoException()
    
