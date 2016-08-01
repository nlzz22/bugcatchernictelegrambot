# This code is adapted <Telebot starter kit> , created by yukuku: https://github.com/yukuku/telebot'
# Telegram Bot by Nicholas

import StringIO
import json
import logging
import random
import urllib
import urllib2
import re

# for sending images
from PIL import Image
import multipart

# standard app engine imports
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import webapp2

TOKEN = '268318692:AAGzQ2_X45RYzuYTosgltc9vGoTe0ajCGJU'

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
        text = message.get('text')
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
                    # 'text': msg,
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

        def getRandomSongTitle():
            list_songs = ['可愛女人', '星晴', '黑色幽默', '龍捲風', '愛在西元前', '爸我回來了',
            '簡單愛', '開不了口', '雙截棍', '安靜', '暗號', '回到過去',
            '最後的戰役', '以父之名', '晴天', '三年二班', '東風破', '妳聽得到', '她的睫毛',
            '軌跡', '我的地盤', '七里香', '藉口', '外婆', '擱淺', '園遊會', '止戰之殤',
            '一路向北', '飄移', '夜曲', '藍色風暴', '髮如雪', '黑色毛衣', '楓', '浪漫手機',
            '麥芽糖', '珊瑚海', '霍元甲', '夜的第七章', '聽媽媽的話', '千里之外', '本草綱目',
            '退後', '心雨', '白色風車', '迷迭香', '菊花台', '黃金甲', '不能說的秘密',
            '牛仔很忙', '彩虹', '青花瓷', '陽光宅男', '蒲公英的約定', '我不配', '甜甜的',
            '最長的電影', '給我一首歌的時間', '花海', '說好的幸福呢', '時光機', '稻香',
            '說了再見', '雨下一整晚', '愛的飛行日記', '超人不會飛', '我落淚。情緒零碎',
            'Mine Mine', '水手怕水', '手語', '公公偏頭痛', '明明就', '傻笑', '愛你沒差',
            '大笨鐘', '哪裡都是你', '算什麼男人', '怎麼了', '我要夏天', '手寫的從前',
            '鞋子特大號', '聽爸爸的話', '美人魚', '聽見下雨的聲音', '床邊故事',
            '前世情人', '不該', 'Now You See Me']

            chosen_index = random.randint(0, len(list_songs)-1)

            return list_songs[chosen_index].decode('utf-8')

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
            # elif text == '/image':
            #     img = Image.new('RGB', (512, 512))
            #     base = random.randint(0, 16777216)
            #     pixels = [base+i*j for i in range(512) for j in range(512)]  # generate sample image
            #     img.putdata(pixels)
            #     output = StringIO.StringIO()
            #     img.save(output, 'JPEG')
            #     reply(img=output.getvalue())

        # CUSTOMIZE FROM HERE

            elif '/fight' in text:
                reply(msg='Bugcatcher Nic wants to battle!', reply=False)
            elif '/sobad' in text:
                image_url = 'https://c7.staticflickr.com/9/8666/15776594150_240386133c_n.jpg'
                reply(img=urllib2.urlopen(image_url).read())
            elif '/metapod' in text:
                reply(msg='Bugcatcher Nic sends out Metapod!', reply=False)
                sendStickerSelf(STICKER_METAPOD)
            elif '/scyther' in text:
                reply(msg='Bugcatcher Nic sends out Scyther!', reply=False)
                sendStickerSelf(STICKER_SCYTHER)
            elif '/help' in text:
                reply('/start /stop to enable/disable bot. \n /fight /sobad /metapod /scyther')
        elif (not getEnabled(chat_id)):
            return
        elif 'youtube ' in text:
            m = re.search('(?<=youtube ).*', text)
            req_search = m.group(0)
            link = '+'.join(req_search.split(' '))
            full_link = "https://www.youtube.com/results?search_query=" + link
            reply(full_link)
        else:
            reply_str = ""
            if 'hello' in text:
                reply_str += "Hello there. "
            if 'you' in text and 'how' in text:
                reply_str += "I am fine, thank you. " 

            pattern = re.compile('(.*jay chou.*)')
            if pattern.match(text):
                reply_str += getRandomSongTitle()

            reply(reply_str)

        # else:
        #     if getEnabled(chat_id):
        #         reply('I got your message! (but I do not know how to answer)')
        #     else:
        #         logging.info('not enabled for chat_id {}'.format(chat_id))


app = webapp2.WSGIApplication([
    ('/me', MeHandler),
    ('/updates', GetUpdatesHandler),
    ('/set_webhook', SetWebhookHandler),
    ('/webhook', WebhookHandler),
], debug=True)
