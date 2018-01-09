# This code is adapted <Telebot starter kit> , created by yukuku: https://github.com/yukuku/telebot'
# Telegram Bot by Nicholas

import StringIO
import json
import logging
import random
import urllib
import urllib2
import re
import secretBot
import time

# for sending images
from PIL import Image
import multipart

# standard app engine imports
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import webapp2

TOKEN = secretBot.getToken()

BASE_URL = 'https://api.telegram.org/bot' + TOKEN + '/'


# ================================

class EnableStatus(ndb.Model):
    # key name: str(chat_id)
    enabled = ndb.BooleanProperty(indexed=False, default=False)


# ================================

def setEnabled(chat_id, yes):
    es = EnableStatus.get_or_insert(str(chat_id))
    es.enabled = yes
    es.put()

def getEnabled(chat_id):
    es = EnableStatus.get_by_id(str(chat_id))
    if es:
        return es.enabled
    return False


# ================================

class RaidLocation(ndb.Model):
    gym_name = ndb.StringProperty()
    latitude = ndb.FloatProperty()
    longitude = ndb.FloatProperty()
    has_raided = ndb.BooleanProperty()

class GymTime(ndb.Model):
    time = ndb.StringProperty()
    user = ndb.StringProperty()


# ================================

class MeHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getMe'))))


class GetUpdatesHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getUpdates'))))


class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        url = self.request.get('url')
        if url:
            self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'setWebhook', urllib.urlencode({'url': url})))))


class WebhookHandler(webapp2.RequestHandler):
    def post(self):
        urlfetch.set_default_fetch_deadline(60)
        body = json.loads(self.request.body)
        logging.info('request body:')
        logging.info(body)
        self.response.write(json.dumps(body))

        update_id = body['update_id']
        try:
            message = body['message']
        except:
            message = body['edited_message']
        message_id = message.get('message_id')
        date = message.get('date')
        text = message.get('text').lower()
        fr = message.get('from')
        chat = message['chat']
        chat_id = chat['id']

        if not text:
            logging.info('no text')
            return

        def reply(msg=None, img=None, reply=True):
            if msg:
                if (reply):
                    reply_msg = str(message_id)
                else:
                    reply_msg = ""

                resp = urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode({
                    'chat_id': str(chat_id),
                    'text': msg.encode('utf-8'),
                    'disable_web_page_preview': 'true',
                    'reply_to_message_id': reply_msg,
                })).read()
            elif img:
                resp = multipart.post_multipart(BASE_URL + 'sendPhoto', [
                    ('chat_id', str(chat_id)),
                    ('reply_to_message_id', str(message_id)),
                ], [
                    ('photo', 'image.jpg', img),
                ])
            else:
                logging.error('no msg or img specified')
                resp = None

            logging.info('send response:')
            logging.info(resp)

        def sendStickerSelf(sticker_id=None):
            resp = urllib2.urlopen(BASE_URL + 'sendSticker', urllib.urlencode({
                    'chat_id': str(chat_id),
                    'sticker': sticker_id,
            })).read()
            
        def split_coord(coords):
            parts = coords.split(",")
            latitude = parts[0]
            longitude = parts[1]
            return latitude, longitude
            
        def is_coords_same(lat, long, latB, longB):
            THRESHOLD = 0.00001
            
            if (abs(lat - latB) <= THRESHOLD and abs(long - longB) <= THRESHOLD):
                return True
            else:
                return False

        def get_gym_details(given_gym):
            header_str = ""
            if given_gym.has_raided:
                header_str = "[Raided] "
            return header_str + given_gym.gym_name + " - " + str(given_gym.latitude) + " , " + str(given_gym.longitude)            
            
        def analyze_raids(given_lat, given_long):
            has_raid_found = False
            
            try:
                given_lat = float(given_lat)
                given_long = float(given_long)
            except:
                reply('invalid coordinates')
                return

            queryResult = RaidLocation.query()
            for curr_raid_loc in queryResult:
                predict_lat = curr_raid_loc.latitude
                predict_long = curr_raid_loc.longitude
                
                if is_coords_same(predict_lat, predict_long, given_lat, given_long):
                    reply(get_gym_details(curr_raid_loc))
                    has_raid_found = True
                    break
            if not has_raid_found:
                reply('no suitable raids found.')

        def add_ex_raid(text):
            try:
                parts = text.split(",")
                name = parts[0]
                lat = float(parts[1].replace(" ", ""))
                long = float(parts[2].replace(" ", ""))
                new_raid = RaidLocation(gym_name=name, latitude=lat, longitude=long, has_raided=False)
                new_raid.put()
                reply('The gym - ' + str(name) + ' is successfully added @ ' + str(lat) + " , " + str(long) + ".")
            except:
                reply('Wrong format. Example: " /add Gym Name, 1.12345, 1.67890 "')

        def del_ex_raid(text):
            try:
                latitude, longitude = split_coord(text)
                given_lat = float(latitude)
                given_long = float(longitude)

                queryResult = RaidLocation.query()
                for curr_raid_loc in queryResult:
                    predict_lat = curr_raid_loc.latitude
                    predict_long = curr_raid_loc.longitude
                    
                    if is_coords_same(predict_lat, predict_long, given_lat, given_long):
                        reply ('Removed: ' + get_gym_details(curr_raid_loc))
                        curr_raid_loc.key.delete()
                        return

                reply('Invalid coordinates')
            except:
                reply('Wrong format. Example: " /delete 1.12345, 1.67890 "')
                
        def show_all_raids():
            queryResult = RaidLocation.query()
            gym_list = []
            for curr_raid_loc in queryResult:
                gym_list.append(get_gym_details(curr_raid_loc) + "\n")
                
            gym_list.sort(reverse=True)
            reply_string = " ".join(gym_list)
                    
            if queryResult.count() == 0:
                reply('no raids are added yet.')
            else:
                reply(reply_string)

        def delete_all_raids():
            queryResult = RaidLocation.query()
            for item in queryResult:
                item.key.delete()
            reply('You have deleted all raids.')

        def format_time(int_time):
            joined_time = "0" + str(int_time)
            return joined_time[-2:] # get last 2 characters

        def minus_seconds(hour, minute, second, minus_amt):
            second -= minus_amt
            if second < 0:
                second += 60
                minute -= 1
                if minute < 0:
                    minute += 60
                    hour -= 1
                    if hour == 0:
                        hour = 12

            return format_time(hour) + ":" + format_time(minute) + ":" + format_time(second)
            

        def format_gym_time(time):
            hour = int(time[0:2])
            minute = int(time[2:4])
            second = int(time[4:6])
            
            # Add 10 mins
            minute += 10
            if minute > 59:
                minute -= 60
                hour += 1
                if hour == 13:
                    hour = 1

            # minus X seconds
            time_minus_two = minus_seconds(hour, minute, second, 2)
            time_minus_three = minus_seconds(hour, minute, second, 3)

            return "[Time if -2] " + str(time_minus_two) + "  ||   " + "[Time if -3] " + str(time_minus_three)

        def register_gym(text):
            try:
                if len(text) == 5:
                    text = "0" + text
                elif len(text) != 6:
                    raise Exception("wrong format")

                curr_time = text
                int(curr_time) # test if it is in numbers
                
                curr_user = str(chat_id)
                new_gymtime = GymTime(time=curr_time, user=curr_user)
                new_gymtime.put()

                time.sleep(1) # delay for time to update db before querying

                queryResult = GymTime.query(GymTime.user == str(chat_id))
                reply_string = "Gym timings: \n"
                for gymtime in queryResult:
                    reply_string += format_gym_time(gymtime.time) + "\n"
                reply(reply_string)                    
            except:
                reply('Wrong format. Example: " /gym 121034 " ')

        def clear_gym():
            queryResult = GymTime.query(GymTime.user == str(chat_id))
            for item in queryResult:
                item.key.delete()
            reply('All gym timings are cleared.')
        
        def raid_gym(text, set_raid):
            try:
                latitude, longitude = split_coord(text)
                latitude = float(latitude)
                longitude = float(longitude)
                
                queryResult = RaidLocation.query()
                for curr_raid_loc in queryResult:
                    curr_lat = curr_raid_loc.latitude
                    curr_long = curr_raid_loc.longitude
                    
                    if is_coords_same(curr_lat, curr_long, latitude, longitude):
                        if curr_raid_loc.has_raided == set_raid:
                            if set_raid:
                                reply('This location has already been raided before.')
                            else:
                                reply('This location has not been raided yet.')
                        else:
                            curr_raid_loc.has_raided = set_raid
                            curr_raid_loc.put()
                            prepend = ""
                            if set_raid:
                                prepend = "R"
                            else:
                                prepend = "Unr"
                            reply(prepend + "egistered the raid for " + get_gym_details(curr_raid_loc))
                        return
                        
                reply('the specified gym does not exist in database.')
            except:
                mid_str = ""
                if set_raid:
                    mid_str = "/raid"
                else:
                    mid_str = "/unraid"
                    
                reply('Wrong format. Example: " ' + mid_str + ' 1.12345, 1.67890 "')

        def process_ex_raid(given_coords):
            latitude, longitude = split_coord(given_coords)
            analyze_raids(latitude, longitude)
            
        def random_choice(choices):
            parts = choices.split(",")
            reply("The bot has picked " + str(random.choice(parts)) + " ! ")
                

        # Define constants here
        STICKER_METAPOD = "BQADBAADoRIAAjZHEwABGO4_KV2DvAQC"
        STICKER_SCYTHER = "BQADBAADrgQAAjZHEwABpXs1uQHdx-0C"
        
        # remove instances of self-call
        text = text.replace("@bugcatcherbot", "")

        if text.startswith('/'):
            if text == '/start':
                reply('Bot enabled')
                setEnabled(chat_id, True)
            elif text == '/stop':
                reply('Bot disabled')
                setEnabled(chat_id, False)
            elif (not getEnabled(chat_id)):
                return

        # CUSTOMIZE FROM HERE
            #elif '/fight' in text:
                #reply(msg='Bugcatcher Nic wants to battle!', reply=False)
            #elif '/sobad' in text:
                #image_url = 'https://c7.staticflickr.com/9/8666/15776594150_240386133c_n.jpg'
                #reply(img=urllib2.urlopen(image_url).read())
            #elif '/metapod' in text:
                #reply(msg='Bugcatcher Nic sends out Metapod!', reply=False)
                #sendStickerSelf(STICKER_METAPOD)
            #elif '/scyther' in text:
                #reply(msg='Bugcatcher Nic sends out Scyther!', reply=False)
                #sendStickerSelf(STICKER_SCYTHER)
            elif '/add' in text:
                if len(text) >= 5 and text[0:4] == "/add":
                    add_ex_raid(text[5:])
                else:
                    add_ex_raid("/add error")
            elif text == '/all':
                show_all_raids()
            elif text == '/deleteall':
                delete_all_raids()
            elif '/delete' in text:
                if len(text) >= 8 and text[0:7] == "/delete":
                    del_ex_raid(text[8:])
                else:
                    del_ex_raid("/delete error")
            elif '/raid' in text:
                if len(text) >= 6 and text[0:5] == "/raid":
                    raid_gym(text[6:], True)
                else:
                    raid_gym("/raid error", True)
            elif '/unraid' in text:
                if len(text) >= 8 and text[0:7] == "/unraid":
                    raid_gym(text[8:], False)
                else:
                    raid_gym("/unraid error", False)
            elif text == "/gymdone":
                clear_gym()
            elif '/gym' in text:
                if len(text) >= 5  and text[0:4] == "/gym":
                    register_gym(text[5:])
                else:
                    register_gym("/gym error")
            elif '/random' in text:
                if len(text) >= 8 and text[0:7] == "/random":
                    random_choice(text[8:])
                else:
                    reply("please type /random choice1, choice2, choice3 for example.")
            elif '/help' in text:
                help_msg = "/start /stop to enable/disable bot." + \
                    "\n\n Type coordinates to see if it is in list of predicted raids. \nExample: 1.2345, 103.1234" + \
                    "\n\n To add a gym with coords to the database, type this:\n/add Gym Name, 1.12345, 1.67890 " + \
                    "\n\n To remove a gym with coords from database, type this:\n/delete 1.12345, 1.67890 " + \
                    "\n\n To specify a gym which you have raided, type this:\n/raid 1.12345, 1.67890 " + \
                    "\n\n To remove the raid status of the gym, type this:\n/unraid 1.12345, 1.67890 " + \
                    "\n\n To see list of all predicted raids in the database,\ntype: /all " + \
                    "\n\n To add the time after shaving first pokemon from gym, \ntype: /gym 121034 " + \
                    "\n\n To remove all gym timings for slotting purposes,\ntype: /gymdone " + \
                    "\n\n To remove all raids, \ntype: /deleteall " + \
                    "\n\n To let the bot pick something at random,\ntype: /random choice1, choice2, choice3 "
                reply(help_msg)
                
        elif (not getEnabled(chat_id)):
            return
        elif 'youtube ' in text:
            m = re.search('(?<=youtube ).*', text)
            req_search = m.group(0)
            link = '+'.join(req_search.split(' '))
            full_link = "https://www.youtube.com/results?search_query=" + link
            reply(full_link)
        elif ',' in text:
            process_ex_raid(text)
        else:
            reply_str = ""
            if 'hello' in text:
                reply_str += "Hello there. "
            if 'you' in text and 'how' in text:
                reply_str += "I am fine, thank you. " 

            reply(reply_str)


app = webapp2.WSGIApplication([
    ('/me', MeHandler),
    ('/updates', GetUpdatesHandler),
    ('/set_webhook', SetWebhookHandler),
    ('/webhook', WebhookHandler),
], debug=True)
