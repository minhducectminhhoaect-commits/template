import os
import requests
import random
import subprocess
import urllib.parse
from moviepy.editor import ImageClip, VideoFileClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips, vfx
from PIL import Image, ImageDraw, ImageFont
import textwrap
import time

# Patch for Moviepy 1.0.3 using new Pillow
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

os.makedirs('assets_v3', exist_ok=True)
os.makedirs('raw_footage', exist_ok=True)

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. Chuẩn bị source video thô để minh họa tính năng tự động cắt ghép
raw_video_path = 'raw_footage/raw_video.mp4'
if not os.path.exists(raw_video_path):
    print("Đang tải source video thô 10s (Big Buck Bunny) để test tính năng Auto-Trimming...")
    vid_url = "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/720/Big_Buck_Bunny_720_10s_1MB.mp4"
    with open(raw_video_path, 'wb') as f:
        f.write(requests.get(vid_url, verify=False, headers={'User-Agent': 'Mozilla/5.0'}).content)

scenes = [
    {
        "text": "Bạn có biết 3 sự thật thú vị này về Hệ Mặt Trời?",
        "type": "ai_image",
        "prompt": "A hyper-realistic 4K vertical image of the Solar System, glowing sun and planets, deep space background, cinematic lighting",
        "pan_dir": "down"
    },
    {
        "text": "Thứ nhất: Mặt Trời chiếm 99,8 phần trăm khối lượng của cả hệ.",
        "type": "raw_video",
        # Thuật toán sẽ tự động cắt một khoảng thời gian ngẫu nhiên từ raw video cho khớp với Audio
    },
    {
        "text": "Thứ hai: Một ngày trên Sao Kim dài hơn 1 năm trên Trái Đất.",
        "type": "ai_image",
        "prompt": "A cinematic highly detailed vertical landscape of Venus surface, extremely hot, glowing magma, alien planet terrain",
        "pan_dir": "up"
    },
    {
        "text": "Thứ ba: Sao Mộc có thể chứa 1300 Trái Đất bên trong.",
        "type": "raw_video",
    }
]

def generate_ai_image(prompt, output_path):
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=2200&nologo=true"
    print(f"Generating AI image via Pollinations (FLUX.1): {prompt}")
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=30, verify=False)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                break
        except Exception as e:
            print(f"AI Image generation failed on attempt {attempt+1}: {e}")
            time.sleep(2)

def create_text_overlay(text, output_path):
    img = Image.new('RGBA', (1080, 1920), (0,0,0,0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 1050, 1080, 1920], fill=(0,0,0,190))
    
    try: font = ImageFont.truetype("arialbd.ttf", 68)
    except: font = ImageFont.load_default()
            
    offset = 1300
    for line in textwrap.wrap(text, width=22):
        bbox = d.textbbox((0, 0), line, font=font)
        x = (1080 - (bbox[2] - bbox[0])) / 2
        
        stroke = 3
        d.text((x-stroke, offset), line, font=font, fill="black")
        d.text((x+stroke, offset), line, font=font, fill="black")
        d.text((x, offset-stroke), line, font=font, fill="black")
        d.text((x, offset+stroke), line, font=font, fill="black")
        
        d.text((x, offset), line, font=font, fill="#00FFCC")
        offset += (bbox[3] - bbox[1]) + 20
    img.save(output_path)

def apply_pan_effect(clip, duration, direction='down'):
    max_y = clip.h - 1920
    def fl(get_frame, t):
        frame = get_frame(t)
        y = int(max_y * (t / duration)) if direction == 'down' else int(max_y * (1 - (t / duration)))
        y = max(0, min(max_y, y))
        return frame[y:y+1920, 0:1080, :]
    return clip.fl(fl)

def process_raw_video(source_path, target_duration):
    clip = VideoFileClip(source_path)
    
    # Tìm khoảng thời gian bắt đầu ngẫu nhiên sao cho đủ thời lượng cần cắt
    max_start = max(0, clip.duration - target_duration)
    start_time = random.uniform(0, max_start)
    print(f"-> Tự động phân tích và trích xuất {target_duration:.2f}s từ giây thứ {start_time:.2f} của video gốc.")
    
    trimmed = clip.subclip(start_time, start_time + target_duration)
    
    # Crop video ngang thành chuẩn video dọc 9:16 (1080x1920)
    w, h = trimmed.size
    aspect = w / h
    target_aspect = 1080 / 1920
    
    if aspect > target_aspect:
        trimmed = trimmed.resize(height=1920)
        x_center = trimmed.size[0] / 2
        trimmed = trimmed.crop(x_center=x_center, y_center=1920/2, width=1080, height=1920)
    else:
        trimmed = trimmed.resize(width=1080)
        y_center = trimmed.size[1] / 2
        trimmed = trimmed.crop(x_center=1080/2, y_center=y_center, width=1080, height=1920)
        
    # Xóa audio gốc của video thô
    trimmed = trimmed.without_audio()
    return trimmed

clips = []
for i, scene in enumerate(scenes):
    print(f"\n--- Xử lý cảnh {i+1} ---")
    txt_path = f"assets_v3/txt_{i}.png"
    audio_path = f"assets_v3/audio_{i}.mp3"
    
    # Tạo TTS
    cmd = ["edge-tts", "--voice", "vi-VN-HoaiMyNeural", "--rate", "+10%", "--text", scene['text'], "--write-media", audio_path]
    for attempt in range(3):
        try:
            subprocess.run(cmd, check=True, shell=True)
            break
        except subprocess.CalledProcessError:
            print("Edge-TTS lỗi mạng. Đang thử lại...")
            time.sleep(2)
            
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration + 0.4
    
    # Xử lý Hình ảnh AI / Video Thô
    if scene['type'] == 'ai_image':
        bg_path = f"assets_v3/bg_{i}.jpg"
        generate_ai_image(scene['prompt'], bg_path)
        bg_clip = ImageClip(bg_path).set_duration(duration)
        bg_clip = apply_pan_effect(bg_clip, duration, scene['pan_dir'])
        
    elif scene['type'] == 'raw_video':
        bg_clip = process_raw_video(raw_video_path, duration)
        
    # Chèn Subtitle
    create_text_overlay(scene['text'], txt_path)
    txt_clip = ImageClip(txt_path).set_duration(duration)
    
    video = CompositeVideoClip([bg_clip, txt_clip])
    video = video.set_audio(audio_clip)
    clips.append(video)

print("\n[AI] Đang nối tất cả (Hình AI + Video cắt ghép + Audio + Sub) và render H.264 1080p...")
final = concatenate_videoclips(clips, method="compose")
final.write_videofile("demo_video_v3_ultimate.mp4", fps=30, codec="libx264", audio_codec="aac", bitrate="5000k")
print("Hoàn tất quy trình v3!")
