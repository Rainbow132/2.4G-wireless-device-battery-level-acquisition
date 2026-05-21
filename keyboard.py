import sys
import time

try:
    import hid
except ImportError:
    print("错误: 请先安装 hidapi 库。在终端中运行: pip install hidapi")
    sys.exit(1)

def get_wireless_battery():
    # 迈从/狼蛛 Compx 2.4G 无线接收器的 VID 和 PID
    VENDOR_ID = 0x3554
    PRODUCT_ID = 0xfa09

    devices = hid.enumerate()
    target_path = None
    for d in devices:
        if d['vendor_id'] == VENDOR_ID and d['product_id'] == PRODUCT_ID:
            # 严格锁定 0xff02 秘密自定义通信通道
            if d['usage_page'] == 0xff02 or d['usage_page'] == 65282:
                target_path = d['path']
                break
                
    if not target_path:
        print("未找到包含 0xff02 通道的无线设备，请确认无线接收器已插好。")
        return

    try:
        device = hid.device()
        device.open_path(target_path)
        
        # 1. 发送我们验证成功、最稳定的无线握手/查询指令（指令一）
        query_packet = [0x13, 0x05, 0x01] + [0] * 16 + [0x19]
        device.write(query_packet)
        
        # 2. 连续读取所有回包，直到抓取到以 13 0A 开头的状态/电量包
        response_found = False
        start_time = time.time()
        
        print("正在等待并过滤电量数据包...\n")
        
        while time.time() - start_time < 2.0:  # 最多读取 2 秒，超时退出
            # 100 毫秒超时，进行快速循环读取
            response = device.read(64, timeout_ms=100) 
            if response:
                # 打印所有接收到的原始数据包，方便观察多包应答过程
                hex_data = [hex(b) for b in response]
                print(f"[收到回包]: {hex_data}")
                
                # 匹配电量/状态包的特征：首字节为 0x13，第二字节为 0x0a
                if response[0] == 0x13 and response[1] == 0x0a:
                    battery_val = response[6]     # 第 7 字节：电量百分比
                    connect_status = response[7]  # 第 8 字节：连接状态
                    
                    print("\n============= 键盘无线状态 =============")
                    print(f"当前电量: {battery_val}%")
                    if connect_status == 1:
                        print("连接状态: 2.4G 无线已连接 📶")
                    else:
                        print("连接状态: 离线或休眠")
                    print("========================================")
                    response_found = True
                    break
                    
        if not response_found:
            print("\n未能在限定时间内捕获到以 13 0A 开头的电量数据包。")
            
    except Exception as e:
        print(f"通信过程中出错: {e}")
    finally:
        device.close()

if __name__ == "__main__":
    get_wireless_battery()