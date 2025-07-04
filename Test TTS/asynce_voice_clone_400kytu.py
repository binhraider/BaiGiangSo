import requests
import time
import sys
import os
from pydub import AudioSegment

# 🔐 Nhập API key
API_KEY = ""

# Giới hạn ký tự cho tài khoản miễn phí
MAX_CHAR_LIMIT = 500

# Hàm chia văn bản thành các đoạn < 500 ký tự
def split_text(text, max_length=MAX_CHAR_LIMIT):
    sentences = text.split(". ")
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip() + ". " if sentence.strip() else ""
        if len(current_chunk) + len(sentence) <= max_length:
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

# Hàm đọc văn bản từ file .txt
def read_text_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        print(f"📖 Đọc văn bản từ {file_path}: {len(text)} ký tự")
        return text
    except FileNotFoundError:
        print(f"❌ File {file_path} không tồn tại")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Lỗi khi đọc file: {e}")
        sys.exit(1)

# Hàm ghép các file audio và xóa file tạm
def merge_audio_files(file_paths, output_file):
    try:
        combined = AudioSegment.empty()
        for file_path in file_paths:
            # Dùng from_file để nhận diện định dạng tự động
            audio = AudioSegment.from_file(file_path)
            # Chuẩn hóa: stereo, 24000 Hz (khớp với file đầu vào)
            audio = audio.set_channels(2).set_frame_rate(24000)
            combined += audio
        # Xuất MP3 với bitrate 128k
        combined.export(output_file, format="mp3", bitrate="128k")
        print(f"🎉 Đã ghép các file thành: {output_file}")
        # Xóa file tạm
        for file_path in file_paths:
            os.remove(file_path)
            print(f"🗑️ Đã xóa file tạm: {file_path}")
    except Exception as e:
        print(f"❌ Lỗi khi ghép file: {e}")
        sys.exit(1)

# === KIỂM TRA SERVER ===
print("🔍 Kiểm tra trạng thái server...")
try:
    test_url = "https://api.ausynclab.org/api/v1/voices/list"
    test_res = requests.get(test_url, headers={"X-API-Key": API_KEY, "accept": "application/json"}, timeout=30)
    test_res.raise_for_status()
    print("✅ Server hoạt động bình thường")
except requests.exceptions.RequestException as e:
    print("❌ Không thể kết nối đến server:", e)
    sys.exit(1)

# === BƯỚC 1: Dùng voice_id có sẵn ===
voice_id = "310169"
print("✅ Sử dụng Voice ID:", voice_id)

# === BƯỚC 2: Đọc văn bản từ file ===
text = read_text_from_file("input_text.txt")
text_chunks = split_text(text, MAX_CHAR_LIMIT)
print(f"🎤 Chuẩn bị tạo bài giảng với {len(text_chunks)} đoạn văn bản...")

audio_urls = []
output_files = []
for i, chunk in enumerate(text_chunks):
    if len(chunk) > MAX_CHAR_LIMIT:
        print(f"❌ Đoạn {i+1} vượt giới hạn 500 ký tự ({len(chunk)} ký tự)")
        sys.exit(1)
    
    print(f"🎤 Đang tạo audio cho đoạn {i+1}/{len(text_chunks)} ({len(chunk)} ký tự)...")
    tts_url = "https://api.ausynclab.org/api/v1/speech/text-to-speech"
    data = {
        "audio_name": f"bai_giang_toan_lop5_part_{i+1}",
        "text": chunk,
        "voice_id": voice_id,
        "speed": 1.0,
        "model_name": "myna-1",
        "language": "vi",
        "callback_url": "https://webhook.site/your-unique-id"  # Thay bằng URL thực
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
        print(f"❌ Lỗi kết nối mạng (đoạn {i+1}):", e)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"❌ Lỗi HTTP (đoạn {i+1}):", e, res_tts.text)
        sys.exit(1)

    audio_id = res_tts.json().get("result", {}).get("audio_id")
    if not audio_id:
        print(f"❌ Không tìm thấy audio_id trong phản hồi (đoạn {i+1}):", res_tts.json())
        sys.exit(1)
    print(f"✅ Đã gửi yêu cầu tạo audio (đoạn {i+1}). Audio ID:", audio_id)

    # === BƯỚC 3: Lấy thông tin audio (polling) ===
    print(f"⏳ Đang đợi xử lý âm thanh (đoạn {i+1})...")
    max_attempts = 20
    for attempt in range(max_attempts):
        try:
            audio_info_url = f"https://api.ausynclab.org/api/v1/speech/{audio_id}"
            res_info = requests.get(audio_info_url, headers={"X-API-Key": API_KEY, "accept": "application/json"}, timeout=30)
            res_info.raise_for_status()
            audio_data = res_info.json().get("result", {})
            if audio_data.get("state") == "SUCCEED" and audio_data.get("audio_url"):
                audio_url = audio_data["audio_url"]
                print(f"🎧 Link audio (đoạn {i+1}):", audio_url)
                audio_urls.append(audio_url)
                break
            print(f"⌛ Audio chưa sẵn sàng, thử lại sau {attempt + 1}/{max_attempts}...")
            time.sleep(5)
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Lỗi kết nối mạng (đoạn {i+1}):", e)
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            print(f"❌ Lỗi HTTP (đoạn {i+1}):", e, res_info.text)
            sys.exit(1)
    else:
        print(f"❌ Hết thời gian chờ, audio không sẵn sàng (đoạn {i+1})")
        sys.exit(1)

# === BƯỚC 4: Tải file audio về ===
for i, audio_url in enumerate(audio_urls):
    print(f"⬇️ Đang tải file bài giảng (đoạn {i+1})...")
    try:
        response = requests.get(audio_url, timeout=60)
        response.raise_for_status()
        wav_file = f"bai_giang_ausync_part_{i+1}.wav"
        with open(wav_file, "wb") as f:
            f.write(response.content)
        # Kiểm tra kích thước file
        if os.path.getsize(wav_file) < 1000:
            print(f"❌ File {wav_file} quá nhỏ, có thể bị lỗi")
            sys.exit(1)
        # Chuyển WAV sang MP3 chuẩn
        mp3_file = f"bai_giang_ausync_part_{i+1}.mp3"
        audio = AudioSegment.from_wav(wav_file)
        audio = audio.set_channels(2).set_frame_rate(24000)  # Chuẩn hóa: stereo, 24000 Hz
        audio.export(mp3_file, format="mp3", bitrate="128k")
        os.remove(wav_file)  # Xóa file WAV tạm
        output_files.append(mp3_file)
        print(f"🎉 Đã lưu bài giảng tại: {mp3_file}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi khi tải file (đoạn {i+1}):", e)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Lỗi khi xử lý file (đoạn {i+1}):", e)
        sys.exit(1)

# === BƯỚC 5: Ghép file MP3 ===
if len(output_files) > 1:
    print("🔗 Đang ghép các file MP3 thành một file duy nhất...")
    merge_audio_files(output_files, "bai_giang_ausync_full.mp3")
else:
    os.rename(output_files[0], "bai_giang_ausync_full.mp3")
    print("🎉 Chỉ có 1 file, đã đổi tên thành: bai_giang_ausync_full.mp3")

print("🎉 Hoàn thành! Kiểm tra file bai_giang_ausync_full.mp3")