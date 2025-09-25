# URL访问监控系统

一个用于监控多个URL可访问性的Python应用程序。支持定时监控和随机访问模式，并提供Web界面进行配置和实时查看监控结果。

## 功能特点

- **定时监控模式**：按设定的时间间隔循环检查URL可访问性
- **随机访问模式**：在指定时间段内随机访问URL，模拟真实用户行为
- **真实访问模拟**：使用随机User-Agent和请求头，添加随机延迟
- **Web界面**：提供友好的Web界面进行配置和查看监控结果
- **实时日志**：通过WebSocket实时推送访问日志到前端
- **配置管理**：通过config.json文件管理所有配置参数

## 技术架构

- **后端**：Python + websockets + asyncio
- **前端**：HTML + CSS + JavaScript
- **通信**：WebSocket实时通信
- **部署**：HTTP服务器(端口8000) + WebSocket服务器(端口8001)

## 安装依赖

首先确保已安装Python 3.7+，然后安装依赖：

```bash
pip install -r requirements.txt
```

## 配置文件

项目使用`config.json`文件进行配置，包含以下主要配置项：

- `urls`: 要监控的URL列表
- `scheduled_mode`: 定时监控模式配置
  - `check_interval_minutes`: 检查间隔（分钟）
- `random_mode`: 随机访问模式配置
  - `total_visits`: 总访问次数
  - `total_time_seconds`: 总时间（秒）
- `realistic_mode`: 真实访问模拟配置
  - `user_agents`: User-Agent列表
  - `min_delay_seconds`: 最小延迟（秒）
  - `max_delay_seconds`: 最大延迟（秒）

## 运行项目

```bash
python server.py
```

然后在浏览器中访问 http://localhost:8000

## 使用方法

1. 打开Web界面
2. 根据需要修改配置参数：
   - 定时检查间隔
   - 随机访问总次数
   - 随机访问总时间
   - 最小延迟和最大延迟
3. 点击相应的启动按钮开始监控：
   - "启动定时监控"：按设定间隔循环检查
   - "启动随机监控"：在指定时间内随机访问
   - "停止所有监控"：停止所有监控任务
4. 在日志区域查看实时访问结果

## 项目结构

```
url_time/
├── server.py          # 主服务器文件
├── index.html         # 前端界面
├── config.json        # 配置文件
├── requirements.txt   # 依赖列表
└── README.md          # 说明文档
```

## 注意事项

- 确保端口8000和8001未被其他程序占用
- 前端配置参数会覆盖config.json中的默认配置
- 日志同时输出到控制台和浏览器界面
- 支持通过Web界面动态调整配置参数