# Trae Solo 云环境文件下载方法

## 需求场景
在 Trae Solo 云环境中开发完成后，需要把 APK 或其他大文件下载到本地。

## 解决方案

### 步骤 1：把文件和下载页面放到可访问目录
```bash
# 复制 APK 和下载页面到 dist 目录
cp /workspace/xxx.apk /workspace/frontend/dist/
cp /workspace/download.html /workspace/frontend/dist/
```

### 步骤 2：启动 HTTP 服务器
```bash
cd /workspace/frontend/dist
python3 -m http.server 16003 &
sleep 2
```

### 步骤 3：用 OpenPreview 打开下载页面
```typescript
OpenPreview({
  command_id: "服务器启动命令的ID",
  preview_url: "http://localhost:16003/download.html"
})
```

## 注意事项

- 端口选择：16000 端口被 Trae 系统占用，选择 16001-16009 之间的端口
- 服务器后台运行：使用 `nohup ... &` 确保服务器在后台运行
- 下载页面添加提示：告知用户如果浏览器直接预览文件，如何另存为

## 示例下载页面模板

```html
<a href="xxx.apk" class="download-btn" download="xxx.apk">
    点击下载 APK
</a>

<p style="margin-top: 20px; color: #888; font-size: 13px;">
    如果浏览器直接预览了APK，请长按链接选择"另存为"或"下载"
</p>
```

## 适用场景
- APK 下载
- 大文件传输（base64 太大不适合聊天传输时）
- 临时分享文件给用户
