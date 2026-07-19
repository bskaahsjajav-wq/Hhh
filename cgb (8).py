# -*- coding: utf-8 -*-
"""
Tool War Mess Đa Chức Năng By CGB Team
Giao diện ychi.py + Code từ 1.py + 3.py
FULL CODE - NO ĂN BỚT - NHÂY TAG ĐẦY ĐỦ
"""

import os
import sys
import time
import ssl
import json
import random
import string
import multiprocessing
import hashlib
import threading
import re
import requests
import psutil
import gc
from collections import defaultdict
from urllib.parse import urlparse, urlencode
from datetime import datetime
import paho.mqtt.client as mqtt
import warnings
import pyfiglet
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore", category=DeprecationWarning)
console = Console()
RESET = "\033[0m"

cookie_attempts = defaultdict(lambda: {'count': 0, 'last_reset': time.time(), 'banned_until': 0, 'permanent_ban': False})
cookie_delays = {}
active_threads = {}
cleanup_lock = threading.Lock()

# ====================== TIỆN ÍCH MÀU SẮC ======================
def rgb(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"

def gradient_text(text, colors):
    lines = text.splitlines()
    result = ""
    total_chars = sum(len(line) for line in lines if line.strip())
    idx = 0
    for line in lines:
        for ch in line:
            t = idx / max(total_chars-1, 1)
            seg = int(t * (len(colors)-1))
            c1, c2 = colors[seg], colors[min(seg+1, len(colors)-1)]
            ratio = (t * (len(colors)-1)) - seg
            r = int(c1[0] + (c2[0]-c1[0]) * ratio)
            g = int(c1[1] + (c2[1]-c1[1]) * ratio)
            b = int(c1[2] + (c2[2]-c1[2]) * ratio)
            result += rgb(r,g,b) + ch
            idx += 1
        result += RESET
        if line != lines[-1]:
            result += "\n"
    return result + RESET

def print_color(text, color_type="info"):
    colors = {
        "success": "\033[92m",
        "error": "\033[91m",
        "warning": "\033[93m",
        "info": "\033[94m",
        "cyan": "\033[96m",
        "magenta": "\033[95m",
        "reset": RESET
    }
    print(f"{colors.get(color_type, colors['info'])}{text}{colors['reset']}")

def print_line(char="=", length=60, color="cyan"):
    """In đường kẻ ngang"""
    print_color(char * length, color)

def print_header(text, color="cyan"):
    """In tiêu đề đẹp"""
    print_line("═", 70, color)
    print_color(f"  {text}", color)
    print_line("═", 70, color)

def print_section(text, color="info"):
    """In tiêu đề section"""
    print_color(f"\n┌─ {text} ─" + "─" * (60 - len(text)), color)

def print_option(num, name, desc=""):
    """In option với số"""
    if desc:
        print_color(f"  ├─ {num}. {name:<30} │ {desc}", "info")
    else:
        print_color(f"  ├─ {num}. {name}", "info")

def print_banner():
    banner = r"""
 ▄████▄   ▄████  ▓██████
██▒  ██▒ ██▒ ▀█▒ ██╔══██
██░      ▒██░▄▄▄░ ██████╔╝
██░  ██▒ ░▓█  ██▓ ██╔══██
╚█████▓▒ ░▒▓███▀▒ ██████╔╝
 ░▒   ▒   ░▒   ▒  ╚═════╝
  ░   ░    ░   ░ 
    Tool By ☯ 𝐂𝐆𝐁 ☯
    """
    colors = [(0,255,0), (0,0,255), (255,255,255)]
    print(gradient_text(banner, colors))
    print_color("="*60, "cyan")
    print_color("        Bản quyền thuộc về CGB", "magenta")
    print_color("="*60, "cyan")

def clr():
    os.system('cls' if os.name == 'nt' else 'clear')

def handle_failed_connection(cookie_hash):
    global cookie_attempts
    current_time = time.time()
    if current_time - cookie_attempts[cookie_hash]['last_reset'] > 43200:
        cookie_attempts[cookie_hash]['count'] = 0
        cookie_attempts[cookie_hash]['last_reset'] = current_time
        cookie_attempts[cookie_hash]['banned_until'] = 0
    if cookie_attempts[cookie_hash]['banned_until'] > 0:
        ban_count = getattr(cookie_attempts[cookie_hash], 'ban_count', 0) + 1
        cookie_attempts[cookie_hash]['ban_count'] = ban_count
        if ban_count >= 5:
            cookie_attempts[cookie_hash]['permanent_ban'] = True
            print_color(f"Cookie {cookie_hash[:10]} Đã Bị Ngưng Hoạt Động Vĩnh Viễn", "error")
            for key in list(active_threads.keys()):
                if key.startswith(cookie_hash):
                    active_threads[key].stop()
                    del active_threads[key]

def cleanup_global_memory():
    global active_threads, cookie_attempts
    with cleanup_lock:
        current_time = time.time()
        expired_cookies = []
        for cookie_hash, data in cookie_attempts.items():
            if data['permanent_ban'] or (current_time - data['last_reset'] > 86400):
                expired_cookies.append(cookie_hash)
        for cookie_hash in expired_cookies:
            del cookie_attempts[cookie_hash]
            for key in list(active_threads.keys()):
                if key.startswith(cookie_hash):
                    active_threads[key].stop()
                    del active_threads[key]
        gc.collect()
        process = psutil.Process()
        memory_info = process.memory_info()
        print_color(f"Memory Usage: {memory_info.rss / (1024**3):.2f} GB", "info")

def parse_cookie_string(cookie_string):
    cookie_dict = {}
    cookies = cookie_string.split(";")
    for cookie in cookies:
        if "=" in cookie:
            key, value = cookie.strip().split("=", 1)
            cookie_dict[key] = value
    return cookie_dict

def generate_offline_threading_id() -> str:
    ret = int(time.time() * 1000)
    value = random.randint(0, 4294967295)
    binary_str = format(value, "022b")[-22:]
    msgs = bin(ret)[2:] + binary_str
    return str(int(msgs, 2))

def get_headers(url: str, options: dict = {}, ctx: dict = {}, customHeader: dict = {}) -> dict:
    headers = {
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://www.facebook.com/",
        "Host": urlparse(url).netloc,
        "Origin": "https://www.facebook.com",
        "User-Agent": "Mozilla/5.0 (Linux; Android 9; SM-G973U Build/PPR1.180610.011) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Mobile Safari/537.36",
        "Connection": "keep-alive",
    }
    if "user_agent" in options:
        headers["User-Agent"] = options["user_agent"]
    for key in customHeader:
        headers[key] = customHeader[key]
    if "region" in ctx:
        headers["X-MSGR-Region"] = ctx["region"]
    return headers

def json_minimal(data):
    return json.dumps(data, separators=(",", ":"))

class Counter:
    def __init__(self, initial_value=0):
        self.value = initial_value
    def increment(self):
        self.value += 1
        return self.value
    @property
    def counter(self):
        return self.value

def digitToChar(digit):
    if digit < 10:
        return str(digit)
    return chr(ord('a') + digit - 10)

def str_base(number, base):
    if number < 0:
        return "-" + str_base(-number, base)
    (d, m) = divmod(number, base)
    if d > 0:
        return str_base(d, base) + digitToChar(m)
    return digitToChar(m)

def generate_session_id():
    return random.randint(1, 2 ** 53)

def generate_client_id():
    def gen(length):
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return gen(8) + '-' + gen(4) + '-' + gen(4) + '-' + gen(4) + '-' + gen(12)

def formAll(dataFB, FBApiReqFriendlyName=None, docID=None, requireGraphql=None):
    global _req_counter
    if '_req_counter' not in globals():
        _req_counter = Counter(0)
    __reg = _req_counter.increment()
    dataForm = {}
    if requireGraphql is None:
        dataForm["fb_dtsg"] = dataFB["fb_dtsg"]
        dataForm["jazoest"] = dataFB["jazoest"]
        dataForm["__a"] = 1
        dataForm["__user"] = str(dataFB["FacebookID"])
        dataForm["__req"] = str_base(__reg, 36)
        dataForm["__rev"] = dataFB["clientRevision"]
        dataForm["av"] = dataFB["FacebookID"]
        dataForm["fb_api_caller_class"] = "RelayModern"
        dataForm["fb_api_req_friendly_name"] = FBApiReqFriendlyName
        dataForm["server_timestamps"] = "true"
        dataForm["doc_id"] = str(docID)
    else:
        dataForm["fb_dtsg"] = dataFB["fb_dtsg"]
        dataForm["jazoest"] = dataFB["jazoest"]
        dataForm["__a"] = 1
        dataForm["__user"] = str(dataFB["FacebookID"])
        dataForm["__req"] = str_base(__reg, 36)
        dataForm["__rev"] = dataFB["clientRevision"]
        dataForm["av"] = dataFB["FacebookID"]
    return dataForm

def mainRequests(url, data, cookies):
    return {
        "url": url,
        "data": data,
        "headers": {
            "authority": "www.facebook.com",
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9,vi;q=0.8",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://www.facebook.com",
            "referer": "https://www.facebook.com/",
            "sec-ch-ua": "\"Not?A_Brand\";v=\"8\", \"Chromium\";v=\"108\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "x-fb-friendly-name": "FriendingCometFriendRequestsRootQueryRelayPreloader",
            "x-fb-lsd": "YCb7tYCGWDI6JLU5Aexa1-"
        },
        "cookies": parse_cookie_string(cookies),
        "verify": True
    }

# ====================== CLASS ngquanghuyakadzi ======================
class ngquanghuyakadzi:
    def __init__(self, cookie):
        self.cookie = cookie
        self.user_id = self.id_user()
        self.fb_dtsg = None
        self.jazoest = None
        self.rev = None
        self.init_params()

    def id_user(self):
        try:
            match = re.search(r"c_user=(\d+)", self.cookie)
            if not match:
                raise Exception("Cookie không hợp lệ")
            return match.group(1)
        except Exception as e:
            raise Exception(f"Lỗi khi lấy user_id: {str(e)}")

    def init_params(self):
        headers = {
            'Cookie': self.cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }
        urls = ['https://www.facebook.com', 'https://mbasic.facebook.com', 'https://m.facebook.com']
        for url in urls:
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code != 200:
                    continue
                fb_dtsg_patterns = [
                    r'"token":"(.*?)"',
                    r'name="fb_dtsg" value="(.*?)"',
                    r'"fb_dtsg":"(.*?)"',
                    r'fb_dtsg=([^&"]+)'
                ]
                jazoest_pattern = r'name="jazoest" value="(\d+)"'
                rev_pattern = r'"__rev":"(\d+)"'
                fb_dtsg = None
                for pattern in fb_dtsg_patterns:
                    match = re.search(pattern, response.text)
                    if match:
                        fb_dtsg = match.group(1)
                        break
                jazoest_match = re.search(jazoest_pattern, response.text)
                rev_match = re.search(rev_pattern, response.text)
                if fb_dtsg:
                    self.fb_dtsg = fb_dtsg
                    self.jazoest = jazoest_match.group(1) if jazoest_match else "22036"
                    self.rev = rev_match.group(1) if rev_match else "1015919737"
                    return
            except:
                pass
        raise Exception("Không thể lấy fb_dtsg")

    def gui_tn(self, recipient_id, message):
        if not self.fb_dtsg:
            self.init_params()
        timestamp = int(time.time() * 1000)
        data = {
            'thread_fbid': recipient_id,
            'action_type': 'ma-type:user-generated-message',
            'body': message,
            'client': 'mercury',
            'author': f'fbid:{self.user_id}',
            'timestamp': timestamp,
            'source': 'source:chat:web',
            'offline_threading_id': str(timestamp),
            'message_id': str(timestamp),
            'ephemeral_ttl_mode': '',
            '__user': self.user_id,
            '__a': '1',
            '__req': '1b',
            '__rev': self.rev,
            'fb_dtsg': self.fb_dtsg,
            'jazoest': self.jazoest
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (Chrome)',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.facebook.com',
            'Referer': f'https://www.facebook.com/messages/t/{recipient_id}',
            'Cookie': self.cookie
        }
        try:
            response = requests.post('https://www.facebook.com/messaging/send/', data=data, headers=headers, timeout=10)
            if response.status_code != 200:
                return {'success': False}
            if 'for (;;);' in response.text:
                json_data = json.loads(response.text.replace('for (;;);', ''))
                if 'error' in json_data:
                    return {'success': False}
            return {'success': True}
        except:
            return {'success': False}

# ====================== CLASS fbTools ======================
class fbTools:
    def __init__(self, dataFB, threadID="0"):
        self.threadID = threadID
        self.dataGet = None
        self.dataFB = dataFB
        self.ProcessingTime = None
        self.last_seq_id = None

    def getAllThreadList(self):
        randomNumber = str(int(format(int(time.time() * 1000), "b") + ("0000000000000000000000" + format(int(random.random() * 4294967295), "b"))[-22:], 2))
        dataForm = formAll(self.dataFB, requireGraphql=0)
        dataForm["queries"] = json.dumps({
            "o0": {
                "doc_id": "3336396659757871",
                "query_params": {
                    "limit": 20,
                    "before": None,
                    "tags": ["INBOX"],
                    "includeDeliveryReceipts": False,
                    "includeSeqID": True,
                }
            }
        })
        sendRequests = requests.post(**mainRequests("https://www.facebook.com/api/graphqlbatch/", dataForm, self.dataFB["cookieFacebook"]))
        response_text = sendRequests.text
        self.ProcessingTime = sendRequests.elapsed.total_seconds()
        if response_text.startswith("for(;;);"):
            response_text = response_text[9:]
        if not response_text.strip():
            return False
        try:
            response_parts = response_text.split("\n")
            first_part = response_parts[0]
            if first_part.strip():
                response_data = json.loads(first_part)
                self.dataGet = first_part
                if "o0" in response_data and "data" in response_data["o0"] and "viewer" in response_data["o0"]["data"] and "message_threads" in response_data["o0"]["data"]["viewer"]:
                    self.last_seq_id = response_data["o0"]["data"]["viewer"]["message_threads"]["sync_sequence_id"]
                    return True
                else:
                    return False
            else:
                return False
        except:
            return False

# ====================== CLASS MessageSender - FULL CODE ======================
class MessageSender:
    THEMES = [
        {"id": "3650637715209675", "name": "Besties"},
        {"id": "769656934577391", "name": "Women's History Month"},
        {"id": "702099018755409", "name": "Dune: Part Two"},
        {"id": "1480404512543552", "name": "Avatar: The Last Airbender"},
        {"id": "952656233130616", "name": "J.Lo"},
        {"id": "741311439775765", "name": "Love"},
        {"id": "215565958307259", "name": "Bob Marley: One Love"},
        {"id": "194982117007866", "name": "Football"},
        {"id": "1743641112805218", "name": "Soccer"},
        {"id": "730357905262632", "name": "Mean Girls"},
        {"id": "1270466356981452", "name": "Wonka"},
        {"id": "704702021720552", "name": "Pizza"},
        {"id": "1013083536414851", "name": "Wish"},
        {"id": "359537246600743", "name": "Trolls"},
        {"id": "173976782455615", "name": "The Marvels"},
        {"id": "2317258455139234", "name": "One Piece"},
        {"id": "6685081604943977", "name": "1989"},
        {"id": "1508524016651271", "name": "Avocado"},
        {"id": "265997946276694", "name": "Loki Season 2"},
        {"id": "6584393768293861", "name": "olivia rodrigo"},
        {"id": "845097890371902", "name": "Baseball"},
        {"id": "292955489929680", "name": "Lollipop"},
        {"id": "976389323536938", "name": "Loops"},
        {"id": "810978360551741", "name": "Parenthood"},
        {"id": "195296273246380", "name": "Bubble Tea"},
        {"id": "6026716157422736", "name": "Basketball"},
        {"id": "693996545771691", "name": "Elephants & Flowers"},
        {"id": "390127158985345", "name": "Chill"},
        {"id": "365557122117011", "name": "Support"},
        {"id": "339021464972092", "name": "Music"},
        {"id": "1060619084701625", "name": "Lo-Fi"},
        {"id": "3190514984517598", "name": "Sky"},
        {"id": "627144732056021", "name": "Celebration"},
        {"id": "275041734441112", "name": "Care"},
        {"id": "3082966625307060", "name": "Astrology"},
        {"id": "539927563794799", "name": "Cottagecore"},
        {"id": "527564631955494", "name": "Ocean"},
        {"id": "230032715012014", "name": "Tie-Dye"},
        {"id": "788274591712841", "name": "Monochrome"},
        {"id": "3259963564026002", "name": "Default"},
        {"id": "724096885023603", "name": "Berry"},
        {"id": "624266884847972", "name": "Candy"},
        {"id": "273728810607574", "name": "Unicorn"},
        {"id": "262191918210707", "name": "Tropical"},
        {"id": "2533652183614000", "name": "Maple"},
        {"id": "909695489504566", "name": "Sushi"},
        {"id": "582065306070020", "name": "Rocket"},
        {"id": "557344741607350", "name": "Citrus"},
        {"id": "280333826736184", "name": "Lollipop"},
        {"id": "271607034185782", "name": "Shadow"},
        {"id": "1257453361255152", "name": "Rose"},
        {"id": "571193503540759", "name": "Lavender"},
        {"id": "2873642949430623", "name": "Tulip"},
        {"id": "3273938616164733", "name": "Classic"},
        {"id": "403422283881973", "name": "Apple"},
        {"id": "3022526817824329", "name": "Peach"},
        {"id": "672058580051520", "name": "Honey"},
        {"id": "3151463484918004", "name": "Kiwi"},
        {"id": "736591620215564", "name": "Ocean"},
        {"id": "193497045377796", "name": "Grape"},
    ]

    def __init__(self, fbt, dataFB, fb_instance):
        self.fbt = fbt
        self.dataFB = dataFB
        self.fb_instance = fb_instance
        self.mqtt = None
        self.ws_req_number = 0
        self.ws_task_number = 0
        self.syncToken = None
        self.lastSeqID = None
        self.req_callbacks = {}
        self.cookie_hash = hashlib.md5(dataFB['cookieFacebook'].encode()).hexdigest()
        self.connect_attempts = 0
        self.last_cleanup = time.time()
        self.mqtt_lock = threading.Lock()

    def cleanup_memory(self):
        current_time = time.time()
        if current_time - self.last_cleanup > 3600:
            self.req_callbacks.clear()
            gc.collect()
            self.last_cleanup = current_time

    def get_last_seq_id(self):
        success = self.fbt.getAllThreadList()
        if success:
            self.lastSeqID = self.fbt.last_seq_id
        else:
            print_color("Failed To Get Last Sequence ID.", "error")

    def on_disconnect(self, client, userdata, rc):
        global cookie_attempts
        print_color(f"Disconnected With Code {rc}", "warning")
        cookie_attempts[self.cookie_hash]['count'] += 1
        current_time = time.time()
        if current_time - cookie_attempts[self.cookie_hash]['last_reset'] > 43200:
            cookie_attempts[self.cookie_hash]['count'] = 1
            cookie_attempts[self.cookie_hash]['last_reset'] = current_time
        if cookie_attempts[self.cookie_hash]['count'] >= 20:
            print_color(f"Cookie {self.cookie_hash[:10]} Bị Tạm Ngưng Connect Trong 12 Giờ", "error")
            cookie_attempts[self.cookie_hash]['banned_until'] = current_time + 43200
            return
        if rc != 0:
            print_color("Attempting To Reconnect...", "warning")
            try:
                time.sleep(min(cookie_attempts[self.cookie_hash]['count'] * 2, 30))
                client.reconnect()
            except:
                print_color("Reconnect Failed", "error")

    def _messenger_queue_publish(self, client, userdata, flags, rc, properties=None):
        print_color(f"Connected To MQTT With Code: {rc}", "info")
        if rc != 0:
            print_color(f"Connection Failed With Code {rc}", "error")
            return
        topics = [("/t_ms", 0)]
        client.subscribe(topics)
        queue = {
            "sync_api_version": 10,
            "max_deltas_able_to_process": 1000,
            "delta_batch_size": 500,
            "encoding": "JSON",
            "entity_fbid": self.dataFB['FacebookID']
        }
        if self.syncToken is None:
            topic = "/messenger_sync_create_queue"
            queue["initial_titan_sequence_id"] = self.lastSeqID
            queue["device_params"] = None
        else:
            topic = "/messenger_sync_get_diffs"
            queue["last_seq_id"] = self.lastSeqID
            queue["sync_token"] = self.syncToken
        client.publish(topic, json_minimal(queue), qos=1, retain=False)

    def connect_mqtt(self):
        global cookie_attempts
        if cookie_attempts[self.cookie_hash]['permanent_ban']:
            print_color(f"Cookie {self.cookie_hash[:10]} Đã Bị Ngưng Connect Vĩnh Viễn", "error")
            return False
        current_time = time.time()
        if current_time < cookie_attempts[self.cookie_hash]['banned_until']:
            remaining = cookie_attempts[self.cookie_hash]['banned_until'] - current_time
            print_color(f"Cookie {self.cookie_hash[:10]} Bị Tạm Khóa, Còn {remaining/3600:.1f} Giờ", "warning")
            return False
        if not self.lastSeqID:
            print_color("Error: No last_seq_id Available.", "error")
            return False
        
        chat_on = json_minimal(True)
        session_id = generate_session_id()
        user = {
            "u": self.dataFB["FacebookID"],
            "s": session_id,
            "chat_on": chat_on,
            "fg": False,
            "d": generate_client_id(),
            "ct": "websocket",
            "aid": 219994525426954,
            "mqtt_sid": "",
            "cp": 3,
            "ecp": 10,
            "st": ["/t_ms", "/messenger_sync_get_diffs", "/messenger_sync_create_queue"],
            "pm": [],
            "dc": "",
            "no_auto_fg": True,
            "gas": None,
            "pack": [],
        }
        host = f"wss://edge-chat.messenger.com/chat?region=eag&sid={session_id}"
        options = {
            "client_id": "mqttwsclient",
            "username": json_minimal(user),
            "clean": True,
            "ws_options": {
                "headers": {
                    "Cookie": self.dataFB['cookieFacebook'],
                    "Origin": "https://www.messenger.com",
                    "User-Agent": "Mozilla/5.0 (Linux; Android 9; SM-G973U Build/PPR1.180610.011) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Mobile Safari/537.36",
                    "Referer": "https://www.messenger.com/",
                    "Host": "edge-chat.messenger.com",
                },
            },
            "keepalive": 10,
        }
        
        try:
            self.mqtt = mqtt.Client(
                client_id="mqttwsclient",
                clean_session=True,
                protocol=mqtt.MQTTv31,
                transport="websockets",
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2
            )
        except:
            self.mqtt = mqtt.Client(
                client_id="mqttwsclient",
                clean_session=True,
                protocol=mqtt.MQTTv31,
                transport="websockets"
            )
        
        self.mqtt.tls_set(certfile=None, keyfile=None, cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLSv1_2)
        self.mqtt.on_connect = self._messenger_queue_publish
        self.mqtt.on_disconnect = self.on_disconnect
        self.mqtt.username_pw_set(username=options["username"])
        parsed_host = urlparse(host)
        self.mqtt.ws_set_options(
            path=f"{parsed_host.path}?{parsed_host.query}",
            headers=options["ws_options"]["headers"],
        )
        print_color(f"Connecting To {options['ws_options']['headers']['Host']}...", "info")
        try:
            self.mqtt.connect(
                host=options["ws_options"]["headers"]["Host"],
                port=443,
                keepalive=options["keepalive"],
            )
            print_color("MQTT Connection Established", "success")
            self.mqtt.loop_start()
            time.sleep(2)
            return True
        except Exception as e:
            print_color(f"MQTT Connection Error: {e}", "error")
            cookie_attempts[self.cookie_hash]['count'] += 1
            return False

    def stop(self):
        if self.mqtt:
            print_color("Stopping MQTT Client...", "info")
            try:
                self.mqtt.loop_stop()
                self.mqtt.disconnect()
                time.sleep(1)
            except:
                pass
        self.cleanup_memory()

    def sendTypingIndicatorMqtt(self, isTyping, thread_id, callback=None):
        if self.mqtt is None:
            return False
        
        with self.mqtt_lock:
            try:
                self.cleanup_memory()
                self.ws_req_number += 1
                label = '3'
                is_group_thread = 1
                attribution = 0
                task_payload = {
                    "thread_key": thread_id,
                    "is_group_thread": is_group_thread,
                    "is_typing": 1 if isTyping else 0,
                    "attribution": attribution,
                }
                content = {
                    "app_id": "2220391788200892",
                    "payload": json.dumps({
                        "label": label,
                        "payload": json.dumps(task_payload, separators=(",", ":")),
                        "version": "25393437286970779",
                    }, separators=(",", ":")),
                    "request_id": self.ws_req_number,
                    "type": 4,
                }
                if callback is not None and callable(callback):
                    self.req_callbacks[self.ws_req_number] = callback
                self.mqtt.publish(
                    topic="/ls_req",
                    payload=json.dumps(content, separators=(",", ":")),
                    qos=1,
                    retain=False,
                )
                return True
            except Exception as e:
                return False

    def send_message_with_mentions(self, thread_id, text, mentions_data):
        """GỬI TIN NHẮN CÓ MENTION ĐẦY ĐỦ - KHÔNG ĂN BỚT"""
        if self.mqtt is None:
            return False
        
        with self.mqtt_lock:
            try:
                self.ws_req_number += 1
                content = {
                    "app_id": "2220391788200892",
                    "payload": {
                        "data_trace_id": None,
                        "epoch_id": int(generate_offline_threading_id()),
                        "tasks": [],
                        "version_id": "7545284305482586",
                    },
                    "request_id": self.ws_req_number,
                    "type": 3,
                }
                
                if text:
                    self.ws_task_number += 1
                    
                    # Xây dựng tin nhắn với mention
                    task_payload = {
                        "initiating_source": 0,
                        "multitab_env": 0,
                        "otid": generate_offline_threading_id(),
                        "send_type": 1,
                        "skip_url_preview_gen": 0,
                        "source": 0,
                        "sync_group": 1,
                        "text": text,
                        "text_has_links": 0,
                        "thread_id": int(thread_id),
                    }
                    
                    # Thêm mention data nếu có
                    if mentions_data and len(mentions_data) > 0:
                        valid_mentions = []
                        
                        for mention in mentions_data:
                            if "id" in mention and "tag" in mention:
                                tag_text = f"@{mention['tag']}"
                                find = text.find(tag_text)
                                
                                if find != -1:
                                    valid_mentions.append({
                                        "i": mention["id"],
                                        "o": find,
                                        "l": len(tag_text),
                                    })
                        
                        # Chỉ thêm mention_data nếu có valid mentions
                        if valid_mentions:
                            task_payload["mention_data"] = {
                                "mention_ids": ",".join([str(x["i"]) for x in valid_mentions]),
                                "mention_lengths": ",".join([str(x["l"]) for x in valid_mentions]),
                                "mention_offsets": ",".join([str(x["o"]) for x in valid_mentions]),
                                "mention_types": ",".join(["p" for _ in valid_mentions]),
                            }
                    
                    task = {
                        "failure_count": None,
                        "label": "46",
                        "payload": json.dumps(task_payload, separators=(",", ":")),
                        "queue_name": str(thread_id),
                        "task_id": self.ws_task_number,
                    }
                    content["payload"]["tasks"].append(task)
                    
                    # Mark as read
                    self.ws_task_number += 1
                    task_mark_payload = {
                        "last_read_watermark_ts": int(time.time() * 1000),
                        "sync_group": 1,
                        "thread_id": int(thread_id),
                    }
                    task_mark = {
                        "failure_count": None,
                        "label": "21",
                        "payload": json.dumps(task_mark_payload, separators=(",", ":")),
                        "queue_name": str(thread_id),
                        "task_id": self.ws_task_number,
                    }
                    content["payload"]["tasks"].append(task_mark)
                
                content["payload"] = json.dumps(content["payload"], separators=(",", ":"))
                
                self.mqtt.publish(
                    topic="/ls_req",
                    payload=json.dumps(content, separators=(",", ":")),
                    qos=1,
                    retain=False,
                )
                return True
            except Exception as e:
                print_color(f"Error Publishing Message: {e}", "error")
                return False

    def send_message(self, text=None, thread_id=None, attachment=None, mention=None, message_id=None, callback=None):
        if self.mqtt is None:
            return False
        if thread_id is None:
            return False
        if text is None and attachment is None:
            return False
        
        with self.mqtt_lock:
            try:
                self.cleanup_memory()
                self.ws_req_number += 1
                content = {
                    "app_id": "2220391788200892",
                    "payload": {
                        "data_trace_id": None,
                        "epoch_id": int(generate_offline_threading_id()),
                        "tasks": [],
                        "version_id": "7545284305482586",
                    },
                    "request_id": self.ws_req_number,
                    "type": 3,
                }
                text = str(text) if text is not None else ""
                if len(text) > 0:
                    self.ws_task_number += 1
                    task_payload = {
                        "initiating_source": 0,
                        "multitab_env": 0,
                        "otid": generate_offline_threading_id(),
                        "send_type": 1,
                        "skip_url_preview_gen": 0,
                        "source": 0,
                        "sync_group": 1,
                        "text": text,
                        "text_has_links": 0,
                        "thread_id": int(thread_id),
                    }
                    if message_id is not None:
                        if not isinstance(message_id, str):
                            raise ValueError("message_id must be a string")
                        task_payload["reply_metadata"] = {
                            "reply_source_id": message_id,
                            "reply_source_type": 1,
                            "reply_type": 0,
                        }
                    task = {
                        "failure_count": None,
                        "label": "46",
                        "payload": json.dumps(task_payload, separators=(",", ":")),
                        "queue_name": str(thread_id),
                        "task_id": self.ws_task_number,
                    }
                    content["payload"]["tasks"].append(task)
                self.ws_task_number += 1
                task_mark_payload = {
                    "last_read_watermark_ts": int(time.time() * 1000),
                    "sync_group": 1,
                    "thread_id": int(thread_id),
                }
                task_mark = {
                    "failure_count": None,
                    "label": "21",
                    "payload": json.dumps(task_mark_payload, separators=(",", ":")),
                    "queue_name": str(thread_id),
                    "task_id": self.ws_task_number,
                }
                content["payload"]["tasks"].append(task_mark)
                content["payload"] = json.dumps(content["payload"], separators=(",", ":"))
                if callback is not None and callable(callback):
                    self.req_callbacks[self.ws_req_number] = callback
                self.mqtt.publish(
                    topic="/ls_req",
                    payload=json.dumps(content, separators=(",", ":")),
                    qos=1,
                    retain=False,
                )
                return True
            except Exception as e:
                return False

    def createPollMqtt(self, title, options, thread_id, callback=None):
        if self.mqtt is None:
            return False
        
        with self.mqtt_lock:
            try:
                self.cleanup_memory()
                self.ws_req_number += 1
                self.ws_task_number += 1
                task_payload = {
                    "question_text": title,
                    "thread_key": thread_id,
                    "options": options,
                    "sync_group": 1,
                }
                task = {
                    "failure_count": None,
                    "label": "163",
                    "payload": json.dumps(task_payload, separators=(",", ":")),
                    "queue_name": "poll_creation",
                    "task_id": self.ws_task_number,
                }
                content = {
                    "app_id": "2220391788200892",
                    "payload": json.dumps({
                        "data_trace_id": None,
                        "epoch_id": int(generate_offline_threading_id()),
                        "tasks": [task],
                        "version_id": "7158486590867448",
                    }, separators=(",", ":")),
                    "request_id": self.ws_req_number,
                    "type": 3,
                }
                if callback is not None and callable(callback):
                    self.req_callbacks[self.ws_req_number] = callback
                self.mqtt.publish(
                    topic="/ls_req",
                    payload=json.dumps(content, separators=(",", ":")),
                    qos=1,
                    retain=False,
                )
                return True
            except Exception as e:
                return False

    def set_theme(self, theme_id, thread_id, callback=None):
        if self.mqtt is None:
            return False
        
        with self.mqtt_lock:
            try:
                self.cleanup_memory()
                if not theme_id:
                    selected_theme = random.choice(self.THEMES)
                    theme_id = selected_theme["id"]
                    theme_name = selected_theme["name"]
                else:
                    selected_theme = next((theme for theme in self.THEMES if theme["id"] == theme_id), None)
                    if not selected_theme:
                        return False
                    theme_name = selected_theme["name"]
                self.ws_req_number += 1
                self.ws_task_number += 1
                task_payload = {
                    "thread_key": thread_id,
                    "theme_fbid": theme_id,
                    "source": None,
                    "sync_group": 1,
                    "payload": None,
                }
                task = {
                    "failure_count": None,
                    "label": "43",
                    "payload": json.dumps(task_payload, separators=(",", ":")),
                    "queue_name": "thread_theme",
                    "task_id": self.ws_task_number,
                }
                content = {
                    "app_id": "2220391788200892",
                    "payload": json.dumps({
                        "data_trace_id": None,
                        "epoch_id": int(generate_offline_threading_id()),
                        "tasks": [task],
                        "version_id": "25095469420099952",
                    }, separators=(",", ":")),
                    "request_id": self.ws_req_number,
                    "type": 3,
                }
                if callback is not None and callable(callback):
                    self.req_callbacks[self.ws_req_number] = callback
                self.mqtt.publish(
                    topic="/ls_req",
                    payload=json.dumps(content, separators=(",", ":")),
                    qos=1,
                    retain=False,
                )
                print_color(f"Đã thay đổi theme thành: {theme_name}", "success")
                return True
            except Exception as e:
                return False

    def share_contact(self, text=None, sender_id=None, thread_id=None):
        if self.mqtt is None:
            return False
        if sender_id is None or thread_id is None:
            return False
        
        with self.mqtt_lock:
            try:
                self.cleanup_memory()
                self.ws_req_number += 1
                self.ws_task_number += 1
                content = {
                    "app_id": "2220391788200892",
                    "payload": {
                        "tasks": [{
                            "label": 359,
                            "payload": json.dumps({
                                "contact_id": sender_id,
                                "sync_group": 1,
                                "text": text or "",
                                "thread_id": thread_id
                            }, separators=(",", ":")),
                            "queue_name": "xma_open_contact_share",
                            "task_id": self.ws_task_number,
                            "failure_count": None,
                        }],
                        "epoch_id": generate_offline_threading_id(),
                        "version_id": "7214102258676893",
                    },
                    "request_id": self.ws_req_number,
                    "type": 3
                }
                content["payload"] = json.dumps(content["payload"], separators=(",", ":"))
                self.mqtt.publish(
                    topic="/ls_req",
                    payload=json.dumps(content, separators=(",", ":")),
                    qos=1,
                    retain=False,
                )
                return True
            except Exception as e:
                return False

    def share_link(self, text=None, url=None, thread_id=None, callback=None):
        if self.mqtt is None:
            return False
        if thread_id is None:
            return False
        
        with self.mqtt_lock:
            try:
                self.cleanup_memory()
                self.ws_req_number += 1
                self.ws_task_number += 1
                content = {
                    "app_id": "2220391788200892",
                    "payload": {
                        "tasks": [{
                            "label": 46,
                            "payload": json.dumps({
                                "otid": generate_offline_threading_id(),
                                "source": 524289,
                                "sync_group": 1,
                                "send_type": 6,
                                "mark_thread_read": 0,
                                "url": url or "https://www.facebook.com",
                                "text": text or "",
                                "thread_id": thread_id,
                                "initiating_source": 0
                            }, separators=(",", ":")),
                            "queue_name": str(thread_id),
                            "task_id": self.ws_task_number,
                            "failure_count": None,
                        }],
                        "epoch_id": generate_offline_threading_id(),
                        "version_id": "7191105584331330",
                    },
                    "request_id": self.ws_req_number,
                    "type": 3
                }
                content["payload"] = json.dumps(content["payload"], separators=(",", ":"))
                if callback is not None and callable(callback):
                    self.req_callbacks[self.ws_req_number] = callback
                self.mqtt.publish(
                    topic="/ls_req",
                    payload=json.dumps(content, separators=(",", ":")),
                    qos=1,
                    retain=False,
                )
                return True
            except Exception as e:
                return False

    def upload_file(self, file_path):
        user_id = self.fb_instance.user_id
        url = "https://www.facebook.com/ajax/mercury/upload.php"
        headers = {
            'Cookie': self.dataFB['cookieFacebook'],
            'User-Agent': 'python-http/0.27.0',
            'Origin': 'https://www.facebook.com',
            'Referer': 'https://www.facebook.com/'
        }
        params = {
            'ads_manager_write_regions': 'true',
            '__aaid': '0',
            '__user': user_id,
            '__a': '1',
            '__hs': '20207.HYP:comet_pkg.2.1...0',
            'dpr': '3',
            '__ccg': 'GOOD',
            '__rev': '1022311521',
            'fb_dtsg': self.dataFB['fb_dtsg'],
            'jazoest': self.dataFB['jazoest'],
            '__crn': 'comet.fbweb.CometHomeRoute'
        }
        mime_type = 'image/jpeg'
        if file_path.lower().endswith(('.mp4', '.mov', '.avi', '.wmv')):
            mime_type = 'video/mp4'
        with open(file_path, 'rb') as file:
            files = {'farr': (file_path.split('/')[-1], file, mime_type)}
            response = requests.post(url, headers=headers, params=params, files=files)
        if response.status_code == 200:
            content = response.text.replace('for (;;);', '')
            try:
                data = json.loads(content)
                if 'payload' in data and 'metadata' in data['payload'] and '0' in data['payload']['metadata']:
                    metadata = data['payload']['metadata']['0']
                    if mime_type.startswith('video'):
                        file_id = metadata.get('video_id')
                        return {'id': file_id, 'type': 'video'}
                    else:
                        file_id = metadata.get('fbid') or metadata.get('image_id')
                        return {'id': file_id, 'type': 'image'}
            except json.JSONDecodeError:
                raise Exception("Cannot Parse JSON From Response")
        else:
            raise Exception(f"Error Uploading File: {response.status_code}")

    def download_and_upload_file(self, file_url):
        user_id = self.fb_instance.user_id
        url = "https://www.facebook.com/ajax/mercury/upload.php"
        headers = {
            'Cookie': self.dataFB['cookieFacebook'],
            'User-Agent': 'python-http/0.27.0',
            'Origin': 'https://www.facebook.com',
            'Referer': 'https://www.facebook.com/'
        }
        params = {
            'ads_manager_write_regions': 'true',
            '__aaid': '0',
            '__user': user_id,
            '__a': '1',
            '__hs': '20207.HYP:comet_pkg.2.1...0',
            'dpr': '3',
            '__ccg': 'GOOD',
            '__rev': '1022311521',
            'fb_dtsg': self.dataFB['fb_dtsg'],
            'jazoest': self.dataFB['jazoest'],
            '__crn': 'comet.fbweb.CometHomeRoute'
        }
        mime_type = 'image/jpeg'
        if file_url.lower().endswith(('.mp4', '.mov', '.avi', '.wmv')):
            mime_type = 'video/mp4'
        elif file_url.lower().endswith(('.png', '.gif')):
            mime_type = f'image/{file_url.split(".")[-1].lower()}'
        try:
            response = requests.get(file_url, stream=True, timeout=10)
            if response.status_code != 200:
                raise Exception(f"Cannot download file from URL: {response.status_code}")
            file_name = file_url.split('/')[-1] or f"temp_{int(time.time())}.{mime_type.split('/')[-1]}"
            files = {'farr': (file_name, response.content, mime_type)}
            upload_response = requests.post(url, headers=headers, params=params, files=files)
            if upload_response.status_code == 200:
                content = upload_response.text.replace('for (;;);', '')
                try:
                    data = json.loads(content)
                    if 'payload' in data and 'metadata' in data['payload'] and '0' in data['payload']['metadata']:
                        metadata = data['payload']['metadata']['0']
                        if mime_type.startswith('video'):
                            file_id = metadata.get('video_id')
                            return {'id': file_id, 'type': 'video'}
                        else:
                            file_id = metadata.get('fbid') or metadata.get('image_id')
                            return {'id': file_id, 'type': 'image'}
                except json.JSONDecodeError:
                    raise Exception("Cannot Parse JSON From Response")
            else:
                raise Exception(f"Error Uploading File: {upload_response.status_code}")
        except Exception as e:
            print_color(f"Error: {e}", "error")
            return None

    def send_message_with_attachment(self, text, thread_id, file_path_or_url, message_id=None, callback=None):
        if self.mqtt is None:
            return False
        if thread_id is None:
            return False
        try:
            if file_path_or_url.startswith(('http://', 'https://')):
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                try:
                    response = requests.get(file_path_or_url, headers=headers, timeout=10)
                    response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    return False
                content_type = response.headers.get('Content-Type', '')
                if 'image' not in content_type and 'video' not in content_type:
                    return False
                file_info = self.download_and_upload_file(file_path_or_url)
            else:
                file_info = self.upload_file(file_path_or_url)
            if not file_info:
                return False
            
            with self.mqtt_lock:
                self.cleanup_memory()
                self.ws_req_number += 1
                content = {
                    "app_id": "2220391788200892",
                    "payload": {
                        "data_trace_id": None,
                        "epoch_id": int(generate_offline_threading_id()),
                        "tasks": [],
                        "version_id": "7545284305482586",
                    },
                    "request_id": self.ws_req_number,
                    "type": 3,
                }
                self.ws_task_number += 1
                task_payload = {
                    "attachment_fbids": [file_info["id"]],
                    "initiating_source": 0,
                    "multitab_env": 0,
                    "otid": generate_offline_threading_id(),
                    "send_type": 3,
                    "skip_url_preview_gen": 0,
                    "source": 0,
                    "sync_group": 1,
                    "text": text,
                    "text_has_links": 0,
                    "thread_id": int(thread_id),
                }
                if message_id is not None:
                    if not isinstance(message_id, str):
                        raise ValueError("message_id must be a string")
                    task_payload["reply_metadata"] = {
                        "reply_source_id": message_id,
                        "reply_source_type": 1,
                        "reply_type": 0,
                    }
                task = {
                    "failure_count": None,
                    "label": "46",
                    "payload": json.dumps(task_payload, separators=(",", ":")),
                    "queue_name": str(thread_id),
                    "task_id": self.ws_task_number,
                }
                content["payload"]["tasks"].append(task)
                self.ws_task_number += 1
                task_mark_payload = {
                    "last_read_watermark_ts": int(time.time() * 1000),
                    "sync_group": 1,
                    "thread_id": int(thread_id),
                }
                task_mark = {
                    "failure_count": None,
                    "label": "21",
                    "payload": json.dumps(task_mark_payload, separators=(",", ":")),
                    "queue_name": str(thread_id),
                    "task_id": self.ws_task_number,
                }
                content["payload"]["tasks"].append(task_mark)
                content["payload"] = json.dumps(content["payload"], separators=(",", ":"))
                if callback is not None and callable(callback):
                    self.req_callbacks[self.ws_req_number] = callback
                try:
                    self.mqtt.publish(
                        topic="/ls_req",
                        payload=json.dumps(content, separators=(",", ":")),
                        qos=1,
                        retain=False,
                    )
                    return True
                except Exception as e:
                    return False
        except Exception as e:
            return False

# ====================== CLASS Messenger ======================
class Messenger:
    def __init__(self, cookie, dataFB):
        self.cookie = cookie
        self.user_id = dataFB["FacebookID"]
        self.fb_dtsg = dataFB["fb_dtsg"]
        self.jazoest = dataFB["jazoest"]
        self.fb = ngquanghuyakadzi(cookie)
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        ]

    def get_thread_list(self, limit=100):
        headers = {
            'Cookie': self.cookie,
            'User-Agent': random.choice(self.user_agents),
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
            'Origin': 'https://www.facebook.com',
            'Referer': 'https://www.facebook.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-FB-Friendly-Name': 'MessengerThreadListQuery',
            'X-FB-LSD': 'null'
        }
        form_data = {
            "av": self.user_id,
            "__user": self.user_id,
            "__a": "1",
            "__req": "1b",
            "__hs": "19234.HYP:comet_pkg.2.1..2.1",
            "dpr": "1",
            "__ccg": "EXCELLENT",
            "__rev": "1015919737",
            "__comet_req": "15",
            "fb_dtsg": self.fb_dtsg,
            "jazoest": self.jazoest,
            "lsd": "null",
            "__spin_r": "",
            "__spin_b": "trunk",
            "__spin_t": str(int(time.time())),
            "queries": json.dumps({
                "o0": {
                    "doc_id": "3336396659757871",
                    "query_params": {
                        "limit": limit,
                        "before": None,
                        "tags": ["INBOX"],
                        "includeDeliveryReceipts": False,
                        "includeSeqID": True,
                    }
                }
            })
        }
        try:
            response = requests.post('https://www.facebook.com/api/graphqlbatch/', data=form_data, headers=headers, timeout=15)
            if response.status_code != 200:
                return {"error": f"HTTP Error: {response.status_code}"}
            response_text = response.text.split('{"successful_results"')[0]
            data = json.loads(response_text)
            if "o0" not in data:
                return {"error": "Không tìm thấy dữ liệu thread list"}
            if "errors" in data["o0"]:
                return {"error": f"Facebook API Error: {data['o0']['errors'][0]['summary']}"}
            threads = data["o0"]["data"]["viewer"]["message_threads"]["nodes"]
            thread_list = []
            for thread in threads:
                if not thread.get("thread_key") or not thread["thread_key"].get("thread_fbid"):
                    continue
                thread_list.append({
                    "thread_id": thread["thread_key"]["thread_fbid"],
                    "thread_name": thread.get("name", "Không có tên")
                })
            return {
                "success": True,
                "thread_count": len(thread_list),
                "threads": thread_list
            }
        except Exception as e:
            return {"error": f"Lỗi: {str(e)}"}

    def get_group_members(self, thread_id):
        headers = {
            'Cookie': self.cookie,
            'User-Agent': 'python-http/0.27.0',
            'Accept': '*/*',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.facebook.com',
            'Host': 'www.facebook.com',
            'Referer': 'https://www.facebook.com/'
        }
        payload = {
            'queries': json.dumps({
                'o0': {
                    'doc_id': '3449967031715030',
                    'query_params': {
                        'id': thread_id,
                        'message_limit': 0,
                        'load_messages': False,
                        'load_read_receipts': False,
                        'before': None
                    }
                }
            }),
            'batch_name': 'MessengerGraphQLThreadFetcher',
            'fb_dtsg': self.fb_dtsg,
            'jazoest': self.jazoest
        }
        try:
            response = requests.post('https://www.facebook.com/api/graphqlbatch/', headers=headers, data=payload)
            content = response.text
            if content.startswith('for(;;);'):
                content = content[9:]
            json_objects = []
            current_json = ""
            in_quotes = False
            escape_next = False
            brackets = 0
            for char in content:
                if escape_next:
                    current_json += char
                    escape_next = False
                    continue
                if char == '\\' and not escape_next:
                    current_json += char
                    escape_next = True
                    continue
                if char == '"' and not escape_next:
                    in_quotes = not in_quotes
                if not in_quotes:
                    if char == '{':
                        brackets += 1
                    elif char == '}':
                        brackets -= 1
                        if brackets == 0:
                            current_json += char
                            json_objects.append(current_json)
                            current_json = ""
                            continue
                if brackets > 0:
                    current_json += char
            if json_objects:
                data = json.loads(json_objects[0])
                thread_data = data.get("o0", {}).get("data", {}).get("message_thread", {})
                all_participants = thread_data.get("all_participants", {}).get("edges", [])
                members = []
                for participant in all_participants:
                    user = participant.get("node", {}).get("messaging_actor", {})
                    members.append({
                        "name": user.get("name"),
                        "id": user.get("id")
                    })
                return {"success": True, "members": members}
            else:
                return {"error": "Không tìm thấy dữ liệu thành viên"}
        except Exception as e:
            return {"error": f"Lỗi: {str(e)}"}

# ====================== HÀM UTILITY ======================
def generateTimestampRelative():
    current_time = datetime.now()
    hours_ago = (datetime.now() - datetime.now()).seconds // 3600
    if hours_ago == 0:
        return "Just now"
    elif hours_ago == 1:
        return "1 hour ago"
    else:
        return f"{hours_ago} hours ago"

def tenbox(newTitle, threadID, dataFB):
    try:
        message_id = generate_offline_threading_id()
        timestamp = int(time.time() * 1000)
        form_data = {
            "client": "mercury",
            "action_type": "ma-type:log-message",
            "author": f"fbid:{dataFB['FacebookID']}",
            "thread_id": str(threadID),
            "timestamp": timestamp,
            "timestamp_relative": str(int(time.time())),
            "source": "source:chat:web",
            "source_tags[0]": "source:chat",
            "offline_threading_id": message_id,
            "message_id": message_id,
            "threading_id": generate_offline_threading_id(),
            "thread_fbid": str(threadID),
            "thread_name": str(newTitle),
            "log_message_type": "log:thread-name",
            "fb_dtsg": dataFB["fb_dtsg"],
            "jazoest": dataFB["jazoest"],
            "__user": str(dataFB["FacebookID"]),
            "__a": "1",
            "__req": "1",
            "__rev": dataFB.get("clientRevision", "1015919737")
        }
        response = requests.post(
            "https://www.facebook.com/messaging/set_thread_name/",
            data=form_data,
            headers=get_headers("https://www.facebook.com", customHeader={"Content-Length": str(len(form_data))}),
            cookies=parse_cookie_string(dataFB["cookieFacebook"]),
            timeout=10
        )
        if response.status_code == 200:
            return True, f"✅ Đã đổi tên thành: {newTitle}"
        else:
            return False, f"❌ Lỗi HTTP {response.status_code} khi đổi tên."
    except Exception as e:
        return False, f"❌ Lỗi: {e}"

def add_user_to_group(dataFB, user_ids, thread_id, max_retries=3):
    for attempt in range(max_retries):
        try:
            if not isinstance(user_ids, list):
                user_ids = [user_ids]
            for user_id in user_ids:
                if not isinstance(user_id, (str, int)) or not str(user_id).isdigit():
                    raise ValueError(f"Invalid user_id: {user_id}")
            if not isinstance(thread_id, (str, int)) or not str(thread_id).isdigit():
                raise ValueError(f"Invalid thread_id: {thread_id}")
            message_and_otid = generate_offline_threading_id()
            form = {
                "client": "mercury",
                "action_type": "ma-type:log-message",
                "author": f"fbid:{dataFB['FacebookID']}",
                "thread_id": "",
                "timestamp": str(int(time.time() * 1000)),
                "timestamp_absolute": "Today",
                "timestamp_relative": generateTimestampRelative(),
                "timestamp_time_passed": "0",
                "is_unread": "false",
                "is_cleared": "false",
                "is_forward": "false",
                "is_filtered_content": "false",
                "is_filtered_content_bh": "false",
                "is_filtered_content_account": "false",
                "is_spoof_warning": "false",
                "source": "source:chat:web",
                "source_tags[0]": "source:chat",
                "log_message_type": "log:subscribe",
                "status": "0",
                "offline_threading_id": message_and_otid,
                "message_id": message_and_otid,
                "threading_id": f"<{int(time.time() * 1000)}:{message_and_otid}>",
                "manual_retry_cnt": "0",
                "thread_fbid": str(thread_id),
                "fb_dtsg": dataFB["fb_dtsg"],
                "jazoest": dataFB["jazoest"],
                "__user": str(dataFB["FacebookID"]),
                "__a": "1",
                "__req": str_base(Counter().increment(), 36),
                "__rev": dataFB.get("clientRevision", "1015919737")
            }
            for i, user_id in enumerate(user_ids):
                form[f"log_message_data[added_participants][{i}]"] = f"fbid:{user_id}"
            headers = get_headers("https://www.facebook.com/messaging/send/", customHeader={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-FB-LSD": dataFB.get("lsd", "YCb7tYCGWDI6JLU5Aexa1-"),
                "Content-Length": str(len(urlencode(form)))
            })
            response = requests.post(
                "https://www.facebook.com/messaging/send/",
                data=form,
                headers=headers,
                cookies=parse_cookie_string(dataFB["cookieFacebook"]),
                timeout=15
            )
            if response.status_code != 200:
                raise Exception(f"HTTP Error {response.status_code}")
            content = response.text.replace('for (;;);', '')
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                raise Exception(f"JSON Decode Error: {e}")
            if "error" in data:
                error_msg = data.get('errorDescription', 'Unknown error')
                error_code = data.get('error', 'No error code')
                if error_code == 1545052 and attempt < max_retries - 1:
                    time.sleep(10)
                    continue
                raise Exception(f"API Error {error_code}: {error_msg}")
            return True, f"✅ Đã thêm {len(user_ids)} người vào nhóm {thread_id}"
        except Exception as e:
            error_msg = f"❌ Lỗi khi thêm người vào nhóm {thread_id}: {str(e)}"
            print_color(error_msg, "error")
            if attempt == max_retries - 1:
                return False, error_msg
            time.sleep(10)
    return False, f"❌ Failed after {max_retries} attempts"

def create_new_group(dataFB, participant_ids, group_title):
    try:
        if not isinstance(participant_ids, list):
            raise ValueError("participant_ids should be an array.")
        if len(participant_ids) < 2:
            raise ValueError("participant_ids should have at least 2 IDs.")
        pids = [{"fbid": str(pid)} for pid in participant_ids]
        pids.append({"fbid": str(dataFB["FacebookID"])})
        form = {
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "MessengerGroupCreateMutation",
            "av": str(dataFB["FacebookID"]),
            "doc_id": "577041672419534",
            "variables": json.dumps({
                "input": {
                    "entry_point": "jewel_new_group",
                    "actor_id": str(dataFB["FacebookID"]),
                    "participants": pids,
                    "client_mutation_id": str(random.randint(1, 1024)),
                    "thread_settings": {
                        "name": group_title,
                        "joinable_mode": "PRIVATE",
                        "thread_image_fbid": None
                    }
                }
            }, separators=(",", ":")),
            "fb_dtsg": dataFB["fb_dtsg"],
            "jazoest": dataFB["jazoest"],
            "__user": str(dataFB["FacebookID"]),
            "__a": "1",
            "__req": "1",
            "__rev": dataFB.get("clientRevision", "1015919737")
        }
        headers = get_headers("https://www.facebook.com/api/graphql/", customHeader={
            "Content-Type": "application/x-www-form-urlencoded"
        })
        response = requests.post(
            "https://www.facebook.com/api/graphql/",
            data=form,
            headers=headers,
            cookies=parse_cookie_string(dataFB["cookieFacebook"]),
            timeout=10
        )
        if response.status_code != 200:
            raise Exception(f"HTTP Error {response.status_code}")
        content = response.text.replace('for (;;);', '')
        data = json.loads(content)
        if "errors" in data:
            raise Exception(f"API Error: {data['errors'][0]['message']}")
        thread_id = data["data"]["messenger_group_thread_create"]["thread"]["thread_key"]["thread_fbid"]
        return True, thread_id, f"✅ Đã tạo nhóm: {group_title} (ID: {thread_id})"
    except Exception as e:
        return False, None, f"❌ Lỗi khi tạo nhóm {group_title}: {str(e)}"

def change_nickname(nickname, thread_id, participant_id, dataFB):
    try:
        form = {
            "nickname": nickname,
            "participant_id": str(participant_id),
            "thread_or_other_fbid": str(thread_id),
            "source": "thread_settings",
            "dpr": "1",
            "fb_dtsg": dataFB["fb_dtsg"],
            "jazoest": dataFB["jazoest"],
            "__user": str(dataFB["FacebookID"]),
            "__a": "1",
            "__req": str_base(Counter().increment(), 36),
            "__rev": dataFB.get("clientRevision", "1015919737")
        }
        headers = get_headers("https://www.facebook.com/messaging/save_thread_nickname/", customHeader={
            "Content-Type": "application/x-www-form-urlencoded"
        })
        response = requests.post(
            "https://www.facebook.com/messaging/save_thread_nickname/",
            data=form,
            headers=headers,
            cookies=parse_cookie_string(dataFB["cookieFacebook"]),
            timeout=10
        )
        if response.status_code != 200:
            raise Exception(f"HTTP Error {response.status_code}")
        content = response.text.replace('for (;;);', '')
        data = json.loads(content)
        if "error" in data:
            error_code = data.get("error")
            if error_code == 1545014:
                raise Exception("Trying to change nickname of user who isn't in thread")
            if error_code == 1357031:
                raise Exception("Thread doesn't exist or has no messages")
            raise Exception(f"API Error: {data.get('errorDescription', 'Unknown error')}")
        return True, f"✅ Đã đổi biệt danh cho user {participant_id} thành {nickname} trong box {thread_id}"
    except Exception as e:
        return False, f"❌ Lỗi khi đổi biệt danh cho user {participant_id}: {str(e)}"

def get_thread_info_graphql(thread_id, dataFB):
    try:
        form = {
            "queries": json.dumps({
                "o0": {
                    "doc_id": "3449967031715030",
                    "query_params": {
                        "id": str(thread_id),
                        "message_limit": 0,
                        "load_messages": False,
                        "load_read_receipts": False,
                        "before": None
                    }
                }
            }, separators=(",", ":")),
            "batch_name": "MessengerGraphQLThreadFetcher",
            "fb_dtsg": dataFB["fb_dtsg"],
            "jazoest": dataFB["jazoest"],
            "__user": str(dataFB["FacebookID"]),
            "__a": "1",
            "__req": str_base(Counter().increment(), 36),
            "__rev": dataFB.get("clientRevision", "1015919737")
        }
        headers = get_headers("https://www.facebook.com/api/graphqlbatch/", customHeader={
            "Content-Type": "application/x-www-form-urlencoded"
        })
        response = requests.post(
            "https://www.facebook.com/api/graphqlbatch/",
            data=form,
            headers=headers,
            cookies=parse_cookie_string(dataFB["cookieFacebook"]),
            timeout=10
        )
        if response.status_code != 200:
            raise Exception(f"HTTP Error {response.status_code}")
        content = response.text.replace('for (;;);', '')
        response_parts = content.split("\n")
        if not response_parts or not response_parts[0].strip():
            raise Exception("Empty response from API")
        data = json.loads(response_parts[0])
        if "error" in data:
            raise Exception(f"API Error: {data.get('errorDescription', 'Unknown error')}")
        if data.get("error_results", 0) != 0:
            raise Exception("Error results in response")
        message_thread = data["o0"]["data"]["message_thread"]
        thread_id = (message_thread["thread_key"]["thread_fbid"] 
                     if message_thread["thread_key"].get("thread_fbid") 
                     else message_thread["thread_key"]["other_user_id"])
        participant_ids = [edge["node"]["messaging_actor"]["id"] 
                          for edge in message_thread["all_participants"]["edges"]]
        return True, participant_ids, f"✅ Lấy được {len(participant_ids)} thành viên trong box {thread_id}"
    except Exception as e:
        return False, [], f"❌ Lỗi khi lấy thông tin box {thread_id}: {str(e)}"

def get_friends_list(dataFB):
    try:
        form = {
            "viewer": str(dataFB["FacebookID"]),
            "fb_dtsg": dataFB["fb_dtsg"],
            "jazoest": dataFB["jazoest"],
            "__user": str(dataFB["FacebookID"]),
            "__a": "1",
            "__req": "1",
            "__rev": dataFB.get("clientRevision", "1015919737")
        }
        headers = get_headers("https://www.facebook.com/chat/user_info_all", customHeader={
            "Content-Type": "application/x-www-form-urlencoded"
        })
        response = requests.post(
            "https://www.facebook.com/chat/user_info_all",
            data=form,
            headers=headers,
            cookies=parse_cookie_string(dataFB["cookieFacebook"]),
            timeout=10
        )
        if response.status_code != 200:
            raise Exception(f"HTTP Error {response.status_code}")
        content = response.text.replace('for (;;);', '')
        data = json.loads(content)
        if not data or "payload" not in data:
            raise Exception("getFriendsList returned empty object or missing payload.")
        if "error" in data:
            raise Exception(f"API Error: {data.get('errorDescription', 'Unknown error')}")
        friends = data["payload"]
        friend_ids = [str(user_id) for user_id in friends.keys()]
        return True, friend_ids, f"✅ Lấy được {len(friend_ids)} bạn bè."
    except Exception as e:
        return False, [], f"❌ Lỗi khi lấy danh sách bạn bè: {str(e)}"

def check_live(cookie):
    try:
        if 'c_user=' not in cookie:
            return {"status": "failed", "msg": "Cookie không chứa user_id"}
        user_id = cookie.split('c_user=')[1].split(';')[0]
        headers = {
            'authority': 'm.facebook.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'vi-VN,vi;q=0.9',
            'cache-control': 'max-age=0',
            'cookie': cookie,
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'
        }
        profile_response = requests.get(f'https://m.facebook.com/profile.php?id={user_id}', headers=headers, timeout=30)
        name = profile_response.text.split('<title>')[1].split('<')[0].strip()
        return {"status": "success", "name": name, "user_id": user_id, "msg": "successful"}
    except Exception as e:
        return {"status": "failed", "msg": f"Lỗi: {str(e)}"}

def read_cookies_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            cookies = [line.strip() for line in f if line.strip()]
        if not cookies:
            raise ValueError("File cookie rỗng hoặc không có cookie hợp lệ.")
        return cookies
    except FileNotFoundError:
        raise FileNotFoundError(f"File không tồn tại: {file_path}")
    except Exception as e:
        raise Exception(f"Lỗi khi đọc file cookie: {str(e)}")

def parse_selection(input_str, max_index):
    try:
        numbers = [int(i.strip()) for i in input_str.split(',')]
        return [n for n in numbers if 1 <= n <= max_index]
    except:
        print_color("❌ Định dạng không hợp lệ!", "error")
        return []

# ====================== HÀM NHÂY TAG - FULL CODE CHO BỐ ======================
def start_spam_with_tag_full(cookie, account_name, user_id, thread_ids, thread_names, delay, message_lines, replace_text, tag_ids, tag_names, dataFB):
    """
    NHÂY TAG ĐẦY ĐỦ - MỘT LẦN GỬICHO TOÀN BỘ TAG
    """
    try:
        print_color(f"\n🚀 [{account_name}] Khởi động nhây tag đầy đủ", "success")
        fbt = fbTools(dataFB)
        sender = MessageSender(fbt, dataFB, ngquanghuyakadzi(cookie))
        sender.get_last_seq_id()
        
        if not sender.connect_mqtt():
            print_color(f"⚠️ [{account_name}] Không kết nối được MQTT", "warning")
            return
        
        print_color(f"✅ [{account_name}] Kết nối MQTT thành công", "success")
        message_index = 0
        
        while True:
            try:
                for thread_id, thread_name in zip(thread_ids, thread_names):
                    # Lấy nội dung tin nhắn
                    content = message_lines[message_index]
                    if "{name}" in content:
                        content = content.replace("{name}", replace_text)
                    
                    # Tạo mentions data cho TẤT CẢ tag trong một lần gửi
                    mentions_data = []
                    full_message = content
                    
                    if tag_ids and tag_names:
                        for tag_id, tag_name in zip(tag_ids, tag_names):
                            mentions_data.append({
                                "id": tag_id,
                                "tag": tag_name
                            })
                        # Thêm tất cả tag vào cuối tin nhắn
                        full_message = content + " " + " ".join([f"@{name}" for name in tag_names])
                    
                    # GỬI TYPING
                    sender.sendTypingIndicatorMqtt(True, thread_id)
                    time.sleep(2)
                    
                    # GỬI TIN NHẮN CÓ TAG
                    if sender.mqtt and mentions_data:
                        success = sender.send_message_with_mentions(thread_id, full_message, mentions_data)
                    else:
                        success = sender.send_message(full_message, thread_id)
                    
                    # TẮT TYPING
                    sender.sendTypingIndicatorMqtt(False, thread_id)
                    
                    # In log
                    status_text = "✅ Thành Công" if success else "❌ Thất Bại"
                    print_color(f"  📦 Box: {thread_name:<30} | 🏷️ Tag: {len(tag_names):>3} người | {status_text}", "success" if success else "error")
                    
                    # Chuyển sang message tiếp theo
                    message_index = (message_index + 1) % len(message_lines)
                    time.sleep(delay)
                    
            except KeyboardInterrupt:
                print_color(f"\n🛑 [{account_name}] Dừng nhây tag", "warning")
                break
            except Exception as e:
                print_color(f"❌ [{account_name}] Lỗi trong vòng lặp: {e}", "error")
                time.sleep(2)
    
    except Exception as e:
        print_color(f"❌ [{account_name}] Lỗi tài khoản: {e}", "error")
    
    finally:
        if 'sender' in locals():
            sender.stop()

def send_messages_with_cookie(cookies, thread_ids, message_files, delay, option=0, file_path=None, contact_uid=None, name_file=None, nickname=None):
    global cookie_attempts, active_threads
    
    for cookie in cookies:
        cookie_hash = hashlib.md5(cookie.encode()).hexdigest()
        if cookie_attempts[cookie_hash]['permanent_ban']:
            print_color(f"Cookie {cookie_hash[:10]} Đã Bị Ngưng Hoạt Động Vĩnh Viễn", "error")
            continue
        
        current_time = time.time()
        if current_time < cookie_attempts[cookie_hash]['banned_until']:
            remaining = cookie_attempts[cookie_hash]['banned_until'] - current_time
            print_color(f"Cookie {cookie_hash[:10]} Bị Tạm Khóa, Còn {remaining/3600:.1f} Giờ", "warning")
            continue
        
        try:
            fb = ngquanghuyakadzi(cookie)
            dataFB = {
                "FacebookID": fb.user_id,
                "fb_dtsg": fb.fb_dtsg,
                "clientRevision": fb.rev,
                "jazoest": fb.jazoest,
                "cookieFacebook": cookie
            }
            
            sender = MessageSender(fbTools(dataFB), dataFB, fb)
            
            if option not in [4, 10]:
                sender.get_last_seq_id()
                if not sender.connect_mqtt():
                    handle_failed_connection(cookie_hash)
                    continue
            
            for thread_id in thread_ids:
                print_color(f"Bắt Đầu Xử Lý Cho Box: {thread_id} với Cookie: {cookie_hash[:10]}", "info")
                active_threads[f"{cookie_hash}_{thread_id}"] = sender
                
                try:
                    if option == 4:  # Nhay tên nhóm
                        if not name_file:
                            print_color("[!] Chưa cung cấp file chứa tên nhóm (nhay.txt)", "error")
                            break
                        with open(name_file, 'r', encoding='utf-8') as f:
                            group_names = [line.strip() for line in f if line.strip()]
                        if not group_names:
                            print_color("[!] File nhay.txt không có nội dung!", "error")
                            break
                        while True:
                            try:
                                for group_name in group_names:
                                    success, log = tenbox(group_name, thread_id, dataFB)
                                    print_color(log, "info" if success else "error")
                                    time.sleep(delay)
                            except Exception as e:
                                print_color(f"❌ Lỗi trong nhay tên: {e}", "error")
                                time.sleep(2)
                    
                    elif option == 7:  # Treo poll
                        if not name_file:
                            print_color("[!] Chưa cung cấp file chứa tiêu đề poll (nhay.txt)", "error")
                            break
                        with open(name_file, 'r', encoding='utf-8') as f:
                            poll_titles = [line.strip() for line in f if line.strip()]
                        if not poll_titles:
                            print_color("[!] File nhay.txt không có nội dung!", "error")
                            break
                        while True:
                            try:
                                single_title = random.choice(poll_titles)
                                selected_options = random.sample(poll_titles, min(4, len(poll_titles)))
                                success = sender.createPollMqtt(single_title, selected_options, thread_id)
                                print_color(f"[{'✓' if success else '❌'}] Poll: {single_title}", "success" if success else "error")
                                time.sleep(delay)
                            except Exception as e:
                                print_color(f"❌ Lỗi trong poll: {e}", "error")
                                time.sleep(2)
                    
                    elif option == 8:  # Fake typing
                        if not name_file:
                            print_color("[!] Chưa cung cấp file chứa nội dung tin nhắn (nhay.txt)", "error")
                            break
                        with open(name_file, 'r', encoding='utf-8') as f:
                            messages = [line.strip() for line in f if line.strip()]
                        if not messages:
                            print_color("[!] File nhay.txt không có nội dung!", "error")
                            break
                        while True:
                            try:
                                for message in messages:
                                    if not message:
                                        continue
                                    sender.sendTypingIndicatorMqtt(True, thread_id)
                                    time.sleep(random.uniform(1, 3))
                                    success = sender.send_message(message, thread_id)
                                    sender.sendTypingIndicatorMqtt(False, thread_id)
                                    print_color(f"[{'✓' if success else '❌'}] {message[:50]}", "success" if success else "error")
                                    time.sleep(delay)
                            except Exception as e:
                                print_color(f"❌ Lỗi trong fake typing: {e}", "error")
                                time.sleep(2)
                    
                    elif option == 9:  # Đổi theme
                        themes = sender.THEMES
                        theme_index = 0
                        while True:
                            try:
                                theme = themes[theme_index % len(themes)]
                                success = sender.set_theme(theme["id"], thread_id)
                                theme_index += 1
                                time.sleep(delay)
                            except Exception as e:
                                print_color(f"❌ Lỗi trong theme: {e}", "error")
                                time.sleep(2)
                    
                    elif option == 10:  # Đổi biệt danh
                        while True:
                            try:
                                nickname = input("[+] Nhập biệt danh (Enter = dừng):\n> ").strip()
                                if not nickname:
                                    break
                                success, participant_ids, log = get_thread_info_graphql(thread_id, dataFB)
                                print_color(log, "info")
                                if not success:
                                    break
                                for participant_id in participant_ids:
                                    success, log = change_nickname(nickname, thread_id, participant_id, dataFB)
                                    print_color(log, "info" if success else "error")
                                    time.sleep(delay)
                            except Exception as e:
                                print_color(f"❌ Lỗi trong đổi biệt danh: {e}", "error")
                                time.sleep(2)
                    
                    else:  # Options 1, 2, 3, 5
                        while True:
                            try:
                                content = ""
                                if message_files:
                                    selected = random.choice(message_files)
                                    with open(selected, 'r', encoding='utf-8') as f:
                                        content = f.read().strip()
                                
                                if option == 2:
                                    uid_to_share = contact_uid or fb.user_id
                                    sender.share_contact(content, uid_to_share, thread_id)
                                elif option == 3:
                                    uid_to_share = contact_uid or fb.user_id
                                    share_url = f"https://www.facebook.com/{uid_to_share}"
                                    sender.share_link(content, share_url, thread_id)
                                elif option == 5:
                                    if not file_path:
                                        break
                                    success = sender.send_message_with_attachment(content, thread_id, file_path)
                                else:  # Option 1
                                    sender.send_message(content, thread_id)
                                
                                time.sleep(delay)
                            except Exception as e:
                                print_color(f"❌ Lỗi trong vòng lặp gửi: {e}", "error")
                                time.sleep(2)
                
                except KeyboardInterrupt:
                    print_color(f"\nDừng Xử Lý Cho Box: {thread_id}", "warning")
                    break
                
                finally:
                    if option not in [4, 10]:
                        sender.stop()
                    if f"{cookie_hash}_{thread_id}" in active_threads:
                        del active_threads[f"{cookie_hash}_{thread_id}"]
        
        except Exception as e:
            print_color(f"Lỗi Trong Luồng Xử Lý Với Cookie {cookie_hash[:10]}: {e}", "error")
            handle_failed_connection(cookie_hash)
            continue
    
    return True

# ====================== MENU MAIN ======================
def menu_main():
    """Menu chính trang trí"""
    clr()
    print_banner()
    print_header("⚡ TOOL WAR MESSENGER ĐA CHỨC NĂNG ĐÚ META ⚡","blue")
    
    print_section("📌 CHỨC NĂNG GỬI TIN NHẮN", "magenta")
    print_option("1", "Treo Bình Thường", "Gửi tin nhắn văn bản")
    print_option("2", "Treo Danh Bạ", "Share contact (name card)")
    print_option("3", "Treo Share Link", "Share link từ UID")
    print_option("5", "Treo Ảnh/Video", "Gửi từ URL hoặc file")
    print_option("7", "Treo Poll", "Tạo poll/bình chọn")
    print_option("11", "Nhây Tag Đầy Đủ", "NHÂY TAG MỘT LẦN GỬI")
    print_option("8", "Nhây Combo", "Fake typing + Tag thật")
    print_section("🎭 CHỨC NĂNG NHÓM", "magenta")
    print_option("4", "Nhây Tên Nhóm", "Đổi tên nhóm liên tục")
    print_option("6", "Reg Box Messenger", "Tạo nhóm mới")
    print_option("10", "Đổi Biệt Danh", "Đặt tên cho all thành viên")
    print_option("9", "Nhây Đổi Theme", "Thay đổi màu sắc chat")
    
    print_line("═", 70, "magenta")
    option = input(gradient_text("┌─ Chọn chế độ (1-11): ", [(0,255,0), (0,0,255)])).strip()
    return option

def main_full():
    """Main function đầy đủ"""
    option = menu_main()
    
    if not option.isdigit() or int(option) not in range(1, 12):
        print_error_box("Chế độ không hợp lệ!")
        return
    
    option = int(option)
    
    # Chọn cookie
    cookie_file = input(gradient_text("[+] Nhập đường dẫn file cookie: ", [(0,255,0), (0,0,255)])).strip()
    if not os.path.isfile(cookie_file):
        print_error_box(f"File không tồn tại: {cookie_file}")
        return
    
    try:
        cookies = read_cookies_from_file(cookie_file)
        print_color(f"✅ Đã tải {len(cookies)} cookie từ file", "success")
    except Exception as e:
        print_error_box(f"Lỗi đọc file: {e}")
        return
    
    # Option 6: Tạo nhóm
    if option == 6:
        num_groups = int(input(gradient_text("[+] Số lượng nhóm: ", [(0,255,0), (0,0,255)])).strip())
        base_group_name = input(gradient_text("[+] Tên cơ bản: ", [(0,255,0), (0,0,255)])).strip()
        user_ids_input = input(gradient_text("[+] ID thành viên (cách nhau bởi ,): ", [(0,255,0), (0,0,255)])).strip()
        user_ids = [uid.strip() for uid in user_ids_input.split(",") if uid.strip()]
        
        if len(user_ids) < 2:
            print_error_box("Cần ít nhất 2 ID để tạo nhóm!")
            return
        
        print_color(f"Sẽ tạo {num_groups} nhóm với {len(user_ids)} thành viên", "info")
        
        for cookie in cookies:
            try:
                fb = ngquanghuyakadzi(cookie)
                dataFB = {
                    "FacebookID": fb.user_id,
                    "fb_dtsg": fb.fb_dtsg,
                    "clientRevision": fb.rev,
                    "jazoest": fb.jazoest,
                    "cookieFacebook": cookie
                }
                
                for i in range(num_groups):
                    group_title = f"{base_group_name} {i+1}"
                    success, thread_id, log = create_new_group(dataFB, user_ids, group_title)
                    print_color(log, "success" if success else "error")
                    time.sleep(2)
            except Exception as e:
                print_color(f"Lỗi: {e}", "error")
                continue
        return
    
    # Chọn box
    num_threads = int(input(gradient_text("[+] Số lượng box: ", [(0,255,0), (0,0,255)])).strip())
    thread_ids = []
    for i in range(num_threads):
        tid = input(f"[+] Box thứ {i+1}: ").strip()
        if tid:
            thread_ids.append(tid)
    
    if not thread_ids:
        print_error_box("Chưa chọn box nào!")
        return
    
    print_color(f"✅ Đã chọn {len(thread_ids)} box", "success")
    
    # Nhập delay
    delay = float(input(gradient_text("[+] Delay (giây): ", [(0,255,0), (0,0,255)])).strip())
    
    # Cấu hình theo option
    message_files = []
    file_url = None
    contact_uid = None
    name_file = None
    tag_ids = []
    tag_names = []
    
    if option == 1:
        message_files = [input(gradient_text("[+] File tin nhắn: ", [(0,255,0), (0,0,255)])).strip()]

    elif option == 2:
        contact_uid = input(gradient_text("[+] UID share (Enter = bạn): ", [(0,255,0), (0,0,255)])).strip()
        message_files = [input(gradient_text("[+] File tin nhắn: ", [(0,255,0), (0,0,255)])).strip()]
    
    elif option == 3:
        contact_uid = input(gradient_text("[+] UID link (Enter = bạn): ", [(0,255,0), (0,0,255)])).strip()
        message_files = [input(gradient_text("[+] File tin nhắn: ", [(0,255,0), (0,0,255)])).strip()]
    
    elif option == 4:
        name_file = input(gradient_text("[+] File tên nhóm: ", [(0,255,0), (0,0,255)])).strip()
    
    elif option == 5:
        file_url = input(gradient_text("[+] URL ảnh/video: ", [(0,255,0), (0,0,255)])).strip()
        file_txt = input(gradient_text("[+] File tin nhắn (tuỳ chọn): ", [(0,255,0), (0,0,255)])).strip()
        message_files = [file_txt] if file_txt else []
    
    elif option == 7:
        name_file = input(gradient_text("[+] File poll title: ", [(0,255,0), (0,0,255)])).strip()
    
    elif option == 8:
        name_file = input(gradient_text("[+] File tin nhắn: ", [(0,255,0), (0,0,255)])).strip()
    
    elif option == 11:  # NHÂY TAG ĐẦY ĐỦ
        print_header("🏷️ NHÂY TAG ĐẦY ĐỦ - MỘT LẦN GỬI TẤT CẢ", "cyan")
        
        processes = []
        
        for idx, cookie in enumerate(cookies):
            print_color(f"\n📝 Xử lý cookie {idx+1}/{len(cookies)}", "info")
            
            cl = check_live(cookie)
            if cl["status"] != "success":
                print_color(f"❌ Cookie {idx+1} không hợp lệ: {cl['msg']}", "error")
                continue
            
            account_name = cl['name']
            user_id = cl['user_id']
            print_color(f"✅ Facebook: {account_name} (ID: {user_id})", "success")
            
            fb = ngquanghuyakadzi(cookie)
            dataFB = {
                "FacebookID": fb.user_id,
                "fb_dtsg": fb.fb_dtsg,
                "clientRevision": fb.rev,
                "jazoest": fb.jazoest,
                "cookieFacebook": cookie
            }
            
            messenger = Messenger(cookie, dataFB)
            
            # Lấy danh sách box
            print_color("🔄 Lấy danh sách box...", "info")
            result = messenger.get_thread_list(limit=100)
            
            if "error" in result:
                print_color(f"❌ {result['error']}", "error")
                continue
            
            threads = result['threads']
            if not threads:
                print_color("❌ Không có box nào", "error")
                continue
            
            # Hiển thị box
            table = Table(title=f"📦 BOX - {len(threads)} CÁI", show_header=True, header_style="bold magenta", box=box.ROUNDED)
            table.add_column("STT", style="cyan")
            table.add_column("Tên", style="green")
            table.add_column("ID", style="yellow")
            for idx_box, thread in enumerate(threads, 1):
                display_name = f"{thread['thread_name'][:40]}{'...' if len(thread['thread_name']) > 40 else ''}"
                table.add_row(str(idx_box), display_name, thread['thread_id'])
            console.print(table)
            
            raw = input(gradient_text("🎯 Chọn box (1,2,3 hoặc all): ", [(0,255,0), (0,0,255)])).strip()
            
            if raw.lower() == 'all':
                selected = list(range(1, len(threads) + 1))
            else:
                selected = parse_selection(raw, len(threads))
            
            if not selected:
                print_color("❌ Chưa chọn box nào", "error")
                continue
            
            selected_ids = [threads[i-1]['thread_id'] for i in selected]
            selected_names = [threads[i-1]['thread_name'] for i in selected]
            
            print_color(f"✅ Đã chọn {len(selected_ids)} box", "success")
            
            # Lấy danh sách thành viên
            print_color("👥 Lấy danh sách thành viên...", "info")
            members = []
            for tid in selected_ids:
                result = messenger.get_group_members(tid)
                if result.get("success"):
                    members.extend(result["members"])
            
            if not members:
                print_color("❌ Không có thành viên nào", "error")
                continue
            
            # Hiển thị thành viên
            member_table = Table(title=f"👥 THÀNH VIÊN - {len(members)} NGƯỜI", show_header=True, header_style="bold blue", box=box.ROUNDED)
            member_table.add_column("STT", style="cyan")
            member_table.add_column("Tên", style="green")
            member_table.add_column("ID", style="yellow")
            for idx_mem, member in enumerate(members, 1):
                member_name = f"{member['name'][:40]}{'...' if len(member['name']) > 40 else ''}"
                member_table.add_row(str(idx_mem), member_name, member['id'])
            console.print(member_table)
            
            raw_tags = input(gradient_text("🏷️ Chọn người tag (1,2,3 hoặc all): ", [(0,255,0), (0,0,255)])).strip()
            
            if raw_tags.lower() == 'all':
                selected_tags = list(range(1, len(members) + 1))
            else:
                selected_tags = parse_selection(raw_tags, len(members))
            
            if not selected_tags:
                print_color("❌ Không chọn ai để tag", "error")
                continue
            
            tag_ids = [members[i-1]['id'] for i in selected_tags]
            tag_names = [members[i-1]['name'] for i in selected_tags]
            print_color(f"✅ Đã chọn {len(tag_ids)} người để tag", "success")
            
            # File tin nhắn
            file_txt = input(gradient_text("[+] File tin nhắn: ", [(0,255,0), (0,0,255)])).strip()
            try:
                with open(file_txt, 'r', encoding='utf-8') as f:
                    message_lines = [line.strip() for line in f if line.strip()]
                print_color(f"✅ Tải {len(message_lines)} dòng", "success")
            except Exception as e:
                print_color(f"❌ Lỗi: {e}", "error")
                continue
            
            replace_text = input(gradient_text("[+] Thay thế {name} (Enter = không): ", [(0,255,0), (0,0,255)])).strip()
            
            # Khởi động process
            p = multiprocessing.Process(
                target=start_spam_with_tag_full,
                args=(cookie, account_name, user_id, selected_ids, selected_names, delay, message_lines, replace_text, tag_ids, tag_names, dataFB)
            )
            processes.append(p)
            p.start()
            time.sleep(2)
        
        if not processes:
            print_error_box("Không có cookie nào hoạt động!")
            return
        
        print_header(f"🚀 KHỞI ĐỘNG {len(processes)} COOKIE NHÂY TAG", "success")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print_color("\n🛑 Dừng tất cả tiến trình...", "error")
            for p in processes:
                p.terminate()
            time.sleep(2)
            print_color("✅ Đã dừng", "success")
        
        return
    
    # Xác nhận
    print_header(f"🚀 KHỞI ĐỘNG CHẾ ĐỘ {option}", "success")
    
    send_messages_with_cookie(
        cookies,
        thread_ids,
        message_files,
        delay,
        option=option,
        file_path=file_url if option == 5 else None,
        contact_uid=contact_uid if option in [2,3] else None,
        name_file=name_file if option in [4,7,8] else None
    )
    
    print_line("═", 70, "magenta")
    print_color("✅ Hoàn tất!", "success")

def print_error_box(text):
    """In box lỗi"""
    print_color(f"\n❌ {text}", "error")
    print_line("─", 70, "error")

if __name__ == "__main__":
    try:
        main_full()
    except KeyboardInterrupt:
        print_error_box("Dừng chương trình!")
    except Exception as e:
        print_error_box(f"Lỗi: {str(e)}")
       