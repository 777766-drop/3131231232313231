name: Build Android APK

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-22.04

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          sudo apt update
          sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
          # 关键：锁定 Cython 版本并安装 buildozer
          pip install "Cython<3.0" buildozer virtualenv

      - name: Build with Buildozer
        run: |
          # 这里的 yes 会自动同意 SDK 协议
          yes | buildozer android debug

      - name: Upload APK
        uses: actions/upload-artifact@v4
        with:
          name: my-android-app
          path: bin/*.apk
