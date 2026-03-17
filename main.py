# -*- coding: utf-8 -*-
import os, sys, json, base64, random, math, time, hashlib, platform
from datetime import datetime, timedelta
from threading import Thread
import logging

# ===== Android 路径兼容 =====
if hasattr(sys, 'getandroidapilevel'):
    from android.permissions import request_permissions, Permission
    from android.storage import app_storage_path
    request_permissions([
        Permission.INTERNET,
        Permission.ACCESS_NETWORK_STATE,
    ])
    STORAGE_PATH = app_storage_path()
else:
    STORAGE_PATH = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(
    filename=os.path.join(STORAGE_PATH, 'ecust_run.log'),
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

try:
    import requests
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.label import Label
    from kivy.uix.button import Button
    from kivy.uix.textinput import TextInput
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.gridlayout import GridLayout
    from kivy.clock import Clock
    from kivy.core.window import Window
    from kivy.properties import StringProperty
except Exception as e:
    logging.critical(f"Import error: {str(e)}")
    raise

# ===== 配置常量 =====
AES_KEY = b'A7fK92LmXyQw8vRp'
BASE_URL = "https://run.ecust.edu.cn"
CAMPUS_BOUNDS = {
    'lat_min': 30.825, 'lat_max': 30.835,
    'lng_min': 121.498, 'lng_max': 121.510
}
AMAP_KEY = "3519797a53c3f3a8f7aee41f97f3d6a9"  # 需替换为真实Key

# ===== 加密模块 =====
def aes_encrypt(data: str) -> str:
    try:
        cipher = AES.new(AES_KEY, AES.MODE_ECB)
        padded = pad(data.encode(), AES.block_size)
        return base64.b64encode(cipher.encrypt(padded)).decode()
    except:
        return None

def aes_decrypt(data: str) -> str:
    try:
        cipher = AES.new(AES_KEY, AES.MODE_ECB)
        return unpad(cipher.decrypt(base64.b64decode(data)), AES.block_size).decode()
    except:
        return None

# ===== 登录管理（手机号+密码）=====
class LoginManager:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "X-Session-ID": "ts3p8g1xr75we94x9r6ivbtzwadpk646",
            "Authorization": "",
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-G9750) AppleWebKit/537.0.36",
            "Accept-Encoding": "gzip"
        })
        self.student_id = None
        self.user_name = None
        
    def login(self, phone, password):
        """手机号+密码登录，返回(student_id, name)或None"""
        try:
            # 根据抓包，登录数据可能是明文或加密，这里先尝试明文JSON加密
            login_data = {
                "phone": phone,
                "password": password
            }
            payload = {"a": aes_encrypt(json.dumps(login_data))}
            
            resp = self.session.post(
                f"{BASE_URL}/xcxapi/userLogin/",
                json=payload,
                timeout=10
            )
            result = resp.json()
            
            if result.get('code') == 1:
                data = result.get('data', {})
                self.student_id = data.get('id')
                self.user_name = data.get('name')
                # 如果返回了新的session_id，更新
                if 'session_id' in data:
                    self.session.headers.update({"X-Session-ID": data['session_id']})
                return self.student_id, self.user_name
            else:
                return None, result.get('message', '登录失败')
        except Exception as e:
            return None, str(e)

# ===== 高德地图轨迹生成 =====
class TrajectoryGenerator:
    def __init__(self):
        self.start_time = datetime.now()
        
    def generate_points(self, num_points=4):
        points = []
        time_offsets = [0, 4, 8, 12, 16]  # 分钟
        
        for i in range(num_points):
            if i == 0:
                lat = random.uniform(30.828, 30.832)
                lng = random.uniform(121.501, 121.508)
            else:
                prev = points[-1]
                lat = prev['lat'] + random.uniform(0.001, 0.003) * random.choice([-1, 1])
                lng = prev['lng'] + random.uniform(0.001, 0.003) * random.choice([-1, 1])
            
            lat = max(CAMPUS_BOUNDS['lat_min'], min(CAMPUS_BOUNDS['lat_max'], lat))
            lng = max(CAMPUS_BOUNDS['lng_min'], min(CAMPUS_BOUNDS['lng_max'], lng))
            lat += random.uniform(-0.00005, 0.00005)
            lng += random.uniform(-0.00005, 0.00005)
            
            timestamp = int((self.start_time + timedelta(minutes=time_offsets[i])).timestamp())
            points.append({
                'name': f'打卡点{i+1}',
                'lat': round(lat, 6),
                'lng': round(lng, 6),
                'timestamp': timestamp,
                'accuracy': random.randint(15, 30)
            })
        return points
    
    def calc_distance(self, points):
        total = 0
        for i in range(len(points)-1):
            lat1, lng1 = math.radians(points[i]['lat']), math.radians(points[i]['lng'])
            lat2, lng2 = math.radians(points[i+1]['lat']), math.radians(points[i+1]['lng'])
            dlat, dlng = lat2 - lat1, lng2 - lng1
            a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlng/2)**2
            total += 6371000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return round(total * random.uniform(1.2, 1.4), 2)
    
    def build_map_url(self, points, size="400*400"):
        path_str = ";".join([f"{p['lng']},{p['lat']}" for p in points])
        paths = f"5,0x24c789,1,,:{path_str}"
        center_lat = sum(p['lat'] for p in points) / len(points)
        center_lng = sum(p['lng'] for p in points) / len(points)
        params = {
            'key': AMAP_KEY,
            'size': size,
            'zoom': 16,
            'center': f"{center_lng},{center_lat}",
            'paths': paths,
            'scale': 2
        }
        return f"https://restapi.amap.com/v3/staticmap?{requests.compat.urlencode(params)}"
    
    def get_base64_image(self, url):
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                return base64.b64encode(r.content).decode()
        except Exception as e:
            logging.error(f"Map error: {e}")
        return None

# ===== 核心跑步逻辑 =====
class ECUSTRunner:
    def __init__(self, login_mgr, student_id, status_callback=None):
        self.login_mgr = login_mgr
        self.student_id = student_id
        self.callback = status_callback
        self.running = False
        
    def log(self, msg):
        logging.info(msg)
        if self.callback:
            Clock.schedule_once(lambda dt: self.callback(msg), 0)
            
    def run_full_process(self):
        self.running = True
        session = self.login_mgr.session
        
        # 1. 创建记录
        self.log("📍 创建跑步记录...")
        try:
            create_data = {"student_id": self.student_id, "pass_point": []}
            r = session.post(
                f"{BASE_URL}/xcxapi/createLine/",
                json={"a": aes_encrypt(json.dumps(create_data))},
                timeout=10
            )
            result = r.json()
            if result.get('code') != 1:
                self.log(f"❌ 创建失败: {result}")
                return
            record_id = result['data']['record_id']
            self.log(f"✅ 记录ID: {record_id}")
        except Exception as e:
            self.log(f"❌ 错误: {e}")
            return
        
        # 2. 生成轨迹与地图
        self.log("🗺️ 生成轨迹...")
        gen = TrajectoryGenerator()
        points = gen.generate_points(4)
        mileage = gen.calc_distance(points)
        while not (2000 <= mileage <= 4000):
            points = gen.generate_points(4)
            mileage = gen.calc_distance(points)
            
        map_url = gen.build_map_url(points)
        path_image = gen.get_base64_image(map_url)
        
        if path_image:
            self.log(f"✅ 地图生成成功 ({len(path_image)//1024}KB)")
        else:
            self.log("⚠️ 地图获取失败")
            path_image = ""
            
        # 3. 上传轨迹
        self.log("⬆️ 上传轨迹...")
        upload_payload = {
            "record_id": record_id,
            "path_point": points,
            "path_image": path_image,
            "student_id": self.student_id,
            "start_time": int(points[0]['timestamp']),
            "end_time": int(points[-1]['timestamp']),
            "mileage": mileage,
            "step_count": int(mileage * 0.8),
            "run_time": points[-1]['timestamp'] - points[0]['timestamp']
        }
        
        try:
            r = session.post(
                f"{BASE_URL}/xcxapi/uploadPathPointV3/",
                json={"a": aes_encrypt(json.dumps(upload_payload))},
                timeout=15
            )
            self.log(f"📤 上传: {r.json().get('message', 'OK')}")
        except Exception as e:
            self.log(f"⚠️ 上传警告: {e}")
            
        # 4. 模拟倒计时（视觉反馈）
        self.log("🏃 模拟跑步过程...")
        duration = upload_payload['run_time']
        for i in range(5):
            if not self.running:
                return
            progress = (i+1) * 20
            self.log(f"⏳ 进度: {progress}%")
            time.sleep(1)
            
        # 5. 提交结果
        self.log("🏁 提交结果...")
        submit_payload = {
            "record_id": record_id,
            "student_id": self.student_id,
            "verify_mode": 0,
            "run_type": 0
        }
        try:
            r = session.post(
                f"{BASE_URL}/xcxapi/updateRecordNew/",
                json={"a": aes_encrypt(json.dumps(submit_payload))},
                timeout=10
            )
            result = r.json()
            if result.get('code') == 1:
                self.log(f"✅ 完成！距离: {mileage:.0f}m")
            else:
                self.log(f"❌ 失败: {result}")
        except Exception as e:
            self.log(f"❌ 错误: {e}")

# ===== 激活码系统 =====
class LicenseManager:
    def __init__(self):
        self.config_file = os.path.join(STORAGE_PATH, 'ecust_config.json')
        self.config = self.load_config()
        
    def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except:
            return {}
            
    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f)
            
    def get_device_id(self):
        device_str = f"{platform.machine()}{platform.node()}{STORAGE_PATH}"
        return hashlib.md5(device_str.encode()).hexdigest()[:16].upper()
    
    def generate_activation_code(self, device_id=None):
        target = device_id or self.get_device_id()
        hash_val = hashlib.sha256(f"{target}ECUST_SECRET_2025".encode()).hexdigest()
        return f"ECUST-{hash_val[:4].upper()}-{hash_val[4:8].upper()}"
    
    def verify_code(self, code, is_admin=False):
        device_id = self.get_device_id()
        expected = self.generate_activation_code(device_id)
        
        if is_admin:
            admin_hash = hashlib.sha256(b"ECUST_ADMIN_2025_SECRET").hexdigest()[:8].upper()
            return code == f"ADMIN-{admin_hash}"
        return code == expected

# ===== Kivy GUI界面 =====
class MainLayout(BoxLayout):
    status_text = StringProperty("状态: 等待激活")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 10
        self.license_mgr = LicenseManager()
        self.login_mgr = None
        self.runner = None
        
        # 状态显示
        self.status_label = Label(
            text=self.status_text,
            size_hint_y=None,
            height=200,
            text_size=(Window.width-20, None),
            markup=True,
            color=(0.9, 0.9, 0.9, 1)
        )
        scroll = ScrollView(size_hint=(1, 0.4))
        scroll.add_widget(self.status_label)
        self.add_widget(scroll)
        
        # 输入区
        grid = GridLayout(cols=1, spacing=10, size_hint_y=0.6)
        
        # 激活码输入
        self.code_input = TextInput(
            hint_text='激活码 (ECUST-XXXX-XXXX)',
            multiline=False,
            height=50,
            size_hint_y=None
        )
        grid.add_widget(self.code_input)
        
        # 手机号输入（登录用）
        self.phone_input = TextInput(
            hint_text='手机号 (登录账号)',
            multiline=False,
            input_filter='int',
            height=50,
            size_hint_y=None,
            disabled=True
        )
        grid.add_widget(self.phone_input)
        
        # 密码输入
        self.pwd_input = TextInput(
            hint_text='密码',
            multiline=False,
            password=True,  # 密码掩码
            height=50,
            size_hint_y=None,
            disabled=True
        )
        grid.add_widget(self.pwd_input)
        
        # 按钮区
        btn_grid = GridLayout(cols=2, spacing=10, size_hint_y=None, height=150)
        
        self.activate_btn = Button(
            text='🔐 激活设备',
            on_press=self.do_activate
        )
        btn_grid.add_widget(self.activate_btn)
        
        self.device_btn = Button(
            text='📱 设备码',
            on_press=self.show_device
        )
        btn_grid.add_widget(self.device_btn)
        
        self.login_btn = Button(
            text='🔑 登录账号',
            on_press=self.do_login,
            disabled=True
        )
        btn_grid.add_widget(self.login_btn)
        
        self.run_btn = Button(
            text='🏃 开始跑步',
            on_press=self.do_run,
            disabled=True
        )
        btn_grid.add_widget(self.run_btn)
        
        grid.add_widget(btn_grid)
        self.add_widget(grid)
        
        # 检查已激活
        if self.license_mgr.config.get('activated'):
            self.on_activated()
            
    def on_activated(self):
        """激活后解锁登录功能"""
        self.status_text = "✅ 设备已激活\n请登录手机号+密码"
        self.code_input.disabled = True
        self.phone_input.disabled = False
        self.pwd_input.disabled = False
        self.login_btn.disabled = False
        self.activate_btn.disabled = True
        
    def update_status(self, msg):
        self.status_text += f"\n{msg}"
        self.status_label.text = self.status_text
        
    def do_activate(self, instance):
        code = self.code_input.text.strip()
        if self.license_mgr.verify_code(code) or self.license_mgr.verify_code(code, is_admin=True):
            self.license_mgr.config['activated'] = True
            self.license_mgr.save_config()
            self.update_status("✅ 激活成功")
            self.on_activated()
        else:
            self.update_status("❌ 激活码无效")
            
    def show_device(self, instance):
        did = self.license_mgr.get_device_id()
        code = self.license_mgr.generate_activation_code()
        self.update_status(f"设备ID: {did}\n管理员生成码: {code}")
        
    def do_login(self, instance):
        phone = self.phone_input.text.strip()
        pwd = self.pwd_input.text.strip()
        
        if not phone or not pwd:
            self.update_status("⚠️ 请输入手机号和密码")
            return
            
        self.update_status("🔄 登录中...")
        
        def login_thread():
            self.login_mgr = LoginManager()
            sid, name_or_err = self.login_mgr.login(phone, pwd)
            
            if sid:
                Clock.schedule_once(lambda dt: self.on_login_success(sid, name_or_err), 0)
            else:
                Clock.schedule_once(lambda dt: self.update_status(f"❌ 登录失败: {name_or_err}"), 0)
                
        Thread(target=login_thread, daemon=True).start()
        
    def on_login_success(self, student_id, user_name):
        self.update_status(f"✅ 登录成功\n用户: {user_name}\n学号: {student_id}")
        self.run_btn.disabled = False
        self.login_btn.disabled = True  # 已登录，禁用再次登录
        self.student_id = student_id
        
    def do_run(self, instance):
        if not hasattr(self, 'student_id'):
            self.update_status("⚠️ 未获取学号")
            return
            
        self.run_btn.disabled = True
        self.update_status("🚀 启动跑步...")
        
        def run_thread():
            self.runner = ECUSTRunner(self.login_mgr, self.student_id, self.update_status)
            self.runner.run_full_process()
            Clock.schedule_once(lambda dt: setattr(self.run_btn, 'disabled', False), 0)
            
        Thread(target=run_thread, daemon=True).start()

class ECUSTApp(App):
    def build(self):
        Window.clearcolor = (0.15, 0.15, 0.2, 1)
        return MainLayout()

if __name__ == '__main__':
    try:
        ECUSTApp().run()
    except Exception as e:
        logging.critical(f"Crash: {str(e)}", exc_info=True)
        raise
