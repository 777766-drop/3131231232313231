[app]

title = ECUST Run
package.name = ecustrun
package.domain = org.ecust

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,txt,json

version = 4.4

requirements = python3==3.10.12,hostpython3==3.10.12,requests,pycryptodomex,certifi,charset-normalizer,idna,urllib3

orientation = portrait
fullscreen = 0

[app:android]

android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b

# 关键：必须显式设置路径，让 Buildozer 找到预装的 SDK
android.sdk_path = ~/.buildozer/android/platform/android-sdk
android.ndk_path = ~/.buildozer/android/platform/android-ndk-r25b

# 关键：允许自动更新和接受 license
android.skip_update = False
android.accept_sdk_license = True

android.archs = arm64-v8a, armeabi-v7a
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,WAKE_LOCK

[buildozer]

log_level = 2
warn_on_root = 0
build_dir = ./.buildozer
bin_dir = ./bin
