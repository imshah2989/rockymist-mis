import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

key = os.environ.get("CEREBRAS_API_KEY")

try:
    client = OpenAI(
        api_key=key,
        base_url="https://api.cerebras.ai/v1"
    )
    
    print("Attempting to connect to Cerebras with Key:", key[:8] + "...")
    
    response = client.chat.completions.create(
        model="llama3.1-8b",
        messages=[{"role": "user", "content": "Reply with only the word OK"}],
        max_tokens=5
    )
    
    print("\n✅ CONNECTION SUCCESSFUL!")
    print("Cerebras AI says:", response.choices[0].message.content.strip())
    
except Exception as e:
    print("\n❌ CONNECTION FAILED!")
    print("Error Details:", str(e))
