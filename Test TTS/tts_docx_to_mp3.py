import requests
import time
import docx
import re
import os
from pydub import AudioSegment

# --- Cấu hình ---
API_KEY = "" # ⚠️ Thay bằng API key MỚI của bạn
TTS_URL = 'https://api.fpt.ai/hmi/tts/v5'
DOCX_INPUT_FILE = "bai_giang_dai.docx"
MP3_OUTPUT_FILE = "bai_giang_hoan_chinh.mp3"
TEMP_FOLDER = "temp_audio"
VOICE = 'lannhi'
SPEED = '0'
MAX_CHARS_PER_CHUNK = 4000

# (Các hàm read_text_from_docx, clean_text, chunk_text giữ nguyên như cũ)
def read_text_from_docx(file_path):
    try:
        doc = docx.Document(file_path)
        full_text = [para.text for para in doc.paragraphs if para.text.strip() != '']
        return '\n'.join(full_text)
    except Exception as e:
        return None

def clean_text(text):
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def chunk_text(text, max_length):
    chunks = []
    sentences = re.findall(r'.*?[.?!]', text)
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_length:
            current_chunk += sentence + " "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

# --- HÀM TTS ĐÃ NÂNG CẤP LOGGING ---
def text_to_speech_for_chunk(chunk_text, chunk_index):
    print(f"  Gửi yêu cầu cho mẩu {chunk_index}...")
    try:
        headers = {'api-key': API_KEY, 'speed': SPEED, 'voice': VOICE}
        response = requests.post(TTS_URL, data=chunk_text.encode('utf-8'), headers=headers)
        
        print(f"  Phản hồi từ FPT.AI (Status Code: {response.status_code}):")
        # In ra toàn bộ nội dung JSON để chẩn đoán
        print(f"  Nội dung JSON: {response.text}")

        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('error') == 0 and response_data.get('async'):
                async_url = response_data['async']
                print(f"  >> Nhận được link async: {async_url}")
                time.sleep(30)
                audio_response = requests.get(async_url)
                if audio_response.status_code == 200:
                    temp_file_path = os.path.join(TEMP_FOLDER, f"chunk_{chunk_index}.mp3")
                    with open(temp_file_path, 'wb') as f:
                        f.write(audio_response.content)
                    print(f"  >> Tải và lưu file tạm thành công: {temp_file_path}")
                    return temp_file_path
                else:
                    print(f"  >> LỖI: Không tải được file từ link async. Status: {audio_response.status_code}")
            else:
                print("  >> LỖI: JSON trả về không hợp lệ hoặc có lỗi từ FPT.AI.")
        else:
            print("  >> LỖI: Yêu cầu POST thất bại.")
    except Exception as e:
        print(f"  >> LỖI NGOẠI LỆ: {e}")
    return None

def merge_audio_files(chunk_files, output_file):
    # (Hàm này giữ nguyên)
    print("Bắt đầu ghép các file audio...")
    combined = AudioSegment.empty()
    for file_path in chunk_files:
        try:
            segment = AudioSegment.from_file(file_path, format="mp3")
            combined += segment
        except Exception as e:
            print(f"Lỗi khi đọc file {file_path}: {e}")
    combined.export(output_file, format="mp3")
    print(f"✅ Đã ghép và lưu file hoàn chỉnh tại: {output_file}")


# --- QUY TRÌNH CHÍNH ---
if __name__ == "__main__":
    # (Phần này giữ nguyên)
    if not os.path.exists(TEMP_FOLDER): os.makedirs(TEMP_FOLDER)
    raw_text = read_text_from_docx(DOCX_INPUT_FILE)
    if raw_text:
        cleaned_text = clean_text(raw_text)
        text_chunks = chunk_text(cleaned_text, MAX_CHARS_PER_CHUNK)
        audio_chunk_files = []
        for i, chunk in enumerate(text_chunks):
            print(f"--- Đang xử lý mẩu {i+1}/{len(text_chunks)} ---")
            file_path = text_to_speech_for_chunk(chunk, i)
            if file_path:
                audio_chunk_files.append(file_path)
            else:
                print(f"!!! Không thể tạo audio cho mẩu {i}, bỏ qua.")
        
        if audio_chunk_files:
            merge_audio_files(audio_chunk_files, MP3_OUTPUT_FILE)
            print("Đang dọn dẹp các file tạm...")
            for file in audio_chunk_files: os.remove(file)
            os.rmdir(TEMP_FOLDER)
            print("✅ Hoàn tất!")
        else:
            print("\nKhông có file audio nào được tạo để ghép.")
    else:
        print("Không thể đọc nội dung từ file Word.")