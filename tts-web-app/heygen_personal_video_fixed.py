import requests
import json
import time
import os

# HeyGen API configuration
API_KEY = ""
BASE_URL = "https://api.heygen.com"
UPLOAD_BASE_URL = "https://upload.heygen.com"

# Hàm kiểm tra file
def check_file_exists(file_path):
    if not os.path.exists(file_path):
        print(f"File không tồn tại: {file_path}")
        return False
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"Kích thước {file_path}: {size_mb:.2f} MB")
    return True

# Hàm upload file
def upload_asset(file_path, content_type):
    url = f"{UPLOAD_BASE_URL}/v1/asset"
    headers = {
        "X-Api-Key": API_KEY,
        "Content-Type": content_type
    }
    
    try:
        with open(file_path, "rb") as file:
            response = requests.post(url, headers=headers, data=file, timeout=60)
            print(f"Mã trạng thái HTTP cho {file_path}: {response.status_code}")
            print(f"Nội dung phản hồi: {response.text}")
            response.raise_for_status()
            result = response.json()
            print(f"Phản hồi JSON: {result}")
            if result.get("code") == 100:
                return result["data"]["id"]
            else:
                print(f"Upload thất bại: {result.get('message')}")
                return None
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi upload {file_path}: {str(e)}")
        return None
    except ValueError as e:
        print(f"Lỗi parse JSON {file_path}: {str(e)}")
        return None

# Hàm kiểm tra trạng thái video
def check_video_status(video_id):
    url = f"{BASE_URL}/v1/video_status.get?video_id={video_id}"
    headers = {
        "X-Api-Key": API_KEY,
        "Accept": "application/json"
    }
    
    while True:
        try:
            response = requests.get(url, headers=headers, timeout=30)
            print(f"Mã trạng thái HTTP trạng thái video: {response.status_code}")
            print(f"Nội dung phản hồi: {response.text}")
            result = response.json()
            status = result["data"]["status"]
            print(f"Trạng thái video: {status}")
            
            if status == "completed":
                return result["data"]["video_url"]
            elif status in ["failed", "error"]:
                print(f"Lỗi: {result['data']['error']}")
                return None
            time.sleep(5)
        except requests.exceptions.RequestException as e:
            print(f"Lỗi khi kiểm tra trạng thái: {str(e)}")
            return None
        except ValueError as e:
            print(f"Lỗi parse JSON trạng thái: {str(e)}")
            return None

# Đường dẫn file
audio_file = "C:/Users/Admin/Downloads/tts-web-app/downloads/bai_giang_ausync_full.mp3"
background_image = "C:/Users/Admin/Downloads/tts-web-app/02-background.jpg"

# Kiểm tra file
if not all(check_file_exists(f) for f in [audio_file, background_image]):
    print("Một hoặc nhiều file không tồn tại. Thoát chương trình.")
    exit()

# Upload audio
audio_asset_id = upload_asset(audio_file, "audio/mpeg")
if not audio_asset_id:
    print("Không thể upload audio. Thoát chương trình.")
    exit()

# Upload background
image_asset_id = upload_asset(background_image, "image/jpeg")
if not image_asset_id:
    print("Không thể upload hình nền. Thoát chương trình.")
    exit()

# Dùng Talking Photo ID (ví dụ: Harry)
talking_photo_id = "0f32e8513d3248849aacc33958442d6d"  # bạn có thể thay bằng Liam, Leonardo,...

# Tạo payload tạo video
video_data = {
    "video_inputs": [
        {
            "character": {
                "type": "talking_photo",
                "talking_photo_id": talking_photo_id
            },
            "voice": {
                "type": "audio",
                "audio_asset_id": audio_asset_id
            },
            "background": {
                "type": "image",
                "image_asset_id": image_asset_id
            }
        }
    ],
    "dimension": {
        "width": 1280,
        "height": 720
    },
    "aspect_ratio": "16:9"
}

# Gửi yêu cầu tạo video
url = f"{BASE_URL}/v2/video/generate"
headers = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, headers=headers, data=json.dumps(video_data), timeout=60)
    print(f"Mã trạng thái HTTP tạo video: {response.status_code}")
    print(f"Nội dung phản hồi: {response.text}")
    result = response.json()
except requests.exceptions.RequestException as e:
    print(f"Lỗi khi tạo video: {str(e)}")
    exit()
except ValueError as e:
    print(f"Lỗi parse JSON tạo video: {str(e)}")
    exit()

# Kiểm tra và tải video
if result.get("code") == 100 or result.get("data", {}).get("video_id"):
    video_id = result["data"]["video_id"]
    print(f"Video đang được tạo, ID: {video_id}")
    
    video_url = check_video_status(video_id)
    if video_url:
        print(f"✅ Video đã hoàn thành! URL: {video_url}")
        try:
            video_response = requests.get(video_url, timeout=60)
            with open("output_video.mp4", "wb") as f:
                f.write(video_response.content)
            print("🎉 Video đã được tải về: output_video.mp4")
        except requests.exceptions.RequestException as e:
            print(f"Lỗi khi tải video: {str(e)}")
    else:
        print("❌ Tạo video thất bại.")
else:
    error = result.get('error')
    if isinstance(error, dict):
        error_message = error.get('message', 'Không có thông tin lỗi')
    else:
        error_message = 'Không có thông tin lỗi'
    print(f"Lỗi khi tạo video: {error_message}")
