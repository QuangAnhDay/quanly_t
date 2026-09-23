import os
import urllib.parse
import requests
from typing import Optional

PROJECT_DIR = os.path.dirname(__file__)
THUMB_DIR = os.path.join(PROJECT_DIR, "4_thumbnails")

def generate_thumbnail(
    prompt: str,
    output_filename: str = "thumb.jpg",
    aspect_ratio: str = "9:16",
    output_path: Optional[str] = None
) -> str:
    """
    Tạo thumbnail chất lượng cao miễn phí sử dụng Pollinations (FLUX / SDXL).
    """
    if not output_path:
        if not (output_filename.endswith(".jpg") or output_filename.endswith(".png")):
            output_filename += ".jpg"
        output_path = os.path.join(THUMB_DIR, output_filename)
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    
    width, height = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
    
    # Bổ sung phong cách điện ảnh cho prompt
    enhanced_prompt = f"{prompt}, highly detailed, cinematic lighting, photorealistic, 8k resolution, trending on artstation"
    encoded_prompt = urllib.parse.quote(enhanced_prompt)
    
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&nologo=true"
    
    response = requests.get(image_url, timeout=45)
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        return output_path
    else:
        raise Exception(f"Không thể tải ảnh từ Pollinations (HTTP {response.status_code})")

if __name__ == "__main__":
    test_prompt = "mysterious ancient temple in a foggy Vietnamese mountain, cinematic lighting"
    print("Đang tạo thumbnail thử nghiệm...")
    t_out = generate_thumbnail(test_prompt, "test_thumb.jpg")
    print(f"Tạo thumbnail thành công tại: {t_out}")
