from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings, play

# 1. Khởi tạo client với API key
client = ElevenLabs(api_key="")  # Thay bằng key thật

# 2. Văn bản
text_to_speak = "Chào bạn! Đây là giọng nói hỗ trợ tiếng Việt."

# 3. Tạo âm thanh (trả về generator)
audio = client.text_to_speech.convert(
    voice_id="pNInz6obpgDQGcFmaJgB",
    model_id="eleven_multilingual_v2",
    text=text_to_speak,
    voice_settings=VoiceSettings(stability=0.75, similarity_boost=0.75)
)

# 4. Phát âm thanh (nếu bạn đã cài ffmpeg)
# print("Đang phát âm thanh...")
# play(audio)

# 5. Ghi âm thanh ra file
print("Đang lưu file âm thanh...")
with open("final_working_output.mp3", "wb") as f:
    f.write(b"".join(audio))  # ✅ CHỖ NÀY
print("✅ Thành công! Đã lưu file tại final_working_output.mp3")
