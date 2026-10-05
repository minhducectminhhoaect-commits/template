import os
import requests
import math
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
import textwrap
import subprocess

os.makedirs('assets_v2', exist_ok=True)

scenes = [
    {
        "text": "Bạn có biết 3 sự thật thú vị này về Hệ Mặt Trời?",
        "image_url": "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?q=80&w=1920",
        "pan_dir": "down"
    },
    {
        "text": "Thứ nhất: Mặt Trời chiếm 99,8 phần trăm khối lượng của cả hệ.",
        "image_url": "https://images.unsplash.com/photo-1542621334-a254cf47733d?q=80&w=1920",
        "pan_dir": "up"
    },
    {
        "text": "Thứ hai: Một ngày trên Sao Kim dài hơn 1 năm trên Trái Đất.",
        "image_url": "https://images.unsplash.com/photo-1614728894747-a83421e2b9c9?q=80&w=1920",
        "pan_dir": "down"
    },
    {
        "text": "Thứ ba: Sao Mộc có thể chứa 1300 Trái Đất bên trong.",
        "image_url": "https://images.unsplash.com/photo-1614730321146-b6fa6a46bcb4?q=80&w=1920",
        "pan_dir": "up"
    }
]

def prepare_background(image_path, output_path):
    img = Image.open(image_path).convert('RGB')
    w, h = img.size
    
    # Tạo ảnh lớn hơn (1080 x 2200) để làm không gian cho hiệu ứng di chuyển camera
    target_w, target_h = 1080, 2200
    aspect = w / h
    target_aspect = target_w / target_h
    
    if aspect > target_aspect:
        new_w = int(h * target_aspect)
        offset = (w - new_w) // 2
        img = img.crop((offset, 0, offset + new_w, h))
    else:
        new_h = int(w / target_aspect)
        offset = (h - new_h) // 2
        img = img.crop((0, offset, w, offset + new_h))
        
    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    img.save(output_path)

def create_text_overlay(text, output_path):
    img = Image.new('RGBA', (1080, 1920), (0,0,0,0))
    d = ImageDraw.Draw(img)
    
    # Nền mờ cho chữ dễ đọc
    d.rectangle([0, 1050, 1080, 1920], fill=(0,0,0,190))
    
    # Thử font Arial Bold
    try:
        font = ImageFont.truetype("arialbd.ttf", 68)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", 68)
        except:
            font = ImageFont.load_default()
            
    offset = 1300
    for line in textwrap.wrap(text, width=22):
        bbox = d.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        x = (1080 - text_w) / 2
        
        # Đổ viền (Stroke) dày cho chữ
        stroke = 3
        d.text((x-stroke, offset), line, font=font, fill="black")
        d.text((x+stroke, offset), line, font=font, fill="black")
        d.text((x, offset-stroke), line, font=font, fill="black")
        d.text((x, offset+stroke), line, font=font, fill="black")
        
        d.text((x-stroke, offset+stroke), line, font=font, fill="black")
        d.text((x+stroke, offset+stroke), line, font=font, fill="black")
        d.text((x-stroke, offset-stroke), line, font=font, fill="black")
        d.text((x+stroke, offset-stroke), line, font=font, fill="black")
        
        # Chữ Cyan nổi bật
        d.text((x, offset), line, font=font, fill="#00FFCC")
        offset += text_h + 20
        
    img.save(output_path)

def apply_pan_effect(clip, duration, direction='down'):
    # Ảnh nền lớn hơn (1080x2200), ta cắt ra 1080x1920 và di chuyển vùng cắt
    max_y = clip.h - 1920
    
    def fl(get_frame, t):
        frame = get_frame(t)
        if direction == 'down':
            y = int(max_y * (t / duration))
        else:
            y = int(max_y * (1 - (t / duration)))
            
        y = max(0, min(max_y, y))
        return frame[y:y+1920, 0:1080, :]
        
    return clip.fl(fl)

clips = []
for i, scene in enumerate(scenes):
    print(f"Processing scene {i+1}...")
    img_path = f"assets_v2/raw_{i}.jpg"
    bg_path = f"assets_v2/bg_{i}.jpg"
    txt_path = f"assets_v2/txt_{i}.png"
    audio_path = f"assets_v2/audio_{i}.mp3"
    
    if not os.path.exists(img_path):
        with open(img_path, 'wb') as f:
            f.write(requests.get(scene['image_url']).content)
            
    prepare_background(img_path, bg_path)
    create_text_overlay(scene['text'], txt_path)
    
    # Dùng edge-tts với giọng vi-VN-HoaiMyNeural cực kỳ tự nhiên
    cmd = ["edge-tts", "--voice", "vi-VN-HoaiMyNeural", "--rate", "+10%", "--text", scene['text'], "--write-media", audio_path]
    import time
    for attempt in range(3):
        try:
            subprocess.run(cmd, check=True, shell=True)
            break
        except subprocess.CalledProcessError:
            print(f"Edge-TTS failed on attempt {attempt+1}. Retrying...")
            time.sleep(2)
    else:
        print("Falling back to gTTS")
        from gtts import gTTS
        gTTS(scene['text'], lang='vi').save(audio_path)
    
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration + 0.4
    
    bg_clip = ImageClip(bg_path).set_duration(duration)
    # Hiệu ứng chuyển động (Pan)
    bg_clip = apply_pan_effect(bg_clip, duration, scene['pan_dir'])
    
    txt_clip = ImageClip(txt_path).set_duration(duration)
    
    video = CompositeVideoClip([bg_clip, txt_clip])
    video = video.set_audio(audio_clip)
    clips.append(video)

print("Đang nối các cảnh và render H.264 1080p, 5000k bitrate...")
final = concatenate_videoclips(clips, method="compose")
final.write_videofile("demo_video_v2.mp4", fps=30, codec="libx264", audio_codec="aac", bitrate="5000k")
print("Hoàn tất Phiên bản 2.0!")
