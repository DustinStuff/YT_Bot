from pprint import pprint
from time import sleep
from datetime import timedelta
import logging
import requests

user_pass_dict = { "user": "USER",
                "passwd": "PASS", 
                "api_type": "json" }
headers = { "User-agent": "YT_Bot by /u/ME" }
bot_signature = '[^^Bot ^^subreddit](http://www.reddit.com/r/YT_Bot/) ^^| [^^FAQ](http://www.reddit.com/r/YT_Bot/comments/1qtd52/hello_i_am_yt_bot/) ^^| ^^Still ^^in ^^testing ^^mode, ^^may ^^be ^^unstable.'

scrape_url = "http://www.reddit.com/comments.json?limit=100"

session = requests.session()
session.headers.update(headers)

already_done = []
YT_Bot_Comments = []

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
        title = text['title']
        duration = text['duration']
        viewCount = text['viewCount']
        author = text['author']
        rating = text['rating']
        comment_text = '**Title:** %s\n\n**Duration:** %s\n\n**Views:** %s\n\n**Author:** %s\n\n**Rating:** %s\n\n %s' % (title,duration,viewCount,author,rating,bot_signature)
        comment_data = { 'api_type': 'json',
                        'text' : comment_text,
                        'thing_id' : fullname,
                        'uh' : redditLogin() }
        post = session.post('http://www.reddit.com/api/comment', data = comment_data)
        js = post.json()
        if js['json']['errors'] != []:
            pprint(js['json']['errors'])
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
def getVideoID(string):
    video_id = ""
    if 'youtube.com/watch' in string:
        for i in range(len(string)):
            if string[i:i+3] == "?v=":
                id_start = i + 3
                video_id = string[i+3:i+14]
            if string[i:i+3] == "&v=":
                    id_start = i + 3
                    video_id = string[i+3:i+14]
    if 'youtu.be/' in string:
        for i in range(len(string)):
            if string[i:i+9] == 'youtu.be/':
                video_id = string[i+9:i+20]
    #Useless error handling.
    if len(video_id) == 0:
        return 'Error'
    return(video_id)

# Returns select video data from a valid video ID.
# E.g., getVideoData('H_pVkarLMb8') should return:
# {'rating': 5.0, 'viewCount': '449', 'author': 'IntelligentRogue', 'duration': '0:01:24', 'title': 'Kaden and Stephen singing Barbie Girl (better)'}
def getVideoData(VideoID):
    try:
        video_data = {}
        url = 'https://gdata.youtube.com/feeds/api/videos/' + VideoID + '?v=2&alt=json'
        r = requests.get(url)
        js = r.json()
        for i in js['entry']:
            if 'author' in i:
                author = js['entry'][i][0]['name']['$t']
                video_data['author'] = author
            if 'title' in i:
                title = js['entry'][i]['$t']
                video_data['title'] = title
            if 'yt$statistics' in i:
                viewCount = js['entry']['yt$statistics']['viewCount']
                viewCount = format(int(viewCount),',d')
                video_data['viewCount'] = viewCount
            if 'media$group' in i:
                seconds = js['entry'][i]['yt$duration']['seconds']
                seconds = str(timedelta(seconds=int(seconds)))
                video_data['duration'] = seconds
            if 'gd$rating' in i:
                rating = js['entry'][i]['average']
                video_data['rating'] = str(rating)
        return(video_data)
    except(ValueError):
        return 'ValueError'
    except(requests.exceptions.ConnectionError):
        return 'ConnectionError'




def run_bot():
    while True:
        comments = getFirstTwoPages(scrape_url)
        for i in comments:
            c = i['data']
            if c['id'] in already_done:
                print('Found a previous comment, or reached end of list! Breaking...')
                break
            else:
                already_done.append(c['id'])
                # Shears the back off of the list already_done
                # when it gets longer than 200 entries.
                # Don't want it clogging up resources. ;)
                for i in range(len(already_done)):
                    if i >= 200:
                        already_done.pop()
            if 'youtube.com/watch' in c['body'] or 'youtu.be/' in c['body']:
                print('Found video!')
                reply_id = c['name']
                video_id = getVideoID(c['body'])
                if video_id == 'Error':
                    print('error getting video ID - ' + c['body'])
                else:
                    video_data = getVideoData(video_id)
                    if 'title' in video_data:
                        if c['parent_id'] not in YT_Bot_Comments:
                            make_comment = postYTComment(reply_id,video_data)
                            print(make_comment)
                            if 'error' in make_comment:
                                if make_comment.get('ratelimit'):
                                    print('ratelimit error! Sleeping for %i seconds...' % make_comment['ratelimit'])
                                    sleep(make_comment['ratelimit'])
                                else:
                                    print('An error occured making the comment. Skipping... ' + str(make_comment))
                            else:
                                YT_Bot_Comments.append(make_comment)
                                # Pops the back off the list if the comment list is more than 1000 comments.
                                for i in range(len(YT_Bot_Comments)):
                                    if i >= 1000:
                                        YT_Bot_Comments.pop()
                                print('Comment posted! Sleeping for 10 seconds...' + str(make_comment))
                                sleep(10)
                        else:
                            print(c['author'] + ' has replied to YT_Bot with another video! Not doing anything...')
                    else:
                        print('Video looks broken! Passing... ' + c['body'])
        print('Reached end of list. Sleeping 30 seconds...')
        sleep(30)

def bot_start():
    while True:
        try:
            run_bot()
        except:
            logging.exception("Error running bot!")
            print("Will try again in 5 minutes.")
            sleep(300)
            


