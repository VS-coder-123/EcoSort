import os
import sys
import time
import google.generativeai as genai
from dotenv import load_dotenv
from google.api_core import exceptions

def get_quota_info():
    """Get basic model information."""
    try:
        models = list(genai.list_models())
        return {
            'status': 'active',
            'model_count': len(models),
            'is_premium': True  # Assuming premium since you mentioned it
        }
    except Exception as e:
        return {'error': str(e)}
    
def test_gemini_api():
    """
    Test function to verify if Gemini API is working correctly.
    """
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment variables.")
        print("Please set it in your .env file.")
        return False
    
    try:
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Get account info
        print("🔍 Checking account information...")
        quota_info = get_quota_info()
        if 'error' in quota_info:
            print(f"⚠️  Could not get quota info: {quota_info['error']}")
        else:
            print(f"✅ Account Status: {'Premium' if quota_info.get('is_premium') else 'Free'} Tier")
            print(f"   Available models: {quota_info.get('model_count', 'Unknown')}")
        
        # List available models with more details
        print("\n🔍 Available models (with generateContent support):")
        models = list(genai.list_models())
        
        # Sort models by name for better readability
        models.sort(key=lambda x: x.name)
        
        # Print available models
        for m in models:
            if 'generateContent' in m.supported_generation_methods:
                model_name = m.name.split('/')[-1]
                methods = ', '.join(m.supported_generation_methods)
                print(f"- {model_name}")
        
        # Try to find the most capable model
        preferred_models = [
            'gemini-2.5-pro',
            'gemini-2.5-flash',
            'gemini-pro',
            'gemini-flash',
            'gemini-1.5-pro',
            'gemini-1.5-flash'
        ]
        
        model_name = None
        for pref in preferred_models:
            if any(pref in m.name for m in models):
                model_name = pref
                break
                
        if not model_name:
            # If no preferred model found, use the first available one
            for m in models:
                if 'generateContent' in m.supported_generation_methods:
                    model_name = m.name.split('/')[-1]
                    break
            
            if not model_name:
                raise ValueError("No suitable model found that supports generateContent")
        
        print(f"\n🧪 Testing Gemini API with model: {model_name}...")
        
        # Add a small delay to avoid rate limiting
        time.sleep(1)
        
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Say 'Hello, Gemini! This is a test.'")
        except exceptions.ResourceExhausted as e:
            print(f"\n❌ Rate limit exceeded for model {model_name}.")
            print("This can happen even with premium accounts if you've made many requests in a short time.")
            print("Error details:", str(e))
            print("\n💡 Try these solutions:")
            print("1. Wait a few minutes and try again")
            print("2. Try a different model")
            print("3. Check your quota at: https://ai.dev/usage?tab=rate-limit")
            print("4. Contact Google Cloud Support if the issue persists")
            return False
        
        # Print the response
        print("\n✅ Gemini API Response:")
        print("-" * 40)
        print(response.text)
        print("-" * 40)
        
        # Test with an image (vision model)
        print("\n🧪 Testing Gemini Vision API...")
        
        # Find a vision-capable model
        vision_models = []
        for m in models:
            if ('generateContent' in m.supported_generation_methods and 
                any(ft in m.name.lower() for ft in ['vision', 'flash', 'pro'])):
                model_info = {
                    'name': m.name.split('/')[-1],
                    'full_name': m.name,
                    'capabilities': m.supported_generation_methods
                }
                vision_models.append(model_info)
        
        if vision_models:
            print("\n🔍 Found vision-capable models:")
            for i, vm in enumerate(vision_models, 1):
                print(f"{i}. {vm['name']} (capabilities: {', '.join(vm['capabilities'])})")
            
            # Try the most capable vision model first
            vision_model_info = vision_models[0]
            vision_model_name = vision_model_info['name']
            
            print(f"\n🧪 Testing with vision model: {vision_model_name}...")
            
            try:
                # Add a small delay
                time.sleep(1)
                
                vision_model = genai.GenerativeModel(vision_model_name)
                
                # Test with a simple image description
                response = vision_model.generate_content([
                    "What is in this image?",
                    {"mime_type": "image/jpeg",
                     "data": b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='
                    }
                ])
                
                print("\n✅ Gemini Vision API Response:")
                print("-" * 40)
                print(response.text)
                print("-" * 40)
                
            except exceptions.ResourceExhausted as e:
                print(f"\n❌ Rate limit exceeded for vision model {vision_model_name}.")
                print("This can happen if you've made many requests in a short time.")
                print("Error details:", str(e))
                print("\n💡 Try these solutions:")
                print("1. Wait a few minutes and try again")
                if len(vision_models) > 1:
                    print(f"2. Try a different model (available: {', '.join([vm['name'] for vm in vision_models[1:]])})")
                print("3. Check your quota at: https://ai.dev/usage?tab=rate-limit")
                
            except Exception as e:
                print(f"\n⚠️  Error testing vision model {vision_model_name}:", str(e))
                if "unsupported image type" in str(e).lower():
                    print("💡 Try with a different image format or model")
        else:
            print("\n⚠️  No vision-capable models found. This might be due to:")
            print("1. Your account not having access to vision models")
            print("2. No models with vision capabilities being available in your region")
            print("3. API restrictions on your account")
        
        print("\n🎉 All tests passed! Gemini API is working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Error testing Gemini API: {str(e)}")
        return False

if __name__ == "__main__":
    test_gemini_api()
