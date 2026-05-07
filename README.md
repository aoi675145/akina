```yaml
curl -L -o /tmp/ffmpeg.tar.xz https://github.com/akina005/akina/releases/download/ffmpeg/ffmpeg-release-amd64-static.tar.xz
mkdir -p /tmp/ffmpeg-static
tar -xf /tmp/ffmpeg.tar.xz -C /tmp/ffmpeg-static --strip-components=1
sudo ln -sf /tmp/ffmpeg-static/ffmpeg /usr/local/bin/ffmpeg
sudo ln -sf /tmp/ffmpeg-static/ffprobe /usr/local/bin/ffprobe
ffmpeg -version
```

---

```yaml
        wget -q https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip
        mkdir -p xray-bin
        unzip -oq Xray-linux-64.zip -d xray-bin
        chmod +x xray-bin/xray
        sudo mv xray-bin/xray /usr/local/bin/xray
