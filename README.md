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
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
pip install -r requirements.txt
```

## 运行服务

```bash
python server.py
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