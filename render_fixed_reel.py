import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Paths
img_path = Path(r"C:\Users\PANKAJ\.gemini\antigravity\brain\f062ec80-f2d6-4fb7-9d92-186893a74276\candid_real_selfie_1789370200781.jpg")
font_path = Path(r"assets/fonts/SF-Pro-Display-Semibold.otf")
emoji_moon = Path(r"assets/emojis/1f31a.png")
emoji_kiss = Path(r"assets/emojis/1f48b.png")
overlay_path = Path(r"data/temp/fixed_reel_overlay.png")
audio_path = Path(r"data/audio/sensual_ambient.mp3")
out_video = Path(r"data/output/fixed_ai_reel.mp4")

# Text to render (Compact, wrapped into 3 short lines, max 4 words per line)
text_lines = [
    "Ghar pe sab so rahe hain...",
    "aur mera dimaag tumhari",
    "shararaton me uljha hua hai"
]

font_size = 46
font = ImageFont.truetype(str(font_path), font_size)

canvas = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
draw = ImageDraw.Draw(canvas)

# Calculate measurements
line_metrics = []
emoji_size = 44
emoji_gap = 10

for idx, line in enumerate(text_lines):
    bbox = draw.textbbox((0, 0), line, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    if idx == len(text_lines) - 1:
        # Last line has two emojis
        total_w = w + (emoji_size * 2) + (emoji_gap * 2)
    else:
        total_w = w
    line_metrics.append((w, h, total_w))

line_spacing = 22
total_height = sum(m[1] for m in line_metrics) + (len(text_lines) - 1) * line_spacing
max_block_w = max(m[2] for m in line_metrics)

# Position centered in lower half (around chest/waist level of the selfie)
start_y = 1180
pad_x = 44
pad_y = 30

# Translucent dark glass card
card_box = [
    (1080 - max_block_w) // 2 - pad_x,
    start_y - pad_y,
    (1080 + max_block_w) // 2 + pad_x,
    start_y + total_height + pad_y
]
draw.rounded_rectangle(card_box, radius=24, fill=(10, 10, 12, 165))

# Draw lines
curr_y = start_y
for idx, line in enumerate(text_lines):
    w, h, total_w = line_metrics[idx]
    x = (1080 - total_w) // 2

    # Drop shadow
    draw.text((x + 2, curr_y + 2), line, font=font, fill=(0, 0, 0, 220))
    # Crisp white text
    draw.text((x, curr_y), line, font=font, fill=(255, 255, 255, 255))

    if idx == len(text_lines) - 1:
        # Paste Apple iOS Emojis on last line
        moon_img = Image.open(emoji_moon).resize((emoji_size, emoji_size), Image.Resampling.LANCZOS)
        kiss_img = Image.open(emoji_kiss).resize((emoji_size, emoji_size), Image.Resampling.LANCZOS)
        canvas.paste(moon_img, (x + w + emoji_gap, curr_y - 2), moon_img)
        canvas.paste(kiss_img, (x + w + emoji_gap + emoji_size + emoji_gap, curr_y - 2), kiss_img)

    curr_y += h + line_spacing

overlay_path.parent.mkdir(parents=True, exist_ok=True)
canvas.save(str(overlay_path))
print(f"Overlay saved. Max width: {max_block_w}px (Safe bound is 1080px). Perfectly fits inside screen!")

# Render with FFmpeg:
# 1. Base image with smooth 10% linear zoom (zero shake)
# 2. Composite text overlay
# 3. Synchronized soft fade-in (1.2s) and fade-out (1.2s)
# 4. Synchronized audio fade-in & out
filter_complex = (
    "[0:v]scale=1080:1920,"
    "zoompan=z='min(1.0+0.0004*on,1.10)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=250:s=1080x1920:fps=25[base];"
    "[base][1:v]overlay=0:0[combined];"
    "[combined]fade=t=in:st=0:d=1.2,fade=t=out:st=8.8:d=1.2,format=yuv420p[v];"
    "[2:a]volume=0.85,afade=t=in:st=0:d=1.2,afade=t=out:st=8.8:d=1.2[a]"
)

out_video.parent.mkdir(parents=True, exist_ok=True)
cmd = [
    "ffmpeg", "-y",
    "-loop", "1", "-i", str(img_path),
    "-loop", "1", "-i", str(overlay_path),
    "-i", str(audio_path),
    "-filter_complex", filter_complex,
    "-map", "[v]",
    "-map", "[a]",
    "-t", "10",
    "-c:v", "libx264",
    "-preset", "fast",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-b:a", "192k",
    "-movflags", "+faststart",
    str(out_video)
]

print("Rendering video with FFmpeg...")
res = subprocess.run(cmd, capture_output=True, text=True)
if res.returncode != 0:
    print("FFmpeg error:", res.stderr[-500:])
else:
    print(f"Rendered successfully! File: {out_video} ({out_video.stat().st_size} bytes)")
