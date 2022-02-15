import os
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDBBase
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTags

from hydrus.client.db import ClientDBModule
from hydrus.client.networking import ClientNetworkingFunctions

class ClientDBMasterHashes( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor ):
        
        ClientDBModule.ClientDBModule.__init__( self, 'client hashes master', cursor )
        
        self._hash_ids_to_hashes_cache = {}
        
    
    def _GetCriticalTableNames( self ) -> typing.Collection[ str ]:
        
        return {
            'external_master.hashes'
        }
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        index_generation_dict[ 'external_master.local_hashes' ] = [
            ( [ 'md5' ], False, 400 ),
            ( [ 'sha1' ], False, 400 ),
            ( [ 'sha512' ], False, 400 )
        ]
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'external_master.hashes' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, hash BLOB_BYTES UNIQUE );', 400 ),
            'external_master.local_hashes' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, md5 BLOB_BYTES, sha1 BLOB_BYTES, sha512 BLOB_BYTES );', 400 )
        }
        
    
    def _PopulateHashIdsToHashesCache( self, hash_ids, exception_on_error = False ):
        
        if len( self._hash_ids_to_hashes_cache ) > 100000:
            
            if not isinstance( hash_ids, set ):
                
                hash_ids = set( hash_ids )
                
            
            self._hash_ids_to_hashes_cache = { hash_id : hash for ( hash_id, hash ) in self._hash_ids_to_hashes_cache.items() if hash_id in hash_ids }
            
        
        uncached_hash_ids = { hash_id for hash_id in hash_ids if hash_id not in self._hash_ids_to_hashes_cache }
        
        if len( uncached_hash_ids ) > 0:
            
            pubbed_error = False
            
            if len( uncached_hash_ids ) == 1:
                
                ( uncached_hash_id, ) = uncached_hash_ids
                
                rows = self._Execute( 'SELECT hash_id, hash FROM hashes WHERE hash_id = ?;', ( uncached_hash_id, )  ).fetchall()
                
            else:
                
                with self._MakeTemporaryIntegerTable( uncached_hash_ids, 'hash_id' ) as temp_table_name:
                    
                    # temp hash_ids to actual hashes
                    rows = self._Execute( 'SELECT hash_id, hash FROM {} CROSS JOIN hashes USING ( hash_id );'.format( temp_table_name ) ).fetchall()
                    
                
            
            uncached_hash_ids_to_hashes = dict( rows )
            
            if len( uncached_hash_ids_to_hashes ) < len( uncached_hash_ids ):
                
                for hash_id in uncached_hash_ids:
                    
                    if hash_id not in uncached_hash_ids_to_hashes:
                        
                        if exception_on_error:
                            
                            raise HydrusExceptions.DataMissing( 'Did not find all entries for those hash ids!' )
                            
                        
                        HydrusData.DebugPrint( 'Database hash error: hash_id ' + str( hash_id ) + ' was missing!' )
                        HydrusData.PrintException( Exception( 'Missing file identifier stack trace.' ) )
                        
                        if not pubbed_error:
                            
                            HydrusData.ShowText( 'A file identifier was missing! This is a serious error that means your client database has an orphan file id! Think about contacting hydrus dev!' )
                            
                            pubbed_error = True
                            
                        
                        hash = bytes.fromhex( 'aaaaaaaaaaaaaaaa' ) + os.urandom( 16 )
                        
                        uncached_hash_ids_to_hashes[ hash_id ] = hash
                        
                    
                
            
            self._hash_ids_to_hashes_cache.update( uncached_hash_ids_to_hashes )
            
        
    
    def GetExtraHash( self, hash_type, hash_id ) -> bytes:
        
        result = self._Execute( 'SELECT {} FROM local_hashes WHERE hash_id = ?;'.format( hash_type ), ( hash_id, ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.DataMissing( '{} not available for file {}!'.format( hash_type, hash_id ) )
            
        
        ( hash, ) = result
        
        return hash
        
    
    def GetFileHashes( self, given_hashes, given_hash_type, desired_hash_type ) -> typing.Collection[ bytes ]:
        
        if given_hash_type == 'sha256':
            
            hash_ids = self.GetHashIds( given_hashes )
            
        else:
            
            hash_ids = []
            
            for given_hash in given_hashes:
                
                if given_hash is None:
                    
                    continue
                    
                
                result = self._Execute( 'SELECT hash_id FROM local_hashes WHERE {} = ?;'.format( given_hash_type ), ( sqlite3.Binary( given_hash ), ) ).fetchone()
                
                if result is not None:
                    
                    ( hash_id, ) = result
                    
                    hash_ids.append( hash_id )
                    
                
            
        
        if desired_hash_type == 'sha256':
            
            desired_hashes = self.GetHashes( hash_ids )
            
        else:
            
            desired_hashes = [ desired_hash for ( desired_hash, ) in self._Execute( 'SELECT {} FROM local_hashes WHERE hash_id IN {};'.format( desired_hash_type, HydrusData.SplayListForDB( hash_ids ) ) ) ]
            
        
        return desired_hashes
        
    
    def GetHash( self, hash_id ) -> bytes:
        
        self._PopulateHashIdsToHashesCache( ( hash_id, ) )
        
        return self._hash_ids_to_hashes_cache[ hash_id ]
        
    
    def GetHashes( self, hash_ids ) -> typing.List[ bytes ]:
        
        self._PopulateHashIdsToHashesCache( hash_ids )
        
        return [ self._hash_ids_to_hashes_cache[ hash_id ] for hash_id in hash_ids ]
        
    
    def GetHashId( self, hash ) -> int:
        
        result = self._Execute( 'SELECT hash_id FROM hashes WHERE hash = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
        
        if result is None:
            
            self._Execute( 'INSERT INTO hashes ( hash ) VALUES ( ? );', ( sqlite3.Binary( hash ), ) )
            
            hash_id = self._GetLastRowId()
            
        else:
            
            ( hash_id, ) = result
            
        
        return hash_id
        
    
    def GetHashIdFromExtraHash( self, hash_type, hash ):
        
        if hash_type == 'md5':
            
            result = self._Execute( 'SELECT hash_id FROM local_hashes WHERE md5 = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
            
        elif hash_type == 'sha1':
            
            result = self._Execute( 'SELECT hash_id FROM local_hashes WHERE sha1 = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
            
        elif hash_type == 'sha512':
            
            result = self._Execute( 'SELECT hash_id FROM local_hashes WHERE sha512 = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
            
        
        if result is None:
            
            raise HydrusExceptions.DataMissing( 'Hash Id not found for {} hash {}!'.format( hash_type, hash.hex() ) )
            
        
        ( hash_id, ) = result
        
        return hash_id
        
    
    def GetHashIds( self, hashes ) -> typing.Set[ int ]:
        
        hash_ids = set()
        hashes_not_in_db = set()
        
        for hash in hashes:
            
            if hash is None:
                
                continue
                
            
            result = self._Execute( 'SELECT hash_id FROM hashes WHERE hash = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
            
            if result is None:
                
                hashes_not_in_db.add( hash )
                
            else:
                
                ( hash_id, ) = result
                
                hash_ids.add( hash_id )
                
            
        
        if len( hashes_not_in_db ) > 0:
            
            self._ExecuteMany( 'INSERT INTO hashes ( hash ) VALUES ( ? );', ( ( sqlite3.Binary( hash ), ) for hash in hashes_not_in_db ) )
            
            for hash in hashes_not_in_db:
                
                ( hash_id, ) = self._Execute( 'SELECT hash_id FROM hashes WHERE hash = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
                
                hash_ids.add( hash_id )
                
            
        
        return hash_ids
        
    
    def GetHashIdsToHashes( self, hash_ids = None, hashes = None ):
        
        if hash_ids is not None:
            
            self._PopulateHashIdsToHashesCache( hash_ids, exception_on_error = True )
            
            hash_ids_to_hashes = { hash_id : self._hash_ids_to_hashes_cache[ hash_id ] for hash_id in hash_ids }
            
        elif hashes is not None:
            
            hash_ids_to_hashes = { self.GetHashId( hash ) : hash for hash in hashes }
            
        
        return hash_ids_to_hashes
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            return [ ( 'local_hashes', 'hash_id' ) ]
            
        
        return []
        
    
    def HasExtraHashes( self, hash_id ):
        
        result = self._Execute( 'SELECT 1 FROM local_hashes WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        return result is not None
        
    
    def HasHash( self, hash ):
        
        result = self._Execute( 'SELECT 1 FROM hashes WHERE hash = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
        
        return result is not None
        
    
    def HasHashId( self, hash_id: int ):
        
        result = self._Execute( 'SELECT 1 FROM hashes WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        return result is not None
        
    
    def SetExtraHashes( self, hash_id, md5, sha1, sha512 ):
        
        self._Execute( 'INSERT OR IGNORE INTO local_hashes ( hash_id, md5, sha1, sha512 ) VALUES ( ?, ?, ?, ? );', ( hash_id, sqlite3.Binary( md5 ), sqlite3.Binary( sha1 ), sqlite3.Binary( sha512 ) ) )
        
    
class ClientDBMasterTexts( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor ):
        
        ClientDBModule.ClientDBModule.__init__( self, 'client texts master', cursor )
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'external_master.labels' : ( 'CREATE TABLE IF NOT EXISTS {} ( label_id INTEGER PRIMARY KEY, label TEXT UNIQUE );', 400 ),
            'external_master.notes' : ( 'CREATE TABLE IF NOT EXISTS {} ( note_id INTEGER PRIMARY KEY, note TEXT UNIQUE );', 400 ),
            'external_master.texts' : ( 'CREATE TABLE IF NOT EXISTS {} ( text_id INTEGER PRIMARY KEY, text TEXT UNIQUE );', 400 ),
            'external_caches.notes_fts4' : ( 'CREATE VIRTUAL TABLE IF NOT EXISTS {} USING fts4( note );', 400 )
        }
        
    
    def _RepairRepopulateTables( self, repopulate_table_names, cursor_transaction_wrapper: HydrusDBBase.DBCursorTransactionWrapper ):
        
        if 'external_caches.notes_fts4' in repopulate_table_names:
            
            self._Execute( 'REPLACE INTO notes_fts4 ( docid, note ) SELECT note_id, note FROM notes;' )
            
        
    
    def GetLabelId( self, label ):
        
        result = self._Execute( 'SELECT label_id FROM labels WHERE label = ?;', ( label, ) ).fetchone()
        
        if result is None:
            
            self._Execute( 'INSERT INTO labels ( label ) VALUES ( ? );', ( label, ) )
            
            label_id = self._GetLastRowId()
            
        else:
            
            ( label_id, ) = result
            
        
        return label_id
        
    
    def GetNoteId( self, note: str ) -> int:
        
        result = self._Execute( 'SELECT note_id FROM notes WHERE note = ?;', ( note, ) ).fetchone()
        
        if result is None:
            
            self._Execute( 'INSERT INTO notes ( note ) VALUES ( ? );', ( note, ) )
            
            note_id = self._GetLastRowId()
            
            self._Execute( 'REPLACE INTO notes_fts4 ( docid, note ) VALUES ( ?, ? );', ( note_id, note ) )
            
        else:
            
            ( note_id, ) = result
            
        
        return note_id
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        return []
        
    
    def GetText( self, text_id ):
        
        result = self._Execute( 'SELECT text FROM texts WHERE text_id = ?;', ( text_id, ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.DataMissing( 'Text lookup error in database' )
            
        
        ( text, ) = result
        
        return text
        
    
    def GetTextId( self, text ):
        
        result = self._Execute( 'SELECT text_id FROM texts WHERE text = ?;', ( text, ) ).fetchone()
        
        if result is None:
            
            self._Execute( 'INSERT INTO texts ( text ) VALUES ( ? );', ( text, ) )
            
            text_id = self._GetLastRowId()
            
        else:
            
            ( text_id, ) = result
            
        
        return text_id
        
    
class ClientDBMasterTags( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor ):
        
        ClientDBModule.ClientDBModule.__init__( self, 'client tags master', cursor )
        
        self.null_namespace_id = None
        
        self._tag_ids_to_tags_cache = {}
        
    
    def _GetCriticalTableNames( self ) -> typing.Collection[ str ]:
        
        return {
            'external_master.namespaces',
            'external_master.subtags',
            'external_master.tags'
        }
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        index_generation_dict[ 'external_master.tags' ] = [
            ( [ 'subtag_id' ], False, 400 ),
            ( [ 'namespace_id', 'subtag_id' ], True, 412 )
        ]
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'external_master.namespaces' : ( 'CREATE TABLE IF NOT EXISTS {} ( namespace_id INTEGER PRIMARY KEY, namespace TEXT UNIQUE );', 400 ),
            'external_master.subtags' : ( 'CREATE TABLE IF NOT EXISTS {} ( subtag_id INTEGER PRIMARY KEY, subtag TEXT UNIQUE );', 400 ),
            'external_master.tags' : ( 'CREATE TABLE IF NOT EXISTS {} ( tag_id INTEGER PRIMARY KEY, namespace_id INTEGER, subtag_id INTEGER );', 400 )
        }
        
    
    def _PopulateTagIdsToTagsCache( self, tag_ids ):
        
        if len( self._tag_ids_to_tags_cache ) > 100000:
            
            if not isinstance( tag_ids, set ):
                
                tag_ids = set( tag_ids )
                
            
            self._tag_ids_to_tags_cache = { tag_id : tag for ( tag_id, tag ) in self._tag_ids_to_tags_cache.items() if tag_id in tag_ids }
            
        
        uncached_tag_ids = { tag_id for tag_id in tag_ids if tag_id not in self._tag_ids_to_tags_cache }
        
        if len( uncached_tag_ids ) > 0:
            
            if len( uncached_tag_ids ) == 1:
                
                ( uncached_tag_id, ) = uncached_tag_ids
                
                rows = self._Execute( 'SELECT tag_id, namespace, subtag FROM tags NATURAL JOIN namespaces NATURAL JOIN subtags WHERE tag_id = ?;', ( uncached_tag_id, ) ).fetchall()
                
            else:
                
                with self._MakeTemporaryIntegerTable( uncached_tag_ids, 'tag_id' ) as temp_table_name:
                    
                    # temp tag_ids to tags to subtags and namespaces
                    rows = self._Execute( 'SELECT tag_id, namespace, subtag FROM {} CROSS JOIN tags USING ( tag_id ) CROSS JOIN subtags USING ( subtag_id ) CROSS JOIN namespaces USING ( namespace_id );'.format( temp_table_name ) ).fetchall()
                    
                
            
            uncached_tag_ids_to_tags = { tag_id : HydrusTags.CombineTag( namespace, subtag ) for ( tag_id, namespace, subtag ) in rows }
            
            if len( uncached_tag_ids_to_tags ) < len( uncached_tag_ids ):
                
                for tag_id in uncached_tag_ids:
                    
                    if tag_id not in uncached_tag_ids_to_tags:
                        
                        tag = 'unknown tag:' + HydrusData.GenerateKey().hex()
                        
                        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
                        
                        namespace_id = self.GetNamespaceId( namespace )
                        subtag_id = self.GetSubtagId( subtag )
                        
                        self._Execute( 'REPLACE INTO tags ( tag_id, namespace_id, subtag_id ) VALUES ( ?, ?, ? );', ( tag_id, namespace_id, subtag_id ) )
                        
                        uncached_tag_ids_to_tags[ tag_id ] = tag
                        
                    
                
            
            self._tag_ids_to_tags_cache.update( uncached_tag_ids_to_tags )
            
        
    
    def GetNamespaceId( self, namespace ) -> int:
        
        if namespace == '':
            
            if self.null_namespace_id is None:
                
                ( self.null_namespace_id, ) = self._Execute( 'SELECT namespace_id FROM namespaces WHERE namespace = ?;', ( '', ) ).fetchone()
                
            
            return self.null_namespace_id
            
        
        result = self._Execute( 'SELECT namespace_id FROM namespaces WHERE namespace = ?;', ( namespace, ) ).fetchone()
        
        if result is None:
            
            self._Execute( 'INSERT INTO namespaces ( namespace ) VALUES ( ? );', ( namespace, ) )
            
            namespace_id = self._GetLastRowId()
            
        else:
            
            ( namespace_id, ) = result
            
        
        return namespace_id
        
    
    def GetSubtagId( self, subtag ) -> int:
        
        result = self._Execute( 'SELECT subtag_id FROM subtags WHERE subtag = ?;', ( subtag, ) ).fetchone()
        
        if result is None:
            
            self._Execute( 'INSERT INTO subtags ( subtag ) VALUES ( ? );', ( subtag, ) )
            
            subtag_id = self._GetLastRowId()
            
        else:
            
            ( subtag_id, ) = result
            
        
        return subtag_id
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        # maybe content type subtag/namespace, which would useful for bad subtags, although that's tricky because then the knock-on is killing tag definition rows
        
        return []
        
    
    def GetTag( self, tag_id ) -> str:
        
        self._PopulateTagIdsToTagsCache( ( tag_id, ) )
        
        return self._tag_ids_to_tags_cache[ tag_id ]
        
    
    def GetTagId( self, tag ) -> int:
        
        clean_tag = HydrusTags.CleanTag( tag )
        
        try:
            
            HydrusTags.CheckTagNotEmpty( clean_tag )
            
        except HydrusExceptions.TagSizeException:
            
            # update this to instead go 'hey, does the dirty tag exist?' if it does, run the fix invalid tags routine
            
            raise HydrusExceptions.TagSizeException( '"{}" tag seems not valid--when cleaned, it ends up with zero size!'.format( tag ) )
            
        
        ( namespace, subtag ) = HydrusTags.SplitTag( clean_tag )
        
        namespace_id = self.GetNamespaceId( namespace )
        subtag_id = self.GetSubtagId( subtag )
        
        result = self._Execute( 'SELECT tag_id FROM tags WHERE namespace_id = ? AND subtag_id = ?;', ( namespace_id, subtag_id ) ).fetchone()
        
        if result is None:
            
            self._Execute( 'INSERT INTO tags ( namespace_id, subtag_id ) VALUES ( ?, ? );', ( namespace_id, subtag_id ) )
            
            tag_id = self._GetLastRowId()
            
        else:
            
            ( tag_id, ) = result
            
        
        return tag_id
        
    
    def GetTagIdsToTags( self, tag_ids = None, tags = None ) -> typing.Dict[ int, str ]:
        
        if tag_ids is not None:
            
            self._PopulateTagIdsToTagsCache( tag_ids )
            
            tag_ids_to_tags = { tag_id : self._tag_ids_to_tags_cache[ tag_id ] for tag_id in tag_ids }
            
        elif tags is not None:
            
            tag_ids_to_tags = { self.GetTagId( tag ) : tag for tag in tags }
            
        
        return tag_ids_to_tags
        
    
    def NamespaceExists( self, namespace ):
        
        if namespace == '':
            
            return True
            
        
        result = self._Execute( 'SELECT 1 FROM namespaces WHERE namespace = ?;', ( namespace, ) ).fetchone()
        
        if result is None:
            
            return False
            
        else:
            
            return True
            
        
    
    def SubtagExists( self, subtag ):
        
        try:
            
            HydrusTags.CheckTagNotEmpty( subtag )
            
        except HydrusExceptions.TagSizeException:
            
            return False
            
        
        result = self._Execute( 'SELECT 1 FROM subtags WHERE subtag = ?;', ( subtag, ) ).fetchone()
        
        if result is None:
            
            return False
            
        else:
            
            return True
            
        
    
    def TagExists( self, tag ):
        
        try:
            
            tag = HydrusTags.CleanTag( tag )
            
        except:
            
            return False
            
        
        try:
            
            HydrusTags.CheckTagNotEmpty( tag )
            
        except HydrusExceptions.TagSizeException:
            
            return False
            
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        if self.NamespaceExists( namespace ):
            
            namespace_id = self.GetNamespaceId( namespace )
            
        else:
            
            return False
            
        
        if self.SubtagExists( subtag ):
            
            subtag_id = self.GetSubtagId( subtag )
            
            result = self._Execute( 'SELECT 1 FROM tags WHERE namespace_id = ? AND subtag_id = ?;', ( namespace_id, subtag_id ) ).fetchone()
            
            if result is None:
                
                return False
                
            else:
                
                return True
                
            
        else:
            
            return False
            
        
    
    def UpdateTagId( self, tag_id, namespace_id, subtag_id ):
        
        self._Execute( 'UPDATE tags SET namespace_id = ?, subtag_id = ? WHERE tag_id = ?;', ( namespace_id, subtag_id, tag_id ) )
    
        if tag_id in self._tag_ids_to_tags_cache:
    
            del self._tag_ids_to_tags_cache[ tag_id ]
            
        
    
class ClientDBMasterURLs( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor ):
        
        ClientDBModule.ClientDBModule.__init__( self, 'client urls master', cursor )
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        index_generation_dict[ 'external_master.urls' ] = [
            ( [ 'domain_id' ], False, 400 )
        ]
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'external_master.url_domains' : ( 'CREATE TABLE IF NOT EXISTS {} ( domain_id INTEGER PRIMARY KEY, domain TEXT UNIQUE );', 400 ),
            'external_master.urls' : ( 'CREATE TABLE IF NOT EXISTS {} ( url_id INTEGER PRIMARY KEY, domain_id INTEGER, url TEXT UNIQUE );', 400 )
        }
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        # if content type is a domain, then give urls? bleh
        
        return []
        
    
    def GetURLDomainId( self, domain ):
        
        result = self._Execute( 'SELECT domain_id FROM url_domains WHERE domain = ?;', ( domain, ) ).fetchone()
        
        if result is None:
            
            self._Execute( 'INSERT INTO url_domains ( domain ) VALUES ( ? );', ( domain, ) )
            
            domain_id = self._GetLastRowId()
            
        else:
            
            ( domain_id, ) = result
            
        
        return domain_id
        
    
    def GetURLDomainAndSubdomainIds( self, domain, only_www_subdomains = False ):
        
        domain = ClientNetworkingFunctions.RemoveWWWFromDomain( domain )
        
        domain_ids = set()
        
        domain_ids.add( self.GetURLDomainId( domain ) )
        
        if only_www_subdomains:
            
            search_phrase = 'www%.{}'.format( domain )
            
        else:
            
            search_phrase = '%.{}'.format( domain )
            
        
        for ( domain_id, ) in self._Execute( 'SELECT domain_id FROM url_domains WHERE domain LIKE ?;', ( search_phrase, ) ):
            
            domain_ids.add( domain_id )
            
        
        return domain_ids
        
    
    def GetURLId( self, url ):
        
        result = self._Execute( 'SELECT url_id FROM urls WHERE url = ?;', ( url, ) ).fetchone()
        
        if result is None:
            
            try:
                
                domain = ClientNetworkingFunctions.ConvertURLIntoDomain( url )
                
            except HydrusExceptions.URLClassException:
                
                domain = 'unknown.com'
                
            
            domain_id = self.GetURLDomainId( domain )
            
            self._Execute( 'INSERT INTO urls ( domain_id, url ) VALUES ( ?, ? );', ( domain_id, url ) )
            
            url_id = self._GetLastRowId()
            
        else:
            
            ( url_id, ) = result
            
        
        return url_id
        
    
