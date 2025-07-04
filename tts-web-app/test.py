def split_text_improved(text, max_length=500):
    """
    Chia văn bản thành các chunk nhỏ hơn max_length một cách mạnh mẽ hơn.
    - Giữ lại các đoạn văn (dòng trống).
    - Xử lý các từ dài hơn max_length.
    """
    chunks = []
    # 1. Tách văn bản thành các đoạn dựa trên ký tự xuống dòng
    paragraphs = text.split('\n')

    for i, paragraph in enumerate(paragraphs):
        # Nếu là một dòng trống, ta coi nó là một chunk rỗng để giữ cấu trúc
        if not paragraph:
            # Nếu chunk cuối cùng cũng là dòng trống thì không thêm nữa
            if chunks and chunks[-1] == "":
                continue
            chunks.append("")
            continue

        words = paragraph.split()
        current_chunk = ""
        for word in words:
            # Xử lý từ quá dài
            if len(word) > max_length:
                # Nếu có chunk đang chờ, thêm vào trước
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                # Chia nhỏ từ dài
                while len(word) > max_length:
                    chunks.append(word[:max_length])
                    word = word[max_length:]
                # Phần còn lại của từ (nếu có) sẽ bắt đầu chunk mới
                if word:
                    current_chunk = word + " "
                continue

            # Nếu thêm từ mới sẽ vượt quá độ dài, chốt chunk hiện tại
            if len(current_chunk) + len(word) + 1 > max_length:
                chunks.append(current_chunk.strip())
                current_chunk = word + " "
            else:
                current_chunk += word + " "

        # Thêm chunk cuối cùng của đoạn văn nếu có
        if current_chunk:
            chunks.append(current_chunk.strip())

        # Nếu đây không phải là đoạn cuối cùng và có nội dung,
        # và chunk cuối cùng không phải là dòng trống, ta có thể thêm
        # một dòng trống để phân biệt các đoạn. Tuy nhiên, việc tách riêng đã giữ cấu trúc.
        # Nếu bạn muốn gộp các đoạn lại, bạn có thể dùng `\n`.join(chunks)
        # Phiên bản hiện tại sẽ cho ra một list các chuỗi.

    # Hợp nhất các dòng trống liên tiếp thành một
    final_chunks = []
    for i, chunk in enumerate(chunks):
        if chunk == "" and (i == 0 or chunks[i-1] == ""):
            continue
        final_chunks.append(chunk)


    return final_chunks

# --- Ví dụ ---
text_with_empty_lines = "Đây là đoạn 1.\nNó có một vài dòng.\n\nĐây là đoạn 2, bắt đầu sau một dòng trống."
text_with_long_word = "Một từsiêudàikhôngthểtinđượcmàchúngtaphảichianóralàmnhiềuphần nhỏ hơn."
text_with_extra_spaces = "Từ    1     Từ    2"


print("--- Thử nghiệm với dòng trống ---")
print(split_text_improved(text_with_empty_lines, max_length=30))
# Kết quả mong muốn: ['Đây là đoạn 1.', 'Nó có một vài dòng.', '', 'Đây là đoạn 2, bắt đầu sau', 'một dòng trống.']

print("\n--- Thử nghiệm với từ dài ---")
print(split_text_improved(text_with_long_word, max_length=20))
# Kết quả mong muốn: ['Một', 'từsiêudàikhôngthểti', 'nđượcmàchúngtaphảic', 'hianóralàmnhiềuphần', 'nhỏ hơn.']

print("\n--- Thử nghiệm với khoảng trắng thừa ---")
print(split_text_improved(text_with_extra_spaces, max_length=500))
# Kết quả: ['Từ 1 Từ 2'] (vẫn chuẩn hóa khoảng trắng, đây là hành vi của split())