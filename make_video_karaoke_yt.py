import os
import glob
import webvtt
from PIL import Image, ImageDraw, ImageFont
import textwrap
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip

# Patch cho Pillow 10
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# Tìm file video và audio riêng biệt do yt-dlp tải về
files = glob.glob("ncgb.f*")
files.sort(key=os.path.getsize, reverse=True)
video_file = files[0] # File lớn nhất (mp4)
audio_file = files[1] # File nhỏ hơn (webm)
audio_file = files[1] # File nhỏ hơn thường là audio

print(f"Video file: {video_file}")
print(f"Audio file: {audio_file}")

# Lấy từ giây 20 đến 50 (30 giây) đoạn có hát
v_clip = VideoFileClip(video_file).subclip(20, 50)
a_clip = AudioFileClip(audio_file).subclip(20, 50)
clip = v_clip.set_audio(a_clip)

w, h = clip.size
os.makedirs('assets_karaoke', exist_ok=True)

subs = webvtt.read('ncgb.vi.vtt')
text_clips = []

def create_sub_image(text, i):
    img = Image.new('RGBA', (w, h), (0,0,0,0))
    d = ImageDraw.Draw(img)
    try: font = ImageFont.truetype("arialbd.ttf", int(h*0.06)) # Tùy chỉnh font size theo video
    except: font = ImageFont.load_default()
    
    lines = textwrap.wrap(text, width=40)
    
    # Tính tổng chiều cao
    total_h = 0
    for line in lines:
        bbox = d.textbbox((0, 0), line, font=font)
        total_h += bbox[3] - bbox[1] + 10
        
    y_offset = h - total_h - 50 # Cách đáy 50px
    
    for line in lines:
        bbox = d.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (w - text_w) / 2
        
        stroke = 2
        d.text((x-stroke, y_offset), line, font=font, fill="black")
        d.text((x+stroke, y_offset), line, font=font, fill="black")
        d.text((x, y_offset-stroke), line, font=font, fill="black")
        d.text((x, y_offset+stroke), line, font=font, fill="black")
        
        d.text((x, y_offset), line, font=font, fill="#FFCC00")
        y_offset += text_h + 10
        
    path = f"assets_karaoke/sub_{i}.png"
    img.save(path)
    return path

print("Đang đồng bộ phụ đề...")
for i, sub in enumerate(subs):
    start_time = sub.start_in_seconds
    end_time = sub.end_in_seconds
    
    if end_time < 20 or start_time > 50:
        continue
        
    clip_start = max(0, start_time - 20)
    clip_end = min(30, end_time - 20)
    
    text = sub.text.strip().replace('\n', ' ')
    if not text:
        continue
        
    img_path = create_sub_image(text, i)
    txt_clip = ImageClip(img_path).set_start(clip_start).set_end(clip_end).set_duration(clip_end - clip_start)
    text_clips.append(txt_clip)

final = CompositeVideoClip([clip] + text_clips)

print("Đang Render MV Karaoke...")
final.write_videofile("ngay_chua_giong_bao_karaoke.mp4", fps=24, codec="libx264", audio_codec="aac")
print("Hoàn tất!")
