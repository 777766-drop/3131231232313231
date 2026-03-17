[app]
title = ECUST Run
package.name = ecustrun
package.domain = org.ecust
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,txt,json
version = 4.4

# 删掉所有版本号，只留库名
requirements = python3,hostpython3,kivy,requests,pycryptodomex,certifi,charset-normalizer,idna,urllib3

orientation = portrait
fullscreen = 0

[app:android]
# 修改为 31，这是目前 GitHub Actions 环境下最稳的 API 版本
android.api = 31
android.minapi = 21
# NDK 建议使用 23b，和 API 31 配合最好
android.ndk = 23b
android.skip_update = False
android.accept_sdk_license = True

# 权限
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,WAKE_LOCK

# 暂时只打这一个包，确保成功
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
