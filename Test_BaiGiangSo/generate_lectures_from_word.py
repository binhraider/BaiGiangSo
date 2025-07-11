import json
import time
import requests
import os
import re  # Thêm để trim lặp
from docx import Document
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# === CONFIG ===
load_dotenv()

WORD_PATH = "bai_giang_30_slide_day_du.docx"
OUTPUT_JSON = "slides_with_text.json"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Lỗi: Vui lòng thiết lập biến môi trường GEMINI_API_KEY trong file .env")

GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
MAX_RETRIES = 3
RETRY_DELAY = 1  # Backoff factor cho retry tự động

# Tạo session với retry
session = requests.Session()
retries = Retry(total=MAX_RETRIES, backoff_factor=RETRY_DELAY, status_forcelist=[429, 500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retries))

# === 1. TÁCH SLIDE TỪ WORD ===
def extract_slide_contents(doc_path):
    """Tách nội dung từ file Word dựa trên định dạng '# Slide'."""
    try:
        document = Document(doc_path)
    except Exception as e:
        print(f"❌ Không thể đọc file Word tại đường dẫn: {doc_path}")
        print(f"Lỗi chi tiết: {e}")
        return None

    slides = []
    current_slide = None

    for para in document.paragraphs:
        text = para.text.strip()
        if text.startswith("# Slide"):
            if current_slide:
                slides.append(current_slide)
            slide_title = text.replace("#", "").strip()
            current_slide = {"title": slide_title, "content": ""}
        elif current_slide and text:
            current_slide["content"] += text + " "
    
    if current_slide:
        slides.append(current_slide)
        
    return slides

# === 2. GỌI GEMINI API ===

# THAY THẾ HÀM generate_lecture CŨ BẰNG HÀM NÀY

def generate_lecture(text, max_length=2000, is_first_slide=False):
    """Gửi văn bản đến Gemini API và nhận về lời giảng đã được biên tập."""
    if not text.strip():
        return ""
    if len(text) > max_length:
        text = text[:max_length]

    # Prompt tối ưu mạnh hơn
    prompt = f"""
    Bạn là một giáo viên tiểu học. Viết lại nội dung gốc dưới đây thành lời giảng tự nhiên, ngắn gọn (200-400 ký tự), thân thiện như giáo viên lớp 1 đang giảng bài trực tiếp.
    - BẮT BUỘC tập trung vào nội dung chính, sử dụng từ ngữ đơn giản, thêm ví dụ minh họa cụ thể nếu cần (dùng đồ vật quen thuộc như táo, kẹo, ngón tay, đa dạng ví dụ giữa các Slide).
    - BẮT BUỘC KHÔNG bắt đầu bằng lời chào lặp như 'Chào các con', 'Hôm nay', 'Các con ơi', 'Nào, mình cùng' hoặc bất kỳ mở đầu chào hỏi nào trừ khi đây là Slide đầu tiên. Bắt đầu trực tiếp từ giải thích hoặc ví dụ.
    - Kết thúc bằng câu hỏi khuyến khích hoặc tóm tắt ngắn.
    - Giữ giọng điệu vui vẻ, dễ hiểu, tránh thuật ngữ khô khan.

    Nội dung gốc:
    {text}
    """
    if is_first_slide:
        # Cho phép slide đầu tiên có lời chào
        prompt = prompt.replace("BẮT BUỘC KHÔNG bắt đầu bằng lời chào lặp như 'Chào các con', 'Hôm nay', 'Các con ơi', 'Nào, mình cùng' hoặc bất kỳ mở đầu chào hỏi nào trừ khi đây là Slide đầu tiên.", "Có thể bắt đầu bằng một lời chào ngắn gọn và vui vẻ.")

    headers = {"Content-Type": "application/json"}
    body = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        res = session.post(GEMINI_URL, headers=headers, json=body, timeout=90)
        res.raise_for_status()
        data = res.json()
        generated_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # FIX 1: Loại bỏ logic re.sub không cần thiết vì prompt đã đủ tốt
        
        # FIX 2: Cắt độ dài một cách thông minh, không cắt giữa từ
        if len(generated_text) > 400:
            # Tìm khoảng trắng cuối cùng trước khi đạt tới giới hạn
            cut_pos = generated_text.rfind(' ', 0, 400)
            if cut_pos != -1:
                generated_text = generated_text[:cut_pos] + "..."
            else:
                # Nếu không có khoảng trắng (trường hợp hiếm), cắt cứng
                generated_text = generated_text[:400] + "..."

        return generated_text
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi khi gọi Gemini (sau khi đã thử lại): {e}.")
        return text
    except (KeyError, IndexError):
        print("❌ Cấu trúc phản hồi từ API không hợp lệ. Trả về văn bản gốc.")
        return text

# === 3. QUY TRÌNH CHÍNH ===
def main():
    """Quy trình chính: đọc file, xử lý từng slide và lưu kết quả."""
    print("📘 Đang đọc file Word...")
    slides_data = extract_slide_contents(WORD_PATH)
    
    if slides_data is None:
        print("🛑 Dừng chương trình do không đọc được file Word.")
        return

    result = []
    total_slides = len(slides_data)

    for idx, slide in enumerate(slides_data, start=1):
        print(f"🧠 Xử lý slide {idx}/{total_slides}: {slide['title']}")
        original = slide["content"]
        is_first = (idx == 1)  # Chỉ cho phép chào ở Slide 1
        generated = generate_lecture(original, is_first_slide=is_first)
        result.append({
            "slide_number": idx,
            "title": slide["title"],
            "original_text": original,
            "generated_lecture": generated,
            "audio_path": ""  # thêm sau
        })
        time.sleep(10)  # Tăng delay để tránh rate limit

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ Hoàn tất! {total_slides} slides đã được xử lý. Kết quả lưu tại: {OUTPUT_JSON}")

if __name__ == "__main__":
    main()