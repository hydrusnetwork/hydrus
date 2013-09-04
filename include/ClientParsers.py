import bs4
import lxml
import traceback
import urlparse

def Parse4chanPostScreen( html ):
    
    soup = bs4.BeautifulSoup( html )
    
    title_tag = soup.find( 'title' )
    
    if title_tag.string == 'Post successful!': return ( 'success', None )
    elif title_tag.string == '4chan - Banned':
        
        print( repr( soup ) )
        
        message = 'You are banned from this board! html written to log.'
        
        HC.pubsub.pub( 'message', HC.Message( HC.MESSAGE_TYPE_TEXT, message ) )
        
        return ( 'big error', message )
        
    else:
        
        try:
            
            problem_tag = soup.find( id = 'errmsg' )
            
            if problem_tag is None:
                
                try: print( repr( soup ) )
                except: pass
                
                message = 'Unknown problem; html written to log.'
                
                HC.pubsub.pub( 'message', HC.Message( HC.MESSAGE_TYPE_TEXT, message ) )
                
                return ( 'error', message )
                
            
            problem = HC.u( problem_tag )
            
            if 'CAPTCHA' in problem: return ( 'captcha', None )
            elif 'seconds' in problem: return ( 'too quick', None )
            elif 'Duplicate' in problem: return ( 'error', 'duplicate file detected' )
            else: return ( 'error', problem )
            
        except: return ( 'error', 'unknown error' )
        
    
def ParsePage( html, starting_url ):
    
    soup = bs4.BeautifulSoup( html )
    
    all_links = soup.find_all( 'a' )
    
    links_with_images = [ link for link in all_links if len( link.find_all( 'img' ) ) > 0 ]
    
    urls = [ urlparse.urljoin( starting_url, link[ 'href' ] ) for link in links_with_images ]
    
    # old version included (images that don't have a link wrapped around them)'s src
    
    return urls
    