# URL访问监控系统

这是一个用于监控URL访问状态的系统，支持定时检查和随机访问模式。

## 功能特点

- 定时监控URL状态
- 随机访问模式模拟真实用户行为
- 实时WebSocket推送结果
- 可视化监控界面

## 安装依赖

首先确保已安装Python 3.7或更高版本，然后安装项目依赖：

```bash
pip install -r requirements.txt
```

如果遇到权限问题，可以使用以下命令：

```bash
pip install --user -r requirements.txt
```

对于使用虚拟环境的用户，建议创建并激活虚拟环境：

```bash
apt update
apt install -y python3-venv
# 然后创建虚拟环境
python3 -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
pip install -r requirements.txt
```

下面给你一套 **在 Ubuntu 用 Nginx 把 8085 转发到 127.0.0.1:8005（WebSocket）** 的完整配置步骤——按顺序执行即可。

### 1) 安装并启动 Nginx

```bash
sudo apt update
sudo apt install -y nginx
sudo systemctl enable --now nginx
```

### 2) 写一个独立的站点配置

```bash
sudo tee /etc/nginx/sites-available/url_time.conf >/dev/null <<'EOF'
# 处理 WebSocket 的 Upgrade 头
map $http_upgrade $connection_upgrade {
  default upgrade;
  ''      close;
}

server {
    listen 8085;
    server_name _;

    # 前端连的就是 ws://<你的IP或域名>:8085/ws
    location /ws {
        proxy_pass http://127.0.0.1:8005;   # 后端实际监听在 127.0.0.1:8005
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;

        # 可选：长连接超时
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }
}
EOF

# 启用该站点
sudo ln -sf /etc/nginx/sites-available/url_time.conf /etc/nginx/sites-enabled/url_time.conf
#（可选）如果有 default 站点且端口冲突，先禁用
# sudo rm -f /etc/nginx/sites-enabled/default
```

### 3) 校验并加载配置

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 4) 放通防火墙 / 云安全组

```bash
# 本机防火墙（如启用 UFW）：
sudo ufw allow 8085/tcp
# 云厂商安全组：放行 8085 入站（在控制台设置）
```

### 5) 快速自检

```bash
# 确认 Nginx 在 8085 监听
ss -lntp | grep :8085

# 确认后端仍在本地 8005 监听
ss -lntp | grep :8005
```
---


## 运行服务

```bash
python server.py
```
（可选）用 systemd 跑时，改成用新的 venv 路径
```bash
sudo tee /etc/systemd/system/url_time.service >/dev/null <<'EOF'
[Unit]
Description=URL Access Monitor (url_time)
After=network.target

[Service]
User=root
WorkingDirectory=/root/url_time
Environment="PATH=/root/url_time/venv/bin"
ExecStart=/root/url_time/venv/bin/python /root/url_time/server.py
Restart=always
RestartSec=3
Environment="PYTHONIOENCODING=utf-8"

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now url_time
journalctl -u url_time -f
```
服务启动后，会在控制台输出HTTP和WebSocket服务器的访问地址。

## 使用说明

1. 打开浏览器访问显示的HTTP地址（通常是 http://127.0.0.1:8000）
2. 在界面中配置监控参数
3. 点击"开始定时监控"或"开始随机访问"按钮启动监控任务
4. 实时查看监控结果和日志

## 配置文件

config.json 文件包含以下配置项：

- urls: 要监控的URL列表
- scheduled_mode: 定时监控模式配置
- random_mode: 随机访问模式配置
- realistic_mode: 真实访问模拟配置

## 网络端口

- HTTP服务器默认使用端口范围：8000-8004
- WebSocket服务器默认使用端口范围：8005-8009

如果默认端口被占用，系统会自动尝试下一个可用端口。

## 问题排查

如果遇到连接问题，请检查：

1. 确保端口没有被其他程序占用
2. 检查防火墙设置
3. 查看日志文件 url_monitor.log 获取详细信息

## 常见问题

### WebSocket连接频繁断开重连

这通常是由于网络问题或端口冲突导致的。请确保：

1. 没有其他程序占用WebSocket端口（8005-8009）
2. 防火墙没有阻止相关端口的通信
3. 客户端和服务器之间网络连接稳定

### 无法加载配置

如果页面没有显示URL列表，请检查：

1. config.json文件是否存在且格式正确
2. 服务器是否有权限读取config.json文件
3. 浏览器控制台是否有相关错误信息