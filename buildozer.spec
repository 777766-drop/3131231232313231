[app]
title = ECUST Run
package.name = ecustrun
package.domain = org.ecust
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,txt,json
version = 4.5

# 关键修复：添加sdl2和android防止黑屏
requirements = python3,hostpython3,kivy==2.2.1,requests,pycryptodomex,certifi,urllib3,openssl,pyjnius,android,sdl2

orientation = portrait
fullscreen = 0
android.presplash_color = #2c3e50  # 深色启动背景，避免白屏闪烁

[app:android]
android.api = 31
android.minapi = 21
android.ndk = 23b
android.build_tools = 33.0.0  # 明确build-tools版本
android.accept_sdk_license = True

# 权限：必须包含存储权限，否则Android 11+闪退
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# 架构：仅arm64-v8a减少包体积，避免x86模拟器问题
android.archs = arm64-v8a

# 防止黑屏：禁用某些优化，确保Kivy渲染
android.enable_androidx = True
android.add_aars = 
android.gradle_dependencies = 

# 如果还有黑屏，添加调试标志
android.logcat = 1

[buildozer]
log_level = 2
warn_on_root = 1
