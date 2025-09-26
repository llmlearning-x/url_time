import asyncio
import time
import requests
import logging
import schedule
import random
import json
from datetime import datetime
import threading
import os
import websockets
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import io


# 全局变量
jobs_running = False
random_mode_running = False
websocket_clients = set()
# 保存事件循环的全局变量
event_loop = None

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

# 存储前端传递的配置参数
frontend_config = {}

# 添加全局变量用于存储访问计数
access_counts = {}

# 定义HTTP服务器的备选端口
HTTP_PORTS = [8000, 8001, 8002, 8003, 8004]
# 定义WebSocket服务器的备选端口
WS_PORTS = [8005, 8006, 8007, 8008, 8009]


class WebRequestHandler(BaseHTTPRequestHandler):
    # 设置日志记录器
    def log_message(self, format, *args):
        logging.info("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format % args))
    
    def do_GET(self):
        if self.path == '/':
            self.serve_file('index.html', 'text/html')
        elif self.path == '/api/config':
            self.serve_config()
        else:
            # 尝试提供静态文件
            file_path = self.path[1:]  # 移除开头的 '/'
            if os.path.exists(file_path) and not os.path.isdir(file_path):
                content_type = self.get_content_type(file_path)
                self.serve_file(file_path, content_type)
            else:
                self.send_error(404, "File not found")
    
    def do_POST(self):
        # 获取请求体内容
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        if self.path == '/api/start/scheduled':
            try:
                config = json.loads(post_data) if post_data else {}
                frontend_config.update(config)
                self.start_scheduled_mode()
            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON")
        elif self.path == '/api/start/random':
            try:
                config = json.loads(post_data) if post_data else {}
                frontend_config.update(config)
                self.start_random_mode()
            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON")
        elif self.path == '/api/stop':
            self.stop_all_modes()
        else:
            self.send_error(404, "Endpoint not found")
    
    def serve_file(self, file_path, content_type):
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error serving file: {str(e)}")
    
    def serve_config(self):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(config, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.send_error(500, f"Error reading config: {str(e)}")
    
    def start_scheduled_mode(self):
        global jobs_running
        jobs_running = True
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status": "scheduled mode started"}')
        
        # 在新线程中运行定时任务
        thread = threading.Thread(target=self.run_scheduled_mode)
        thread.daemon = True
        thread.start()
    
    def start_random_mode(self):
        global random_mode_running
        random_mode_running = True
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status": "random mode started"}')
        
        # 在新线程中运行随机任务
        thread = threading.Thread(target=self.run_random_mode)
        thread.daemon = True
        thread.start()
    
    def stop_all_modes(self):
        global jobs_running, random_mode_running
        jobs_running = False
        random_mode_running = False
        
        # 清除所有计划任务
        schedule.clear()
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status": "all modes stopped"}')
    
    def run_scheduled_mode(self):
        global jobs_running
        
        # 优先使用前端传递的参数，否则使用配置文件中的参数
        if 'scheduled_mode' in frontend_config and 'check_interval_minutes' in frontend_config['scheduled_mode']:
            check_interval_minutes = frontend_config['scheduled_mode']['check_interval_minutes']
        else:
            try:
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                check_interval_minutes = config.get('scheduled_mode', {}).get('check_interval_minutes', 1)
            except:
                check_interval_minutes = 1
        
        # 启动时先跑一次
        if jobs_running:
            self.check_random_url()
        
        # 设置定时任务
        schedule.every(check_interval_minutes).minutes.do(self.check_random_url)
        
        # 运行定时任务循环
        while jobs_running:
            schedule.run_pending()
            time.sleep(1)
    
    def run_random_mode(self):
        global random_mode_running
        
        # 优先使用前端传递的参数，否则使用配置文件中的参数
        if 'random_mode' in frontend_config:
            random_config = frontend_config['random_mode']
            total_visits = random_config.get('total_visits', 10)
            total_time_seconds = random_config.get('total_time_seconds', 300)
        else:
            try:
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                total_visits = config.get('random_mode', {}).get('total_visits', 10)
                total_time_seconds = config.get('random_mode', {}).get('total_time_seconds', 300)
            except:
                total_visits = 10
                total_time_seconds = 300
        
        # 优先使用前端传递的参数，否则使用配置文件中的参数
        if 'realistic_mode' in frontend_config:
            realistic_config = frontend_config['realistic_mode']
            min_delay = realistic_config.get('min_delay_seconds', 1)
            max_delay = realistic_config.get('max_delay_seconds', 5)
        else:
            try:
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                min_delay = config.get('realistic_mode', {}).get('min_delay_seconds', 1)
                max_delay = config.get('realistic_mode', {}).get('max_delay_seconds', 5)
            except:
                min_delay = 1
                max_delay = 5
        
        logging.info("开始随机访问模式")
        logging.info(f"总访问次数: {total_visits}")
        logging.info(f"总时间: {total_time_seconds} 秒")
        
        intervals = []
        # 生成随机时间间隔
        for i in range(total_visits):
            # 生成随机时间点（相对于开始时间的秒数）
            interval = random.uniform(0, total_time_seconds)
            intervals.append(interval)
        
        # 按时间排序
        intervals.sort()
        
        start_time = time.time()
        for i, interval in enumerate(intervals):
            if not random_mode_running:
                break
                
            # 等待到下一个时间点
            sleep_time = interval - (time.time() - start_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            # 检查随机URL
            if random_mode_running:
                self.check_random_url()
                logging.info(f"已完成 {i+1}/{total_visits} 次访问")
                # 添加随机延迟
                delay = random.uniform(min_delay, max_delay)
                time.sleep(delay)
        
        random_mode_running = False
        logging.info("随机访问模式结束")
    
    def check_random_url(self):
        # 从配置文件加载URL列表
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            urls = config.get('urls', [])
        except:
            urls = [
                "https://www.modelscope.cn/studios/llmlearningX/DeepSeek-V3.1-Demo",
                "https://www.modelscope.cn/studios/llmlearningX/Wan2.2-Animate-learning",
            ]
        
        # 初始化访问计数器（如果不存在）
        if not access_counts:
            for url in urls:
                access_counts[url] = 0
        
        # 从配置文件加载真实访问模拟配置
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            user_agents = config.get('realistic_mode', {}).get('user_agents', [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59"
            ])
        except:
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59"
            ]
        
        if not urls:
            return
            
        # 随机选择一个URL
        url = random.choice(urls)
        
        # 发送请求
        try:
            start = time.time()
            headers = {
                "User-Agent": random.choice(user_agents),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            resp = requests.get(url, timeout=10, headers=headers)
            elapsed = time.time() - start
            status = resp.status_code
            
            # 增加访问计数
            if url in access_counts:
                access_counts[url] += 1
            else:
                access_counts[url] = 1
                
            if 200 <= status < 300:
                message = f"[{url}] OK — status {status}, time {elapsed:.3f}s"
                logging.info(message)
                # 通过WebSocket发送消息，包含访问次数
                self.broadcast_websocket({
                    "level": "INFO",
                    "message": message,
                    "url": url,
                    "status": status,
                    "elapsed": elapsed,
                    "access_count": access_counts[url]
                })
            else:
                message = f"[{url}] 非 2xx 响应 — status {status}, time {elapsed:.3f}s"
                logging.warning(message)
                # 通过WebSocket发送消息，包含访问次数
                self.broadcast_websocket({
                    "level": "WARNING",
                    "message": message,
                    "url": url,
                    "status": status,
                    "elapsed": elapsed,
                    "access_count": access_counts[url]
                })
        except Exception as e:
            message = f"[{url}] 访问异常 — {e}"
            logging.error(message)
            # 通过WebSocket发送消息，包含访问次数
            self.broadcast_websocket({
                "level": "ERROR",
                "message": message,
                "url": url,
                "access_count": access_counts.get(url, 0)
            })

    def broadcast_websocket(self, data):
        """广播WebSocket消息"""
        global event_loop
        if websocket_clients and event_loop:
            message = json.dumps(data, ensure_ascii=False)
            disconnected = set()
            for client in list(websocket_clients):  # 使用list避免在迭代时修改集合
                try:
                    # 使用保存的事件循环运行协程
                    coroutine = client.send(message)
                    future = asyncio.run_coroutine_threadsafe(coroutine, event_loop)
                    # 等待结果（可选，增加超时）
                    future.result(timeout=1)
                except Exception as e:
                    logging.error(f"WebSocket发送消息失败: {e}")
                    disconnected.add(client)
            
            # 移除断开连接的客户端
            for client in disconnected:
                websocket_clients.discard(client)
                try:
                    coroutine = client.close()
                    future = asyncio.run_coroutine_threadsafe(coroutine, event_loop)
                    future.result(timeout=1)
                except:
                    pass

    def get_content_type(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        content_types = {
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml'
        }
        return content_types.get(ext, 'application/octet-stream')


# 全局变量用于存储事件循环
main_loop = None

# WebSocket处理函数
async def websocket_handler(websocket):
    # 添加客户端到集合
    websocket_clients.add(websocket)
    logging.info(f"新的WebSocket连接: {websocket.remote_address}")
    
    try:
        async for message in websocket:
            # 这里可以处理来自客户端的消息
            pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        # 移除客户端
        websocket_clients.discard(websocket)
        logging.info(f"WebSocket连接已断开: {websocket.remote_address}")

def run_http_server(port=8000):
    """运行HTTP服务器"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, WebRequestHandler)
    logging.info(f"HTTP服务器启动，监听端口 {port}")
    logging.info(f"在浏览器中访问 http://localhost:{port}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("HTTP服务器已停止")
        httpd.server_close()


async def main():
    global event_loop
    # 保存事件循环引用
    event_loop = asyncio.get_running_loop()
    
    # 尝试启动HTTP服务器，使用备选端口
    http_port = None
    http_thread = None
    
    for port in HTTP_PORTS:
        try:
            # 启动HTTP服务器（在单独的线程中）
            http_thread = threading.Thread(target=run_http_server, args=(port,))
            http_thread.daemon = True
            http_thread.start()
            http_port = port
            logging.info(f"成功在端口 {port} 上启动HTTP服务器")
            break
        except OSError as e:
            if e.errno == 10048:  # 端口被占用
                logging.warning(f"端口 {port} 已被占用，尝试下一个端口...")
                continue
            else:
                raise e
    
    if http_port is None:
        logging.error("无法在任何备选端口上启动HTTP服务器")
        return
    
    # 尝试启动WebSocket服务器，使用备选端口
    ws_port = None
    for port in WS_PORTS:
        try:
            logging.info(f"WebSocket服务器启动，尝试监听端口 {port}")
            # 只绑定IPv4地址，避免与IPv6地址冲突
            async with websockets.serve(websocket_handler, "127.0.0.1", port):
                ws_port = port
                logging.info(f"成功在端口 {port} 上启动WebSocket服务器")
                # 等待服务器完成
                await asyncio.Future()
            break
        except OSError as e:
            if e.errno == 10048:  # 端口被占用
                logging.warning(f"WebSocket端口 {port} 已被占用，尝试下一个端口...")
                continue
            else:
                raise e
    
    if ws_port is None:
        logging.error("无法在任何备选端口上启动WebSocket服务器")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("服务器已停止")
    except OSError as e:
        if e.errno == 10048:
            logging.error("端口已被占用，请确保没有其他实例正在运行，或更改端口号")
        else:
            logging.error(f"服务器启动失败: {e}")
