[app]

# 应用基本信息
title = ECUST Run
package.name = ecustrun
package.domain = org.ecust

# 源文件
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,txt,crt,pem,json

# 版本号
version = 4.4

# 依赖项（关键：用pycryptodomex代替pycryptodome，避免Android编译错误）
requirements = python3==3.10.12,hostpython3==3.10.12,requests,pycryptodomex,certifi,charset-normalizer,idna,urllib3

# 屏幕设置
orientation = portrait
fullscreen = 0

# 防止服务冲突
services = 

[app:android]

# Android API 和 NDK 配置
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b

# 关键修复：允许Buildozer自动下载并安装缺失的build-tools（包含aidl）
android.skip_update = False
android.accept_sdk_license = True

# 架构
android.archs = arm64-v8a, armeabi-v7a

# 必需权限
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,WAKE_LOCK,FOREGROUND_SERVICE

# 允许备份
android.allow_backup = False

# 禁用某些检查以避免错误
android.manifest.application_attributes = android:requestLegacyExternalStorage="true"

[buildozer]

# 关键：详细日志才能看到真实的许可证/下载错误
log_level = 2

# 禁用root警告（GitHub Actions是root用户）
warn_on_root = 0

# 构建目录
build_dir = ./.buildozer

# 二进制输出目录
bin_dir = ./bin

# 指定spec文件路径
source.include_exts = py,png,jpg,kv,atlas,ttf,txt,crt,pem,json,xml,mo,vs,fs,glsl
