import os
import sqlite3

HASH_TYPE_MD5 = 0 # 16 bytes long
HASH_TYPE_SHA1 = 1 # 20 bytes long
HASH_TYPE_SHA256 = 2 # 32 bytes long
HASH_TYPE_SHA512 = 3 # 64 bytes long

# Please feel free to use this file however you wish.
# None of this is thread-safe, though, so don't try to do anything clever.


# If you want to make a new tag archive for use in hydrus, you want to do something like:

# import HydrusTagArchive
# hta = HydrusTagArchive.HydrusTagArchive( 'my_little_archive.db' )
# hta.SetHashType( HydrusTagArchive.HASH_TYPE_MD5 )
# hta.BeginBigJob()
# for ( hash, tags ) in my_complex_mappings_generator: hta.AddMappings( hash, tags )
  # -or-
# for ( hash, tag ) in my_simple_mapping_generator: hta.AddMapping( hash, tag )
# hta.CommitBigJob()
# del hta


# If you are only adding a couple tags, you can exclude the BigJob stuff. It just makes millions of sequential writes more efficient.


# Also, this manages hashes as bytes, not hex, so if you have something like:

# hash = ab156e87c5d6e215ab156e87c5d6e215

# Then go hash = hash.decode( 'hex' ) before you pass it to Add/Get/Has/SetMappings


# If you have tags that are namespaced like hydrus (e.g. series:ghost in the shell), then check out:
# GetNamespaces
# DeleteNamespaces
# and
# RebuildNamespaces

# RebuildNamespaces takes namespaces_to_exclude, if you want to curate your namespaces a little better.

# If your GetNamespaces gives garbage, then just hit DeleteNamespaces. I'll be using the result of GetNamespaces to populate
# the tag import options widget when people sync with these archives.


# And also feel free to contact me directly at hydrus.admin@gmail.com if you need help.

class HydrusTagArchive( object ):
    
    def __init__( self, path ):
        
        self._path = path
        
        if not os.path.exists( self._path ): create_db = True
        else: create_db = False
        
        self._InitDBCursor()
        
        if create_db: self._InitDB()
        
        self._namespaces = { namespace for ( namespace, ) in self._c.execute( 'SELECT namespace FROM namespaces;' ) }
        self._namespaces.add( '' )
        
    
    def _AddMappings( self, hash_id, tag_ids ):
        
        self._c.executemany( 'INSERT OR IGNORE INTO mappings ( hash_id, tag_id ) VALUES ( ?, ? );', ( ( hash_id, tag_id ) for tag_id in tag_ids ) )
        
    
    def _InitDB( self ):
        
        self._c.execute( 'CREATE TABLE hash_type ( hash_type INTEGER );', )
        
        self._c.execute( 'CREATE TABLE hashes ( hash_id INTEGER PRIMARY KEY, hash BLOB_BYTES );' )
        self._c.execute( 'CREATE UNIQUE INDEX hashes_hash_index ON hashes ( hash );' )
        
        self._c.execute( 'CREATE TABLE mappings ( hash_id INTEGER, tag_id INTEGER, PRIMARY KEY ( hash_id, tag_id ) );' )
        self._c.execute( 'CREATE INDEX mappings_hash_id_index ON mappings ( hash_id );' )
        
        self._c.execute( 'CREATE TABLE namespaces ( namespace TEXT );' )
        
        self._c.execute( 'CREATE TABLE tags ( tag_id INTEGER PRIMARY KEY, tag TEXT );' )
        self._c.execute( 'CREATE UNIQUE INDEX tags_tag_index ON tags ( tag );' )
        
    
    def _InitDBCursor( self ):
        
        self._db = sqlite3.connect( self._path, isolation_level = None, detect_types = sqlite3.PARSE_DECLTYPES )
        
        self._c = self._db.cursor()
        
    
    def _GetHashId( self, hash, read_only = False ):
        
        result = self._c.execute( 'SELECT hash_id FROM hashes WHERE hash = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
        
        if result is None:
            
            if read_only: raise Exception()
            
            self._c.execute( 'INSERT INTO hashes ( hash ) VALUES ( ? );', ( sqlite3.Binary( hash ), ) )
            
            hash_id = self._c.lastrowid
            
        else: ( hash_id, ) = result
        
        return hash_id
        
    
    def _GetTagId( self, tag ):
        
        if ':' in tag:
            
            ( namespace, subtag ) = tag.split( ':', 1 )
            
            if namespace != '' and namespace not in self._namespaces:
                
                self._c.execute( 'INSERT INTO namespaces ( namespace ) VALUES ( ? );', ( namespace, ) )
                
                self._namespaces.add( namespace )
                
            
        
        result = self._c.execute( 'SELECT tag_id FROM tags WHERE tag = ?;', ( tag, ) ).fetchone()
        
        if result is None:
            
            self._c.execute( 'INSERT INTO tags ( tag ) VALUES ( ? );', ( tag, ) )
            
            tag_id = self._c.lastrowid
            
        else: ( tag_id, ) = result
        
        return tag_id
        
    
    def BeginBigJob( self ):
        
        self._c.execute( 'BEGIN IMMEDIATE;' )
        
    
    def CommitBigJob( self ):
        
        self._c.execute( 'COMMIT;' )
        self._c.execute( 'VACUUM;' )
        
    
    def AddMapping( self, hash, tag ):
        
        hash_id = self._GetHashId( hash )
        tag_id = self._GetTagId( tag )
        
        self._c.execute( 'INSERT OR IGNORE INTO mappings ( hash_id, tag_id ) VALUES ( ?, ? );', ( hash_id, tag_id ) )
        
    
    def AddMappings( self, hash, tags ):
        
        hash_id = self._GetHashId( hash )
        
        tag_ids = [ self._GetTagId( tag ) for tag in tags ]
        
        self._AddMappings( hash_id, tag_ids )
        
    
    def DeleteMapping( self, hash, tag ):
        
        hash_id = self._GetHashId( hash )
        tag_id = self._GetTagId( tag )
        
        self._c.execute( 'DELETE FROM mappings WHERE hash_id = ? AND tag_id = ?;', ( hash_id, tag_id ) )
        
    
    def DeleteMappings( self, hash ): self.DeleteTags( hash )
    
    def DeleteTags( self, hash ):
        
        try: hash_id = self._GetHashId( hash, read_only = True )
        except: return
        
        self._c.execute( 'DELETE FROM mappings WHERE hash_id = ?;', ( hash_id, ) )
        
    
    def DeleteNamespaces( self ):
        
        self._namespaces = {}
        self._namespaces.add( '' )
        
        self._c.execute( 'DELETE FROM namespaces;' )
        
    
    def GetHashType( self ):
        
        result = self._c.execute( 'SELECT hash_type FROM hash_type;' ).fetchone()
        
        if result is None:
            
            result = self._c.execute( 'SELECT hash FROM hashes;' ).fetchone()
            
            if result is None:
                
                raise Exception( 'This archive has no hash type set, and as it has no files, no hash type guess can be made.' )
                
            
            if len( hash ) == 16: self.SetHashType( HASH_TYPE_MD5 )
            elif len( hash ) == 20: self.SetHashType( HASH_TYPE_SHA1 )
            elif len( hash ) == 32: self.SetHashType( HASH_TYPE_SHA256 )
            elif len( hash ) == 64: self.SetHashType( HASH_TYPE_SHA512 )
            else: raise Exception()
            
            return self.GetHashType()
            
        else:
            
            ( hash_type, ) = result
            
            return hash_type
            
        
    
    def GetMappings( self, hash ): return self.GetTags( hash )
    
    def GetName( self ):
        
        filename = os.path.basename( self._path )
        
        if '.' in filename:
            
            filename = filename.split( '.', 1 )[0]
            
        
        return filename
        
    
    def GetNamespaces( self ): return self._namespaces
    
    def GetTags( self, hash ):
        
        try: hash_id = self._GetHashId( hash, read_only = True )
        except: return []
        
        result = { tag for ( tag, ) in self._c.execute( 'SELECT tag FROM mappings NATURAL JOIN tags WHERE hash_id = ?;', ( hash_id, ) ) }
        
        return result
        
    
    def HasHash( self, hash ):
        
        try:
            
            hash_id = self._GetHashId( hash, read_only = True )
            
            return True
            
        except:
            
            return False
            
        
    
    def HasHashTypeSet( self ):
        
        result = self._c.execute( 'SELECT hash_type FROM hash_type;' ).fetchone()
        
        return result is not None
        
    
    def IterateHashes( self ):
        
        for ( hash, ) in self._c.execute( 'SELECT hash FROM hashes;' ): yield hash
        
    
    def IterateMappings( self ):
        
        hash_ids = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM hashes;' ) ]
        
        for hash_id in hash_ids:
            
            ( hash, ) = self._c.execute( 'SELECT hash FROM hashes WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
            
            tags = self.GetTags( hash )
            
            if len( tags ) > 0: yield ( hash, tags )
            
        
    
    def RebuildNamespaces( self, namespaces_to_exclude = set() ):
        
        self._namespaces = set()
        self._namespaces.add( '' )
        
        self._c.execute( 'DELETE FROM namespaces;' )
        
        for ( tag, ) in self._c.execute( 'SELECT tag FROM tags;' ):
            
            if ':' in tag:
                
                ( namespace, subtag ) = tag.split( ':', 1 )
                
                if namespace != '' and namespace not in self._namespaces and namespace not in namespaces_to_exclude:
                    
                    self._namespaces.add( namespace )
                    
                
            
        
        self._c.executemany( 'INSERT INTO namespaces ( namespace ) VALUES ( ? );', ( ( namespace, ) for namespace in self._namespaces ) )
        
    
    def SetHashType( self, hash_type ):
        
        self._c.execute( 'DELETE FROM hash_type;' )
        
        self._c.execute( 'INSERT INTO hash_type ( hash_type ) VALUES ( ? );', ( hash_type, ) )
        
    
    def SetMappings( self, hash, tags ):
        
        hash_id = self._GetHashId( hash )
        
        self._c.execute( 'DELETE FROM mappings WHERE hash_id = ?;', ( hash_id, ) )
        
        tag_ids = [ self._GetTagId( tag ) for tag in tags ]
        
        self._AddMappings( hash_id, tag_ids )
        
    
