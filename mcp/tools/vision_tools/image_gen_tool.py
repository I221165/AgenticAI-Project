import os
import random
import time
import urllib.parse
from typing import Optional
from pydantic import BaseModel, Field
from ...base_tool import BaseAgenticTool

import requests


class ImageGenArgs(BaseModel):
    prompt: str = Field(..., description="The image generation prompt.")
    scene_id: str = Field(..., description="Scene identifier used for filename and seed.")
    frame_type: str = Field("wide", description="Shot type: wide | mid | close")
    output_dir: str = Field("assets/images", description="Directory to save the image.")
    width: int = Field(1280, description="Output image width in pixels.")
    height: int = Field(720, description="Output image height in pixels.")
    seed: Optional[int] = Field(None, description="Seed for reproducibility. Auto-derived from scene_id if None.")
    force_regen: bool = Field(False, description="Skip file cache and use a fresh random seed. Use for edit-time regeneration.")


class ImageGenTool(BaseAgenticTool):
    name = "image_generator"
    description = (
        "Generates images using Pollinations.ai (FLUX model, free, no API key). "
        "Generates 3 shot types per scene: wide, mid, close. Returns saved image path."
    )
    args_schema = ImageGenArgs

    BASE_URL = "https://image.pollinations.ai/prompt"

    # Cinematic angle modifier added to each frame's prompt
    FRAME_MODIFIERS = {
        "wide":  "wide establishing shot, full environment visible, cinematic wide angle",
        "mid":   "medium shot, characters in foreground, background environment visible",
        "close": "close-up shot, expressive faces, emotional detail, shallow depth of field",
    }

    def execute(
        self,
        prompt: str,
        scene_id: str,
        frame_type: str = "wide",
        output_dir: str = "assets/images",
        width: int = 1280,
        height: int = 720,
        seed: Optional[int] = None,
        force_regen: bool = False,
    ) -> str:
        os.makedirs(output_dir, exist_ok=True)

        # force_regen: use a fresh random seed so Pollinations generates a new image.
        # Normal generation: derive seed from scene_id so all 3 frames share the same style.
        if force_regen:
            if seed is None:
                seed = random.randint(1, 99999)
        else:
            if seed is None:
                seed = abs(hash(scene_id)) % 9999

        modifier = self.FRAME_MODIFIERS.get(frame_type, "")
        full_prompt = f"{modifier}, {prompt}" if modifier else prompt

        encoded_prompt = urllib.parse.quote(full_prompt)
        url = (
            f"{self.BASE_URL}/{encoded_prompt}"
            f"?width={width}&height={height}&nologo=true&model=flux&seed={seed}"
        )

        output_path = os.path.join(output_dir, f"{scene_id}_{frame_type}.png")

        if os.path.exists(output_path) and not force_regen:
            print(f"[ImageGen] Cached: {output_path}")
            return output_path

        print(f"[ImageGen] {scene_id} / {frame_type} shot — prompt: {full_prompt[:80]}...")

        for attempt in range(3):
            try:
                resp = requests.get(url, timeout=60)
                resp.raise_for_status()
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                print(f"[ImageGen] Saved: {output_path}")
                return output_path
            except Exception as e:
                print(f"[ImageGen] Attempt {attempt + 1}/3 failed: {e}")
                if attempt < 2:
                    time.sleep(3)

        raise RuntimeError(f"Failed to generate image for {scene_id}/{frame_type} after 3 attempts.")
