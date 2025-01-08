import typing

from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientMetadataMigrationImporters

HOW_MANY_EXAMPLE_OBJECTS_TO_USE = 25

class MigrationTestContextFactory( object ):
    
    def GetExampleTestStrings( self, importer: ClientMetadataMigrationImporters.SingleFileMetadataImporter, sans_string_processing = False ):
        
        test_objects = self.GetTestObjects()
        
        if len( test_objects ) > 0:
            
            first_test_object = list( test_objects )[0]
            
            return self.GetExampleTestStringsForTestObject( importer, first_test_object, sans_string_processing = sans_string_processing )
            
        else:
            
            return []
            
        
    
    def GetExampleTestStringsForTestObject( self, importer: ClientMetadataMigrationImporters.SingleFileMetadataImporter, test_object: object, sans_string_processing = False ):
        
        try:
            
            if sans_string_processing:
                
                return importer.ImportSansStringProcessing( test_object )
                
            else:
                
                return importer.Import( test_object )
                
            
        except Exception as e:
            
            return [ str( e ) ]
            
        
    
    def GetTestObjects( self ) -> typing.Collection[ object ]:
        
        raise NotImplementedError()
        
    
    def GetTestObjectString( self, test_object: object ) -> str:
        
        raise NotImplementedError()
        
    

class MigrationTestContextFactorySidecar( MigrationTestContextFactory ):
    
    def __init__( self, example_file_paths: typing.Collection[ str ] ):
        
        super().__init__()
        
        self._example_file_paths = example_file_paths
        
    
    def GetExampleFilePaths( self ) -> typing.List[ str ]:
        
        return list( self._example_file_paths )
        
    
    def GetExampleTestStringsForTestObject( self, importer: ClientMetadataMigrationImporters.SingleFileMetadataImporterSidecar, test_object: str, sans_string_processing = False ):
        
        return super().GetExampleTestStringsForTestObject( importer, test_object, sans_string_processing = sans_string_processing )
        
    
    def GetTestObjects( self ) -> typing.Collection[ str ]:
        
        return self._example_file_paths
        
    
    def GetTestObjectString( self, test_object: str ) -> str:
        
        return test_object
        
    
    def SetExampleFilePaths( self, paths: typing.Collection[ str ] ):
        
        self._example_file_paths = paths
        
    

class MigrationTestContextFactoryMedia( MigrationTestContextFactory ):
    
    def __init__( self, example_media_results: typing.Collection[ ClientMediaResult.MediaResult ] ):
        
        super().__init__()
        
        self._example_media_results = example_media_results
        
    
    def GetExampleTestStringsForTestObject( self, importer: ClientMetadataMigrationImporters.SingleFileMetadataImporterMedia, test_object: ClientMediaResult.MediaResult, sans_string_processing = False ):
        
        return super().GetExampleTestStringsForTestObject( importer, test_object, sans_string_processing = sans_string_processing )
        
    
    def GetTestObjects( self ) -> typing.Collection[ ClientMediaResult.MediaResult ]:
        
        return self._example_media_results
        
    
    def GetTestObjectString( self, test_object: ClientMediaResult.MediaResult ) -> str:
        
        return test_object.GetHash().hex()
        
    
    def SetExampleMediaResults( self, media_results: typing.Collection[ ClientMediaResult.MediaResult ] ):
        
        self._example_media_results = media_results
        
    
