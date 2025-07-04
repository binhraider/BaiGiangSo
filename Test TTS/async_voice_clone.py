import requests
import time
import sys
import os

# 🔐 Nhập API key
API_KEY = ""

# === KIỂM TRA SERVER TRƯỚC KHI UPLOAD ===
print("🔍 Kiểm tra trạng thái server...")
try:
    test_url = "https://api.ausynclab.org/api/v1/voices/list"
    test_res = requests.get(test_url, headers={"X-API-Key": API_KEY, "accept": "application/json"}, timeout=30)
    test_res.raise_for_status()
    print("✅ Server hoạt động bình thường")
except requests.exceptions.RequestException as e:
    print("❌ Không thể kết nối đến server:", e)
    sys.exit(1)

# === BƯỚC 1: Clone giọng giáo viên ===
print("📤 Đang đăng ký giọng nói...")
voice_register_url = "https://api.ausynclab.org/api/v1/voices/register"
query_params = {
    "name": "GV_Toan_Lop5",
    "language": "vi",
    "gender": "FEMALE",
    "age": "MIDDLE_AGED",
    "use_case": "NARRATION"
}
headers = {
    "X-API-Key": API_KEY,
    "accept": "application/json"
}

# Kiểm tra file audio
audio_file_path = "teacher_sample.mp3"
if not os.path.exists(audio_file_path):
    print("❌ File teacher_sample.mp3 không tồn tại")
    sys.exit(1)
if os.path.getsize(audio_file_path) > 10 * 1024 * 1024:  # Kiểm tra file > 10MB
    print("⚠️ File teacher_sample.mp3 quá lớn (>10MB), nên nén hoặc cắt ngắn")
    sys.exit(1)

try:
    with open(audio_file_path, "rb") as f:
        files = {"audio_file": (audio_file_path, f, "audio/mpeg")}
        res = requests.post(
            voice_register_url,
            headers=headers,
            params=query_params,
            files=files,
            timeout=60  # Tăng timeout lên 60 giây
        )
        res.raise_for_status()
except requests.exceptions.ReadTimeout:
    print("❌ Hết thời gian chờ khi upload giọng nói (timeout). Thử giảm kích thước file hoặc kiểm tra mạng.")
    sys.exit(1)
except requests.exceptions.ConnectionError as e:
    print("❌ Lỗi kết nối mạng:", e)
    sys.exit(1)
except requests.exceptions.HTTPError as e:
    print("❌ Lỗi HTTP:", e, res.text)
    sys.exit(1)
except FileNotFoundError:
    print("❌ File teacher_sample.mp3 không tồn tại")
    sys.exit(1)

voice_id = res.json().get("result", {}).get("id")
if not voice_id:
    print("❌ Không tìm thấy voice_id trong phản hồi:", res.json())
    sys.exit(1)
print("✅ Đã tạo giọng thành công. Voice ID:", voice_id)

# === BƯỚC 2: Tạo bài giảng từ văn bản ===
print("🎤 Đang tạo bài giảng từ văn bản...")
tts_url = "https://api.ausynclab.org/api/v1/speech/text-to-speech"
data = {
    "audio_name": "bai_giang_toan_lop5",
    "text": "Chào các em. Hôm nay chúng ta học về phân số thập phân.",
    "voice_id": voice_id,
    "speed": 1.0,
    "model_name": "myna-1",
    "language": "vi",
    "callback_url": "https://webhook.site/your-unique-id"  # Thay bằng URL thực từ webhook.site
}
headers_tts = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json",
    "accept": "application/json"
}

try:
    res_tts = requests.post(tts_url, headers=headers_tts, json=data, timeout=30)
    res_tts.raise_for_status()
except requests.exceptions.ConnectionError as e:
    print("❌ Lỗi kết nối mạng:", e)
    sys.exit(1)
except requests.exceptions.HTTPError as e:
    print("❌ Lỗi HTTP:", e, res_tts.text)
    sys.exit(1)

audio_id = res_tts.json().get("result", {}).get("audio_id")
if not audio_id:
    print("❌ Không tìm thấy audio_id trong phản hồi:", res_tts.json())
    sys.exit(1)
print("✅ Đã gửi yêu cầu tạo audio. Audio ID:", audio_id)

# === BƯỚC 3: Lấy thông tin audio (polling) ===
print("⏳ Đang đợi xử lý âm thanh...")
max_attempts = 15
for attempt in range(max_attempts):
    try:
        audio_info_url = f"https://api.ausynclab.org/api/v1/speech/{audio_id}"
        res_info = requests.get(audio_info_url, headers={"X-API-Key": API_KEY, "accept": "application/json"}, timeout=30)
        res_info.raise_for_status()
        audio_data = res_info.json().get("result", {})
        if audio_data.get("state") == "SUCCEED" and audio_data.get("audio_url"):
            audio_url = audio_data["audio_url"]
            print("🎧 Link audio:", audio_url)
            break
        print(f"⌛ Audio chưa sẵn sàng, thử lại sau {attempt + 1}/{max_attempts}...")
        time.sleep(5)
    except requests.exceptions.ConnectionError as e:
        print("❌ Lỗi kết nối mạng:", e)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print("❌ Lỗi HTTP:", e, res_info.text)
        sys.exit(1)
else:
    print("❌ Hết thời gian chờ, audio không sẵn sàng")
    sys.exit(1)

# === BƯỚC 4: Tải file audio về ===
print("⬇️ Đang tải file bài giảng về...")
try:
    audio_file = requests.get(audio_url, timeout=30).content
    with open("bai_giang_ausync.mp3", "wb") as f:
        f.write(audio_file)
    print("🎉 Đã lưu bài giảng tại: bai_giang_ausync.mp3")
except requests.exceptions.ConnectionError as e:
    print("❌ Lỗi kết nối mạng khi tải:", e)
    sys.exit(1)
except Exception as e:
    print("❌ Lỗi khi tải file:", e)
    sys.exit(1)