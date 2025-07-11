import requests
import os
import json
import time
from dotenv import load_dotenv
import base64
import cloudinary
import cloudinary.uploader

# Tải các biến môi trường từ file .env
load_dotenv()

# --- Cấu hình ---
D_ID_API_KEY = os.getenv("D_ID_API_KEY")
D_ID_TALK_URL = "https://api.d-id.com/talks"
STORYBOARD_FILE = "storyboard.json"
OUTPUT_FILE = "did_videos.json"
# 🆕 Thư mục để lưu video tải về
VIDEO_OUTPUT_DIR = "videos"

# Cấu hình Cloudinary
cloudinary.config(
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
  api_key = os.getenv("CLOUDINARY_API_KEY"),
  api_secret = os.getenv("CLOUDINARY_API_SECRET"),
  secure = True
)

def upload_media_to_cloudinary(local_path, resource_type):
    """
    Tải file ảnh hoặc audio lên Cloudinary để lấy URL HTTPS công khai.
    """
    if not os.path.exists(local_path):
        print(f"❌ Không tìm thấy file: {local_path}")
        return None
    try:
        print(f"☁️  Đang tải file {resource_type} lên Cloudinary: {local_path}...")
        response = cloudinary.uploader.upload(local_path, resource_type=resource_type)
        public_url = response.get('secure_url')
        if public_url:
            print(f"✅ Upload thành công ({resource_type}): {public_url}")
            return public_url
        else:
            print(f"❌ Lỗi: Không nhận được URL từ Cloudinary cho {resource_type}.")
            return None
    except Exception as e:
        print(f"❌ Lỗi khi tải file {resource_type} lên Cloudinary: {e}")
        return None

# ✅ HÀM MỚI: Tự động tải video về máy
def download_video_from_url(video_url, save_path):
    """
    Tải file video từ một URL và lưu vào đường dẫn cục bộ.
    """
    try:
        print(f"⬇️  Đang tải video từ: {video_url}...")
        res = requests.get(video_url, stream=True)
        res.raise_for_status()
        
        # Tạo thư mục nếu nó chưa tồn tại
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        with open(save_path, 'wb') as f:
            for chunk in res.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✅ Video đã được lưu tại: {save_path}")
        return save_path
    except Exception as e:
        print(f"❌ Lỗi khi tải video: {e}")
        return None

def generate_did_video(photo_url, audio_url):
    """
    Gửi yêu cầu tạo video đến D-ID API.
    """
    api_key_with_colon = D_ID_API_KEY + ":"
    encoded_key = base64.b64encode(api_key_with_colon.encode('utf-8')).decode('utf-8')
    headers = {
        "accept": "application/json", "content-type": "application/json",
        "authorization": f"Basic {encoded_key}"
    }
    payload = {
        "source_url": photo_url,
        "script": { "type": "audio", "audio_url": audio_url },
        "config": { "fluent": "false", "result_format": "mp4" }
    }
    try:
        res = requests.post(D_ID_TALK_URL, json=payload, headers=headers)
        res.raise_for_status()
        talk_id = res.json().get("id")
        print(f"✅ Talk đã được gửi! ID: {talk_id}")
        return talk_id
    except Exception as e:
        print(f"❌ Lỗi khi gọi API tạo talk: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"📄 Chi tiết lỗi từ server: {e.response.text}")
        return None

def get_talk_status(talk_id):
    """
    Kiểm tra trạng thái và lấy URL video.
    """
    api_key_with_colon = D_ID_API_KEY + ":"
    encoded_key = base64.b64encode(api_key_with_colon.encode('utf-8')).decode('utf-8')
    headers = { "accept": "application/json", "authorization": f"Basic {encoded_key}" }
    url = f"{D_ID_TALK_URL}/{talk_id}"
    for attempt in range(30):
        try:
            res = requests.get(url, headers=headers)
            res.raise_for_status()
            data = res.json()
            status = data.get("status")

            if status == "done":
                print(f"🎉 Video sẵn sàng: {data.get('result_url')}")
                return data.get("result_url")
            elif status == "error":
                print(f"❌ D-ID trả về lỗi: {data}")
                return None
            else:
                print(f"⏳ Trạng thái: {status}. Chờ thêm 10s... (Lần {attempt + 1}/30)")
        except Exception as e:
            print(f"⚠️ Lỗi khi kiểm tra status: {e}")
            return None
        time.sleep(10)
    print("❌ Quá thời gian chờ video.")
    return None

def process_storyboard(local_photo_path, limit=5):
    """
    Quy trình chính: Tải ảnh, sau đó xử lý từng slide và tải video kết quả.
    """
    public_photo_url = upload_media_to_cloudinary(local_photo_path, resource_type="image")
    if not public_photo_url:
        print("❌ Dừng chương trình vì không thể tải ảnh đại diện lên.")
        return
    try:
        with open(STORYBOARD_FILE, "r", encoding="utf-8") as f:
            slides = json.load(f)
    except FileNotFoundError:
        print(f"❌ Lỗi: Không tìm thấy file '{STORYBOARD_FILE}'.")
        return

    video_results = []
    for slide in slides[:limit]:
        slide_num = slide.get('slide_number', 'N/A')
        print(f"\n{'='*10} 🎬 Slide {slide_num} {'='*10}")
        local_audio_path = slide.get("audio_path")
        if not local_audio_path or not os.path.exists(local_audio_path):
            print(f"⚠️ Bỏ qua slide vì không tìm thấy file audio: '{local_audio_path}'")
            continue

        public_audio_url = upload_media_to_cloudinary(local_audio_path, resource_type="video")
        if not public_audio_url: continue

        talk_id = generate_did_video(public_photo_url, public_audio_url)
        if not talk_id: continue
        
        time.sleep(5)
        video_url = get_talk_status(talk_id)

        if video_url:
            # ✅ CẬP NHẬT: Tải video về máy
            # Video sẽ được lưu vào thư mục "videos" với tên slide_1.mp4, slide_2.mp4...
            local_video_path = download_video_from_url(video_url, os.path.join(VIDEO_OUTPUT_DIR, f"slide_{slide_num}.mp4"))
            
            # Lưu cả 2 đường link vào file kết quả
            video_results.append({
                "slide_number": slide_num,
                "title": slide.get("title"),
                "video_url_online": video_url,
                "local_video_path": local_video_path
            })
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(video_results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Hoàn tất! {len(video_results)} video đã được xử lý và tải về. Kết quả lưu tại: {OUTPUT_FILE}")

if __name__ == "__main__":
    local_photo_path_for_avatar = "C:/Users/Admin/Downloads/Test_BaiGiangSo/Hinh-anh-trai-dep-Viet-Nam.jpg"
    
    if not all([D_ID_API_KEY, os.getenv("CLOUDINARY_CLOUD_NAME"), os.getenv("CLOUDINARY_API_KEY"), os.getenv("CLOUDINARY_API_SECRET")]):
        print("❌ Lỗi: Vui lòng thiết lập đầy đủ D_ID_API_KEY và các biến CLOUDINARY trong file .env")
    else:
        process_storyboard(local_photo_path_for_avatar, limit=5)