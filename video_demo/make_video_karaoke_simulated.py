import os
import glob
import webvtt
import random
from PIL import Image, ImageDraw, ImageFont
import textwrap
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

os.makedirs('assets_simulated', exist_ok=True)

# 1. Tìm video/audio
files = glob.glob("ncgb.f*")
files.sort(key=os.path.getsize, reverse=True)
video_file = files[0]
audio_file = files[1]

# Cắt 30 giây (giây 20 đến 50)
v_clip = VideoFileClip(video_file).subclip(20, 50)
a_clip = AudioFileClip(audio_file).subclip(20, 50)
clip = v_clip.set_audio(a_clip)

w, h = clip.size

# 2. Đọc phụ đề VTT của YouTube
subs = webvtt.read('ncgb.vi.vtt')

# 3. Phân rã câu thành từng chữ (Simulate Word-Level Timestamps)
print("Đang bóc tách từng chữ dựa trên thuật toán Simulate Timestamps...")
word_data = []

for sub in subs:
    start_time = sub.start_in_seconds
    end_time = sub.end_in_seconds
    
    if end_time < 20 or start_time > 50:
        continue
        
    # Thời gian theo timeline subclip (0 -> 30)
    clip_start = max(0, start_time - 20)
    clip_end = min(30, end_time - 20)
    
    text = sub.text.strip().replace('\n', ' ')
    if not text: continue
    
    # Chia nhỏ thời gian cho từng chữ
    words = text.split()
    if not words: continue
    
    duration = clip_end - clip_start
    time_per_word = duration / len(words)
    
    for idx, w_str in enumerate(words):
        word_start = clip_start + idx * time_per_word
        word_end = word_start + time_per_word
        word_data.append({
            'word': w_str,
            'start': word_start,
            'end': word_end,
            'group_id': sub.start_in_seconds # Dùng mốc thời gian gốc để gom nhóm cùng 1 câu
        })

# 4. Gom nhóm lại thành từng câu để render theo kiểu Karaoke
groups = []
current_group = []
current_group_id = None

for wd in word_data:
    if wd['group_id'] != current_group_id:
        if current_group:
            groups.append(current_group)
        current_group = [wd]
        current_group_id = wd['group_id']
    else:
        current_group.append(wd)
if current_group:
    groups.append(current_group)

def create_karaoke_image(group, active_index):
    img = Image.new('RGBA', (w, h), (0,0,0,0))
    d = ImageDraw.Draw(img)
    try: font = ImageFont.truetype("arialbd.ttf", int(h*0.065))
    except: font = ImageFont.load_default()
    
    # Bọc dòng (Wrap) nếu câu dài
    max_w = w * 0.9
    lines = []
    current_line = []
    current_line_w = 0
    
    words_info = []
    
    for i, wd in enumerate(group):
        word_w = d.textbbox((0,0), wd['word'] + " ", font=font)[2]
        if current_line_w + word_w > max_w and current_line:
            lines.append(current_line)
            current_line = []
            current_line_w = 0
            
        current_line.append((i, wd['word']))
        current_line_w += word_w
    
    if current_line:
        lines.append(current_line)
        
    # Tính tổng chiều cao
    total_h = len(lines) * (d.textbbox((0,0), "A", font=font)[3] + 15)
    y_offset = h - total_h - 60 # Cách đáy 60px
    
    # Kẻ nền mờ
    d.rectangle([0, y_offset - 20, w, h], fill=(0,0,0,160))
    
    # Vẽ chữ
    for line in lines:
        line_w = sum(d.textbbox((0,0), word + " ", font=font)[2] for _, word in line)
        x_offset = (w - line_w) / 2
        
        for i, word in line:
            # Màu vàng cho từ đã hát/đang hát, màu trắng cho từ chưa hát
            color = "#FFCC00" if i <= active_index else "#FFFFFF"
            
            # Viền đen dày
            stroke = 3
            for dx in [-stroke, 0, stroke]:
                for dy in [-stroke, 0, stroke]:
                    d.text((x_offset+dx, y_offset+dy), word, font=font, fill="black")
                    
            d.text((x_offset, y_offset), word, font=font, fill=color)
            x_offset += d.textbbox((0,0), word + " ", font=font)[2]
            
        y_offset += d.textbbox((0,0), "A", font=font)[3] + 15
        
    path = f"assets_simulated/karaoke_{random.randint(100000,999999)}.png"
    img.save(path)
    return path

text_clips = []
print("Đang Render hiệu ứng đổi màu chữ...")
for group in groups:
    group_start = group[0]['start']
    group_end = group[-1]['end']
    
    # Hiển thị toàn bộ câu (Màu trắng) trước khi hát 0.5s
    pre_start = max(0, group_start - 0.5)
    if pre_start < group_start:
        img_path = create_karaoke_image(group, -1)
        txt_clip = ImageClip(img_path).set_start(pre_start).set_end(group_start).set_duration(group_start - pre_start)
        text_clips.append(txt_clip)
        
    # Chạy màu Vàng từng chữ
    for j, wd in enumerate(group):
        start_time = wd['start']
        if j < len(group) - 1:
            end_time = group[j+1]['start']
        else:
            end_time = group_end + 0.3 # Kéo dài chữ cuối 1 xíu
            
        img_path = create_karaoke_image(group, j)
        txt_clip = ImageClip(img_path).set_start(start_time).set_end(end_time).set_duration(end_time - start_time)
        text_clips.append(txt_clip)

final = CompositeVideoClip([clip] + text_clips)
print("Đang xuất file video...")
final.write_videofile("ncgb_karaoke_word_by_word.mp4", fps=24, codec="libx264", audio_codec="aac")
print("Hoàn tất Video Karaoke!")
