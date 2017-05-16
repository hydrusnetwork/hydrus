from __future__ import unicode_literals; import youtube_dl

class MyLogger(object): # prints out warning and error messages
    def debug(self, msg): pass
    def warning(self, msg): print(msg)
    def error(self, msg): print(msg)
def my_hook(d):
    if d['status'] == 'finished': print('Done downloading... start converting')  
def downer(code, link): # standard video and playlist specs for Hydrus
    ydl_opts = {
        'format': code,
        'logger': MyLogger(),
        'progress_hooks': [my_hook],
        'write_all_thumbnails':True,
        'writesubtitles': 'allsubtitles',
        'outtmpl': 'yt-dl/%(title)s/%(title)s-%(format_id)s.%(ext)s'
    }
    if not isinstance(link, list): link = [link]
    with youtube_dl.YoutubeDL(ydl_opts) as ydl: ydl.download(link)

def set_pick(dash, container="mp4", resolution=[360,720], hfr=False):
    assert dash in [True, False, None], "error: dash is not bool or None"
    assert container in ["mp4", "webm", "both"], \
        "error: container variable not correct"
    assert set(resolution) < set([240, 360, 480, 720, 1080]), \
        "error: bad input from resolution"
    assert isinstance(hfr, bool), "error: hfr is not boolean"
    non_dash = [[18,22],[43]]; dash_audio = [[140], [171, 249, 250, 251]]
    dash_video = [
        # 24, 36, 48, 72,108,72h,108h
        [133,134,135,136,137,288,289],
        [242,243,244,247,248,302,303]]
    dash_video_flip = list(zip(*dash_video))
    table = {240:[0], 360:[1], 480:[2,5], 720:[3], 1080:[4,6]}
    unity = sum(dash_audio, []) + sum(dash_video, [])
    royale = unity + sum(non_dash, [])
    def format_war(n): return dash_audio[n] + dash_video[n] + non_dash[n]
    if dash == True: a = unity
    elif dash == None:a = royale
    elif dash == False: a = sum(non_dash, [])
    if container == "mp4": b = format_war(0)
    elif container == "webm": b = format_war(1)
    elif container == "both": b = royale
    c = [sum([dash_video_flip[j] for j in table[i]], ()) for i in resolution]
    c = [e for l in c for e in l] + sum(dash_audio, [])
    if 360 in resolution: c += [18, 43]
    if 720 in resolution: c+= [22]
    if hfr == True: d = unity + sum(non_dash, [])
    elif hfr == False: d = sum(dash_audio, []) + \
        [e for l in dash_video_flip[:5] for e in l] + sum(non_dash, [])
    return list(set(a) & set(b) & set(c) & set(d))
def multi_downer(self, link): # please pipe from set_pick for best results
    for i in self: downer(str(i), link)

# Things to be done:
# 1. Include Vimeo and Dailymotion
# 2. Grab description, uploader, date
# 3. Archiving to IPFS using directory
# 4. Formatting tags to be easily searchable
