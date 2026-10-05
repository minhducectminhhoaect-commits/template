import os
import requests
from gtts import gTTS
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
from PIL import Image, ImageDraw, ImageFont
import textwrap

os.makedirs('assets', exist_ok=True)

# 1. Kịch bản & Data
scenes = [
    {
        "text": "Bạn có biết 3 sự thật thú vị này về Hệ Mặt Trời?",
        "image_url": "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?q=80&w=1920",
    },
    {
        "text": "Thứ nhất: Mặt Trời chiếm 99,8 phần trăm khối lượng của cả hệ.",
        "image_url": "https://images.unsplash.com/photo-1542621334-a254cf47733d?q=80&w=1920",
    },
    {
        "text": "Thứ hai: Một ngày trên Sao Kim dài hơn 1 năm trên Trái Đất.",
        "image_url": "https://images.unsplash.com/photo-1614728894747-a83421e2b9c9?q=80&w=1920",
    },
    {
        "text": "Thứ ba: Sao Mộc có thể chứa 1300 Trái Đất bên trong.",
        "image_url": "https://images.unsplash.com/photo-1614730321146-b6fa6a46bcb4?q=80&w=1920",
    }
]

def add_text_to_image(image_path, text, output_path):
    img = Image.open(image_path).convert('RGB')
    
    # Center crop and resize to 1080x1920 (9:16)
    w, h = img.size
    aspect = w / h
    target_aspect = 1080 / 1920
    
    if aspect > target_aspect:
        # Image is wider than target
        new_w = int(h * target_aspect)
        offset = (w - new_w) // 2
        img = img.crop((offset, 0, offset + new_w, h))
    else:
        # Image is taller than target
        new_h = int(w / target_aspect)
        offset = (h - new_h) // 2
        img = img.crop((0, offset, w, offset + new_h))
        
    img = img.resize((1080, 1920), Image.Resampling.LANCZOS)
    
    try:
        font = ImageFont.truetype("arial.ttf", 60)
    except:
        font = ImageFont.load_default()
        
    # Thêm nền mờ (dark overlay) phía dưới để chữ nổi bật hơn
    overlay = Image.new('RGBA', img.size, (0,0,0,0))
    d_overlay = ImageDraw.Draw(overlay)
    d_overlay.rectangle([0, 1200, 1080, 1920], fill=(0,0,0,160))
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(img)
    
    offset = 1400
    for line in textwrap.wrap(text, width=24):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        x = (1080 - text_w) / 2
        
        # Tạo viền chữ (stroke)
        stroke = 2
        draw.text((x-stroke, offset), line, font=font, fill="black")
        draw.text((x+stroke, offset), line, font=font, fill="black")
        draw.text((x, offset-stroke), line, font=font, fill="black")
        draw.text((x, offset+stroke), line, font=font, fill="black")
        
        # Chữ chính màu vàng
        draw.text((x, offset), line, font=font, fill="#FFCC00")
        offset += text_h + 15
        
    img.save(output_path)

print("Đang tải hình ảnh và tạo giọng đọc...")
clips = []
for i, scene in enumerate(scenes):
    img_path = f"assets/raw_{i}.jpg"
    processed_img_path = f"assets/scene_{i}.jpg"
    
    print(f"Downloading scene {i+1}...")
    with open(img_path, 'wb') as f:
        f.write(requests.get(scene['image_url']).content)
        
    print(f"Adding text to scene {i+1}...")
    add_text_to_image(img_path, scene['text'], processed_img_path)
    
    print(f"Generating audio for scene {i+1}...")
    audio_path = f"assets/audio_{i}.mp3"
    tts = gTTS(scene['text'], lang='vi')
    tts.save(audio_path)
    
    audio_clip = AudioFileClip(audio_path)
    # Tăng thêm một chút thời gian để khán giả kịp đọc
    duration = audio_clip.duration + 0.4
    
    img_clip = ImageClip(processed_img_path).set_duration(duration)
    img_clip = img_clip.set_audio(audio_clip)
    clips.append(img_clip)

print("Đang nối các đoạn video và render file mp4...")
final_video = concatenate_videoclips(clips, method="compose")
final_video.write_videofile("demo_video.mp4", fps=24, codec="libx264", audio_codec="aac")
print("Hoàn tất!")
