from bs4 import BeautifulSoup; from urllib import request; from re import match; import requests

parser = "lxml"

def fanfic_req(link): return BeautifulSoup(request.urlopen(link).read(), parser)
def fanfic_check(id, name):
    if isinstance(id, int): id = str(id)
    else: assert isinstance(id, str), "Error for" + name + ": id not int or str"

def ao3_rip(ao3_id): # downloads whole story in one go
    fanfic_check(ao3_id, "ao3_rip")
    text = fanfic_req('http://archiveofourown.org/works/'+ao3_id+'?view_adult=true&view_full_work=true')
    tag_bar = text.find("dl", class_="stats").find_all("dd") # everything in the top bar
    tag_list = {}
    for i in tag_bar:
        tag = [j.get_text() for j in i.find_all("a", class_="tag")]
        if tag == []: tag = [i.get_text().lstrip('\n').lstrip(' ').rstrip(' ').rstrip('\n')]
        tag_list[i.get("class")[0]] = tag
    tag_list['author'] = [i.get_text() for i in text.find_all("a", rel="author")]
    summary = text.find_all("div", class_="summary module", role="complementary") # just below top bar
    chapter = {}
    for i in text.find_all("div", class_="chapter", id=True): # separating each chapters
        x = i.find("h3", class_="title").find("a").get("href").split("/")[-1]
        chapter[i.get('id')] = [x, i]
    return ao3_id, tag_list, summary, chapter

def ff_rip(ff_id): # no image
    fanfic_check(ff_id, "ff_rip")
    text = fanfic_req("https://www.fanfiction.net/s/" +ff_id +"/1") # first chapter
    tag_line = text.find("span", class_="xgray xcontrast_txt").get_text().split(" - ") # top bar
    tag_list = {}
    for i in tag_line:
        if ":" in i: bracket, item = i.split(": ")[0:2]; tag_list[bracket] = item.rstrip(' ')
        else: tag_list[['Language', 'Genre', 'Characters'][tag_line.index(i)-1]] = i
    tag_list['Characters'] = tag_list['Characters'].split(', ')
    tag_list['Genre'] = tag_list['Genre'].split('/')
    del tag_list['id']
    author = text.find("div", id="profile_top").find("a", class_="xcontrast_txt", title=False, target=False) # tag filtering
    userid, username = author.get("href").split("/")[-2:] # the text in the tag, unlike the last line
    summary = text.find("div", class_="xcontrast_txt", style=True).get_text() # tag filtering
    chapter_list = {}
    for i in range(1, int(tag_list['Chapters'])+1): # loop through each chapter
        r = request.urlopen("https://www.fanfiction.net/s/"+ff_id+"/"+str(i)).read()
        storyid = match(".*storytextid=([0-9]+)", str(r)).group(1) # can't get it any other way
        text = BeautifulSoup(r, "lxml")
        story = text.find("div", class_="storytext xcontrast_txt nocopy", id="storytext") # literal lines
        chapter_list[i] = [storyid, story]
    return ff_id, userid, username, summary, tag_list, chapter_list

def da_rip(user_id, item_id): # name of literature can replace user_id, remember to bypass mature filters
    fanfic_check(user_id, da_rip); fanfic_check(item_id, da_rip)
    text = fanfic_req("https://deviantart.com/art/"+user_id+"-"+itemid) # their url system is shit
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

def watt_rip(watt_id): # 100% queries, WTF? v4 is proprietary, WTF!
    fanfic_check(watt_id, "watt_rip")
    book = requests.get('https://www.wattpad.com/apiv2/info?id=' + watt_id, headers={'User-Agent': 'Mozilla/5.0'}).json()
    chapter_list = book['group']; result = {"tags": book["tags"].split(" ")}
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
