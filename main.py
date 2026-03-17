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
import platform
from datetime import datetime

# ==================== Kivy 界面适配 ====================
try:
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.textinput import TextInput
    from kivy.uix.button import Button
    from kivy.uix.label import Label
    from kivy.uix.scrollview import ScrollView
    from kivy.clock import Clock
    from kivy.uix.screenmanager import ScreenManager, Screen
    HAS_KIVY = True
except ImportError:
    HAS_KIVY = False

# 加密库适配
try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad
except ImportError:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== 配置与常量 ====================
CONFIG = {
    'BASE_URL': 'https://run.ecust.edu.cn',
    'AES_KEY': b'A7fK92LmXyQw8vRp',
    'GAODE_KEY': "1b308ceddafa4645d03ada9a1448a737",
    'MASTER_SECRET': "ECUST_RUN_2025_SEC", # 激活码盐值
    'ADMIN_CODE_SUFFIX': "ADMIN888",      # 管理员激活码后缀标识
    'DATA_FILE': 'user_storage.json'      # 本地数据留存
}

# ==================== 工具类 ====================
class Persistence:
    @staticmethod
    def save(data):
        with open(CONFIG['DATA_FILE'], 'w') as f:
            json.dump(data, f)
    @staticmethod
    def load():
        if os.path.exists(CONFIG['DATA_FILE']):
            with open(CONFIG['DATA_FILE'], 'r') as f:
                return json.load(f)
        return {"activated": False, "is_admin": False, "user": "", "pwd": ""}

class ToolBox:
    @staticmethod
    def get_did():
        raw = platform.node() + platform.machine() + platform.system()
        return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

    @staticmethod
    def gen_code(did, is_admin=False):
        salt = CONFIG['MASTER_SECRET'] + ("ADMIN" if is_admin else "USER")
        res = hashlib.sha256((did + salt).encode()).hexdigest().upper()[:16]
        return res

class MyAES:
    def __init__(self): self.key = CONFIG['AES_KEY']
    def encrypt(self, data):
        if isinstance(data, dict): data = json.dumps(data, separators=(',', ':'))
        iv = os.urandom(16)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return f"{base64.b64encode(iv).decode()}:{base64.b64encode(cipher.encrypt(pad(data.encode(), 16))).decode()}"

# ==================== Kivy UI 界面 ====================
if HAS_KIVY:
    class AuthScreen(Screen):
        def __init__(self, **kw):
            super().__init__(**kw)
            self.layout = BoxLayout(orientation='vertical', padding=40, spacing=20)
            self.did = ToolBox.get_did()
            
            self.layout.add_widget(Label(text="[ 系统权限认证 ]", font_size='24sp'))
            self.layout.add_widget(Label(text=f"设备ID: {self.did}", font_size='14sp'))
            
            self.code_in = TextInput(hint_text="输入激活码", multiline=False, size_hint_y=None, height=120)
            self.layout.add_widget(self.code_in)
            
            btn = Button(text="验证激活", size_hint_y=None, height=140, background_color=(0, 0.7, 0.4, 1))
            btn.bind(on_press=self.validate)
            self.layout.add_widget(btn)
            self.add_widget(self.layout)

        def validate(self, instance):
            code = self.code_in.text.strip().upper()
            user_target = ToolBox.gen_code(self.did, False)
            admin_target = ToolBox.gen_code(self.did, True)
            
            data = Persistence.load()
            if code == admin_target:
                data.update({"activated": True, "is_admin": True})
                Persistence.save(data)
                self.manager.current = 'run_screen'
            elif code == user_target:
                data.update({"activated": True, "is_admin": False})
                Persistence.save(data)
                self.manager.current = 'run_screen'
            else:
                self.code_in.text = "激活码错误"

    class RunScreen(Screen):
        def on_enter(self):
            self.refresh_ui()

        def refresh_ui(self):
            self.clear_widgets()
            data = Persistence.load()
            layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
            
            # 日志区
            self.log_lab = Label(text="[就绪] 等待任务...\n", size_hint_y=None, height=3000, halign='left', valign='top', color=(0,1,0,1))
            self.log_lab.bind(width=lambda s,w: s.setter('text_size')(s,(w,None)))
            scroll = ScrollView(); scroll.add_widget(self.log_lab); layout.add_widget(scroll)
            
            # 输入区 (带留存)
            self.phone = TextInput(hint_text="手机号", text=data.get('user',''), size_hint_y=None, height=110)
            self.pwd = TextInput(hint_text="密码", text=data.get('pwd',''), password=True, size_hint_y=None, height=110)
            layout.add_widget(self.phone); layout.add_widget(self.pwd)
            
            # 功能按钮
            self.run_btn = Button(text="开始自动跑步", size_hint_y=None, height=140, background_color=(0,0.5,1,1))
            self.run_btn.bind(on_press=self.start_work)
            layout.add_widget(self.run_btn)
            
            # 管理员专属功能
            if data.get('is_admin'):
                admin_box = BoxLayout(size_hint_y=None, height=120, spacing=10)
                btn_gen = Button(text="算码器", background_color=(0.7,0.7,0,1))
                btn_gen.bind(on_press=self.show_gen_tool)
                btn_clear = Button(text="清除激活/退出", background_color=(1,0,0,1))
                btn_clear.bind(on_press=self.clear_auth)
                admin_box.add_widget(btn_gen); admin_box.add_widget(btn_clear)
                layout.add_widget(admin_box)
            
            self.add_widget(layout)

        def log(self, msg):
            Clock.schedule_once(lambda dt: setattr(self.log_lab, 'text', self.log_lab.text + f"[{time.strftime('%H:%M:%S')}] {msg}\n"))

        def start_work(self, instance):
            data = Persistence.load()
            data.update({"user": self.phone.text, "pwd": self.pwd.text})
            Persistence.save(data)
            self.run_btn.disabled = True
            threading.Thread(target=self.logic_thread, daemon=True).start()

        def clear_auth(self, instance):
            Persistence.save({"activated": False, "is_admin": False})
            self.manager.current = 'auth_screen'

        def show_gen_tool(self, instance):
            # 简单弹窗演示
            did = ToolBox.get_did()
            self.log(f"当前设备用户码: {ToolBox.gen_code(did, False)}")
            self.log(f"当前设备管理员码: {ToolBox.gen_code(did, True)}")

        def logic_thread(self):
            # 获取上传轨迹和点的核心逻辑
            sess = requests.Session()
            sess.verify = False
            aes = MyAES()
            try:
                self.log("登录中...")
                res = sess.post(f"{CONFIG['BASE_URL']}/xcxapi/userLogin/", json={"iphone":self.phone.text, "password":self.pwd.text}).json()
                if res.get('code')!=1: self.log(f"失败:{res.get('message')}"); return
                uid = res['data']['id']
                
                self.log("获取系统随机点位...")
                # 对应 chunk_4/5 逻辑：先 createLine
                line = sess.post(f"{CONFIG['BASE_URL']}/xcxapi/createLine/", json={"student_id":uid, "pass_point":[]}).json()
                rid = line['data']['record_id']
                
                # 获取三个随机点并生成轨迹线
                pts = []
                for i in range(3):
                    lat = random.uniform(30.825, 30.835)
                    lng = random.uniform(121.498, 121.510)
                    pts.append({"lat":round(lat,6), "lng":round(lng,6), "timestamp":int(time.time())})
                
                # 生成高德地图轨迹图并Base64上传
                map_url = f"https://restapi.amap.com/v3/staticmap?key={CONFIG['GAODE_KEY']}&size=400*400&paths=5,0x24c789,1,,:{pts[0]['lng']},{pts[0]['lat']};{pts[2]['lng']},{pts[2]['lat']}"
                img_b64 = base64.b64encode(requests.get(map_url).content).decode()
                
                self.log("上传轨迹数据...")
                sess.post(f"{CONFIG['BASE_URL']}/xcxapi/uploadPathPointV3/", json={"a": aes.encrypt({"record_id":rid, "path_point":pts, "path_image":img_b64})})
                
                wait = random.randint(650, 850) # 11-14分钟
                self.log(f"模拟运动中...需等待 {wait//60} 分钟")
                time.sleep(10) # 测试用，实际改为 sleep(wait)
                
                self.log("提交最终成绩...")
                final = {
                    "record_id": rid, "pace": 6, "running_time": wait, "mileage": random.randint(2100, 2400),
                    "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "pass_point": 3, "step_count": random.randint(3000, 3800)
                }
                res_fin = sess.post(f"{CONFIG['BASE_URL']}/xcxapi/updateRecordNew/", json={"a": aes.encrypt(final)}).json()
                self.log(f"任务结束: {res_fin.get('message')}")
            except Exception as e: self.log(f"异常: {str(e)}")
            finally: Clock.schedule_once(lambda dt: setattr(self.run_btn, 'disabled', False))

    class MainApp(App):
        def build(self):
            sm = ScreenManager()
            sm.add_widget(AuthScreen(name='auth_screen'))
            sm.add_widget(RunScreen(name='run_screen'))
            
            # 数据留存检查
            data = Persistence.load()
            if data.get('activated'):
                sm.current = 'run_screen'
            return sm

# ==================== PC 命令行模式 ====================
else:
    def pc_main():
        did = ToolBox.get_did()
        print(f"设备ID: {did}")
        data = Persistence.load()
        if not data.get('activated'):
            code = input("输入激活码: ").strip().upper()
            if code == ToolBox.gen_code(did, True):
                data.update({"activated":True, "is_admin":True})
            elif code == ToolBox.gen_code(did, False):
                data.update({"activated":True, "is_admin":False})
            else: print("激活失败"); return
            Persistence.save(data)
        
        print(f"模式: {'管理员' if data.get('is_admin') else '普通用户'}")
        phone = input(f"手机号[{data.get('user','')}]: ") or data.get('user')
        pwd = input(f"密码: ") or data.get('pwd')
        # ... (此处执行逻辑同上)
        print("PC逻辑运行完成，详细逻辑请看代码内部 logic_thread")

if __name__ == '__main__':
    if HAS_KIVY: MainApp().run()
    else: pc_main()
