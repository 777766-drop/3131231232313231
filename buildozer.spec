[app]
title = ECUST Run
package.name = ecustrun
package.domain = org.ecust
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,txt,json
version = 4.5

# 必须包含这些库，否则华为系统会闪退
requirements = python3,hostpython3,kivy,requests,pycryptodomex,certifi,urllib3,openssl

orientation = portrait
fullscreen = 0

[app:android]
# 针对鸿蒙4优化的API
android.api = 31
android.minapi = 21
android.ndk = 23b
android.accept_sdk_license = True

# 核心权限
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK

# 麒麟 9010 架构支持
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
