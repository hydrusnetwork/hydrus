import os
import sqlite3

HASH_TYPE_MD5 = 0 # 16 bytes long
HASH_TYPE_SHA1 = 1 # 20 bytes long
HASH_TYPE_SHA256 = 2 # 32 bytes long
HASH_TYPE_SHA512 = 3 # 64 bytes long

# Please feel free to use this file however you wish.
# None of this is thread-safe, though, so don't try to do anything clever.

# A rating for hydrus is a float from 0.0 to 1.0
# dislike/like are 0.0 and 1.0
# numerical are fractions between 0.0 and 1.0
# for a four-star rating that allows 0 stars, the 5 possibles are: 0.0, 0.25, 0.5, 0.75, 1.0
# for a three-star rating that does not allow 0 stars, the three possibles are: 0.0, 0.5, 1.0
# in truth, at our level:
    # a five-star rating that does allow stars is a six-star rating
    # a ten-star rating that does not allow stars is a ten-star rating

# If you want to make a new rating archive for use in hydrus, you want to do something like:

# import HydrusRatingArchive
# hra = HydrusRatingArchive.HydrusRatingArchive( 'my_little_archive.db' )
# hra.SetHashType( HydrusRatingArchive.HASH_TYPE_MD5 )
# hra.SetNumberOfStars( 5 )
# hra.BeginBigJob()
# for ( hash, rating ) in my_rating_generator: hra.AddRating( hash, rating )
# hra.CommitBigJob()
# del hra


# If you are only adding a couple ratings, you can exclude the BigJob stuff. It just makes millions of sequential writes more efficient.


# Also, this manages hashes as bytes, not hex, so if you have something like:

# hash = ab156e87c5d6e215ab156e87c5d6e215

# Then go hash = hash.decode( 'hex' ) before you pass it to Add/Get/Has/SetRating


# And also feel free to contact me directly at hydrus.admin@gmail.com if you need help.

class HydrusRatingArchive( object ):
    
    def __init__( self, path ):
        
        self._path = path
        
        if not os.path.exists( self._path ): create_db = True
        else: create_db = False
        
        self._InitDBCursor()
        
        if create_db: self._InitDB()
        
    
    def _InitDB( self ):
        
        self._c.execute( 'CREATE TABLE hash_type ( hash_type INTEGER );', )
        
        self._c.execute( 'CREATE TABLE number_of_stars ( number_of_stars INTEGER );', )
        
        self._c.execute( 'CREATE TABLE ratings ( hash BLOB PRIMARY KEY, rating REAL );' )
        
    
    def _InitDBCursor( self ):
        
        self._db = sqlite3.connect( self._path, isolation_level = None, detect_types = sqlite3.PARSE_DECLTYPES )
        
        self._c = self._db.cursor()
        
    
    def BeginBigJob( self ):
        
        self._c.execute( 'BEGIN IMMEDIATE;' )
        
    
    def CommitBigJob( self ):
        
        self._c.execute( 'COMMIT;' )
        self._c.execute( 'VACUUM;' )
        
    
    def DeleteRating( self, hash ):
        
        self._c.execute( 'DELETE FROM ratings WHERE hash = ?;', ( sqlite3.Binary( hash ), ) )
        
    
    def GetHashType( self ):
        
        result = self._c.execute( 'SELECT hash_type FROM hash_type;' ).fetchone()
        
        if result is None:
            
            result = self._c.execute( 'SELECT hash FROM hashes;' ).fetchone()
            
            if result is None:
                
                raise Exception( 'This archive has no hash type set, and as it has no files, no hash type guess can be made.' )
                
            
            if len( hash ) == 16: hash_type = HASH_TYPE_MD5
            elif len( hash ) == 20: hash_type = HASH_TYPE_SHA1
            elif len( hash ) == 32: hash_type = HASH_TYPE_SHA256
            elif len( hash ) == 64: hash_type = HASH_TYPE_SHA512
            else:
                
                raise Exception( 'This archive has non-standard hashes. Something is wrong.' )
                
            
            self.SetHashType( hash_type )
            
            return hash_type
            
        else:
            
            ( hash_type, ) = result
            
            return hash_type
            
        
    
    def GetName( self ):
        
        filename = os.path.basename( self._path )
        
        if '.' in filename:
            
            filename = filename.split( '.', 1 )[0]
            
        
        return filename
        
    
    def GetNumberOfStars( self ):
        
        result = self._c.execute( 'SELECT number_of_stars FROM number_of_stars;' ).fetchone()
        
        if result is None:
            
            raise Exception( 'This rating archive has no number of stars set.' )
            
        else:
            
            ( number_of_stars, ) = result
            
            return number_of_stars
            
        
    
    def GetRating( self, hash ):
        
        result = self._c.execute( 'SELECT rating FROM ratings WHERE hash = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
        
        if result is None:
            
            return None
            
        else:
            
            ( rating, ) = result
            
            return rating
            
        
    
    def HasHash( self, hash ):
        
        result = self._c.execute( 'SELECT 1 FROM ratings WHERE hash = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
        
        if result is None:
            
            return False
            
        else:
            
            return True
            
        
    
    def IterateRatings( self ):
        
        for row in self._c.execute( 'SELECT hash, rating FROM ratings;' ):
            
            yield row
            
        
    
    def SetHashType( self, hash_type ):
        
        self._c.execute( 'DELETE FROM hash_type;' )
        
        self._c.execute( 'INSERT INTO hash_type ( hash_type ) VALUES ( ? );', ( hash_type, ) )
        
    
    def SetNumberOfStars( self, number_of_stars ):
        
        self._c.execute( 'DELETE FROM number_of_stars;' )
        
        self._c.execute( 'INSERT INTO number_of_stars ( number_of_stars ) VALUES ( ? );', ( number_of_stars, ) )
        
    
    def SetRating( self, hash, rating ):
        
        self._c.execute( 'REPLACE INTO ratings ( hash, rating ) VALUES ( ?, ? );', ( sqlite3.Binary( hash ), rating ) )
        
    
