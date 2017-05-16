from bs4 import BeautifulSoup; from urllib import request; from re import match; import requests
def ao3_rip(ao3id): # downloads whole story in one go
    if isinstance(ao3id, int): ao3id = str(ao3id)
    else: assert isinstance(ao3id, str)
    r = request.urlopen('http://archiveofourown.org/works/'+ao3id+'?view_adult=true&view_full_work=true').read()
    text = BeautifulSoup(r, "lxml")
    tag_bar = text.find("dl", class_="stats").find_all("dd") # everything in the top bar
    tag_list = {}
    for i in tag_bar:
        x = [j.get_text() for j in i.find_all("a", class_="tag")]
        if x == []: x = [i.get_text().lstrip('\n').lstrip(' ').rstrip(' ').rstrip('\n')]
        tag_list[i.get("class")[0]] = x
    tag_list['author'] = [i.get_text() for i in text.find_all("a", rel="author")]
    summary = text.find_all("div", class_="summary module", role="complementary") # just below top bar
    chapter = {}
    for i in text.find_all("div", class_="chapter", id=True): # separating each chapters
        x = i.find("h3", class_="title").find("a").get("href").split("/")[-1]
        chapter[i.get('id')] = [x, i]
    return ao3id, tag_list, summary, chapter
def ff_rip(ffid): # no image
    if isinstance(ffid, int): ffid = str(ffid)
    else: assert isinstance(ffid, str)
    r = request.urlopen("https://www.fanfiction.net/s/" + ffid +"/1").read() # first chapter
    text = BeautifulSoup(r, "lxml")
    tag_line = text.find("span", class_="xgray xcontrast_txt").get_text().split(" - ") # top bar
    tag_list = {}
    for i in tag_line:
        if ":" in i: a, b = i.split(": ")[0:2]; tag_list[a] = b.rstrip(' ')
        else: tag_list[['Language', 'Genre', 'Characters'][tag_line.index(i)-1]] = i
    tag_list['Characters'] = tag_list['Characters'].split(', ')
    tag_list['Genre'] = tag_list['Genre'].split('/')
    del tag_list['id']
    author = text.find("div", id="profile_top").find("a", class_="xcontrast_txt", title=False, target=False) # tag filtering
    userid, username = author.get("href").split("/")[-2:] # the text in the tag, unlike the last line
    summary = text.find("div", class_="xcontrast_txt", style=True).get_text() # tag filtering
    chapter_list = {}
    for i in range(1, int(tag_list['Chapters'])+1): # loop through each chapter
        r = request.urlopen("https://www.fanfiction.net/s/" + ffid + "/" + str(i)).read()
        storyid = match(".*storytextid=([0-9]+)", str(r)).group(1) # can't get it any other way
        text = BeautifulSoup(r, "lxml")
        story = text.find("div", class_="storytext xcontrast_txt nocopy", id="storytext") # literal lines
        chapter_list[i] = [storyid, story]
    return ffid, userid, username, summary, tag_list, chapter_list
def da_rip(user_id, item_id): # name of literature can replace user_id, remember to bypass mature filters
    if isinstance(user_id, int): user_id = str(user_id)
    else: assert isinstance(user_id, str)
    if isinstance(item_id, int): item_id = str(item_id)
    else: assert isinstance(item_id, str)
    r = request.urlopen("https://deviantart.com/art/" + user_id + "-" + itemid).read() # their url system is shit
    text = BeautifulSoup(r, "lxml")
    title = text.find("title").get_text() # title of the text
    pretext = text.find("li", class_="author") # description bar
    artist = pretext.find("a", class_="u regular username").get_text()
    upload_time = pretext.find("span", title=True).get_text()
    summary = text.find("meta", property="og:description").get("content") # metadata at the top
    idnum = {}
    for i in ["itemid", "splitid", "ownerid"]: # comments section
        idnum[i] = text.find("input", {"type":"hidden", "name":i}).get("value")
    type_tags = text.find("meta", {"name":"keywords"}).get("content").split(", ") # metadata at the top
    art_tags = [i.get_text()for i in text.findall("a", class_="discoverytag")] # description ber
    img = text.find("meta", property="og:image").get("content") # metadata at the top
    dick = text.find("div", class_="grf-indent").find("div", class_="text").contents[:-2] # js in text is not cool
    return title, artist, summary, idnum, type_tags, art_tags, img, dick
def watt_rip(watt_id): # 100% queries, WTF?
    if isinstance(watt_id, int): watt_id = str(watt_id)
    else: assert isinstance(watt_id, str)
    book = requests.get('https://www.wattpad.com/apiv2/info?id=' + watt_id, headers={'User-Agent': 'Mozilla/5.0'}).json()
    chapter_list = book['group']
    result = {"tags": book["tags"].split(" ")}
    for i in ["cover", "description", "groupId", "author", "completed"]: result[i] = book[i]
    for j in range(1, len(chapter_list)+1):
        chapter_id = str(chapter_list[j-1]['ID'])
        chapter_data = requests.get('https://www.wattpad.com/apiv2/info?id=' + 
            chapter_id, headers={'User-Agent': 'Mozilla/5.0'}).json()
        result[j] = [chapter_data[k] for k in ["id", "title", "date", "modifyDate", "language", 
            "videoid", "photolink"]]+[requests.get('https://www.wattpad.com/apiv2/storytext?id=' +
            chapter_id, headers={'User-Agent': 'Mozilla/5.0'}).text]
    return result

# Things to do:
# 1. Sort out the tags to be consistent betwen each other
# 2. Download the images and IPFS it properly
# 3. Proper text formatting (especially dA and Wattpad)
# 4. Urllib.request vs Requests, which is better?
