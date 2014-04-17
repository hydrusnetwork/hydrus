import collections
import cStringIO
import HydrusConstants as HC
import itertools
import os
import re
import threading
import time
import traceback
import wx
import yaml

# think about using mako, but it may not really be what you want

# basic template for a hydrus booru page
  # title and all that
  # javascript
  # display header
    # local server info
    # how long user has access
  # top and tail html tags
  # css and so on
  # left info div
  # content div
  # start javascript

# gallery info
  # if the user has rights to search, show search box
  # if the user is seeing a static query, show info
  # tag counts, which can be fetched and displayed by the javascript

# gallery content
  # draw each thumb in spans or whatever flows as we want
  # screw limits, just show them all

# file info
  # tags, file info

# generate file page
  # just write the full size image <img>