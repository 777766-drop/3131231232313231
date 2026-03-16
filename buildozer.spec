[app]

# 应用标题和包名
title = ECUST Run
package.name = ecustrun
package.domain = org.ecust

# 源文件目录（包含你的 main.py）
source.dir = .

# 包含的文件扩展名
source.include_exts = py,png,jpg,kv,atlas,ttf,txt,crt,pem

# 版本号
version = 4.4

# 依赖项（关键：包含SSL证书和加密库）
requirements = python3==3.10.12,hostpython3==3.10.12,requests,pycryptodome,certifi,charset-normalizer,idna,urllib3,Pygments

# 防止Android 10+的分区存储限制
android.private_storage = True
android.permission_write_external_storage = True

# 图标（如果有的话）
# icon.filename = %(source.dir)s/icon.png

# 是否全屏（False显示状态栏）
fullscreen = 0

# 屏幕方向（竖屏）
orientation = portrait

# 服务配置（保持后台运行，可选）
# services = CampusRun: campus_service.py

[buildozer]

# 构建目录（避免中文路径）
build_dir = ./.buildozer

# 打包模式（release/debug）
build_mode = debug

# Android 特定配置
log_level = 2
warn_on_root = 1

[app:android]

# Android API 和 NDK 版本（关键：25b NDK 兼容性最好）
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.ndk_path = 

# 目标架构（arm64-v8a是主流，armeabi-v7a兼容旧设备）
android.archs = arm64-v8a, armeabi-v7a

# 关键权限（网络、存储、防止休眠）
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,WAKE_LOCK,FOREGROUND_SERVICE

# 防止Android 11+的权限拒绝导致的闪退
android.storage_permissions = True

# 禁用API检查（防止某些Python库调用反射时崩溃）
android.allow_backup = False

# SSL证书处理（防止"SSL: CERTIFICATE_VERIFY_FAILED"闪退）
android.add_compile_options = --release
android.add_gradle_repositories = mavenCentral(),google()
android.gradle_dependencies = com.android.support:support-compat:28.0.0,org.conscrypt:conscrypt-android:2.5.2

# 如果需要在Android 10+访问/sdcard/Download
android.manifest.application_attributes = android:requestLegacyExternalStorage="true"

# 避免某些x86设备上的崩溃
android.skip_update = False

# 启动模式（防止重复实例）
android.manifest.launch_mode = singleTask

[app:android:entry]

# 主入口（确保你的Python文件叫main.py，或者修改这里）
android.entrypoint = org.kivy.android.PythonActivity
android.python_name = ecustrun

[app:android:meta_data]

# 支持刘海屏/全面屏
android.meta_data = android.max_aspect=2.4

[app:android:build]

# 防止Java堆内存不足导致的构建失败
android.gradle_options = org.gradle.jvmargs=-Xmx4096M

# 构建工具版本
android.build_tools_version = 33.0.0