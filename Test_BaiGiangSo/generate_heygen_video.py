import os
import json
import time
import requests
import glob
from dotenv import load_dotenv

load_dotenv()

class HeyGenTalkingPhotoClient:
    """Client tạo video từ 1 ảnh sử dụng HeyGen Talking Photo API (cập nhật 2025)."""

    def __init__(self):
        self.api_key = os.getenv("HEYGEN_API_KEY")
        if not self.api_key:
            raise ValueError("❌ Thiếu HEYGEN_API_KEY trong file .env")

        self.base_url = "https://api.heygen.com"
        self.upload_url = "https://upload.heygen.com"  # Endpoint upload mới
        self.headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }

    def upload_local_file(self, file_path, file_type="audio"):
        """
        Upload file local (audio hoặc image) lên HeyGen.
        file_type: "audio", "image", hoặc "talking_photo"
        """
        if not os.path.exists(file_path):
            raise Exception(f"❌ File không tồn tại: {file_path}")

        print(f"📁 Đang upload file local: {os.path.basename(file_path)}")

        # Xác định content type và endpoint
        if file_type == "audio":
            content_type = "audio/mpeg"
            endpoint = "v1/asset"
        elif file_type == "talking_photo":
            content_type = "image/jpeg"
            endpoint = "v1/talking_photo"
        else:
            raise Exception(f"❌ Loại file không hỗ trợ: {file_type}")

        # Upload file
        upload_headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": content_type
        }

        with open(file_path, 'rb') as f:
            upload_response = requests.post(
                f"{self.upload_url}/{endpoint}",
                headers=upload_headers,
                data=f.read()
            )

        if upload_response.status_code == 200:
            response_data = upload_response.json()
            asset_id = response_data['data'].get('talking_photo_id') or response_data['data'].get('id')
            print(f"✅ Upload thành công: {asset_id}")
            return asset_id
        else:
            raise Exception(f"❌ Lỗi upload {file_type}: {upload_response.text}")


    def create_video_with_talking_photo(self, talking_photo_id, audio_asset_id):
        """Tạo video với talking_photo_id và audio_asset_id."""
        print("\n🎬 BƯỚC 2: Tạo video với Talking Photo...")

        voice_payload = {
            "type": "audio",
            "audio_asset_id": audio_asset_id
        }

        resolutions = [
            {"width": 640, "height": 480},
            {"width": 480, "height": 640},
            {"width": 360, "height": 640}
        ]

        for i, dimension in enumerate(resolutions):
            payload = {
                "video_inputs": [{
                    "character": {
                        "type": "talking_photo",
                        "talking_photo_id": talking_photo_id
                    },
                    "voice": voice_payload
                }],
                "test": True,
                "dimension": dimension
            }
            print(f"   Thử resolution: {dimension['width']}x{dimension['height']}")

            url = f"{self.base_url}/v2/video/generate"
            response = requests.post(url, headers=self.headers, json=payload)

            if response.status_code == 200:
                video_id = response.json()['data']['video_id']
                print(f"✅ Video đang được tạo: {video_id}")
                return video_id
            else:
                error_data = response.json()
                error_code = error_data.get('error', {}).get('code', '')
                if 'RESOLUTION' in error_code and i < len(resolutions) - 1:
                    print(f"   ❌ Resolution bị từ chối, thử resolution thấp hơn...")
                    continue
                else:
                    raise Exception(f"❌ Lỗi tạo video: {response.text}")

        raise Exception("❌ Không thể tạo video với bất kỳ resolution nào")

    def wait_and_get_video_url(self, video_id, max_wait=600):
        """Chờ video xong và lấy URL."""
        print("\n⏳ BƯỚC 3: Chờ video hoàn thành...")
        start_time = time.time()

        while time.time() - start_time < max_wait:
            url = f"{self.base_url}/v1/video_status.get?video_id={video_id}"
            response = requests.get(url, headers={"X-Api-Key": self.api_key})

            if response.status_code == 200:
                data = response.json()['data']
                status = data['status']
                print(f"   Trạng thái: {status}...")

                if status == 'completed':
                    video_url = data['video_url']
                    print(f"🎉 Hoàn thành! URL Video: {video_url}")
                    return video_url
                elif status == 'failed':
                    error_msg = data.get('error', {})
                    raise Exception(f"❌ Video generation thất bại: {error_msg}")

            time.sleep(10)

        raise Exception("❌ Hết thời gian chờ video.")

    def download_video(self, video_url, filename=None):
        """Tự động download video từ URL về máy local."""
        try:
            print("\n📥 BƯỚC 4: Download video về máy...")

            if not filename:
                timestamp = int(time.time())
                filename = f"heygen_video_{timestamp}.mp4"

            if not filename.endswith('.mp4'):
                filename += '.mp4'

            print(f"   Đang download: {filename}")

            response = requests.get(video_url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            print(f"\r   Progress: {progress:.1f}%", end="", flush=True)

            print(f"\n✅ Download thành công: {filename}")
            print(f"📁 File size: {downloaded_size / (1024*1024):.2f} MB")
            return filename

        except Exception as e:
            print(f"\n❌ Lỗi download: {e}")
            print("💡 Bạn có thể download thủ công từ URL:")
            print(f"   {video_url}")
            return None

    def batch_create_videos(self, photo_path, audio_folder, output_folder="videos"):
        """Tạo nhiều video từ 1 ảnh và nhiều file audio."""
        print(f"\n🎬 BATCH PROCESSING: Tạo video hàng loạt")
        print("=" * 60)

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"📁 Đã tạo thư mục: {output_folder}")

        print("\n📸 BƯỚC 1: Upload ảnh talking photo...")
        talking_photo_id = self.upload_local_file(photo_path, "talking_photo")

        audio_files = []
        for ext in ['*.mp3', '*.wav', '*.m4a', '*.aac']:
            audio_files.extend(glob.glob(os.path.join(audio_folder, ext)))

        if not audio_files:
            raise Exception(f"❌ Không tìm thấy file audio nào trong: {audio_folder}")

        print(f"📂 Tìm thấy {len(audio_files)} file audio")

        results = []

        for i, audio_file in enumerate(audio_files, 1):
            try:
                print(f"\n🎵 [{i}/{len(audio_files)}] Xử lý: {os.path.basename(audio_file)}")

                print("   📤 Upload audio...")
                audio_asset_id = self.upload_local_file(audio_file, "audio")

                print("   🎬 Tạo video...")
                video_id = self.create_video_with_talking_photo(talking_photo_id, audio_asset_id)

                print("   ⏳ Chờ render...")
                video_url = self.wait_and_get_video_url(video_id)

                filename = f"video_{i:03d}_{os.path.splitext(os.path.basename(audio_file))[0]}.mp4"
                output_path = os.path.join(output_folder, filename)

                print("   📥 Download video...")
                downloaded_file = self.download_video(video_url, output_path)

                results.append({
                    'audio_file': audio_file,
                    'video_id': video_id,
                    'video_url': video_url,
                    'local_file': downloaded_file,
                    'status': 'success'
                })
                print(f"   ✅ Hoàn thành: {filename}")

            except Exception as e:
                print(f"   ❌ Lỗi: {e}")
                results.append({
                    'audio_file': audio_file,
                    'status': 'failed',
                    'error': str(e)
                })
                continue

        print(f"\n📊 TỔNG KẾT:")
        print("=" * 60)
        success_count = len([r for r in results if r['status'] == 'success'])
        failed_count = len(results) - success_count

        print(f"✅ Thành công: {success_count}/{len(audio_files)} video")
        print(f"❌ Thất bại: {failed_count}/{len(audio_files)} video")
        print(f"📁 Thư mục output: {os.path.abspath(output_folder)}")

        if failed_count > 0:
            print(f"\n⚠️  Các file lỗi:")
            for result in results:
                if result['status'] == 'failed':
                    print(f"   - {os.path.basename(result['audio_file'])}: {result['error']}")

        return results


def main():
    """Hàm chính để chạy chương trình với menu tương tác."""
    print("🎬 HEYGEN TALKING PHOTO GENERATOR")
    print("=" * 60)
    print("1. Single Video (1 ảnh + 1 audio)")
    print("2. Batch Videos (1 ảnh + nhiều audio)")
    print("=" * 60)

    choice = input("Chọn mode (1 hoặc 2): ").strip()

    client = HeyGenTalkingPhotoClient()

    if choice == "2":
        print("\n📝 MODE 2: Tạo nhiều video")
        photo_path = input("Đường dẫn ảnh: ").strip()
        audio_folder = input("Thư mục chứa file audio: ").strip()
        output_folder = input("Thư mục lưu video (mặc định: videos): ").strip() or "videos"

        if not photo_path or not audio_folder:
            print("❌ Vui lòng nhập đầy đủ đường dẫn ảnh và thư mục audio!")
            return

        try:
            client.batch_create_videos(photo_path, audio_folder, output_folder)
        except Exception as e:
            print(f"\n💥 LỖI KHÔNG XÁC ĐỊNH: {e}")

    else:
        print("❌ Lựa chọn không hợp lệ!")


if __name__ == "__main__":
    main()