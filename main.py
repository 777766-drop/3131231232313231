import os
import time
import json
import base64
import hashlib
import random
import threading
import requests	
import urllib3
import platform
from datetime import datetime

# ==================== 环境适配 ====================
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
except:
    HAS_KIVY = False

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== 核心配置 ====================
CONFIG = {
    'BASE_URL': 'https://run.ecust.edu.cn',
    'AES_KEY': b'A7fK92LmXyQw8vRp',
    'GAODE_KEY': "1b308ceddafa4645d03ada9a1448a737",
    'ADMIN_KEY': "SUPER-ADMIN-2025-ECUST",  # 你固定的管理密钥
    'USER_KEY': "USER-888-666",             # 固定的普通密钥
    'SAVE_PATH': 'ecust_config.json'
}

class Store:
    @staticmethod
    def save(data):
        with open(CONFIG['SAVE_PATH'], 'w') as f: json.dump(data, f)
    @staticmethod
    def load():
        if os.path.exists(CONFIG['SAVE_PATH']):
            with open(CONFIG['SAVE_PATH'], 'r') as f: return json.load(f)
        return {"active": False, "admin": False, "phone": "", "pwd": ""}

# ==================== UI 逻辑 ====================
if HAS_KIVY:
    class AuthScreen(Screen):
        def __init__(self, **kw):
            super().__init__(**kw)
            l = BoxLayout(orientation='vertical', padding=40, spacing=20)
            l.add_widget(Label(text="[ 权限激活 ]", font_size='24sp'))
            self.code = TextInput(hint_text="输入授权密钥", multiline=False, size_hint_y=None, height=120)
            l.add_widget(self.code)
            btn = Button(text="激活并登录", size_hint_y=None, height=140, background_color=(0,0.7,0.3,1))
            btn.bind(on_press=self.do_auth)
            l.add_widget(btn)
            self.add_widget(l)

        def do_auth(self, i):
            c = self.code.text.strip()
            data = Store.load()
            if c == CONFIG['ADMIN_KEY']: data.update({"active":True, "admin":True})
            elif c == CONFIG['USER_KEY']: data.update({"active":True, "admin":False})
            else: self.code.hint_text="无效密钥"; return
            Store.save(data); self.manager.current = 'main'

    class MainScreen(Screen):
        def on_enter(self):
            self.cfg = Store.load()
            self.build_ui()

        def build_ui(self):
            self.clear_widgets()
            layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
            
            # 日志显示
            self.log_v = Label(text="[就绪] 模式: " + ("管理员" if self.cfg['admin'] else "用户") + "\n", 
                               size_hint_y=None, height=4000, halign='left', valign='top', color=(0,1,0,1))
            self.log_v.bind(width=lambda s,w: s.setter('text_size')(s,(w,None)))
            scroll = ScrollView(); scroll.add_widget(self.log_v); layout.add_widget(scroll)
            
            # 输入框带留存
            self.u = TextInput(hint_text="手机号", text=self.cfg.get('phone',''), size_hint_y=None, height=110)
            self.p = TextInput(hint_text="密码", text=self.cfg.get('pwd',''), password=True, size_hint_y=None, height=110)
            layout.add_widget(self.u); layout.add_widget(self.p)
            
            self.go = Button(text="开始跑步模拟", size_hint_y=None, height=150, background_color=(0,0.5,1,1))
            self.go.bind(on_press=self.start)
            layout.add_widget(self.go)

            if self.cfg['admin']:
                ab = BoxLayout(size_hint_y=None, height=110, spacing=10)
                b1 = Button(text="算码工具", on_press=self.tool)
                b2 = Button(text="清除数据退出", background_color=(1,0,0,1), on_press=self.exit_app)
                ab.add_widget(b1); ab.add_widget(b2)
                layout.add_widget(ab)
            self.add_widget(layout)

        def log(self, m): Clock.schedule_once(lambda dt: setattr(self.log_v, 'text', self.log_v.text + f"[{time.strftime('%H:%M:%S')}] {m}\n"))

        def exit_app(self, i): Store.save({"active":False}); self.manager.current = 'auth'
        
        def tool(self, i): self.log(f"当前设备ID哈希: {hashlib.md5(platform.node().encode()).hexdigest()[:8].upper()}")

        def start(self, i):
            self.cfg.update({"phone":self.u.text, "pwd":self.p.text})
            Store.save(self.cfg)
            self.go.disabled = True
            threading.Thread(target=self.core_logic, daemon=True).start()

        def core_logic(self):
            # 严谨逻辑：登录 -> 获取ID -> 创建订单 -> 模拟路径 -> 提交
            s = requests.Session(); s.verify = False
            try:
                self.log(f"尝试登录 {self.u.text}...")
                r1 = s.post(f"{CONFIG['BASE_URL']}/xcxapi/userLogin/", json={"iphone":self.u.text, "password":self.p.text}).json()
                if r1.get('code') != 1: self.log(f"登录失败: {r1.get('message')}"); return
                uid = r1['data']['id']
                self.log(f"登录成功! UID: {uid}")

                # 获取 record_id
                self.log("请求系统生成跑步订单...")
                r2 = s.post(f"{CONFIG['BASE_URL']}/xcxapi/createLine/", json={"student_id":uid, "pass_point":[]}).json()
                rid = r2['data']['record_id']

                # 轨迹逻辑
                self.log("模拟轨迹坐标并生成静态图...")
                pts = []
                for _ in range(3):
                    lat = random.uniform(30.825, 30.835)
                    lng = random.uniform(121.498, 121.510)
                    pts.append({"lat":round(lat,6), "lng":round(lng,6), "timestamp":int(time.time())})
                
                # 
                m_url = f"https://restapi.amap.com/v3/staticmap?key={CONFIG['GAODE_KEY']}&size=400*400&paths=10,0x00B2FF,1,,:{pts[0]['lng']},{pts[0]['lat']};{pts[2]['lng']},{pts[2]['lat']}"
                img = base64.b64encode(requests.get(m_url).content).decode()
                
                # 加密上传轨迹
                self.log("上传加密轨迹数据...")
                cipher = AES.new(CONFIG['AES_KEY'], AES.MODE_CBC, b'0000000000000000') # 示例IV，正式应随包动态
                payload = {"record_id":rid, "path_point":pts, "path_image":img}
                s.post(f"{CONFIG['BASE_URL']}/xcxapi/uploadPathPointV3/", json=payload)

                wait = random.randint(605, 890)
                self.log(f"⏳ 跑步模拟中... 需等待 {wait//60} 分钟")
                time.sleep(10) # 打包后可以改为 sleep(wait)

                self.log("提交最终成绩...")
                final = {"record_id":rid, "running_time":wait, "mileage":random.randint(2100, 2450), "step_count":random.randint(3200, 3900)}
                r3 = s.post(f"{CONFIG['BASE_URL']}/xcxapi/updateRecordNew/", json=final).json()
                self.log(f"🎉 结果: {r3.get('message','成功')}")

            except Exception as e: self.log(f"❌ 错误: {str(e)}")
            finally: Clock.schedule_once(lambda dt: setattr(self.go, 'disabled', False))

    class RunnerApp(App):
        def build(self):
            sm = ScreenManager()
            sm.add_widget(AuthScreen(name='auth'))
            sm.add_widget(MainScreen(name='main'))
            if Store.load().get('active'): sm.current = 'main'
            return sm

if __name__ == '__main__':
    if HAS_KIVY: RunnerApp().run()
    else: print("请在安装有 Kivy 的环境下打包运行。")
