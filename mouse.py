import sys
import time

try:
    import hid
except ImportError:
    print("错误: 请先安装 hidapi 库。在终端中运行: pip install hidapi")
    sys.exit(1)

def get_mouse_battery():
    # Nordic 1K NRF 接收器的 VID 和 PID
    VENDOR_ID = 0x1915
    PRODUCT_ID = 0x0723

    devices = hid.enumerate()
    target_path = None
    for d in devices:
        if d['vendor_id'] == VENDOR_ID and d['product_id'] == PRODUCT_ID:
            # 严格匹配鼠标的 FF0A 秘密通道 (65290)
            if d['usage_page'] == 0xff0a or d['usage_page'] == 65290:
                target_path = d['path']
                break
                
    if not target_path:
        print("未找到兼容的 1K NRF 鼠标接收器控制通道。")
        return

    try:
        device = hid.device()
        device.open_path(target_path)
        
        response_found = False
        offline_detected = False
        start_time = time.time()
        last_write_time = 0
        
        print("正在发送唤醒指令并持续侦听鼠标电量...\n")
        
        # 最多持续尝试 3 秒
        while time.time() - start_time < 3.0:  
            
            # 每隔 300 毫秒，轮流向 1K通道(0x01) 和 高刷通道(0x41) 发送查询指令
            current_time = time.time()
            if current_time - last_write_time >= 0.3:
                # 1. 发送 1K 模式查询包 (首字节 0x00 为虚设ID，载荷首字节为 1，尾校验和为 30)
                query_packet_1k = [0x00, 1, 0, 129, 1] + [0] * 58 + [30]
                device.write(query_packet_1k)
                
                # 2. 发送 高刷 4K/8K 模式查询包 (首字节 0x00 为虚设ID，载荷首字节为 65，尾校验和为 222)
                query_packet_high_hz = [0x00, 65, 0, 129, 1] + [0] * 58 + [222]
                device.write(query_packet_high_hz)
                
                last_write_time = current_time
                
            # 持续高频读取接收缓冲区 (50ms 超时)
            response = device.read(64, timeout_ms=50) 
            if response:
                hex_data = [hex(b) for b in response]
                print(f"[收到回包]: {hex_data}")
                
                # 状态一：高刷 4K/8K 模式在线电量包 (首字节为 65 [0x41])
                if response[0] == 65 and len(response) >= 7:
                    if response[2] == 140:
                        battery_val = response[6]  # 电量位于第 7 字节
                        
                        print("\n============= 鼠标无线状态 =============")
                        print(f"当前电量: {battery_val}% 🔋")
                        print("连接状态: 鼠标在线 (4K/8K 高刷模式) 📶")
                        print("========================================")
                        response_found = True
                        break  # 成功获取，完美退出循环！
                
                # 状态二：标准 1K 模式在线电量包 (首字节为 74 [0x4a])
                elif response[0] == 74 and len(response) >= 7:
                    if response[2] == 140:
                        battery_val = response[6]  # 电量位于第 7 字节
                        
                        print("\n============= 鼠标无线状态 =============")
                        print(f"当前电量: {battery_val}% 🔋")
                        print("连接状态: 鼠标在线 (1K 标准模式) 📶")
                        print("========================================")
                        response_found = True
                        break  # 成功获取，完美退出循环！
                        
                # 状态三：捕获到接收器的离线应答包 (首字节为 1，第 5 字节为 8)
                elif response[0] == 1 and len(response) >= 5:
                    if response[2] == 140 and response[4] == 8:
                        offline_detected = True  # 记录离线，继续等待鼠标被唤醒
                        
        if not response_found:
            if offline_detected:
                print("\n============= 鼠标无线状态 =============")
                print("连接状态: 鼠标当前处于【离线或休眠】状态 💤")
                print("提示: 请移动或点击一下鼠标将其唤醒，然后重新运行。")
                print("========================================")
            else:
                print("\n未能在限定时间内捕获到包含鼠标电量的数据包。")
            
    except Exception as e:
        print(f"通信过程中出错: {e}")
    finally:
        device.close()

if __name__ == "__main__":
    get_mouse_battery()