# File: clone_voice.py (phiên bản cuối cùng, đã xác minh)

from elevenlabs.client import ElevenLabs

# 1. Khởi tạo client với API key MỚI của bạn
client = ElevenLabs(
  api_key="", # Thay bằng key MỚI
)

# 2. Đường dẫn tới file audio mẫu
audio_sample_paths = [
    "C:/Users/Admin/Downloads/J2TEAM-TTS/giong-toan-nam.mp3"
]

print("Đang tải lên các mẫu âm thanh để clone...")

try:
    # 3. Sử dụng phương thức chính xác đã tìm thấy
    cloned_voice = client.voices.ivc.create(
        name="Final Cloned Voice",
        description="Giọng clone từ tiếng Việt (đã hoạt động).",
        files=audio_sample_paths
    )

    print("-" * 30)
    print("✅ TẠO GIỌNG NÓI THÀNH CÔNG!")
    print(f"Tên: {cloned_voice.name}")
    print(f"Voice ID: {cloned_voice.voice_id}") # LƯU LẠI VOICE ID NÀY
    print("-" * 30)

except Exception as e:
    print(f"❌ Lỗi khi clone giọng nói: {e}")