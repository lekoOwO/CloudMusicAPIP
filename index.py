#!/bin/env python2.7
# -*- coding: utf-8 -*-

from flask import *

from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from random import randint

import binascii, os, json
import yaml, requests

from redis_session import RedisSessionInterface
from generate_china_ip import get_china_ip
import random

import socket

# Load and parse config file
config = yaml.load(open('config.yaml', 'r'), Loader=yaml.FullLoader)
encrypt = config['encrypt']

app = Flask(__name__, static_url_path='/static')
app.config['recaptcha'] = config['recaptcha']
app.debug = config['debug']
app.session_interface = RedisSessionInterface(config['redis'])

m10s = [socket.gethostbyname('ws.acgvideo.com')]
def m10():
  return random.sample(m10s, 1)[0]

def aesEncrypt(text, secKey):
  pad = 16 - len(text) % 16
  text = text + pad * chr(pad)
  encryptor = AES.new(secKey, 1)
  cipherText = encryptor.encrypt(text)
  cipherText = binascii.b2a_hex(cipherText).upper()
  return cipherText

def encrypted_request(jsonDict):
  jsonStr = json.dumps(jsonDict, separators = (",", ":"))
  encText = aesEncrypt(jsonStr, secretKey)
  data = {
    'eparams': encText,
  }
  return data

nonce = encrypt['nonce']
n, e = int(encrypt["n"], 16), int(encrypt["e"], 16)

def req_netease_lyric(songId):
  r = requests.post('http://music.163.com/api/song/lyric?os=pc&id={}&lv=-1&tv=-1'.format(songId), headers = headers)
  result = json.loads(r.text)
  chs = result['tlyric']["lyric"] if 'lrc' in result else False if ('nolyric' in result) and result['nolyric'] else None
  if (chs):
    cht = json.loads(requests.post('https://api.zhconvert.org/convert', data = {'text': chs, 'converter': 'Taiwan'}).text)['data']['text']
  else:
    cht = chs
  return {
    'origin': result['lrc']["lyric"] if 'lrc' in result else False if ('nolyric' in result) and result['nolyric'] else None,
    'chs': chs,
    'cht': cht
  }

def req_netease(url, payload):
  data = encrypted_request(payload)
  r = requests.post(url, data = data, headers = headers)
  result = json.loads(r.text)
  if result['code'] != 200:
    return None
  return result

def req_netease_get(url):
  r = requests.get(url, headers = headers)
  result = json.loads(r.text)
  if result['code'] != 200:
    return None
  return result

if config["napi"]["enabled"]:
  napi = requests.Session()
  def login():
    r = napi.get(config["napi"]["host"] + '/login/status')
    r = json.loads(r.text)
    if "userId" in r:
      return True
    else:
      r = napi.get(config["napi"]["host"] + '/login/?email={}&password={}'.format(config["napi"]['username'], config["napi"]['password']))
      r = json.loads(r.text)
      if (r["code"] == 200):
        return True
      else:
        return False
  def req_netease_url(songId, rate):
    if login():
      r = napi.get(config["napi"]["host"] + '/song/url?id={}'.format(songId))
      r = json.loads(r.text)
      return r["data"][0]
    else:
      print("{} Login Error.".format(songId))

  def req_netease_detail(songId):
    if login():
      r = napi.get(config["napi"]["host"] + '/song/detail?ids={}'.format(songId))
      r = json.loads(r.text)

      return r["songs"][0]
    else:
      print("{} Login Error.".format(songId))
  def req_netease_list_detail(listId):
    if login():
      r = napi.get(config["napi"]["host"] + '/playlist/detail?id={}'.format(listId))
      r = json.loads(r.text)

      return r
    else:
      print("{} Login Error.".format(songId))
  
else:
  def req_netease_url(songId, rate):
    payload = {"method": "POST", "params": {"ids": [songId],"br": rate}, "url": "http://music.163.com/api/song/enhance/player/url"}
    data = req_netease('http://music.163.com/api/linux/forward', payload)
    if data is None or data['data'] is None or len(data['data']) != 1:
      return None
    
    song = data['data'][0]
    if song['code'] != 200 or song['url'] is None:
      return None
    # song['url'] = song['url'].replace('http:', '')
    return song

  def req_netease_detail(songId):
    payload = {"method": "POST", "params": {"c": "[{id:%d}]" % songId}, "url": "http://music.163.com/api/v3/song/detail"}
    data = req_netease('http://music.163.com/api/linux/forward', payload)
    if data is None or data['songs'] is None or len(data['songs']) != 1:
      return None
    song =  data['songs'][0]
    song['al']['picUrl'] = song['al']['picUrl'].replace("http:", "https:", 1)
    return song
  def req_netease_list_detail(listId):
    data = req_netease_get("http://music.163.com/api/v3/playlist/detail?id={}&n=10000".format(listId))
    if data is None or data['playlist'] is None:
      return None
    return data

def req_recaptcha(response, remote_ip):
  r = requests.post('https://www.google.com/recaptcha/api/siteverify', data = {
    'secret': config['recaptcha']['secret'],
    'response': response,
    'remoteip': remote_ip
  })
  result = json.loads(r.text)
  print("req_recaptcha from %s, result: %s" % (remote_ip, r.text))
  return result['success']


print("Generating secretKey for current session...")
secretKey = binascii.a2b_hex(encrypt['secret'])

headers = {
  'Referer': 'http://music.163.com',
  'X-Real-IP': get_china_ip(),
  'User-Agent': 'Mozilla/5.0 (Linux; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/60.0.3112.107 Mobile Safari/537.36',
  'Host': 'music.163.com',
  'Proxy-Connection': 'keep-alive',
  'Origin': 'http://music.163.com',
  'Content-Type': 'application/x-www-form-urlencoded',
  'Accept': '*/*',
  'Accept-Encoding': 'gzip, deflate',
  'Accept-Language': 'zh-TW, fr-CH, fr;q=0.9, en;q=0.8'
}

def sign_request(songId, rate):
  h = SHA256.new()
  h.update(str(songId).encode())
  h.update(str(rate).encode())
  h.update(config["sign_salt"].encode())
  return h.hexdigest()

def is_verified(session):
  if not config['recaptcha']:
    return True
  return 'verified' in session and session['verified'] > 0

def set_verified(session):
  if config['recaptcha']:
    session['verified'] = randint(10, 20)

def decrease_verified(session):
  if config['recaptcha']:
    session['verified'] -= 1

@app.route("/")
def index():
  verified = is_verified(session)
  return render_template('index.j2', verified = verified, **request.args.to_dict())

@app.route("/backdoor")
def backdoor():
  if app.debug:
    set_verified(session)
  return 'ok!'

@app.route('/s/<path:path>')
def static_route(path):
  return app.send_static_file(path)

@app.route("/sign/<int:songId>/<int:rate>", methods=['POST'])
def generate_sign(songId, rate):
  if not is_verified(session):
    # 首先检查谷歌验证
    if 'g-recaptcha-response' not in request.form \
      or not req_recaptcha(
        request.form['g-recaptcha-response'],
        request.headers[config['ip_header']] if config['ip_header'] else request.remote_addr
      ):
      #
      return jsonify({"verified": is_verified(session), "errno": 2})

    set_verified(session)

  # 请求歌曲信息, 然后签个名
  decrease_verified(session)
  song = req_netease_detail(songId)
  if song is None:
    return jsonify({"verified": is_verified(session), "errno": 1})

  return jsonify({
    "verified": True,
    "sign": sign_request(songId, rate),
    "song": {
      "id": song['id'],
      "name": song['name'],
      "artist": song["artists"] if "artists" in song else [{"id": a['id'], "name": a['name']} for a in song['ar']],
      "album": {
        "id": song["album" if "album" in song else 'al']['id'],
        "name": song["album" if "album" in song else 'al']['name'],
        "picUrl": song["album" if "album" in song else 'al']['picUrl'].replace("http:", "https:", 1) if song["album" if "album" in song else 'al']['picUrl'] else None
      },
      "lyric": req_netease_lyric(songId)}
  })

@app.route("/signList/<int:listId>/<int:rate>", methods=['POST'])
def generate_sign_list(listId, rate):
  if not is_verified(session):
    # 首先检查谷歌验证
    if 'g-recaptcha-response' not in request.form \
      or not req_recaptcha(
        request.form['g-recaptcha-response'],
        request.headers[config['ip_header']] if config['ip_header'] else request.remote_addr
      ):
      #
      return jsonify({"verified": is_verified(session), "errno": 2})

    set_verified(session)

  decrease_verified(session)
  songs = req_netease_list_detail(listId)
  if songs is None:
    return jsonify({"verified": is_verified(session), "errno": 1})

  return jsonify({
    "verified": True,
    "sign": sign_request(listId, rate),
    "creator": songs["playlist"]["creator"],
    "coverImgUrl": songs["playlist"]["coverImgUrl"],
    "trackCount": songs["playlist"]["trackCount"],
    "description": songs["playlist"]["description"],
    "tags": songs["playlist"]["tags"],
    "tracks": songs["playlist"]["tracks"],
    "tracks": [{
      "id": i["id"],
      "no": i["no"],
      "name": i["name"],
      "alias": i["alia"],
      "album": {
        "name": i['al']["name"],
        "picUrl": i['al']['picUrl'].replace("http:", "https:", 1) if i['al']['picUrl'] else None,
        "id": i['al']["id"]
      },
      "artist": [{
        "name": k['name'],
        'id': k['id'],
        "alias": k["alias"]
      } for k in i["ar"]],
      "h": i['h'],
      "m": i['m'],
      "l": i['l']
    } for i in songs["playlist"]["tracks"]] 
  })

@app.route("/<int:songId>/<int:rate>/<sign>")
def get_song_url(songId, rate, sign):
  if sign_request(songId, rate) != sign:
    return abort(403)

  song = req_netease_url(songId, rate)
  if song is None:
    return abort(404)
  response = redirect(song['url'].replace('m10.music.126.net', m10() + '/m10.music.126.net', 1).replace("http:", "https:", 1), code=302)
  response.headers["max-age"] = song['expi']
  response.headers["Referrer-Policy"] = "no-referrer"
  return response

@app.route("/api/<int:songId>/<int:rate>")
def bot_get_song_url(songId, rate):
  if req_netease_url(songId, rate) is None:
    return jsonify({
      "success": "false",
  })
  song = req_netease_detail(songId)
  return jsonify({
    "verified": True,
    "sign": sign_request(songId, rate),
    "song": {
      "id": song['id'],
      "name": song['name'],
      "artist": [{"id": a['id'], "name": a['name']} for a in song['ar']],
      "album": {
        "id": song['al']['id'],
        "name": song['al']['name'],
        "picUrl": song['al']['picUrl'].replace("http:", "https:", 1) if song['al']['picUrl'] else None
    }}
  })

if __name__ == "__main__":
  print("Running...")
  app.run(host='0.0.0.0')
