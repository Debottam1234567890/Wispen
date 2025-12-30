from huggingface_hub import InferenceClient
import os
import dotenv

dotenv.load_dotenv()
HF_KEY = os.getenv("STABLE_DIFFUSION_API_KEY")

def test_client():
    print("Testing InferenceClient...")
    # Use valid model for T2I
    model = "stabilityai/stable-diffusion-xl-base-1.0"
    
    client = InferenceClient(model=model, token=HF_KEY)
    
    try:
        print("Generating...")
        image = client.text_to_image("An astronaut riding a unicorn")
        image.save("test_hf_client.png")
        print("Success! Saved test_hf_client.png")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_client()
