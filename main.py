import sys
import os
import time
import json
import base64
import hashlib
import random
import platform
import threading
import requests
import urllib3

# Kivy UI 适配
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform as kivy_platform

# 加密适配
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========== 配置 ==========
CONFIG = {
    'BASE_URL': "https://run.ecust.edu.cn",
    'AES_KEY': b'A7fK92LmXyQw8vRp',
    'GAODE_KEY': "1b308ceddafa4645d03ada9a1448a737",
    'MASTER_SECRET': "ECUST_2025_RUNNING_SYSTEM_V2",
    'CAMPUS_BOUNDS': {
        "lat_min": 30.825, "lat_max": 30.835,
        "lng_min": 121.498, "lng_max": 121.510
    }
}

# ========== 存储路径适配 ==========
def get_save_path():
    if kivy_platform == 'android':
        from android.permissions import request_permissions, Permission
        # 使用私有目录，避免权限麻烦
        path = os.path.join(os.environ['PYTHON_HOME'], 'app_data')
    else:
        path = os.path.dirname(os.path.abspath(__file__))
    
    if not os.path.exists(path):
        os.makedirs(path)
    return path

SAVE_PATH = get_save_path()
AUTH_FILE = os.path.join(SAVE_PATH, ".ecust_auth_v2")
CRED_FILE = os.path.join(SAVE_PATH, ".ecust_cred")

# ========== 加密模块 ==========
class AESCipher:
    def __init__(self, key):
        self.key = key
    def encrypt(self, data):
        if isinstance(data, dict):
            data = json.dumps(data, separators=(',', ':'))
        iv = os.urandom(16)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        padded = pad(data.encode('utf-8'), AES.block_size)
        encrypted = cipher.encrypt(padded)
        return f"{base64.b64encode(iv).decode()}:{base64.b64encode(encrypted).decode()}"

# ========== 主程序 UI ==========
class ECUSTRunnerApp(App):
    def build(self):
        self.title = "ECUST Run v4.3-Mobile"
        self.root = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # 日志滚动显示
        self.scroll = ScrollView(size_hint=(1, 0.6))
        self.log_label = Label(text="[程序启动] 等待激活...\n", size_hint_y=None, halign='left', valign='top', color=(0, 1, 0, 1))
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        self.scroll.add_widget(self.log_label)
        self.root.add_widget(self.scroll)

        # 输入框
        self.input_box = BoxLayout(orientation='vertical', size_hint_y=None, height=350, spacing=10)
        self.phone_in = TextInput(hint_text="手机号", multiline=False, font_size=40)
        self.pwd_in = TextInput(hint_text="密码", password=True, multiline=False, font_size=40)
        self.code_in = TextInput(hint_text="如未激活,在此输入激活码", multiline=False, font_size=40)
        
        self.input_box.add_widget(self.phone_in)
        self.input_box.add_widget(self.pwd_in)
        self.input_box.add_widget(self.code_in)
        self.root.add_widget(self.input_box)

        # 按钮
        self.btn = Button(text="开始全自动任务", size_hint_y=None, height=140, background_color=(0, 0.6, 0.3, 1))
        self.btn.bind(on_press=self.start_thread)
        self.root.add_widget(self.btn)

        # 初始检查凭证
        Clock.schedule_once(self.check_auth, 1)
        return self.root

    def logger(self, msg):
        Clock.schedule_once(lambda dt: setattr(self.log_label, 'text', self.log_label.text + f"> {msg}\n"))

    def check_auth(self, dt):
        self.device_id = hashlib.sha256(platform.node().encode()).hexdigest()[:16].upper()
        self.logger(f"本机ID: {self.device_id}")
        if os.path.exists(AUTH_FILE):
            self.logger("状态: 已激活")
        else:
            self.logger("状态: 未激活，请输入激活码")

    def start_thread(self, instance):
        threading.Thread(target=self.main_logic).start()

    def main_logic(self):
        # 1. 激活检测
        if not os.path.exists(AUTH_FILE):
            code = self.code_in.text.strip().replace('-', '').upper()
            # 简化验证：此处逻辑同你 v4.3
            expected = hashlib.sha256(f"{self.device_id}{CONFIG['MASTER_SECRET']}USER".encode()).hexdigest().upper()[:16]
            if code == expected:
                with open(AUTH_FILE, 'w') as f: f.write("activated")
                self.logger("✅ 激活成功！")
            else:
                self.logger("❌ 激活码错误")
                return

        # 2. 登录
        phone = self.phone_in.text.strip()
        pwd = self.pwd_in.text.strip()
        self.logger(f"正在登录 {phone}...")
        
        session = requests.Session()
        session.verify = False
        cipher = AESCipher(CONFIG['AES_KEY'])
        
        try:
            login_resp = session.post(f"{CONFIG['BASE_URL']}/xcxapi/userLogin/", 
                                      json={"iphone": phone, "password": pwd}, timeout=10).json()
            if login_resp.get('code') != 1:
                self.logger(f"登录失败: {login_resp.get('message')}")
                return
            
            sid = login_resp['data']['id']
            self.logger(f"登录成功! StudentID: {sid}")

            # 3. 创建记录与生成打卡点
            self.logger("正在申请随机打卡点...")
            create_resp = session.post(f"{CONFIG['BASE_URL']}/xcxapi/createLine/", 
                                       json={"student_id": sid, "pass_point": []}).json()
            rid = create_resp['data']['record_id']
            
            # 生成随机轨迹点 (基于你 4.3 的随机逻辑)
            pts = []
            for i in range(3):
                lat = random.uniform(CONFIG['CAMPUS_BOUNDS']["lat_min"], CONFIG['CAMPUS_BOUNDS']["lat_max"])
                lng = random.uniform(CONFIG['CAMPUS_BOUNDS']["lng_min"], CONFIG['CAMPUS_BOUNDS']["lng_max"])
                pts.append({"name": f"点{i}", "lat": round(lat, 6), "lng": round(lng, 6), "timestamp": int(time.time()), "accuracy": 20})

            # 4. 生成静态地图
            self.logger("正在请求高德 API 生成轨迹图...")
            map_url = f"https://restapi.amap.com/v3/staticmap?key={CONFIG['GAODE_KEY']}&size=400*400&zoom=15&paths=5,0x24c789,1,,:{pts[0]['lng']},{pts[0]['lat']};{pts[1]['lng']},{pts[1]['lat']}"
            map_data = base64.b64encode(requests.get(map_url).content).decode()

            # 5. 上传轨迹
            self.logger("轨迹点上传中...")
            up_data = {"record_id": rid, "path_point": pts, "path_image": map_data}
            session.post(f"{CONFIG['BASE_URL']}/xcxapi/uploadPathPointV3/", json={"a": cipher.encrypt(up_data)})

            # 6. 模拟等待 (这里缩短为 10 秒演示，实际会根据 random 生成)
            wait = random.randint(600, 800)
            self.logger(f"模拟跑步中，倒计时 {wait} 秒，请保持 App 开启...")
            time.sleep(10) # 演示用

            # 7. 提交记录
            self.logger("正在提交最终成绩...")
            final_data = {
                "record_id": rid, "pace": 6, "running_time": wait, 
                "mileage": 2000, "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": time.strftime("%Y-%m-%d %H:%M:%S"), "pass_point": 3, "step_count": 3000
            }
            res = session.post(f"{CONFIG['BASE_URL']}/xcxapi/updateRecordNew/", json={"a": cipher.encrypt(final_data)}).json()
            
            if res.get('code') == 1:
                self.logger("🎉 跑步圆满完成！数据已同步。")
            else:
                self.logger(f"❌ 提交失败: {res.get('message')}")

        except Exception as e:
            self.logger(f"发生异常: {str(e)}")

if __name__ == '__main__':
    ECUSTRunnerApp().run()
