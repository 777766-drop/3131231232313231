#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ECUST Campus Run Automation v4.4 - Android Compatible
修复内容：移除 msvcrt 依赖，适配 Android 存储路径，添加 SSL 兼容性
"""

import requests
import json
import base64
import hashlib
import time
import os
import sys
import platform
import getpass
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import warnings
warnings.filterwarnings('ignore')

# ==================== 配置区 ====================
CONFIG = {
    'BASE_URL': 'https://run.ecust.edu.cn',
    'AES_KEY': 'A7fK92LmXyQw8vRp',
    'ADMIN_SECRET': 'ECUST_ADMIN_2025_SECRET',  # 管理员密钥
    'VERSION': '4.4-Android',
    'DEFAULT_TIMEOUT': 15,
    'MIN_RUNNING_TIME': 600,  # 最少跑步时间（秒），防止被检测
    'MAX_RUNNING_TIME': 900   # 最多15分钟
}

# ==================== Android 路径适配 ====================
def get_storage_path():
    """获取跨平台的存储路径"""
    system = platform.system()
    
    # Android 检测 (Termux 或 Buildozer)
    if 'ANDROID_ROOT' in os.environ or os.path.exists('/data/data/com.termux'):
        # Termux 路径或 Android 应用私有目录
        if os.path.exists('/sdcard'):
            base_path = '/sdcard/Download'
        else:
            base_path = os.path.expanduser('~')
    elif system == 'Windows':
        base_path = os.path.expanduser('~')
    else:  # Linux/Mac
        base_path = os.path.expanduser('~')
    
    config_dir = os.path.join(base_path, '.ecust_run')
    os.makedirs(config_dir, exist_ok=True)
    return config_dir

STORAGE_PATH = get_storage_path()
CONFIG_FILE = os.path.join(STORAGE_PATH, 'config.json')
ACTIVATION_FILE = os.path.join(STORAGE_PATH, 'activation.json')

# ==================== 加密模块 ====================
class CryptoUtil:
    def __init__(self, key):
        self.key = key.encode('utf-8')
    
    def encrypt(self, data):
        if isinstance(data, dict):
            data = json.dumps(data, separators=(',', ':'))
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        cipher = AES.new(self.key, AES.MODE_ECB)
        padded = pad(data, AES.block_size, style='pkcs7')
        encrypted = cipher.encrypt(padded)
        return base64.b64encode(encrypted).decode('utf-8')
    
    def decrypt(self, data):
        try:
            cipher = AES.new(self.key, AES.MODE_ECB)
            decoded = base64.b64decode(data)
            decrypted = cipher.decrypt(decoded)
            unpadded = unpad(decrypted, AES.block_size, style='pkcs7')
            return unpadded.decode('utf-8')
        except Exception as e:
            return None

crypto = CryptoUtil(CONFIG['AES_KEY'])

# ==================== 跨平台输入模块 ====================
class SecureInput:
    """兼容 Windows/Linux/Android 的密码输入"""
    
    @staticmethod
    def get_password(prompt="密码: "):
        """
        跨平台密码输入，Android 上自动回退到无回显模式
        """
        system = platform.system()
        
        # Windows 下尝试使用 msvcrt，如果失败则回退
        if system == 'Windows':
            try:
                import msvcrt
                print(prompt, end='', flush=True)
                password = ''
                while True:
                    ch = msvcrt.getch()
                    if ch == b'\r' or ch == b'\n':
                        print()
                        break
                    elif ch == b'\b':
                        if password:
                            password = password[:-1]
                            print('\b \b', end='', flush=True)
                    else:
                        password += ch.decode('utf-8', errors='ignore')
                        print('*', end='', flush=True)
                return password
            except ImportError:
                pass
        
        # Android/Linux/Mac 使用 getpass（终端无回显）
        try:
            return getpass.getpass(prompt)
        except (ImportError, OSError):
            # 如果 getpass 也不可用（某些 Android 终端），直接输入
            print(f"[Android模式] {prompt}", end='', flush=True)
            return input()

    @staticmethod
    def get_input(prompt):
        """普通输入"""
        print(prompt, end='', flush=True)
        return input()

# ==================== 设备指纹 ====================
def get_device_id():
    """生成基于设备的唯一ID（用于激活码绑定）"""
    try:
        # 尝试获取 Android ID 或 MAC 地址
        if 'ANDROID_ROOT' in os.environ:
            try:
                # 尝试读取 Android ID（需要 READ_PHONE_STATE 权限，可能失败）
                import subprocess
                result = subprocess.run(['settings', 'get', 'secure', 'android_id'], 
                                      capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except:
                pass
        
        # 回退到基于文件系统的指纹
        system_info = f"{platform.node()}-{platform.machine()}-{platform.processor()}"
        return hashlib.md5(system_info.encode()).hexdigest()[:16]
    except:
        # 最后的回退：随机生成但持久化存储
        if os.path.exists(os.path.join(STORAGE_PATH, '.device_id')):
            with open(os.path.join(STORAGE_PATH, '.device_id'), 'r') as f:
                return f.read().strip()
        else:
            device_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:16]
            with open(os.path.join(STORAGE_PATH, '.device_id'), 'w') as f:
                f.write(device_id)
            return device_id

DEVICE_ID = get_device_id()

# ==================== 激活系统 ====================
class ActivationSystem:
    def __init__(self):
        self.data = self.load_activation()
    
    def load_activation(self):
        if os.path.exists(ACTIVATION_FILE):
            try:
                with open(ACTIVATION_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_activation(self):
        with open(ACTIVATION_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)
    
    def generate_activation_code(self, device_id):
        """管理员使用：为指定设备生成激活码"""
        seed = f"{device_id}{CONFIG['ADMIN_SECRET']}2025"
        code = hashlib.md5(seed.encode()).hexdigest()[:8].upper()
        return f"ECUST-{code[:4]}-{code[4:]}"
    
    def verify_activation(self, code):
        """验证激活码是否匹配本机"""
        expected = self.generate_activation_code(DEVICE_ID)
        return code == expected
    
    def is_activated(self):
        return self.data.get('activated', False)
    
    def is_admin(self):
        return self.data.get('is_admin', False)
    
    def activate(self, code, is_admin=False):
        if is_admin or self.verify_activation(code):
            self.data['activated'] = True
            self.data['is_admin'] = is_admin
            self.data['code'] = code if not is_admin else 'ADMIN'
            self.data['activate_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
            self.save_activation()
            return True
        return False
    
    def clear_activation(self):
        """管理员功能：清除凭证"""
        if self.is_admin():
            self.data = {}
            self.save_activation()
            return True
        return False

# ==================== 校园跑 API ====================
class CampusRunAPI:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-G9880 Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/111.0.5563.116 Mobile Safari/537.36 XWEB/1110017 MMWEBSDK/20230805 MMWEBID/2567 MicroMessenger/8.0.42.2460(0x28002A58) WeChat/arm64 Weixin NetType/5G Language/zh_CN ABI/arm64 MiniProgramEnv/android',
            'Content-Type': 'application/json',
            'X-Session-ID': 'ts3p8g1xr75we94x9r6ivbtzwadpk646',
            'Authorization': ''
        })
        self.student_id = None
        self.record_id = None
        self.crypto = crypto
        
        # SSL 适配（Android 可能需要）
        self.session.verify = True
        try:
            # 尝试使用 certifi 的证书（如果安装了）
            import certifi
            self.session.verify = certifi.where()
        except ImportError:
            pass
    
    def login(self, phone, password):
        """自动登录获取 student_id"""
        url = f"{CONFIG['BASE_URL']}/xcxapi/userLogin/"
        data = {
            "phone": phone,
            "password": password
        }
        
        try:
            # 加密请求
            encrypted = self.crypto.encrypt(data)
            resp = self.session.post(url, json={"a": encrypted}, timeout=CONFIG['DEFAULT_TIMEOUT'])
            result = resp.json()
            
            if result.get('code') == 1:
                # 解析返回数据获取 student_id
                if 'data' in result and 'id' in result['data']:
                    self.student_id = result['data']['id']
                return True, result.get('message', '登录成功')
            else:
                return False, result.get('message', '登录失败')
                
        except Exception as e:
            return False, f"请求错误: {str(e)}"
    
    def create_line(self):
        """创建跑步记录"""
        url = f"{CONFIG['BASE_URL']}/xcxapi/createLine/"
        data = {
            "student_id": self.student_id,
            "pass_point": []
        }
        
        try:
            resp = self.session.post(url, json=data, timeout=CONFIG['DEFAULT_TIMEOUT'])
            result = resp.json()
            
            if result.get('code') == 1 and 'data' in result:
                self.record_id = result['data'].get('record_id')
                return True, self.record_id
            return False, result.get('message', '创建失败')
        except Exception as e:
            return False, str(e)
    
    def upload_path(self, path_points):
        """上传轨迹"""
        url = f"{CONFIG['BASE_URL']}/xcxapi/uploadPathPointV3/"
        data = {
            "record_id": self.record_id,
            "path_point": path_points,
            "path_image": ""
        }
        
        try:
            encrypted = self.crypto.encrypt(data)
            resp = self.session.post(url, json={"a": encrypted}, timeout=CONFIG['DEFAULT_TIMEOUT'])
            result = resp.json()
            return result.get('code') == 1, result
        except Exception as e:
            return False, str(e)
    
    def check_record(self):
        """校验记录"""
        url = f"{CONFIG['BASE_URL']}/xcxapi/checkRecord/"
        data = {"record_id": self.record_id}
        
        try:
            encrypted = self.crypto.encrypt(data)
            resp = self.session.post(url, json={"a": encrypted}, timeout=CONFIG['DEFAULT_TIMEOUT'])
            result = resp.json()
            return result.get('code') == 1, result
        except Exception as e:
            return False, str(e)
    
    def submit_record(self):
        """提交最终结果"""
        url = f"{CONFIG['BASE_URL']}/xcxapi/updateRecordNew/"
        data = {"record_id": self.record_id}
        
        try:
            encrypted = self.crypto.encrypt(data)
            resp = self.session.post(url, json={"a": encrypted}, timeout=CONFIG['DEFAULT_TIMEOUT'])
            result = resp.json()
            return result.get('code') == 1, result
        except Exception as e:
            return False, str(e)

# ==================== 跑步模拟器 ====================
class RunningSimulator:
    def __init__(self, api):
        self.api = api
        self.points = []
        
        # 奉贤校区打卡点（可随机或固定）
        self.checkpoints = [
            {"name": "桥东", "lat": 30.830424, "lng": 121.501712},
            {"name": "38号点", "lat": 30.827536, "lng": 121.503933},
            {"name": "南大门", "lat": 30.828600, "lng": 121.505815}
        ]
    
    def generate_path(self, duration_minutes=12):
        """生成合理跑步轨迹"""
        import random
        
        # 根据时间生成适当数量的轨迹点（每3-5秒一个点）
        total_seconds = duration_minutes * 60
        num_points = total_seconds // random.randint(3, 5)
        
        # 简化的直线插值轨迹生成
        path = []
        start_time = int(time.time() * 1000)
        
        for i in range(num_points):
            # 在打卡点之间插值
            cp_index = min(i // (num_points // 3), 2)
            base_cp = self.checkpoints[cp_index]
            
            # 添加随机偏移模拟真实跑步
            lat_offset = random.uniform(-0.0002, 0.0002)
            lng_offset = random.uniform(-0.0002, 0.0002)
            
            path.append({
                "name": f"point_{i}",
                "lat": base_cp["lat"] + lat_offset,
                "lng": base_cp["lng"] + lng_offset,
                "timestamp": start_time + (i * 4000),  # 每4秒一个点
                "accuracy": random.randint(10, 20)
            })
        
        return path
    
    def simulate_running(self, duration=12):
        """模拟跑步过程，带倒计时"""
        print(f"\n🏃 开始模拟跑步（计划{duration}分钟）...")
        print("⚠️  期间请勿关闭程序\n")
        
        total_seconds = duration * 60
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            remaining = total_seconds - elapsed
            
            if remaining <= 0:
                break
            
            # 显示倒计时进度条
            progress = elapsed / total_seconds
            bar_len = 20
            filled = int(bar_len * progress)
            bar = '█' * filled + '░' * (bar_len - filled)
            
            mins, secs = divmod(int(remaining), 60)
            print(f"\r⏳ [{bar}] {mins:02d}:{secs:02d} ({int(progress*100)}%) | 模拟跑步中", 
                  end='', flush=True)
            
            time.sleep(1)
        
        print(f"\r{' ' * 60}\r✅ 跑步时间完成！")
        
        # 生成轨迹
        self.points = self.generate_path(duration)
        return True

# ==================== 主程序 ====================
def main():
    print("╔══════════════════════════════════════╗")
    print("║     ECUST 校园跑助手 v4.4            ║")
    print("║     Android 兼容版                   ║")
    print("╚══════════════════════════════════════╝")
    print(f"设备ID: {DEVICE_ID}")
    print(f"存储路径: {STORAGE_PATH}\n")
    
    # 初始化系统
    activation = ActivationSystem()
    api = CampusRunAPI()
    
    # 首次激活检查
    if not activation.is_activated():
        print("🔐 首次激活需要")
        print("1. 输入激活码")
        print("2. 输入管理员密钥")
        
        choice = SecureInput.get_input("选择 (1/2): ").strip()
        
        if choice == '1':
            code = SecureInput.get_input("激活码: ").strip().upper()
            if activation.activate(code):
                print("✅ 激活成功！")
            else:
                print("❌ 激活码无效或与本机不匹配")
                print(f"本机机器码: {DEVICE_ID}")
                print("请联系管理员获取激活码")
                input("\n按回车退出...")
                return
                
        elif choice == '2':
            key = SecureInput.get_password("管理员密钥: ")
            if key == CONFIG['ADMIN_SECRET']:
                activation.activate("ADMIN", is_admin=True)
                print("✅ 管理员模式激活！")
            else:
                print("❌ 密钥错误")
                input("\n按回车退出...")
                return
        else:
            print("无效选择")
            return
    else:
        print(f"✅ 已激活 ({'管理员' if activation.is_admin() else '普通用户'})")
    
    # 主菜单
    while True:
        print("\n" + "="*40)
        print("主菜单")
        print("="*40)
        print("1. 开始跑步")
        print("2. 查看设备信息")
        if activation.is_admin():
            print("3. 生成激活码（管理员）")
            print("4. 清除所有凭证（管理员）")
        print("0. 退出")
        
        choice = SecureInput.get_input("\n选择: ").strip()
        
        if choice == '1':
            # 登录流程
            print("\n📱 登录账号")
            phone = SecureInput.get_input("手机号: ").strip()
            password = SecureInput.get_password("密码: ")
            
            print("登录中...")
            success, msg = api.login(phone, password)
            if not success:
                print(f"❌ 登录失败: {msg}")
                continue
            
            print(f"✅ {msg}")
            if not api.student_id:
                api.student_id = int(SecureInput.get_input("请输入学号ID: "))
            
            # 创建记录
            print("创建跑步记录...")
            success, result = api.create_line()
            if not success:
                print(f"❌ 创建失败: {result}")
                continue
            
            print(f"✅ 记录ID: {result}")
            
            # 模拟跑步
            duration = int(SecureInput.get_input("跑步时长(分钟，建议10-15): ") or "12")
            if duration > 15:
                duration = 15
            
            simulator = RunningSimulator(api)
            simulator.simulate_running(duration)
            
            # 上传轨迹
            print("上传轨迹...")
            success, result = api.upload_path(simulator.points)
            if not success:
                print(f"❌ 上传失败: {result}")
                continue
            
            # 校验
            print("校验记录...")
            success, result = api.check_record()
            if not success:
                print(f"⚠️ 校验警告: {result}")
            
            # 提交
            print("提交最终结果...")
            success, result = api.submit_record()
            if success:
                print("🎉 跑步完成！数据已提交")
            else:
                print(f"❌ 提交失败: {result}")
        
        elif choice == '2':
            print(f"\n设备ID: {DEVICE_ID}")
            print(f"激活状态: {'是' if activation.is_activated() else '否'}")
            print(f"管理员: {'是' if activation.is_admin() else '否'}")
            print(f"激活时间: {activation.data.get('activate_time', 'N/A')}")
        
        elif choice == '3' and activation.is_admin():
            target_device = SecureInput.get_input("输入目标设备ID: ").strip()
            if target_device:
                code = activation.generate_activation_code(target_device)
                print(f"生成的激活码: {code}")
        
        elif choice == '4' and activation.is_admin():
            confirm = SecureInput.get_input("确认清除所有凭证？(y/n): ").lower()
            if confirm == 'y':
                activation.clear_activation()
                print("已清除，程序将退出")
                break
        
        elif choice == '0':
            break
    
    print("\n再见！")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序被中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        input("按回车退出...")
