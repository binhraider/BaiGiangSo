import os
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip

# --- Cấu hình ---

# Thư mục chứa các video avatar đã tạo (ví dụ: video_001_slide_1.mp4, video_002_slide_2.mp4)
AVATAR_VIDEOS_DIR = "videos"

# Thư mục chứa các ảnh slide đã xuất từ PowerPoint (ví dụ: Slide1.JPG, Slide2.JPG)
SLIDES_IMAGES_DIR = "slides_images"

# Thư mục để lưu các video thành phẩm
FINAL_VIDEOS_DIR = "final_videos"

# --- Tùy chỉnh giao diện ---

# Kích thước video cuối cùng (chiều rộng, chiều cao)
# 1920x1080 (Full HD) là một lựa chọn tốt
FINAL_VIDEO_SIZE = (1920, 1080)

# Kích thước của video avatar (chiều rộng, chiều cao)
AVATAR_WIDTH = 480  # Chiều rộng khoảng 25% video Full HD

# Vị trí của video avatar trên slide (có thể là "left", "right", "center" và "top", "bottom", "center")
AVATAR_POSITION = ("left", "bottom")

# Khoảng cách lề (tính bằng pixel)
MARGIN = 40

def merge_avatar_and_slide(slide_image_path, avatar_video_path, output_path):
    """
    Ghép một ảnh slide và một video avatar thành video cuối cùng.
    """
    try:
        print(f"🎬 Bắt đầu xử lý: {os.path.basename(avatar_video_path)}")

        # 1. Tải video avatar và ảnh slide
        avatar_clip = VideoFileClip(avatar_video_path)
        
        # 2. Chuẩn hóa kích thước và đặt vị trí cho avatar
        # Thay đổi kích thước avatar theo chiều rộng đã định, chiều cao sẽ tự điều chỉnh
        resized_avatar_clip = avatar_clip.resize(width=AVATAR_WIDTH)
        
        # Đặt vị trí cho avatar có tính cả lề
        resized_avatar_clip = resized_avatar_clip.set_position(
            (
                FINAL_VIDEO_SIZE[0] - resized_avatar_clip.w - MARGIN, # Vị trí X (từ trái qua)
                FINAL_VIDEO_SIZE[1] - resized_avatar_clip.h - MARGIN  # Vị trí Y (từ trên xuống)
            )
        )

        # 3. Tạo nền slide
        # Tải ảnh slide, đặt thời lượng bằng với video avatar, và thay đổi kích thước cho vừa video cuối cùng
        slide_background = (
            ImageClip(slide_image_path)
            .set_duration(resized_avatar_clip.duration)
            .resize(FINAL_VIDEO_SIZE)
        )

        # 4. Ghép lại với nhau (đặt avatar lên trên nền)
        # ✅ ĐÃ SỬA LỖI LOGIC: `slide_background` làm nền, `resized_avatar_clip` ở lớp trên
        final_clip = CompositeVideoClip([slide_background, resized_avatar_clip])

        # 5. Ghi file video cuối cùng
        # codec="libx264" và audio_codec="aac" là các lựa chọn phổ biến, tương thích cao
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
        
        print(f"✅ Hoàn thành: {output_path}")

    except Exception as e:
        print(f"❌ Lỗi khi xử lý file {os.path.basename(avatar_video_path)}: {e}")

def process_all_videos():
    """
    Tìm và xử lý tất cả các cặp slide/video tương ứng.
    """
    # Tạo thư mục đầu ra nếu chưa có
    os.makedirs(FINAL_VIDEOS_DIR, exist_ok=True)
    
    try:
        # Lấy danh sách các video avatar và sắp xếp theo thứ tự
        avatar_videos = sorted(
            [f for f in os.listdir(AVATAR_VIDEOS_DIR) if f.endswith(".mp4")],
            key=lambda x: int(x.split('_')[-1].split('.')[0])  # ✅ SỬA: video_001_slide_1.mp4 -> lấy 1 từ slide_1
        )
    except FileNotFoundError:
        print(f"❌ Lỗi: Không tìm thấy thư mục '{AVATAR_VIDEOS_DIR}'. Hãy chắc chắn bạn đã chạy script tạo video trước đó.")
        return
    except (IndexError, ValueError):
        print("❌ Lỗi: Tên file trong thư mục 'videos' không đúng định dạng 'video_001_slide_1.mp4'.")  # ✅ SỬA: Message
        return

    for video_filename in avatar_videos:
        # Tìm ảnh slide tương ứng (ví dụ: video "video_001_slide_1.mp4" sẽ khớp với ảnh "Slide1.JPG")
        try:
            slide_number = video_filename.split('_')[-1].split('.')[0]  # ✅ SỬA: video_001_slide_1.mp4 -> lấy 1 từ slide_1
        except (IndexError, ValueError):
            print(f"⚠️ Tên file không hợp lệ '{video_filename}'. Bỏ qua.")
            continue

        # Thử cả 2 định dạng .PNG và .JPG phổ biến mà PowerPoint hay xuất ra
        slide_image_name_jpg = f"Slide{slide_number}.JPG" # PowerPoint thường xuất ra đuôi .JPG
        slide_image_name_png = f"Slide{slide_number}.PNG"
        
        slide_image_path_jpg = os.path.join(SLIDES_IMAGES_DIR, slide_image_name_jpg)
        slide_image_path_png = os.path.join(SLIDES_IMAGES_DIR, slide_image_name_png)

        if os.path.exists(slide_image_path_jpg):
            slide_image_path = slide_image_path_jpg
        elif os.path.exists(slide_image_path_png):
            slide_image_path = slide_image_path_png
        else:
            print(f"⚠️ Không tìm thấy ảnh cho video '{video_filename}' (đã tìm kiếm {slide_image_name_jpg} và {slide_image_name_png}). Bỏ qua.")
            continue
            
        avatar_video_path = os.path.join(AVATAR_VIDEOS_DIR, video_filename)
        output_video_path = os.path.join(FINAL_VIDEOS_DIR, f"final_{video_filename}")
        
        merge_avatar_and_slide(slide_image_path, avatar_video_path, output_video_path)

if __name__ == "__main__":
    process_all_videos()