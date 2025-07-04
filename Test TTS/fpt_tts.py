import requests
import time # Thêm thư viện time để chờ
import json

# --- Cấu hình ---
API_KEY = ""  # Thay bằng API key MỚI của bạn
TTS_URL = 'https://api.fpt.ai/hmi/tts/v5'
VOICE = 'leminh'
SPEED = '0'
OUTPUT_FILE = "fpt_voice_final.mp3"

# --- Nội dung ---
payload = "Ối dồi ôi, ối dồi ôi, trình là gì mà là rình ai tắm."

# --- Gọi API ---
print("Đang gửi yêu cầu đến FPT.AI...")

try:
    headers = {
        'api-key': API_KEY,
        'speed': SPEED,
        'voice': VOICE
    }
    
    # Bước 1: Gửi yêu cầu và nhận link async
    response = requests.post(TTS_URL, data=payload.encode('utf-8'), headers=headers)

    if response.status_code == 200:
        # Lấy dữ liệu JSON từ phản hồi
        response_data = response.json()
        
        # Kiểm tra xem yêu cầu có thành công và trả về link async không
        if response_data.get('error') == 0 and response_data.get('async'):
            async_url = response_data['async']
            print(f"Đã nhận được link tải file: {async_url}")
            print("Chờ 3 giây để server tạo file âm thanh...")
            time.sleep(3) # Chờ 3 giây

            # Bước 2: Tải file âm thanh từ link async
            print("Đang tải file âm thanh...")
            audio_response = requests.get(async_url)

            if audio_response.status_code == 200:
                with open(OUTPUT_FILE, 'wb') as f:
                    f.write(audio_response.content)
                print(f"✅ Tạo file âm thanh thành công! Đã lưu tại: {OUTPUT_FILE}")
            else:
                print(f"❌ Lỗi khi tải file từ link async. Status code: {audio_response.status_code}")
        else:
            print("❌ FPT.AI không trả về link async. Lỗi:")
            print(response_data)
    else:
        print(f"❌ Có lỗi xảy ra ở yêu cầu đầu tiên. Status Code: {response.status_code}")
        print(f"Nội dung lỗi: {response.text}")

except Exception as e:
    print(f"❌ Đã xảy ra lỗi ngoại lệ: {e}")