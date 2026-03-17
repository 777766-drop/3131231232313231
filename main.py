#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ECUST Run Mobile v5.1 - System Points
"""

import os, sys, json, base64, random, math, time, hashlib, platform
from datetime import datetime, timedelta
from threading import Thread

if hasattr(sys, 'getandroidapilevel'):
    from android.permissions import request_permissions, Permission
    from android.storage import app_storage_path
    request_permissions([Permission.INTERNET])
    STORAGE = app_storage_path()
else:
    STORAGE = os.path.dirname(os.path.abspath(__file__))

try:
    import requests
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.label import Label
    from kivy.uix.button import Button
    from kivy.uix.textinput import TextInput
    from kivy.uix.scrollview import ScrollView
    from kivy.clock import Clock
    from kivy.core.window import Window
    requests.packages.urllib3.disable_warnings()
except Exception as e:
    print(f"Import error: {e}")
    raise

CONFIG = {
    "aes_key": b'A7fK92LmXyQw8vRp',
    "base_url": "https://run.ecust.edu.cn",
    "amap_key": ""
}
SECURE_FILE = os.path.join(STORAGE, '.ecust_m51')

def aes_encrypt(data):
    cipher = AES.new(CONFIG["aes_key"], AES.MODE_ECB)
    return base64.b64encode(cipher.encrypt(pad(data.encode(), AES.block_size))).decode()

class Auth:
    def __init__(self):
        self.cfg = self._load()
        self.device_id = hashlib.sha256(f"{platform.node()}{platform.machine()}".encode()).hexdigest()[:16].upper()
    
    def _load(self):
        try:
            with open(SECURE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _save(self):
        with open(SECURE_FILE, 'w') as f:
            json.dump(self.cfg, f)
    
    def get_code(self):
        h = hashlib.sha256(f"{self.device_id}ECUST_V51".encode()).hexdigest()
        return f"ECUST-{h[:4].upper()}-{h[4:8].upper()}"
    
    def is_activated(self):
        return self.cfg.get("activated") == True
    
    def activate(self, code):
        if code == self.get_code():
            self.cfg["activated"] = True
            self._save()
            return True
        admin_h = hashlib.sha256(b"ECUST_ADMIN_MASTER_2025").hexdigest()[:8]
        if code == f"ADMIN-{admin_h.upper()}":
            self.cfg["activated"] = True
            self.cfg["admin"] = True
            self._save()
            return True
        return False

class Session:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-G9750) AppleWebKit/537.36"
        })
        self.student_id = None
        self.name = None
        self.system_points = []
    
    def login(self, phone, pwd):
        try:
            r = self.s.post(f"{CONFIG['base_url']}/xcxapi/userLogin/",
                          json={"iphone": phone, "password": pwd}, timeout=10, verify=False)
            if "<" in r.text[:20]:
                return False, "HTML错误"
            d = r.json()
            if d.get("code") == 1:
                self.student_id = d["data"]["id"]
                self.name = d["data"]["name"]
                if d["data"].get("session_keys"):
                    self.s.headers["X-Session-ID"] = d["data"]["session_keys"]
                return True, self.name
            return False, d.get("message")
        except Exception as e:
            return False, str(e)
    
    def create_line(self):
        try:
            r = self.s.post(f"{CONFIG['base_url']}/xcxapi/createLine/",
                json={"a": aes_encrypt(json.dumps({"student_id": self.student_id, "pass_point": []}))},
                timeout=10, verify=False)
            data = r.json()
            if data.get("code") == 1:
                rid = data["data"]["record_id"]
                points = data["data"].get("pass_point", [])
                if not points:
                    anchors = [
                        {"name": "桥东", "lat": 30.830424, "lng": 121.501712},
                        {"name": "38号楼", "lat": 30.827536, "lng": 121.503933},
                        {"name": "南大门", "lat": 30.828600, "lng": 121.505815}
                    ]
                    points = random.sample(anchors, 3)
                self.system_points = points
                return rid, points
            return None, None
        except Exception as e:
            return None, str(e)

class Trajectory:
    def __init__(self, sys_points):
        self.sys = sys_points
        self.all = []
    
    def generate(self):
        pts = []
        random.shuffle(self.sys)
        start = datetime.now()
        
        for i, base in enumerate(self.sys):
            # 添加途经点
            if i > 0:
                mid_lat = (pts[-1]["lat"] + base["lat"])/2 + random.uniform(-0.0002, 0.0002)
                mid_lng = (pts[-1]["lng"] + base["lng"])/2 + random.uniform(-0.0002, 0.0002)
                pts.append({
                    "name": f"途经{i}",
                    "lat": round(mid_lat, 6),
                    "lng": round(mid_lng, 6),
                    "timestamp": int((start + timedelta(minutes=len(pts)*2)).timestamp()),
                    "accuracy": random.randint(10, 25)
                })
            
            # 系统点
            lat = base["lat"] + random.uniform(-0.00005, 0.00005)
            lng = base["lng"] + random.uniform(-0.00005, 0.00005)
            pts.append({
                "name": base.get("name", f"P{i+1}"),
                "lat": round(lat, 6),
                "lng": round(lng, 6),
                "timestamp": int((start + timedelta(minutes=len(pts)*3)).timestamp()),
                "accuracy": random.randint(8, 20)
            })
        
        self.all = pts
        return pts
    
    def calc_dist(self):
        R = 6371000
        total = 0
        for i in range(len(self.all)-1):
            la1, lo1 = math.radians(self.all[i]["lat"]), math.radians(self.all[i]["lng"])
            la2, lo2 = math.radians(self.all[i+1]["lat"]), math.radians(self.all[i+1]["lng"])
            a = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
            total += 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return round(total * 1.2, 2)
    
    def get_map(self):
        if not CONFIG["amap_key"] or not self.all:
            return ""
        try:
            path = ";".join([f"{p['lng']},{p['lat']}" for p in self.all])
            c_lat = sum(p["lat"] for p in self.all)/len(self.all)
            c_lng = sum(p["lng"] for p in self.all)/len(self.all)
            url = f"https://restapi.amap.com/v3/staticmap?key={CONFIG['amap_key']}&size=400*400&zoom=16&center={c_lng},{c_lat}&paths=5,0xFF5722,1,,:{path}"
            r = requests.get(url, timeout=15)
            return base64.b64encode(r.content).decode() if r.status_code == 200 else ""
        except:
            return ""

class RunThread(Thread):
    def __init__(self, session, ui_cb):
        super().__init__(daemon=True)
        self.session = session
        self.cb = ui_cb
    
    def log(self, msg):
        Clock.schedule_once(lambda dt: self.cb(msg), 0)
    
    def run(self):
        rid, sys_pts = self.session.create_line()
        if not rid:
            self.log("❌ 创建记录失败")
            return
        
        self.log(f"✅ 记录: {rid}")
        self.log(f"📌 系统点: {len(sys_pts)}个")
        
        traj = Trajectory(sys_pts)
        pts = traj.generate()
        dist = traj.calc_dist()
        
        while dist < 2000:
            pts = traj.generate()
            dist = traj.calc_dist()
        
        self.log(f"🗺️ 轨迹: {len(pts)}点, {dist:.0f}m")
        
        img = traj.get_map()
        if img:
            self.log(f"🖼️ 地图: {len(img)//1024}KB")
        
        # 上传
        upload = {
            "record_id": rid, "student_id": self.session.student_id,
            "path_point": pts, "path_image": img,
            "start_time": pts[0]["timestamp"], "end_time": pts[-1]["timestamp"],
            "mileage": dist, "run_time": pts[-1]["timestamp"] - pts[0]["timestamp"],
            "step_count": int(dist * 0.8)
        }
        try:
            self.session.s.post(f"{CONFIG['base_url']}/xcxapi/uploadPathPointV3/",
                json={"a": aes_encrypt(json.dumps(upload))}, timeout=15, verify=False)
        except Exception as e:
            self.log(f"⚠️ 上传: {e}")
        
        # 模拟
        self.log("🏃 跑步中...")
        for i in range(5):
            self.log(f"⏳ {(i+1)*20}%")
            time.sleep(1)
        
        # 提交
        try:
            r = self.session.s.post(f"{CONFIG['base_url']}/xcxapi/updateRecordNew/",
                json={"a": aes_encrypt(json.dumps({"record_id": rid, "student_id": self.session.student_id, "verify_mode": 0, "run_type": 0}))},
                timeout=10, verify=False)
            if r.json().get("code") == 1:
                self.log(f"✅ 完成! {dist:.0f}m")
            else:
                self.log("❌ 失败")
        except Exception as e:
            self.log(f"❌ {e}")

class MainUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.auth = Auth()
        self.session = None
        
        # 日志区
        self.log_label = Label(text="ECUST Run v5.1\n系统打卡点版", size_hint_y=None, 
                              markup=True, text_size=(Window.width-20, None))
        scroll = ScrollView(size_hint=(1, 0.5))
        scroll.add_widget(self.log_label)
        self.add_widget(scroll)
        
        # 信息显示
        info_grid = GridLayout(cols=2, size_hint_y=None, height=100)
        info_grid.add_widget(Label(text=f"设备ID: {self.auth.device_id}"))
        info_grid.add_widget(Label(text=f"激活码: {self.auth.get_code()}"))
        self.add_widget(info_grid)
        
        # 输入区
        grid = GridLayout(cols=1, spacing=10, size_hint_y=0.4)
        
        self.code_input = TextInput(hint_text='激活码', multiline=False, size_hint_y=None, height=50)
        self.phone_input = TextInput(hint_text='手机号', multiline=False, input_filter='int', disabled=True)
        self.pwd_input = TextInput(hint_text='密码', multiline=False, password=True, disabled=True)
        
        grid.add_widget(self.code_input)
        grid.add_widget(self.phone_input)
        grid.add_widget(self.pwd_input)
        
        # 按钮
        btn_grid = GridLayout(cols=2, spacing=10, size_hint_y=None, height=120)
        self.btn_act = Button(text='🔐 激活', on_press=self.do_activate)
        self.btn_login = Button(text='🔑 登录', disabled=True, on_press=self.do_login)
        self.btn_run = Button(text='🏃 开始', disabled=True, on_press=self.do_run)
        
        btn_grid.add_widget(self.btn_act)
        btn_grid.add_widget(self.btn_login)
        btn_grid.add_widget(self.btn_run)
        grid.add_widget(btn_grid)
        
        self.add_widget(grid)
        
        if self.auth.is_activated():
            self.on_activated()
    
    def on_activated(self):
        self.code_input.disabled = True
        self.phone_input.disabled = False
        self.pwd_input.disabled = False
        self.btn_login.disabled = False
        self.log("✅ 已激活，请登录")
    
    def log(self, msg):
        self.log_label.text += f"\n{msg}"
    
    def do_activate(self, inst):
        code = self.code_input.text.strip()
        if self.auth.activate(code):
            self.log("✅ 激活成功")
            self.on_activated()
        else:
            self.log("❌ 无效")
    
    def do_login(self, inst):
        self.session = Session()
        ok, msg = self.session.login(self.phone_input.text, self.pwd_input.text)
        if ok:
            self.log(f"✅ 欢迎 {msg}")
            self.btn_run.disabled = False
        else:
            self.log(f"❌ {msg}")
    
    def do_run(self, inst):
        self.btn_run.disabled = True
        self.log("🚀 启动...")
        RunThread(self.session, self.log).start()
        Clock.schedule_once(lambda dt: setattr(self.btn_run, 'disabled', False), 12)

class ECUSTApp(App):
    def build(self):
        Window.clearcolor = (0.1, 0.1, 0.15, 1)
        return MainUI()

if __name__ == '__main__':
    from kivy.uix.gridlayout import GridLayout
    ECUSTApp().run()
