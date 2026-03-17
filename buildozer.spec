[app]
title = ECUST Run
package.name = ecustrun
package.domain = org.ecust
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,txt,json
version = 4.4

# 删掉了具体的 python 版本号，由 Buildozer 自动选择最匹配的
# 增加了六个基础依赖，确保编译环境更稳
requirements = python3,hostpython3,requests,pycryptodomex,certifi,charset-normalizer,idna,urllib3

orientation = portrait
fullscreen = 0

# (Android 特定配置)
android.api = 33
android.minapi = 21
# 删掉了手动指定的 sdk/ndk 路径，让系统自动下载到默认位置
android.ndk = 25b
android.skip_update = False
android.accept_sdk_license = True

# 权限设置
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,WAKE_LOCK

# 先只保留 arm64-v8a 提高打包成功率，如果之后需要老手机支持再加 armeabi-v7a
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
