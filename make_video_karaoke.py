import os
import subprocess
import requests
import webvtt
from PIL import Image, ImageDraw, ImageFont
import urllib.parse
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Patch cho Pillow 10
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

os.makedirs('assets_karaoke', exist_ok=True)

# 1 cảnh siêu ngắn để phô diễn hiệu ứng
scene = {
    "text": "Khám phá bí mật vũ trụ mà bạn chưa từng biết đến!",
    "prompt": "A hyper-realistic 4K image of a glowing galaxy, deep space, cinematic lighting"
}

# 1. Sinh ảnh AI nền
bg_path = "assets_karaoke/bg.jpg"
print("[1] Đang đẻ ảnh AI nền từ Pollinations...")
url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(scene['prompt'])}?width=1080&height=1920&nologo=true"
response = requests.get(url, verify=False)
with open(bg_path, 'wb') as f:
    f.write(response.content)

import asyncio
import edge_tts

# 2. Sinh Audio và Subtitles (Word Boundaries) bằng edge-tts API
audio_path = "assets_karaoke/audio.mp3"
print("[2] Đang tạo Audio và trích xuất Timestamp từng chữ (Karaoke)...")

word_boundaries = []

async def amain():
    communicate = edge_tts.Communicate(scene['text'], "vi-VN-HoaiMyNeural", rate="+5%")
    with open(audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offset và duration tính bằng 100-nanosecond (chuẩn Windows)
                start_sec = chunk["offset"] / 10000000.0
                duration_sec = chunk["duration"] / 10000000.0
                word_boundaries.append({
                    "word": chunk["text"],
                    "start": start_sec,
                    "end": start_sec + duration_sec
                })

# Chạy vòng lặp Asyncio để lấy data
asyncio.run(amain())

audio_clip = AudioFileClip(audio_path)
duration = audio_clip.duration + 0.5
bg_clip = ImageClip(bg_path).set_duration(duration)

# Làm tối nền 1 chút để nổi chữ
def darken(image_clip):
    return image_clip.fl_image(lambda pic: (pic * 0.5).astype('uint8'))
bg_clip = darken(bg_clip)

# 3. Đọc dữ liệu mili-giây và vẽ chữ nhấp nháy (Hormozi Style)
print("[3] Đang phân tích mili-giây và vẽ chữ nhấp nháy (Hormozi Style)...")

def create_word_image(word, index):
    img = Image.new('RGBA', (1080, 1920), (0,0,0,0))
    d = ImageDraw.Draw(img)
    
    try: font = ImageFont.truetype("arialbd.ttf", 150) # Font siêu to khổng lồ
    except: font = ImageFont.load_default()
    
    bbox = d.textbbox((0, 0), word, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    
    x = (1080 - w) / 2
    y = 900 # Giữa màn hình
    
    # Màu nhảy liên tục theo chu kỳ
    colors = ["#FFCC00", "#00FFCC", "#FF00FF", "#FFFFFF", "#00FF00"]
    color = colors[index % len(colors)]
    
    # Bóng đổ sâu (Drop shadow)
    d.text((x+8, y+8), word, font=font, fill="black")
    
    # Viền chữ
    stroke = 6
    d.text((x-stroke, y), word, font=font, fill="black")
    d.text((x+stroke, y), word, font=font, fill="black")
    d.text((x, y-stroke), word, font=font, fill="black")
    d.text((x, y+stroke), word, font=font, fill="black")
    d.text((x-stroke, y-stroke), word, font=font, fill="black")
    d.text((x+stroke, y+stroke), word, font=font, fill="black")
    
    # Lõi chữ
    d.text((x, y), word, font=font, fill=color)
    
    path = f"assets_karaoke/word_{index}.png"
    img.save(path)
    return path

text_clips = []
# Duyệt qua từng từ một
for i, sub in enumerate(word_boundaries):
    word = sub['word'].strip()
    if not word: continue
    
    start_time = sub['start']
    end_time = sub['end']
    
    img_path = create_word_image(word, i)
    
    # Thiết lập clip chữ nảy lên khớp thời gian
    txt_clip = ImageClip(img_path).set_start(start_time).set_end(end_time).set_duration(end_time - start_time)
    text_clips.append(txt_clip)

# Gom tất cả các chữ nhảy vào nền
video = CompositeVideoClip([bg_clip] + text_clips)
video = video.set_audio(audio_clip)

print("[4] Đang Render siêu tốc...")
video.write_videofile("demo_karaoke.mp4", fps=30, codec="libx264", audio_codec="aac")
print("Thành công xuất xưởng!")
