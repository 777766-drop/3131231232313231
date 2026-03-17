import os, time, json, base64, hashlib, random, threading, requests, urllib3, platform
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# Kivy UI 适配
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

urllib3.disable_warnings()

# ==================== 核心配置 ====================
CONFIG = {
    'BASE_URL': 'https://run.ecust.edu.cn',
    'AES_KEY': b'A7fK92LmXyQw8vRp',
    'GAODE_KEY': "1b308ceddafa4645d03ada9a1448a737",
    'ADMIN_KEY': "SUPER888",  # 固定管理密钥
    'USER_KEY': "USER666",    # 固定普通密钥
    'DB_FILE': 'ecust_save.json'
}

class Storage:
    @staticmethod
    def load():
        if os.path.exists(CONFIG['DB_FILE']):
            with open(CONFIG['DB_FILE'], 'r') as f: return json.load(f)
        return {"active": False, "admin": False, "phone": "", "pwd": ""}
    @staticmethod
    def save(data):
        with open(CONFIG['DB_FILE'], 'w') as f: json.dump(data, f)

# ==================== 核心逻辑类 ====================
class RunnerCore:
    def __init__(self, log_func):
        self.log = log_func
        self.sess = requests.Session()
        self.sess.verify = False

    def encrypt_data(self, data):
        cipher = AES.new(CONFIG['AES_KEY'], AES.MODE_CBC, b'0000000000000000')
        return base64.b64encode(cipher.encrypt(pad(json.dumps(data).encode(), 16))).decode()

    def execute(self, phone, pwd):
        try:
            self.log(f"正在登录账号: {phone}...")
            # 1. 登录获取 student_id (关键步骤)
            r1 = self.sess.post(f"{CONFIG['BASE_URL']}/xcxapi/userLogin/", json={"iphone":phone, "password":pwd}).json()
            if r1.get('code') != 1: 
                self.log(f"登录失败: {r1.get('message')}"); return
            
            uid = r1['data']['id']
            self.log(f"登录成功! 内部ID: {uid}")

            # 2. 创建订单获取 record_id
            self.log("正在向服务器申请跑步订单...")
            r2 = self.sess.post(f"{CONFIG['BASE_URL']}/xcxapi/createLine/", json={"student_id":uid, "pass_point":[]}).json()
            rid = r2['data']['record_id']

            # 3. 模拟三个打卡点并生成高德轨迹线
            self.log("生成随机打卡点与轨迹图...")
            pts = []
            for _ in range(3):
                lat = random.uniform(30.825, 30.835)
                lng = random.uniform(121.498, 121.510)
                pts.append({"lat":round(lat,6), "lng":round(lng,6), "timestamp":int(time.time())})
            
            # 模拟轨迹图渲染
            m_url = f"https://restapi.amap.com/v3/staticmap?key={CONFIG['GAODE_KEY']}&size=400*400&paths=10,0x00B2FF,1,,:{pts[0]['lng']},{pts[0]['lat']};{pts[2]['lng']},{pts[2]['lat']}"
            img_b64 = base64.b64encode(requests.get(m_url).content).decode()

            # 4. 上传轨迹 (使用加密接口)
            self.log("上传加密轨迹包至服务器...")
            payload = {"record_id": rid, "path_point": pts, "path_image": img_b64}
            self.sess.post(f"{CONFIG['BASE_URL']}/xcxapi/uploadPathPointV3/", json={"a": self.encrypt_data(payload)})

            # 5. 等待与提交
            wait = random.randint(601, 890)
            self.log(f"⏳ 模拟跑步中... 需等待 {wait//60} 分钟")
            time.sleep(10) # 建议改为 wait

            self.log("正在提交成绩...")
            final = {"record_id": rid, "running_time": wait, "mileage": random.randint(2100, 2480), "step_count": random.randint(3100, 3900)}
            r3 = self.sess.post(f"{CONFIG['BASE_URL']}/xcxapi/updateRecordNew/", json={"a": self.encrypt_data(final)}).json()
            self.log(f"🎉 任务结果: {r3.get('message', '已完成')}")

        except Exception as e: self.log(f"❌ 逻辑异常: {str(e)}")

# ==================== UI 界面 ====================
if HAS_KIVY:
    class ScreenAuth(Screen):
        def __init__(self, **kw):
            super().__init__(**kw)
            l = BoxLayout(orientation='vertical', padding=50, spacing=20)
            l.add_widget(Label(text="系统权限激活", font_size='26sp'))
            self.ci = TextInput(hint_text="输入授权密钥", multiline=False, size_hint_y=None, height=120)
            l.add_widget(self.ci)
            b = Button(text="验证激活", size_hint_y=None, height=140, background_color=(0,0.7,0.4,1))
            b.bind(on_press=self.auth)
            l.add_widget(b); self.add_widget(l)

        def auth(self, i):
            c = self.ci.text.strip()
            d = Storage.load()
            if c == CONFIG['ADMIN_KEY']: d.update({"active":True, "admin":True})
            elif c == CONFIG['USER_KEY']: d.update({"active":True, "admin":False})
            else: self.ci.text=""; self.ci.hint_text="密钥错误"; return
            Storage.save(d); self.manager.current = 'main'

    class ScreenMain(Screen):
        def on_enter(self):
            self.d = Storage.load(); self.ui()

        def ui(self):
            self.clear_widgets()
            l = BoxLayout(orientation='vertical', padding=20, spacing=10)
            self.log_v = Label(text="[就绪]\n", size_hint_y=None, height=4000, halign='left', valign='top', color=(0,1,0,1))
            self.log_v.bind(width=lambda s,w: s.setter('text_size')(s,(w,None)))
            scroll = ScrollView(); scroll.add_widget(self.log_v); l.add_widget(scroll)
            
            self.u = TextInput(hint_text="手机号", text=self.d['phone'], size_hint_y=None, height=110)
            self.p = TextInput(hint_text="密码", text=self.d['pwd'], password=True, size_hint_y=None, height=110)
            l.add_widget(self.u); l.add_widget(self.p)
            
            self.go = Button(text="开始跑步任务", size_hint_y=None, height=150, background_color=(0,0.5,1,1))
            self.go.bind(on_press=self.fire)
            l.add_widget(self.go)

            if self.d['admin']:
                ab = Button(text="【管理模式】清除激活/退出账号", size_hint_y=None, height=110, background_color=(1,0,0,1))
                ab.bind(on_press=self.logout); l.add_widget(ab)
            self.add_widget(l)

        def logout(self, i): Storage.save({"active":False}); self.manager.current = 'auth'
        def log(self, m): Clock.schedule_once(lambda dt: setattr(self.log_v, 'text', self.log_v.text + f"[{time.strftime('%H:%M:%S')}] {m}\n"))
        
        def fire(self, i):
            self.d.update({"phone":self.u.text, "pwd":self.p.text}); Storage.save(self.d)
            self.go.disabled = True
            threading.Thread(target=lambda: RunnerCore(self.log).execute(self.u.text, self.p.text), daemon=True).start()
            Clock.schedule_once(lambda dt: setattr(self.go, 'disabled', False), 5)

    class RunApp(App):
        def build(self):
            sm = ScreenManager()
            sm.add_widget(AuthScreen(name='auth'))
            sm.add_widget(ScreenMain(name='main'))
            if Storage.load().get('active'): sm.current = 'main'
            return sm

if __name__ == '__main__':
    if HAS_KIVY: RunApp().run()
    else: print("请在安装有 Kivy 的环境下打包运行。")
