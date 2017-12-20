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
                
        def show_all_raids():
            queryResult = RaidLocation.query().order(RaidLocation.has_raided)
            reply_string = ""
            for curr_raid_loc in queryResult:
                reply_string += get_gym_details(curr_raid_loc) + "\n"
                    
            if queryResult.count() == 0:
                reply('no raids are added yet.')
            else:
                reply(reply_string)  
        
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
                reply('Wrong format. Example: " /raid 1.12345, 1.67890 "')

        def process_ex_raid(given_coords):
            latitude, longitude = split_coord(given_coords)
            analyze_raids(latitude, longitude)

        # Define constants here
        STICKER_METAPOD = "BQADBAADoRIAAjZHEwABGO4_KV2DvAQC"
        STICKER_SCYTHER = "BQADBAADrgQAAjZHEwABpXs1uQHdx-0C"

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
                add_ex_raid(text[5:])
            elif '/all' in text:
                show_all_raids()
            elif '/raid' in text:
                raid_gym(text[6:], True)
            elif '/unraid' in text:
                raid_gym(text[8:], False)
            elif '/help' in text:
                help_msg = "/start /stop to enable/disable bot." + \
                    "\n\n Type coordinates to see if it is in list of predicted raids. \nExample: 1.2345, 103.1234" + \
                    "\n\n To add a gym with coords to the database, type this:\n/add Gym Name, 1.12345, 1.67890 " + \
                    "\n\n To specify a gym which you have raided, type this:\n/raid 1.12345, 1.67890 " + \
                    "\n\n To remove the raid status of the gym, type this:\n/unraid 1.12345, 1.67890 " + \
                    "\n\n To see list of all predicted raids in the database,\ntype: /all "
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
