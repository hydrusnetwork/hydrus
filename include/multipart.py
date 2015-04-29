'''
Classes for using multipart form data from Python, which does not (at the
time of writing) support this directly.
 
To use this, make an instance of Multipart and add parts to it via the factory
methods field and file.  When you are done, get the content via the get method.
 
@author: Stacy Prowell (http://stacyprowell.com)
'''
 
class Part(object):
    '''
    Class holding a single part of the form.  You should never need to use
    this class directly; instead, use the factory methods in Multipart:
    field and file.
    '''
 
    # The boundary to use.  This is shamelessly taken from the standard.
    BOUNDARY = '----------AaB03x'
    CRLF = '\r\n'
    # Common headers.
    CONTENT_TYPE = 'Content-Type'
    CONTENT_DISPOSITION = 'Content-Disposition'
    # The default content type for parts.
    DEFAULT_CONTENT_TYPE = 'application/octet-stream'
 
    def __init__(self, name, filename, body, headers):
        '''
        Make a new part.  The part will have the given headers added initially.
 
        @param name: The part name.
        @type name: str
        @param filename: If this is a file, the name of the file.  Otherwise
                        None.
        @type filename: str
        @param body: The body of the part.
        @type body: str
        @param headers: Additional headers, or overrides, for this part.
                        You can override Content-Type here.
        @type headers: dict
        '''
        self._headers = headers.copy()
        self._name = name
        self._filename = filename
        self._body = body
        # We respect any content type passed in, but otherwise set it here.
        # We set the content disposition now, overwriting any prior value.
        if self._filename == None:
            self._headers[Part.CONTENT_DISPOSITION] = \
                ('form-data; name="%s"' % self._name)
            self._headers.setdefault(Part.CONTENT_TYPE,
                                     Part.DEFAULT_CONTENT_TYPE)
        else:
            self._headers[Part.CONTENT_DISPOSITION] = \
                ('form-data; name="%s"; filename="%s"' %
                 (self._name, self._filename))
        return
 
    def get(self):
        '''
        Convert the part into a list of lines for output.  This includes
        the boundary lines, part header lines, and the part itself.  A
        blank line is included between the header and the body.
 
        @return: Lines of this part.
        @rtype: list
        '''
        lines = []
        lines.append('--' + Part.BOUNDARY)
        for (key, val) in self._headers.items():
            lines.append('%s: %s' % (key, val))
        lines.append('')
        lines.append(self._body)
        return lines
 
class Multipart(object):
    '''
    Encapsulate multipart form data.  To use this, make an instance and then
    add parts to it via the two methods (field and file).  When done, you can
    get the result via the get method.
 
    See http://www.w3.org/TR/html401/interact/forms.html#h-17.13.4.2 for
    details on multipart/form-data.
 
    Watch http://bugs.python.org/issue3244 to see if this is fixed in the
    Python libraries.
 
    @return: content type, body
    @rtype: tuple
    '''
 
    def __init__(self):
        self.parts = []
        return
 
    def field(self, name, value, headers={}):
        '''
        Create and append a field part.  This kind of part has a field name
        and value.
 
        @param name: The field name.
        @type name: str
        @param value: The field value.
        @type value: str
        @param headers: Headers to set in addition to disposition.
        @type headers: dict
        '''
        self.parts.append(Part(name, None, value, headers))
        return
 
    def file(self, name, filename, value, headers={}):
        '''
        Create and append a file part.  THis kind of part has a field name,
        a filename, and a value.
 
        @param name: The field name.
        @type name: str
        @param value: The field value.
        @type value: str
        @param headers: Headers to set in addition to disposition.
        @type headers: dict
        '''
        self.parts.append(Part(name, filename, value, headers))
        return
 
    def get(self):
        '''
        Get the multipart form data.  This returns the content type, which
        specifies the boundary marker, and also returns the body containing
        all parts and bondary markers.
 
        @return: content type, body
        @rtype: tuple
        '''
        all = []
        for part in self.parts:
            all += part.get()
        all.append('--' + Part.BOUNDARY + '--')
        all.append('')
        # We have to return the content type, since it specifies the boundary.
        content_type = 'multipart/form-data; boundary=%s' % Part.BOUNDARY
        return content_type, Part.CRLF.join(all)