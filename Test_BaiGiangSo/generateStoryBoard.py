import os
import json
import time
import csv
import requests
import argparse
from dotenv import load_dotenv

# === CONFIG ===
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={GEMINI_API_KEY}"  # Sửa model thành gemini-1.5-flash (model hợp lệ)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Generate Storyboard from JSON")
    parser.add_argument("--json", default="slides_with_text_temp.json", help="Path to input JSON")
    parser.add_argument("--output-json", default="storyboard.json", help="Path to output JSON")
    parser.add_argument("--output-csv", default="storyboard.csv", help="Path to output CSV")
    return parser.parse_args()

def generate_storyboard_elements_with_ai(lecture_text):
    """
    Sử dụng Gemini để tạo ra các yếu tố storyboard một cách sáng tạo.
    """
    if not GEMINI_API_KEY:
        print("⚠️  Không tìm thấy GEMINI_API_KEY, sử dụng logic mặc định.")
        return {"action": "Giảng viên trình bày", "graphics": "Hiển thị slide", "camera_angle": "Trung cảnh"}

    prompt = f"""
    Bạn là một đạo diễn video chuyên sản xuất các bài giảng e-learning cho trẻ em. Dựa vào lời giảng dưới đây, hãy đề xuất các yếu tố cho storyboard theo định dạng JSON.
    
    YÊU CẦU:
    - "action": Mô tả hành động của giảng viên (ví dụ: "cười tươi và chỉ vào màn hình", "giơ 2 ngón tay", "vẽ một hình tròn lên bảng"). Hành động phải khớp với lời giảng.
    - "graphics": Đề xuất các yếu tố đồ họa cần hiển thị trên màn hình (ví dụ: "hiện chữ 'Phép cộng'", "icon quả táo bay vào", "số 5 được khoanh tròn").
    - "camera_angle": Đề xuất góc máy (ví dụ: "cận cảnh biểu cảm", "trung cảnh thấy tay", "toàn cảnh").

    LƯU Ý: Chỉ trả về một đối tượng JSON duy nhất, không có giải thích hay ký tự ``` nào khác.
    
    LỜI GIẢNG:
    "{lecture_text}"
    
    JSON OUTPUT:
    """

    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
        }
    }
    
    try:
        res = requests.post(GEMINI_URL, headers=headers, json=body, timeout=60)
        res.raise_for_status()
        storyboard_data = res.json()["candidates"][0]["content"]["parts"][0]["text"]
        ai_elements = json.loads(storyboard_data)
        
        # Xử lý nếu ai_elements là list (lấy phần tử đầu tiên)
        if isinstance(ai_elements, list) and ai_elements:
            ai_elements = ai_elements[0]
        
        if not isinstance(ai_elements, dict):
            raise ValueError("Phản hồi từ Gemini không phải dict hợp lệ.")
        
        return ai_elements
    except Exception as e:
        print(f"❌ Lỗi khi gọi Gemini cho storyboard: {e}. Sử dụng logic mặc định.")
        return {"action": "Giảng viên trình bày", "graphics": "Hiển thị slide", "camera_angle": "Trung cảnh"}


def generateStoryboard(json_path, output_json_path, output_csv_path):
    """Generate Storyboard from JSON and save as JSON/CSV."""
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"File {json_path} không tồn tại")
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            slides = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"File JSON không hợp lệ: {e}")
    
    if not slides:
        raise ValueError("File JSON rỗng hoặc không chứa Slide")

    print("📖 Generating Storyboard...")
    storyboard = []
    total_slides = len(slides)

    for i, slide in enumerate(slides):
        slide_num = slide.get("slide_number", i + 1)
        print(f"🖼️  Processing Slide {slide_num}/{total_slides}: {slide.get('title', 'No Title')}")
        
        lecture = slide.get("generated_lecture", "")
        
        # FIX: Không cần tính lại duration, chỉ cần đọc từ slide
        duration = slide.get("duration", 0)
        print(f"    - ⏱ Duration (from JSON): {duration}s")
        
        # NÂNG CẤP: Gọi AI để tạo storyboard
        if lecture:
            print("    - 🤖 Calling AI Director for creative ideas...")
            ai_elements = generate_storyboard_elements_with_ai(lecture)
            slide["action"] = ai_elements.get("action", "Giảng viên trình bày")
            slide["graphics"] = ai_elements.get("graphics", "Hiển thị slide")
            slide["camera_angle"] = ai_elements.get("camera_angle", "Trung cảnh")
            time.sleep(10) # Thêm độ trễ để tránh lỗi rate limit của Gemini
        else:
            slide["action"] = "N/A"
            slide["graphics"] = "N/A"
            slide["camera_angle"] = "N/A"

        storyboard.append(slide)

    # Save as JSON
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(storyboard, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved Storyboard JSON to: {output_json_path}")

    # Save as CSV
    if storyboard:
        fieldnames = [
            "slide_number", "title", "generated_lecture", "audio_path", 
            "duration", "action", "graphics", "camera_angle"
        ]
        with open(output_csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for slide in storyboard:
                filtered_slide = {key: slide.get(key, "") for key in fieldnames}
                writer.writerow(filtered_slide)
        print(f"✅ Saved Storyboard CSV to: {output_csv_path}")

if __name__ == "__main__":
    args = parse_args()
    generateStoryboard(args.json, args.output_json, args.output_csv)