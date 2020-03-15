# -*- coding: utf-8 -*-

import os
import wget
import json
import vk_api
import requests
import random
import traceback
import threading
from log import log
from pydub import AudioSegment
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

SECOND = 1000 # 1000 milliseconds  
google_key = "GOOGLE_KEY"
google_url = "https://www.google.com/speech-api/v2/recognize?output=json&lang=ru-ru&key=" + google_key
token_vk = "VK_TOKEN"

####################################################################################################

def rnd_sting():
    l = random.randint(10, 15)
    t = ""
    for i in range(l):
        t += chr(random.randint(ord("A"), ord("Z")) + random.randint(0, 1) * (ord("a") - ord("A")))
    return t

def rand():
    return random.randint(1, 100000000)

####################################################################################################

def processing_user(mes):
    message_id = mes["id"]
    mes = vk.messages.getById(message_ids=message_id)["items"][0]
    urls = get_urls(mes)
    if urls:
        vk.messages.send(peer_id=mes["peer_id"], random_id=rand(), message="=== Получил сообщение, начинаю распознавать... ===")
        for url in urls:
            dir_name = rnd_sting() + str(mes["from_id"])
            log("Dir_name is %s" % dir_name)
            os.mkdir(dir_name)
            log("Got URL")
            log(url)
            download(url, dir_name)
            log("Downloaded")
            num_parts = convert_to_flacs(dir_name)
            log("Sliced on %d slices" % num_parts)
            if num_parts > 1:            
                vk.messages.send(peer_id=mes["peer_id"], random_id=rand(), message="=== Присылаю по частям, всего частей будет %d ===" % num_parts)
            for i in range(num_parts):
                t = get_part(i, dir_name)
                if not t:
                    vk.messages.send(peer_id=mes["peer_id"], random_id=rand(), message="&#13;")
                else:
                    vk.messages.send(peer_id=mes["peer_id"], random_id=rand(), message=t)
                log("Sended!")
            os.system("rm -r %s" % dir_name)
    else:
        vk.messages.send(peer_id=mes["peer_id"], random_id=rand(), message="=== Голосовых сообщений не обнаружено! === ")


def processing_chat(mes):
    urls = get_urls(mes)
    if urls:
        for url in urls:
            dir_name = rnd_sting() + str(mes["from_id"])
            log("Dir_name is %s" % dir_name)
            os.mkdir(dir_name)
            log("Got URL")
            download(url, dir_name)
            log("Downloaded")
            num_parts = convert_to_flacs(dir_name)
            log("Sliced on %d slices" % num_parts)
            for i in range(num_parts):
                t = get_part(i, dir_name)
                if not t:
                    vk.messages.send(peer_id=mes["peer_id"], message="&#13;", random_id=rand())
                else:
                    vk.messages.send(peer_id=mes["peer_id"], message=t, random_id=rand())
                log("Sended!")
            os.system("rm -r %s" % dir_name)


def processing(event):
    if event.type == VkEventType.MESSAGE_NEW or event.type == VkBotEventType.MESSAGE_NEW:
        mes = event.object["message"]
        log("Got message")
        log(mes)
        try:
            if event.from_user:
                processing_user(mes)
            else:
                processing_chat(mes)
            log("Success!\n\n")

        except BaseException as e:
            log("Error!")
            log(traceback.format_exc())
            if mes["peer_id"] < 2000000000:
                vk.messages.send(peer_id=mes["peer_id"], random_id=rand(), message="=== Что-то пошло не так, попробуйте ещё раз! ===")

def get_urls(mes):
    urls = []
    if "attachments" in mes:
        for t in mes["attachments"]:
            if t["type"] == "audio_message":
                urls.append(t["audio_message"]["link_mp3"])

    if "fwd_messages" in mes:
        for fwd_mes in mes["fwd_messages"]:
            urls += get_urls(fwd_mes)
    return urls
                    
def download(url, dir_name):
    wget.download(url, "./%s/audio.mp3" % dir_name)

def convert_to_flacs(dir_name):
    audio = AudioSegment.from_mp3("./%s/audio.mp3" % dir_name)
    l = 0
    beg = 0
    end = min(19.5 * SECOND, len(audio))

    while (beg < len(audio)):
        segment = audio[beg:end]
        segment.export("./%s/audio%d.flac" % (dir_name, l), format="flac")
        beg += 19.5 * SECOND
        end = min(end + 19.5 * SECOND, len(audio))
        l += 1

    return l

def get_part(i, dir_name):
    headers={"Content-Type": "audio/x-flac; rate=44100"}

    with open("./%s/audio%d.flac" % (dir_name, i), "rb") as audio_file:
        audio = audio_file.read()
        log("Sending request to Google")
        request = requests.post(google_url, data=audio, headers=headers)
        log("Got answer from Google:")
        log(str(request))

    res = request.text[13:]

    if not res.replace("\n", "").replace(" ", ""):
        return ""

    jsoned = json.loads(res)
    transcript = jsoned["result"][jsoned["result_index"]]["alternative"][0]["transcript"]
    log("Recognized:", transcript)
    return transcript

def login():
    global vk, longpoll, blongpoll
    vk_session = vk_api.VkApi(token=token_vk)
    vk = vk_session.get_api()

    blongpoll = VkBotLongPoll(vk_session, "162352736")


def main():
    try:
        for event in blongpoll.listen():
            try:
                a = threading.Thread(target=processing, args=(event,), name="Processing")
                a.start()
            except KeyboardInterrupt:
                exit()
            except BaseException as e:
                log(e)
    except KeyboardInterrupt:
        log("Exiting")
        exit()
    except BaseException:
        log(traceback.format_exc())
    main()

try:
    login()
    log("Login success!")
except Exception as e:
    log("Login error!")
    log(traceback.format_exc())
    exit()

if __name__ == "__main__":
    main()
