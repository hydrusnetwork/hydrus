import ClientConstants as CC
import ClientGUIDialogs
import HydrusConstants as HC
import HydrusData
import HydrusGlobals
import HydrusTagArchive
import HydrusTags
import os
import wx

def ExportToHTA( parent, service_key, hashes ):
    
    with wx.FileDialog( parent, style = wx.FD_SAVE, defaultFile = 'archive.db' ) as dlg:
        
        if dlg.ShowModal() == wx.ID_OK:
            
            path = HydrusData.ToUnicode( dlg.GetPath() )
            
        else:
            
            return
            
        
    
    message = 'Would you like to use hydrus\'s normal hash type, or an alternative?'
    message += os.linesep * 2
    message += 'Hydrus uses SHA256 to identify files, but other services use different standards. MD5, SHA1 and SHA512 are available, but only for local files, which may limit your export.'
    message += os.linesep * 2
    message += 'If you do not know what this stuff means, click \'normal\'.'
    
    with ClientGUIDialogs.DialogYesNo( parent, message, title = 'Choose which hash type.', yes_label = 'normal', no_label = 'alternative' ) as dlg:
        
        result = dlg.ShowModal()
        
        if result in ( wx.ID_YES, wx.ID_NO ):
            
            if result == wx.ID_YES:
                
                hash_type = HydrusTagArchive.HASH_TYPE_SHA256
                
            else:
                
                list_of_tuples = []
                
                list_of_tuples.append( ( 'md5', HydrusTagArchive.HASH_TYPE_MD5 ) )
                list_of_tuples.append( ( 'sha1', HydrusTagArchive.HASH_TYPE_SHA1 ) )
                list_of_tuples.append( ( 'sha512', HydrusTagArchive.HASH_TYPE_SHA512 ) )
                
                with ClientGUIDialogs.DialogSelectFromList( parent, 'Select the hash type', list_of_tuples ) as hash_dlg:
                    
                    if hash_dlg.ShowModal() == wx.ID_OK:
                        
                        hash_type = hash_dlg.GetChoice()
                        
                    else:
                        
                        return
                        
                    
                
            
        
    
    if hash_type is not None:
        
        HydrusGlobals.client_controller.Write( 'export_mappings', path, service_key, hash_type, hashes )
        
    
def ImportFromHTA( parent, hta_path, tag_service_key, hashes ):
    
    hta = HydrusTagArchive.HydrusTagArchive( hta_path )
    
    potential_namespaces = hta.GetNamespaces()
    
    hash_type = hta.GetHashType() # this tests if the hta can produce a hashtype
    
    del hta
    
    service = HydrusGlobals.client_controller.GetServicesManager().GetService( tag_service_key )
    
    service_type = service.GetServiceType()
    
    can_delete = True
    
    if service_type == HC.TAG_REPOSITORY:
        
        if service.HasPermission( HC.CONTENT_TYPE_MAPPINGS, HC.PERMISSION_ACTION_OVERRULE ):
            
            can_delete = False
            
        
    
    if can_delete:
        
        text = 'Would you like to add or delete the archive\'s tags?'
        
        with ClientGUIDialogs.DialogYesNo( parent, text, title = 'Add or delete?', yes_label = 'add', no_label = 'delete' ) as dlg_add:
            
            result = dlg_add.ShowModal()
            
            if result == wx.ID_YES: adding = True
            elif result == wx.ID_NO: adding = False
            else: return
            
        
    else:
        
        text = 'You cannot quickly delete tags from this service, so I will assume you want to add tags.'
        
        wx.MessageBox( text )
        
        adding = True
        
    
    text = 'Choose which namespaces to '
    
    if adding: text += 'add.'
    else: text += 'delete.'
    
    with ClientGUIDialogs.DialogCheckFromListOfStrings( parent, text, HydrusData.ConvertUglyNamespacesToPrettyStrings( potential_namespaces ) ) as dlg_namespaces:
        
        if dlg_namespaces.ShowModal() == wx.ID_OK:
            
            namespaces = HydrusData.ConvertPrettyStringsToUglyNamespaces( dlg_namespaces.GetChecked() )
            
            if hash_type == HydrusTagArchive.HASH_TYPE_SHA256:
                
                text = 'This tag archive can be fully merged into your database, but this may be more than you want.'
                text += os.linesep * 2
                text += 'Would you like to import the tags only for files you actually have, or do you want absolutely everything?'
                
                with ClientGUIDialogs.DialogYesNo( parent, text, title = 'How much do you want?', yes_label = 'just for my local files', no_label = 'everything' ) as dlg_add:
                    
                    result = dlg_add.ShowModal()
                    
                    if result == wx.ID_YES:
                        
                        file_service_key = CC.LOCAL_FILE_SERVICE_KEY
                        
                    elif result == wx.ID_NO:
                        
                        file_service_key = CC.COMBINED_FILE_SERVICE_KEY
                        
                    else:
                        
                        return
                        
                    
                
            else:
                
                file_service_key = CC.LOCAL_FILE_SERVICE_KEY
                
            
            text = 'Are you absolutely sure you want to '
            
            if adding: text += 'add'
            else: text += 'delete'
            
            text += ' the namespaces:'
            text += os.linesep * 2
            text += os.linesep.join( HydrusData.ConvertUglyNamespacesToPrettyStrings( namespaces ) )
            text += os.linesep * 2
            
            file_service = HydrusGlobals.client_controller.GetServicesManager().GetService( file_service_key )
            
            text += 'For '
            
            if hashes is None:
                
                text += 'all'
                
            else:
                
                text += HydrusData.ConvertIntToPrettyString( len( hashes ) )
                
            
            text += ' files in \'' + file_service.GetName() + '\''
            
            if adding: text += ' to '
            else: text += ' from '
            
            text += '\'' + service.GetName() + '\'?'
            
            with ClientGUIDialogs.DialogYesNo( parent, text ) as dlg_final:
                
                if dlg_final.ShowModal() == wx.ID_YES:
                    
                    HydrusGlobals.client_controller.pub( 'sync_to_tag_archive', hta_path, tag_service_key, file_service_key, adding, namespaces, hashes )
                    
                
            
        
    
def RenderTag( tag, render_for_user ):
    
    ( namespace, subtag ) = HydrusTags.SplitTag( tag )
    
    if namespace == '':
        
        return subtag
        
    else:
        
        if render_for_user:
            
            new_options = HydrusGlobals.client_controller.GetNewOptions()
            
            if new_options.GetBoolean( 'show_namespaces' ):
                
                connector = new_options.GetString( 'namespace_connector' )
                
            else:
                
                return subtag
                
            
        else:
            
            connector = ':'
            
        
        return namespace + connector + subtag
        
    
