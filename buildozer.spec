[app]
title = ECUST Run
package.name = ecustrun
package.domain = org.ecust
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,txt,json
version = 4.5

# 依赖项（最关键）
requirements = python3,hostpython3,kivy,requests,pycryptodomex,certifi,charset-normalizer,idna,urllib3

orientation = portrait
fullscreen = 0

[app:android]
# 安卓 API 配置
android.api = 31
android.minapi = 21
android.ndk = 23b
android.accept_sdk_license = True

# 权限：必须开启网络和存储
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# 架构：目前只编译 arm64 效率最高且最稳
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
