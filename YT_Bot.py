from pprint import pprint
from time import sleep
from datetime import timedelta
from random import choice
import re
import logging
import requests

user_pass_dict = { "user": "USER",
                "passwd": "PASS", 
                "api_type": "json" }
headers = { "User-agent": "YT_Bot by /u/ME" }
bot_signature = '[Bot subreddit](http://www.reddit.com/r/YT_Bot/) | [FAQ](http://www.reddit.com/r/YT_Bot/comments/1qtd52/hello_i_am_yt_bot/) | '

scrape_url = "http://www.reddit.com/comments.json?limit=100"

session = requests.session()
session.headers.update(headers)

already_done = []
YT_Bot_Comments = []

def formatComment(text):
    comment_format = ""
    comment_sort = ['Title:','Views:', 'Rating:', 'Duration:', 'Author:']
    for i in comment_sort:
        if not text.get(i):
            continue
        if i == 'Title:':
            comment_format += '**%s** *[%s](http://youtu.be/%s)* \n\n' % (i,text[i],text['VideoID'])
        if i == 'Views:':
            comment_format += makeSmallText('**%s** *%s* ',1) % (i,text[i])
        if i == 'Rating:':
            comment_format += makeSmallText(text[i],1)
        if i == 'Duration:':
            comment_format += makeSmallText('| **%s** %s',1) % (i,text[i])
        
    comment_format += '\n\n' + makeSmallText(bot_signature + getRandomBotComment())
    return(comment_format)

def makeSmallText(text,size=2):
    separate_text = tuple(text.split())
    small_text = ""
    text_size = '^' * size
    for i in separate_text:
        if i[0] == '[':
            small_text += '[%s%s ' % (text_size,i[1:])
        else:
            small_text += '%s%s ' % (text_size,i)
    if small_text == "":
        return None
    return small_text

def getRandomBotComment():
    file = open('bot_comments.txt', "r")
    read_file = file.read().split('\n')
    get_string = choice(read_file)
    file.close()
    return get_string
    
def redditLogin(): # Returns user's modhash
    login_url = 'https://ssl.reddit.com/api/login'
    r = session.post(login_url, data=user_pass_dict)
    js = r.json()
    return(js['json']['data']['modhash'])

# Returns a list of the first two pages
# of a reddit comments page.
# Very similar output to calling /comments.json.
def getFirstTwoPages(link):
    r = session.get(link)
    js = r.json()
    merged_pages = []
    for i in js['data']['children']:
        c = i['data']
        second_page_start = c['name']
        merged_pages.append(i)
    try:
        second_url = link + "&after=" + second_page_start
        r2 = session.get(second_url)
        js2 = r2.json()
        for i in js2['data']['children']:
            merged_pages.append(i)
    except(ValueError):
        second_url = link + "?after=" + second_page_start
        r2 = session.get(second_url)
        js2 = r2.json()
        for i in js2['data']['children']:
            merged_pages.append(i)
    return(merged_pages)

def postYTComment(fullname,text): # Returns id of posted comment
    try:
        comment_text = formatComment(text)
        comment_data = { 'api_type': 'json',
                        'text' : comment_text,
                        'thing_id' : fullname,
                        'uh' : redditLogin() }
        post = session.post('http://www.reddit.com/api/comment', data = comment_data)
        js = post.json()
        if js['json']['errors'] != []:
            if js['json'].get('ratelimit'):
                ratelimit = { 'error': 'ratelimit','ratelimit': int(js['json']['ratelimit']) }
                return ratelimit
            else:
                return { 'error': str(js['json']) }
        else:
            try:
                return js['json']['data']['things'][0]['data']['id']
            except(KeyError):
                return { 'error': KeyError }       
    except Exception as error:
        return { 'error': error }

# Gets youtube video ID from string.
# Example: "[Hey, check out this video.](https://www.youtube.com/watch?v=H_pVkarLMb8)"
# Would return "H_pVkarLMb8"
# Will not return if there are more than one link in a string.
def getVideoID(string):
    yt_count = re.finditer(r'(youtu\.be/)|(youtube\.com/watch)', string)
    yt_tuple = tuple(yt_count)
    if len(yt_tuple) > 1:
        return None
    video_id = None
    if 'youtube.com/watch' in string:
        search = re.search(r'(\?|&(amp;)?)v=([\w-]{11})', string)
        if search:
            video_id = search.group(3)
    if 'youtu.be/' in string:
        search = re.search(r'youtu\.be/([\w-]{11})', string)
        if search:
            video_id = search.group(1)
    return(video_id)

# Returns select video data from a valid video ID.
# E.g., getVideoData('H_pVkarLMb8') should return:
# {'Title:': 'Kaden and Stephen singing Barbie Girl (better)', 'Duration:': '0:01:24', 'Rating:': '5.0', 'Author:': 'IntelligentRogue', 'Views:': '449'}
def getVideoData(VideoID):
    try:
        video_data = { 'VideoID': VideoID }
        url = 'https://gdata.youtube.com/feeds/api/videos/' + VideoID + '?v=2&alt=json'
        r = requests.get(url)
        js = r.json()
        for i in js['entry']:
            if 'author' in i:
                author = js['entry'][i][0]['name']['$t']
                video_data['Author:'] = author
            if 'title' in i:
                title = js['entry'][i]['$t']
                video_data['Title:'] = title
            if 'yt$statistics' in i:
                viewCount = js['entry']['yt$statistics']['viewCount']
                viewCount = format(int(viewCount),',d')
                video_data['Views:'] = viewCount
            if 'media$group' in i:
                seconds = js['entry'][i]['yt$duration']['seconds']
                seconds = str(timedelta(seconds=int(seconds)))
                video_data['Duration:'] = seconds
            if 'yt$rating' in i:
                likes = js['entry'][i]['numLikes']
                likes = format(int(likes),',d')
                dislikes = js['entry'][i]['numDislikes']
                dislikes = format(int(dislikes),',d')
                video_data['Rating:'] = '\(%s likes/%s dislikes)' % (likes,dislikes)
        return(video_data)
    except(ValueError):
        return 'ValueError'
    except(requests.exceptions.ConnectionError):
        return 'ConnectionError'


def check_keywords(c):
    return 'youtube.com/watch' in c['body'] or 'youtu.be/' in c['body']


def run_bot():
    global already_done
    global YT_Bot_Comments
    print('Bot started!')
    while True:
        comments = getFirstTwoPages(scrape_url)
        for i in comments:
            c = i['data']
            if c['id'] in already_done:
                print('Found a previous comment. Breaking...')
                break
                
            # Puts the comment into a list, sorts the list oldest to newest,
            # and then reverses it to newest to oldest.
            # If this isn't here, bad things happen.
            already_done.append(c['id'])
            already_done.sort()
            already_done.reverse()
            # Shears the oldest comments off if it gets to be bigger than 300 entries.
            already_done = already_done[:300]
            if not check_keywords(c):
                continue
            
            print('Found video!')
            reply_id = c['name']
            video_id = getVideoID(c['body'])
            if video_id == None:
                print('Error finding video ID/multiple vidoes in one post: ' + c['body'])
                continue
                
            video_data = getVideoData(video_id)
            if 'Title:' not in video_data:
                print('Video looks broken! Passing... ' + c['body'])
                continue
            
            if c['parent_id'] in YT_Bot_Comments:
                print(c['author'] + ' has replied to YT_Bot with another video! Not doing anything...')
                continue
            if c['author'] == 'YT_Bot':
                print('Found myself! I\'m retarded! Skipping...')
                continue
            make_comment = postYTComment(reply_id,video_data)
            if 'error' in make_comment:
                if make_comment.get('ratelimit'):
                    print('ratelimit error for %i seconds!' % make_comment['ratelimit'])
                else:
                    print('An error occured making the comment. Skipping... ' + str(make_comment))
                continue
            YT_Bot_Comments.append(make_comment)
            # Pops the back off the list if the comment list is more than 1000 comments.
            YT_Bot_Comments = YT_Bot_Comments[:1000]
            print('Comment posted! Sleeping for 3 seconds...') #+ str(make_comment))
            sleep(3)
        print('Reached end of list. Sleeping for 30 seconds.')
        #break #Uncomment for testing... Will only run through one iteration.
        sleep(30)

def bot_start():
    while True:
        try:
            run_bot()
        except:
            logging.exception("Error running bot!")
            print("Will try again in 5 minutes.")
            sleep(300)
            


