import os
import requests
import json
from dotenv import load_dotenv

def test_ghost_api():
    load_dotenv()
    
    api_key = os.getenv("INFIP_API_KEY")
    if not api_key:
        print("[ERROR] Please add INFIP_API_KEY to your .env file!")
        return

    # Let's use a prompt from your Lyra Flynn character!
    prompt = (
        "Cinematic portrait of Astronaut Lyra Flynn. She has short, spiky hair that's a mix of dark brown and silver. "
        "Her eyes are bright, piercing blue. She wears a sleek black and silver spacesuit adorned with small circuit patterns. "
        "High quality, photorealistic, 8k, highly detailed, dramatic lighting."
    )
    
    print(f"Generating image with GhostAPI (flux2-dev)...")
    print(f"Prompt: {prompt}")

    url = "https://api.infip.pro/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "img3", # Using the default free model
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
        "response_format": "url"
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        image_url = result['data'][0]['url']
        print(f"\n✅ Success! Image generated.")
        print(f"Image URL: {image_url}")
        
        # Download the image to check it locally
        print("\nDownloading image...")
        img_data = requests.get(image_url).content
        with open("test_lyra.png", "wb") as handler:
            handler.write(img_data)
        print("Saved locally as 'test_lyra.png'. Check it out!")
        
    except Exception as e:
        print(f"\n[ERROR] Error calling GhostAPI: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response details: {e.response.text}")

if __name__ == "__main__":
    test_ghost_api()
