import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# We use the openAI client structure pointing to Cerebras
# Ensure CEREBRAS_API_KEY is in your environment variables
client = OpenAI(
    api_key=os.environ.get("CEREBRAS_API_KEY", "default_key"),
    base_url="https://api.cerebras.ai/v1"
)

def analyze_transaction(user_input: str, active_unit: str, valid_accounts: list) -> dict:
    """
    Takes natural language input, feeds it to Cerebras AI, and returns a JSON dictionary 
    with the structured transaction mapping.
    """
    prompt = f"""
    You are an expert financial accountant parsing transactions for a hospitality business.
    Unit: {active_unit}. 
    User Input: '{user_input}'. 
    Valid Chart of Accounts (COA): {valid_accounts}. 
    
    You MUST return ONLY a raw JSON dictionary without any markdown blocks, containing exactly 
    these keys and nothing else: 'description', 'party', 'dr', 'cr', 'amt', 'outcome'.
    'dr' must be the exact name of an account from the valid COA to Debit. 
    'cr' must be the exact name of an account from the valid COA to Credit.
    'outcome' should be a simple English summary of what you did.
    """

    try:
        response = client.chat.completions.create(
            model="llama3.1-8b", # High-speed inference model on Cerebras
            messages=[
                {"role": "system", "content": "You are a specialized JSON-only output agent."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        
        raw_content = response.choices[0].message.content.strip()
        
        # Clean potential markdown wrappers if the AI disobeys instructions
        if raw_content.startswith('```json'):
            raw_content = raw_content[7:]
        if raw_content.startswith('```'):
            raw_content = raw_content[3:]
        if raw_content.endswith('```'):
            raw_content = raw_content[:-3]
            
        return json.loads(raw_content.strip())

    except Exception as e:
        return {"error": str(e)}
