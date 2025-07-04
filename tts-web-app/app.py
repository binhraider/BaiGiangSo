from flask import Flask, request, render_template, send_from_directory, jsonify
import requests
import time
import os
import glob
from pydub import AudioSegment
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

app = Flask(__name__)

# Thiết lập logging
logging.basicConfig(
    filename='tts_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Cấu hình
API_KEY = ""
VOICE_ID = "311890"
CALLBACK_URL = "https://webhook.site/your-unique-id"  # Thay bằng URL thực
MAX_CHAR_LIMIT = 500
MIN_CHUNK_LENGTH = 50  # Độ dài tối thiểu để gộp chunk (mới thêm)
UPLOAD_FOLDER = "Uploads"
DOWNLOAD_FOLDER = "downloads"

# Đảm bảo thư mục uploads và downloads tồn tại
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Tạo session với retry
session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retries))

# Hàm kiểm tra trạng thái server
def check_server_status():
    try:
        test_url = "https://api.ausynclab.org/api/v1/voices/list"
        headers = {"X-API-Key": API_KEY, "accept": "application/json"}
        response = session.get(test_url, headers=headers, timeout=30)
        response.raise_for_status()
        logging.info("Server check: OK")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Server check failed: {e}")
        return False

# Hàm chia văn bản thành các chunk nhỏ hơn max_length
def split_text(text, max_length=500, min_length=50):
    chunks = []
    current_chunk = ""
    
    # Tách văn bản thành các đoạn dựa trên ký tự xuống dòng
    paragraphs = text.split('\n')
    
    for paragraph in paragraphs:
        # Nếu là dòng trống, thêm chunk rỗng để giữ cấu trúc
        if not paragraph.strip():
            if current_chunk:
                # Nếu chunk hiện tại đủ dài, thêm vào danh sách
                if len(current_chunk.rstrip()) >= min_length:
                    chunks.append(current_chunk.rstrip())
                    current_chunk = ""
                # Nếu chunk quá ngắn, giữ lại để gộp tiếp
            # Chỉ thêm chunk rỗng nếu không có chunk rỗng trước đó
            if chunks and chunks[-1] == "":
                continue
            chunks.append("")
            continue
        
        # Nếu đoạn văn quá dài, chia nhỏ
        words = paragraph.split()
        for word in words:
            # Xử lý từ quá dài
            if len(word) > max_length:
                # Nếu có chunk đang chờ, thêm vào trước
                if current_chunk:
                    if len(current_chunk.rstrip()) >= min_length:
                        chunks.append(current_chunk.rstrip())
                        current_chunk = ""
                    else:
                        # Gộp chunk ngắn với từ dài
                        current_chunk = current_chunk.rstrip() + " "
                # Chia nhỏ từ dài
                while len(word) > max_length:
                    chunks.append(word[:max_length])
                    word = word[max_length:]
                # Phần còn lại của từ (nếu có)
                if word:
                    current_chunk += word + " "
                continue
            
            # Nếu thêm từ mới vượt quá max_length
            if len(current_chunk) + len(word) + 1 > max_length:
                if len(current_chunk.rstrip()) >= min_length:
                    chunks.append(current_chunk.rstrip())
                    current_chunk = word + " "
                else:
                    # Gộp với từ tiếp theo trong chunk mới
                    current_chunk = current_chunk.rstrip() + " " + word + " "
            else:
                current_chunk += word + " "
        
        # Thêm dấu xuống dòng nếu không phải đoạn cuối
        if current_chunk and paragraph != paragraphs[-1]:
            current_chunk += "\n"
    
    # Thêm chunk cuối cùng nếu có
    if current_chunk:
        chunks.append(current_chunk.rstrip())
    
    # Hợp nhất các chunk ngắn (trừ chunk rỗng)
    final_chunks = []
    temp_chunk = ""
    for chunk in chunks:
        if chunk == "":
            if temp_chunk:
                final_chunks.append(temp_chunk.rstrip())
                temp_chunk = ""
            final_chunks.append("")
            continue
        if len(temp_chunk) + len(chunk) + 1 <= max_length:
            temp_chunk += (chunk + "\n" if chunk else "")
        else:
            if temp_chunk:
                final_chunks.append(temp_chunk.rstrip('\n'))
            temp_chunk = chunk + "\n"
    
    # Thêm chunk cuối
    if temp_chunk:
        final_chunks.append(temp_chunk.rstrip('\n'))
    
    # Loại bỏ các dòng trống liên tiếp
    result = []
    for i, chunk in enumerate(final_chunks):
        if chunk == "" and (i == 0 or final_chunks[i-1] == ""):
            continue
        result.append(chunk)
    
    return result

# Hàm ghép file audio
def merge_audio_files(file_paths, output_file):
    try:
        combined = AudioSegment.empty()
        for file_path in file_paths:
            audio = AudioSegment.from_file(file_path)
            audio = audio.set_channels(2).set_frame_rate(24000)
            combined += audio
        combined.export(output_file, format="mp3", bitrate="128k")
        for file_path in file_paths:
            os.remove(file_path)
            logging.info(f"Xóa file tạm: {file_path}")
        return True
    except Exception as e:
        logging.error(f"Lỗi khi ghép file: {e}")
        return False

# Route giao diện chính
@app.route('/')
def index():
    return render_template('index.html')

# Route xử lý TTS
@app.route('/tts', methods=['POST'])
def tts():
    try:
        # Xóa file cũ trong thư mục downloads
        for old_file in glob.glob(os.path.join(DOWNLOAD_FOLDER, "bai_giang_ausync_*.mp3")):
            os.remove(old_file)
            logging.info(f"Xóa file cũ: {old_file}")

        # Kiểm tra server trước
        if not check_server_status():
            logging.error("Không thể kết nối đến server AusyncLab")
            return jsonify({'error': 'Không thể kết nối đến server AusyncLab'}), 500

        text = request.form.get('text')
        if 'textFile' in request.files:
            file = request.files['textFile']
            if file.filename:
                file_path = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(file_path)
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
                os.remove(file_path)

        if not text:
            logging.error("Văn bản rỗng")
            return jsonify({'error': 'Văn bản rỗng'}), 400

        text_chunks = split_text(text, max_length=MAX_CHAR_LIMIT, min_length=MIN_CHUNK_LENGTH)
        logging.info(f"Chia thành {len(text_chunks)} đoạn")
        print(f"Chia thành {len(text_chunks)} đoạn")
        audio_urls = []
        output_files = []

        for i, chunk in enumerate(text_chunks):
            if len(chunk) > MAX_CHAR_LIMIT:
                logging.error(f"Đoạn {i+1} vượt giới hạn 500 ký tự: {len(chunk)}")
                return jsonify({'error': f'Đoạn {i+1} vượt giới hạn 500 ký tự ({len(chunk)} ký tự)'}), 400

            logging.info(f"Tạo audio cho đoạn {i+1} ({len(chunk)} ký tự)")
            print(f"Tạo audio cho đoạn {i+1} ({len(chunk)} ký tự)...")
            # Gửi yêu cầu TTS
            tts_url = "https://api.ausynclab.org/api/v1/speech/text-to-speech"
            data = {
                "audio_name": f"bai_giang_toan_lop5_part_{i+1}",
                "text": chunk,
                "voice_id": VOICE_ID,
                "speed": 1.0,
                "model_name": "myna-2",
                "language": "vi",
                "callback_url": CALLBACK_URL
            }
            headers = {
                "X-API-Key": API_KEY,
                "Content-Type": "application/json",
                "accept": "application/json"
            }
            res_tts = session.post(tts_url, json=data, headers=headers, timeout=120)
            res_tts.raise_for_status()

            audio_id = res_tts.json().get("result", {}).get("audio_id")
            if not audio_id:
                logging.error(f"Không tìm thấy audio_id cho đoạn {i+1}: {res_tts.json()}")
                return jsonify({'error': f'Không tìm thấy audio_id cho đoạn {i+1}'}), 500

            logging.info(f"Audio ID đoạn {i+1}: {audio_id}")
            print(f"Audio ID đoạn {i+1}: {audio_id}")
            # Polling lấy audio_url
            max_attempts = 60  # 300 giây
            for attempt in range(max_attempts):
                try:
                    audio_info_url = f"https://api.ausynclab.org/api/v1/speech/{audio_id}"
                    res_info = session.get(audio_info_url, headers=headers, timeout=150)
                    res_info.raise_for_status()
                    audio_data = res_info.json().get("result", {})
                    if audio_data.get("state") == "SUCCEED" and audio_data.get("audio_url"):
                        audio_urls.append(audio_data["audio_url"])
                        logging.info(f"Audio URL đoạn {i+1}: {audio_data['audio_url']}")
                        print(f"Audio URL đoạn {i+1}: {audio_data['audio_url']}")
                        break
                    logging.info(f"Đoạn {i+1} chưa sẵn sàng, thử lại {attempt + 1}/{max_attempts}")
                    print(f"Đoạn {i+1} chưa sẵn sàng, thử lại {attempt + 1}/{max_attempts}...")
                    time.sleep(5)
                except requests.exceptions.RequestException as e:
                    logging.warning(f"Polling lỗi đoạn {i+1}, thử lại {attempt + 1}/{max_attempts}: {e}")
                    if attempt == max_attempts - 1:
                        logging.error(f"Hết thời gian chờ cho đoạn {i+1}")
                        return jsonify({'error': f'Hết thời gian chờ cho đoạn {i+1}'}), 500
            else:
                logging.error(f"Hết thời gian chờ cho đoạn {i+1}")
                return jsonify({'error': f'Hết thời gian chờ cho đoạn {i+1}'}), 500

        # Tải file audio
        for i, audio_url in enumerate(audio_urls):
            logging.info(f"Tải file đoạn {i+1}: {audio_url}")
            print(f"Tải file đoạn {i+1}...")
            response = session.get(audio_url, timeout=150)
            response.raise_for_status()
            wav_file = os.path.join(DOWNLOAD_FOLDER, f"bai_giang_ausync_part_{i+1}.wav")
            with open(wav_file, "wb") as f:
                f.write(response.content)
            if os.path.getsize(wav_file) < 1000:
                logging.error(f"File đoạn {i+1} quá nhỏ: {os.path.getsize(wav_file)} bytes")
                return jsonify({'error': f'File đoạn {i+1} quá nhỏ, có thể bị lỗi'}), 500

            # Chuyển WAV sang MP3
            mp3_file = os.path.join(DOWNLOAD_FOLDER, f"bai_giang_ausync_part_{i+1}.mp3")
            audio = AudioSegment.from_wav(wav_file)
            audio = audio.set_channels(2).set_frame_rate(24000)
            audio.export(mp3_file, format="mp3", bitrate="128k")
            os.remove(wav_file)
            output_files.append(mp3_file)
            logging.info(f"Lưu MP3 đoạn {i+1}: {mp3_file}")
            print(f"Lưu MP3 đoạn {i+1}: {mp3_file}")

        # Ghép file MP3
        final_output = os.path.join(DOWNLOAD_FOLDER, "bai_giang_ausync_full.mp3")
        if len(output_files) > 1:
            if not merge_audio_files(output_files, final_output):
                logging.error("Lỗi khi ghép file MP3")
                return jsonify({'error': 'Lỗi khi ghép file MP3'}), 500
        else:
            os.rename(output_files[0], final_output)

        logging.info("Hoàn thành xử lý TTS")
        return jsonify({'downloadUrl': '/downloads/bai_giang_ausync_full.mp3', 'type': 'audio'})

    except requests.exceptions.ReadTimeout:
        logging.error("Hết thời gian chờ khi kết nối đến AusyncLab")
        return jsonify({'error': 'Hết thời gian chờ khi kết nối đến AusyncLab. Vui lòng thử lại.'}), 500
    except requests.exceptions.RequestException as e:
        logging.error(f"Lỗi kết nối mạng: {e}")
        return jsonify({'error': f'Lỗi kết nối mạng: {str(e)}'}), 500
    except Exception as e:
        logging.error(f"Lỗi tổng quát: {e}")
        return jsonify({'error': f'Lỗi: {str(e)}'}), 500

# Route tải file
@app.route('/downloads/<filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(port=5000, debug=True)