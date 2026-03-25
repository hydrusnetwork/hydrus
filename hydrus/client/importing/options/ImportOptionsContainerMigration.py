from hydrus.client.importing.options import FileImportOptionsLegacy
from hydrus.client.importing.options import ImportOptionsContainer
from hydrus.client.importing.options import NoteImportOptionsLegacy
from hydrus.client.importing.options import TagImportOptionsLegacy

def SetImportOptions( import_options_container: ImportOptionsContainer.ImportOptionsContainer, import_options_type: int, potential_import_options: ImportOptionsContainer.ImportOptionsMetatype, optional_parent_container: ImportOptionsContainer.ImportOptionsContainer | None = None ):
    
    if optional_parent_container is not None:
        
        parent_import_options = optional_parent_container.GetImportOptions( import_options_type )
        
        if parent_import_options is not None and potential_import_options.GetSerialisableTuple() == parent_import_options.GetSerialisableTuple():
            
            return
            
        
    
    import_options_container.SetImportOptions( import_options_type, potential_import_options )
    

def ConvertLegacyOptionsToContainer(
    file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy | None = None,
    tag_import_options: TagImportOptionsLegacy.TagImportOptionsLegacy | None = None,
    note_import_options: NoteImportOptionsLegacy.NoteImportOptionsLegacy | None = None,
    optional_parent_container: ImportOptionsContainer.ImportOptionsContainer | None = None
) -> ImportOptionsContainer.ImportOptionsContainer:
    
    import_options_container = ImportOptionsContainer.ImportOptionsContainer()
    
    if file_import_options is not None and not file_import_options.IsDefault():
        
        prefetch_import_options = file_import_options.GetPrefetchImportOptions()
        
        if tag_import_options is not None and not tag_import_options.IsDefault():
            
            should_fetch_urls_blah = tag_import_options.ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB()
            should_fetch_hashes_blah = tag_import_options.ShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB()
            
            prefetch_import_options.SetShouldFetchMetadataEvenIfURLKnownAndFileAlreadyInDB( should_fetch_urls_blah )
            prefetch_import_options.SetShouldFetchMetadataEvenIfHashKnownAndFileAlreadyInDB( should_fetch_hashes_blah )
            
        
        location_import_options = file_import_options.GetLocationImportOptions()
        file_filtering_import_options = file_import_options.GetFileFilteringImportOptions()
        presentation_import_options = file_import_options.GetPresentationImportOptions()
        
        SetImportOptions( import_options_container, ImportOptionsContainer.IMPORT_OPTIONS_TYPE_PREFETCH, prefetch_import_options, optional_parent_container = optional_parent_container )
        SetImportOptions( import_options_container, ImportOptionsContainer.IMPORT_OPTIONS_TYPE_LOCATIONS, location_import_options, optional_parent_container = optional_parent_container )
        SetImportOptions( import_options_container, ImportOptionsContainer.IMPORT_OPTIONS_TYPE_FILE_FILTERING, file_filtering_import_options, optional_parent_container = optional_parent_container )
        SetImportOptions( import_options_container, ImportOptionsContainer.IMPORT_OPTIONS_TYPE_PRESENTATION, presentation_import_options, optional_parent_container = optional_parent_container )
        
    
    if tag_import_options is not None and not tag_import_options.IsDefault():
        
        tag_import_options_new = tag_import_options.GetTagImportOptions()
        tag_filtering_import_options = tag_import_options.GetTagFilteringImportOptions()
        
        SetImportOptions( import_options_container, ImportOptionsContainer.IMPORT_OPTIONS_TYPE_TAGS, tag_import_options_new, optional_parent_container = optional_parent_container )
        SetImportOptions( import_options_container, ImportOptionsContainer.IMPORT_OPTIONS_TYPE_TAG_FILTERING, tag_filtering_import_options, optional_parent_container = optional_parent_container )
        
    
    if note_import_options is not None and not note_import_options.IsDefault():
        
        note_import_options_new = note_import_options.GetNoteImportOptions()
        
        SetImportOptions( import_options_container, ImportOptionsContainer.IMPORT_OPTIONS_TYPE_NOTES, note_import_options_new, optional_parent_container = optional_parent_container )
        
    
    return import_options_container
    

def GenerateImportOptionsManagerFromOldSystem( 
    file_post_default_tag_import_options: TagImportOptionsLegacy.TagImportOptionsLegacy,
    watchable_default_tag_import_options: TagImportOptionsLegacy.TagImportOptionsLegacy,
    url_class_keys_to_default_tag_import_options: dict[ bytes, TagImportOptionsLegacy.TagImportOptionsLegacy ],
    file_post_default_note_import_options: NoteImportOptionsLegacy.NoteImportOptionsLegacy,
    watchable_default_note_import_options: NoteImportOptionsLegacy.NoteImportOptionsLegacy,
    url_class_keys_to_default_note_import_options: dict[ bytes, NoteImportOptionsLegacy.NoteImportOptionsLegacy ],
    quiet_file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy,
    loud_file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy
) -> ImportOptionsContainer.ImportOptionsManager:
    
    import_options_manager = ImportOptionsContainer.ImportOptionsManager.STATICGetEmptyButValidManager()
    
    global_import_options_container = ConvertLegacyOptionsToContainer( file_import_options = loud_file_import_options, tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy(), note_import_options = NoteImportOptionsLegacy.NoteImportOptionsLegacy() )
    quiet_import_options_container = ConvertLegacyOptionsToContainer( file_import_options = quiet_file_import_options, optional_parent_container = global_import_options_container )
    
    quiet_import_options_container_sans_presentation = quiet_import_options_container.Duplicate()
    quiet_import_options_container_sans_presentation.DeleteImportOptions( ImportOptionsContainer.IMPORT_OPTIONS_TYPE_PRESENTATION )
    
    import_options_manager.SetDefaultImportOptionsContainerForCallerType( ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL, global_import_options_container )
    import_options_manager.SetDefaultImportOptionsContainerForCallerType( ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION, quiet_import_options_container )
    import_options_manager.SetDefaultImportOptionsContainerForCallerType( ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER, quiet_import_options_container )
    import_options_manager.SetDefaultImportOptionsContainerForCallerType( ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_CLIENT_API, quiet_import_options_container_sans_presentation )
    
    file_post_import_options_container = ConvertLegacyOptionsToContainer(
        tag_import_options = file_post_default_tag_import_options,
        note_import_options = file_post_default_note_import_options,
        optional_parent_container = global_import_options_container
    )
    
    watchable_import_options_container = ConvertLegacyOptionsToContainer(
        tag_import_options = watchable_default_tag_import_options,
        note_import_options = watchable_default_note_import_options,
        optional_parent_container = global_import_options_container
    )
    
    import_options_manager.SetDefaultImportOptionsContainerForCallerType( ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_POST_URLS, file_post_import_options_container )
    import_options_manager.SetDefaultImportOptionsContainerForCallerType( ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS, watchable_import_options_container )
    
    all_url_class_keys = set()
    
    all_url_class_keys.update( url_class_keys_to_default_tag_import_options.keys() )
    all_url_class_keys.update( url_class_keys_to_default_note_import_options.keys() )
    
    for url_class_key in all_url_class_keys:
        
        tag_import_options = url_class_keys_to_default_tag_import_options.get( url_class_key, None )
        note_import_options = url_class_keys_to_default_note_import_options.get( url_class_key, None )
        
        url_class_import_options_container = ConvertLegacyOptionsToContainer( tag_import_options = tag_import_options, note_import_options = note_import_options )
        
        import_options_manager.SetDefaultImportOptionsContainerForURLClass( url_class_key, url_class_import_options_container )
        
    
    return import_options_manager
    
