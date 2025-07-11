import os
import json
import time
import requests
import argparse
from pathlib import Path
from dotenv import load_dotenv
from pydub import AudioSegment
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# === CONFIG ===
load_dotenv()

AUSYNC_API_KEY = os.getenv("AUSYNC_API_KEY")
VOICE_ID = int(os.getenv("VOICE_ID", "0"))
MODEL_NAME = "myna-2"
LANGUAGE = "vi"
TTS_ENDPOINT = "https://api.ausynclab.org/api/v1/speech/text-to-speech"
GET_AUDIO_ENDPOINT = "https://api.ausynclab.org/api/v1/speech/{audio_id}"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": AUSYNC_API_KEY
}
MAX_TEXT_LENGTH = 500
SLIDE_DELAY = 2 # FIX: Thêm độ trễ 2 giây giữa các slide

# Tạo session với cơ chế retry tự động, kiên nhẫn hơn
session = requests.Session()
retries = Retry(
    total=5,          # Tổng số lần thử lại
    backoff_factor=1, # Thời gian chờ giữa các lần thử sẽ là {1s, 2s, 4s, 8s, 16s}
    status_forcelist=[429, 500, 502, 503, 504] # Các mã lỗi sẽ được retry
)
session.mount('https://', HTTPAdapter(max_retries=retries))

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Generate audios from JSON")
    parser.add_argument("--json", default="slides_with_text.json", help="Path to input JSON")
    parser.add_argument("--output-dir", default="audios", help="Output directory for audios")
    return parser.parse_args()

def check_server_status():
    """Kiểm tra trạng thái server AusyncLab."""
    try:
        test_url = "https://api.ausynclab.org/api/v1/voices/list"
        response = session.get(test_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        print("✅ Server AusyncLab: OK")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Server AusyncLab không khả dụng: {e}")
        return False

def split_text(text, max_length=MAX_TEXT_LENGTH):
    """Chia văn bản thành các đoạn nhỏ hơn max_length một cách thông minh."""
    if not text or not text.strip(): return []
    text = text.strip()
    if len(text) <= max_length: return [text]
    
    parts = []
    while len(text) > max_length:
        cut_pos = -1
        for delimiter in ['. ', '? ', '! ', ', ', ' ']:
            pos = text.rfind(delimiter, 0, max_length)
            if pos != -1:
                cut_pos = pos + len(delimiter)
                break
        if cut_pos == -1: cut_pos = max_length
        parts.append(text[:cut_pos].strip())
        text = text[cut_pos:].strip()
    
    if text: parts.append(text)
    return [p for p in parts if p]

def request_tts(text, audio_name):
    """Gửi yêu cầu tạo audio (đã có retry tự động từ session)."""
    payload = {
        "audio_name": audio_name, "text": text, "voice_id": VOICE_ID,
        "speed": 1.0, "model_name": MODEL_NAME, "language": LANGUAGE
    }
    try:
        res = session.post(TTS_ENDPOINT, json=payload, headers=HEADERS, timeout=90)
        res.raise_for_status()
        data = res.json()
        audio_id = data.get("result", {}).get("audio_id")
        if not audio_id:
            print(f"❌ Lỗi: API không trả về audio_id. Phản hồi: {data}")
            return None
        return audio_id
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi khi yêu cầu TTS (sau khi đã thử lại): {e}")
        return None

def wait_for_audio_url(audio_id, max_tries=30, delay=5):
    """Chờ và lấy URL audio."""
    if not audio_id: return None
    print("    - Bắt đầu chờ audio sẵn sàng...")
    for attempt in range(max_tries):
        try:
            url = GET_AUDIO_ENDPOINT.format(audio_id=audio_id)
            res = session.get(url, headers=HEADERS, timeout=30)
            if res.status_code == 200:
                data = res.json()
                if data and data.get("result", {}).get("audio_url"):
                    print("    - ✅ Audio đã sẵn sàng!")
                    return data["result"]["audio_url"]
            # Nếu gặp lỗi client (không phải lỗi server), dừng lại
            elif 400 <= res.status_code < 500:
                 print(f"    - ❌ Gặp lỗi không thể thử lại ({res.status_code}): {res.text}. Dừng chờ.")
                 return None
            
            print(f"    - Chờ lần {attempt + 1}/{max_tries}...")
            time.sleep(delay)
        except requests.exceptions.RequestException as e:
            print(f"    - ❌ Lỗi kết nối khi chờ: {e}. Dừng chờ.")
            return None
    print("    - ⏰ Hết thời gian chờ.")
    return None

def save_audio(audio_url, save_path):
    """Tải và lưu file audio."""
    if not audio_url: return False
    try:
        response = session.get(audio_url, timeout=60, stream=True)
        response.raise_for_status()
        content_type = response.headers.get('Content-Type', '')
        if 'audio' not in content_type and 'application/octet-stream' not in content_type:
            print(f"    - ❌ Lỗi: URL không trả về file audio. Content-Type: {content_type}")
            return False
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        if os.path.getsize(save_path) > 100:
            return True
        else:
            print("    - ❌ Lỗi: File audio tải về bị rỗng.")
            try: os.remove(save_path)
            except OSError: pass
            return False
    except requests.exceptions.RequestException as e:
        print(f"    - ❌ Lỗi khi tải file audio: {e}")
        return False

def merge_audio_files(audio_paths, output_path):
    """Gộp các file audio, bỏ qua các file lỗi."""
    if not audio_paths: return False
    valid_segments = []
    for path in audio_paths:
        if not os.path.exists(path): continue
        try:
            segment = AudioSegment.from_file(path)
            valid_segments.append(segment)
        except Exception as e:
            print(f"    - ❌ Lỗi khi đọc file tạm '{path}': {e}. Bỏ qua file này.")
            continue
    if not valid_segments:
        print("❌ Không có đoạn audio hợp lệ nào để gộp.")
        return False
    try:
        combined = AudioSegment.empty()
        for segment in valid_segments:
            combined += segment
        combined.export(output_path, format="mp3", bitrate="128k")
        return True
    except Exception as e:
        print(f"❌ Lỗi trong quá trình gộp audio cuối cùng: {e}")
        return False

def generate_audios_from_json(json_path, output_dir):
    """Quy trình chính: Tạo audio từ file JSON."""
    if not check_server_status(): return
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            slides = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Lỗi đọc file JSON: {e}")
        return

    total_slides = len(slides)
    for i, slide in enumerate(slides):
        slide_num = slide.get("slide_number", i + 1)
        title = slide.get("title", "Không có tiêu đề")
        lecture_text = slide.get("generated_lecture", "").strip()
        
        print(f"\n--- Đang xử lý Slide {slide_num}/{total_slides}: {title} ---")
        if not lecture_text:
            print("⚠️  Slide không có nội dung, bỏ qua.")
            slide["audio_path"] = ""
        elif slide.get("audio_path") and os.path.exists(slide.get("audio_path")):
            print("✅ Audio đã tồn tại, bỏ qua.")
        else:
            text_segments = split_text(lecture_text)
            if not text_segments:
                print("⚠️  Không thể chia nhỏ văn bản, bỏ qua.")
                continue
            print(f"  - Văn bản được chia thành {len(text_segments)} đoạn.")
            segment_audio_paths = []
            for idx, segment_text in enumerate(text_segments):
                print(f"  - Đang xử lý đoạn {idx + 1}/{len(text_segments)}...")
                segment_audio_name = f"slide_{slide_num}_part_{idx+1}"
                segment_save_path = os.path.join(output_dir, f"{segment_audio_name}.wav")
                audio_id = request_tts(segment_text, segment_audio_name)
                if not audio_id: continue
                audio_url = wait_for_audio_url(audio_id)
                if not audio_url: continue
                if save_audio(audio_url, segment_save_path):
                    segment_audio_paths.append(segment_save_path)
            
            if segment_audio_paths:
                final_save_path = os.path.join(output_dir, f"slide_{slide_num}.mp3")
                if merge_audio_files(segment_audio_paths, final_save_path):
                    print(f"✅ Đã gộp thành công: {final_save_path}")
                    slide["audio_path"] = final_save_path
                        # ✅ TÍNH THỜI GIAN AUDIO
                    try:
                        audio = AudioSegment.from_file(final_save_path)
                        duration_sec = round(len(audio) / 1000, 2)
                        slide["duration"] = duration_sec
                        print(f"    - ⏱ Thời lượng: {duration_sec} giây")
                    except Exception as e:
                        print(f"    - ⚠️ Không tính được duration: {e}")
                        slide["duration"] = 0

                    for p in segment_audio_paths:
                        try: os.remove(p)
                        except OSError: pass
                else:
                    print(f"❌ Gộp audio thất bại cho slide {slide_num}.")
                    slide["audio_path"] = ""
            else:
                print(f"❌ Không tạo được audio nào cho slide {slide_num}.")
                slide["audio_path"] = ""
        
        with open("slides_with_text_temp.json", "w", encoding="utf-8") as f:
            json.dump(slides, f, ensure_ascii=False, indent=2)
        
        # FIX: Thêm độ trễ giữa các slide để tránh bị giới hạn
        print(f"--- Tạm nghỉ {SLIDE_DELAY} giây ---")
        time.sleep(SLIDE_DELAY)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(slides, f, ensure_ascii=False, indent=2)
    print(f"\n🎉 Hoàn tất! Dữ liệu đã được cập nhật vào: {json_path}")

if __name__ == "__main__":
    if not os.getenv("AUSYNC_API_KEY"):
        print("Lỗi: Biến môi trường AUSYNC_API_KEY chưa được thiết lập trong file .env")
    else:
        args = parse_args()
        # Cho phép tiếp tục từ file tạm
        temp_json_path = "slides_with_text_temp.json"
        if os.path.exists(temp_json_path):
            print(f"💡 Tìm thấy file tạm '{temp_json_path}', sẽ tiếp tục từ đây.")
            args.json = temp_json_path
        generate_audios_from_json(args.json, args.output_dir)
