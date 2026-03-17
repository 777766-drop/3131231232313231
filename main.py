import os
import time
import json
import base64
import hashlib
import random
import threading
import requests
import urllib3
import certifi
from datetime import datetime

# Kivy 核心组件
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform as kivy_platform

# 加密库适配
try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad, unpad
except ImportError:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== 配置中心 ====================
CONFIG = {
    'BASE_URL': 'https://run.ecust.edu.cn',
    'AES_KEY': b'A7fK92LmXyQw8vRp',  # 必须是 bytes
    'GAODE_KEY': "1b308ceddafa4645d03ada9a1448a737",
    'MASTER_SECRET': "ECUST_2025_RUNNING_SYSTEM_V2",
    'CAMPUS_BOUNDS': {
        "lat_min": 30.825, "lat_max": 30.835,
        "lng_min": 121.498, "lng_max": 121.510
    }
}

# ==================== 加密工具 ====================
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

# ==================== 主程序界面 ====================
class ECUSTRunnerApp(App):
    def build(self):
        self.title = "ECUST Run v4.5 Pura70"
        self.root = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # 1. 滚动日志区域
        self.scroll = ScrollView(size_hint=(1, 0.4))
        self.log_label = Label(
            text="[系统初始化] 准备就绪...\n", 
            size_hint_y=None, 
            height=5000,
            halign='left', 
            valign='top',
            text_size=(None, None),
            color=(0.2, 1, 0.2, 1)
        )
        self.log_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
        self.scroll.add_widget(self.log_label)
        self.root.add_widget(self.scroll)

        # 2. 输入框
        self.phone_in = TextInput(hint_text="手机号", multiline=False, size_hint_y=None, height=120, font_size='18sp')
        self.pwd_in = TextInput(hint_text="密码", password=True, multiline=False, size_hint_y=None, height=120, font_size='18sp')
        self.code_in = TextInput(hint_text="激活码 (首次运行需填)", multiline=False, size_hint_y=None, height=120, font_size='18sp')
        
        self.root.add_widget(self.phone_in)
        self.root.add_widget(self.pwd_in)
        self.root.add_widget(self.code_in)

        # 3. 操作按钮
        self.btn = Button(text="开始任务", size_hint_y=None, height=140, background_color=(0, 0.6, 0.9, 1), font_size='20sp')
        self.btn.bind(on_press=self.start_thread)
        self.root.add_widget(self.btn)

        # 获取设备ID
        self.device_id = hashlib.sha256(platform.node().encode()).hexdigest()[:16].upper()
        Clock.schedule_once(lambda dt: self.logger(f"设备ID: {self.device_id}"))
        
        return self.root

    def logger(self, msg):
        def update(dt):
            self.log_label.text += f"[{time.strftime('%H:%M:%S')}] {msg}\n"
        Clock.schedule_once(update)

    def start_thread(self, instance):
        self.btn.disabled = True
        threading.Thread(target=self.main_logic, daemon=True).start()

    def main_logic(self):
        os.environ['SSL_CERT_FILE'] = certifi.where() # 解决华为SSL问题
        cipher = AESCipher(CONFIG['AES_KEY'])
        session = requests.Session()
        session.verify = True 

        try:
            # 1. 激活码逻辑
            code = self.code_in.text.strip().replace('-', '').upper()
            expected = hashlib.sha256(f"{self.device_id}{CONFIG['MASTER_SECRET']}USER".encode()).hexdigest().upper()[:16]
            if code != expected:
                self.logger("❌ 激活码无效，请检查！")
                return

            # 2. 登录
            phone = self.phone_in.text.strip()
            pwd = self.pwd_in.text.strip()
            self.logger(f"正在登录: {phone}...")
            
            login_data = {"iphone": phone, "password": pwd}
            res = session.post(f"{CONFIG['BASE_URL']}/xcxapi/userLogin/", json=login_data, timeout=10).json()
            
            if res.get('code') != 1:
                self.logger(f"登录失败: {res.get('message')}")
                return
            
            sid = res['data']['id']
            self.logger(f"✅ 登录成功! ID: {sid}")

            # 3. 创建记录与随机点
            self.logger("正在申请随机打卡点...")
            rec = session.post(f"{CONFIG['BASE_URL']}/xcxapi/createLine/", json={"student_id": sid, "pass_point": []}).json()
            rid = rec['data']['record_id']
            
            # 模拟随机打卡点 (基于校园围栏)
            pts = []
            for i in range(3):
                lat = random.uniform(CONFIG['CAMPUS_BOUNDS']["lat_min"], CONFIG['CAMPUS_BOUNDS']["lat_max"])
                lng = random.uniform(CONFIG['CAMPUS_BOUNDS']["lng_min"], CONFIG['CAMPUS_BOUNDS']["lng_max"])
                pts.append({
                    "name": f"随机点{i+1}", 
                    "lat": round(lat, 6), 
                    "lng": round(lng, 6), 
                    "timestamp": int(time.time()),
                    "accuracy": random.randint(15, 25)
                })

            # 4. 高德轨迹生成 (Base64)
            self.logger("生成高德轨迹地图...")
            map_url = f"https://restapi.amap.com/v3/staticmap?key={CONFIG['GAODE_KEY']}&size=400*400&zoom=15&paths=5,0x24c789,1,,:{pts[0]['lng']},{pts[0]['lat']};{pts[1]['lng']},{pts[1]['lat']};{pts[2]['lng']},{pts[2]['lat']}"
            map_img = base64.b64encode(requests.get(map_url).content).decode()

            # 5. 上传轨迹
            self.logger("轨迹点同步中...")
            up_payload = {"record_id": rid, "path_point": pts, "path_image": map_img}
            session.post(f"{CONFIG['BASE_URL']}/xcxapi/uploadPathPointV3/", json={"a": cipher.encrypt(up_payload)})

            # 6. 模拟跑步等待
            wait_time = random.randint(600, 750)
            self.logger(f"⏳ 模拟跑步中，预计 {wait_time//60} 分钟...")
            # 注意：打包测试时可以将下面一行改为 time.sleep(10) 快速验证
            time.sleep(wait_time) 

            # 7. 提交结果
            self.logger("提交最终跑步数据...")
            final_data = {
                "record_id": rid, "pace": 6, "running_time": wait_time, "mileage": 2100,
                "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "pass_point": 3, "step_count": random.randint(2800, 3600)
            }
            res_fin = session.post(f"{CONFIG['BASE_URL']}/xcxapi/updateRecordNew/", json={"a": cipher.encrypt(final_data)}).json()
            
            if res_fin.get('code') == 1:
                self.logger("🎉 任务圆满完成！已同步至小程序。")
            else:
                self.logger(f"❌ 提交失败: {res_fin.get('message')}")

        except Exception as e:
            self.logger(f"⚠️ 运行错误: {str(e)}")
        finally:
            Clock.schedule_once(lambda dt: setattr(self.btn, 'disabled', False))

if __name__ == '__main__':
    ECUSTRunnerApp().run()
