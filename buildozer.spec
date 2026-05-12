[app]
title = FastDrop
package.name = fastdrop
package.domain = org.fastdrop

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0

requirements = python3,kivy==2.3.0,plyer,zeroconf,pillow,ifaddr

orientation = portrait
fullscreen = 0

android.permissions = INTERNET, ACCESS_NETWORK_STATE, ACCESS_WIFI_STATE, CHANGE_WIFI_MULTICAST_STATE, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, READ_MEDIA_IMAGES, READ_MEDIA_VIDEO, READ_MEDIA_AUDIO

# Pin specific versions to avoid license issues
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

# Pin build-tools to a stable version
android.build_tools_version = 33.0.2

p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
