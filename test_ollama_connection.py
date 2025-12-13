from backend.utils.llm_client import OllamaClient
import sys

def test_ollama():
    print("🔄 Testing Ollama Connection...")
    
    try:
        client = OllamaClient()
        print(f"✅ Client initialized (Model: {client.model})")
        
        print("⏳ Sending test prompt...")
        response = client.generate_content("Say 'Hello TripCraft' and nothing else.")
        
        print(f"📩 Response received: {response.text}")
        
        if "TripCraft" in response.text:
            print("✅ Ollama is working correctly!")
            return True
        else:
            print("⚠️ Response content unexpected but valid.")
            return True
            
    except Exception as e:
        print(f"❌ CONNECTION FAILED: {e}")
        print("\nPossible fixes:")
        print("1. Ensure Ollama is running ('ollama serve')")
        print("2. Ensure 'llama3' model is pulled ('ollama pull llama3')")
        return False

if __name__ == "__main__":
    success = test_ollama()
    sys.exit(0 if success else 1)
