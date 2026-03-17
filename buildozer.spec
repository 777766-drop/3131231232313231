[app]

# 项目基本信息
title = ECUST Run
package.name = ecustrun
package.domain = org.ecust
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,txt,json
version = 4.4

# 依赖库：删除了 python3 的版本号限制，增加稳定性
requirements = python3,hostpython3,kivy,requests,pycryptodomex,certifi,charset-normalizer,idna,urllib3

orientation = portrait
fullscreen = 0

[app:android]

# 核心版本配置：使用最稳定的 API 31 和 NDK 23b 组合
android.api = 31
android.minapi = 21
android.ndk = 23b
android.skip_update = False
android.accept_sdk_license = True

# 权限申请
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,WAKE_LOCK

# 架构：先只编译 arm64-v8a，确保打包成功率
android.archs = arm64-v8a

# 移除所有手动指定的 android.sdk_path 和 android.ndk_path
# 让 Buildozer 在 GitHub Actions 环境中自动下载

[buildozer]
log_level = 2
warn_on_root = 1
