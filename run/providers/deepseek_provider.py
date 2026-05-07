# run/providers/deepseek_provider.py

import os
from openai import OpenAI
from typing import Dict, Optional

class DeepSeekProvider:
    def __init__(self):
        # DeepSeek uses the OpenAI Python SDK format
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
        # Choose deepseek-chat or deepseek-reasoner based on your agent's needs
        self.model = "deepseek-chat" 

    def get_decision(self, data: str, context: Optional[Dict]) -> str:
        messages = [
            {"role": "system", "content": "You are the core logic engine. Return strict JSON."},
        ]
        
        if context:
            messages.append({"role": "system", "content": f"Context: {context}"})
            
        messages.append({"role": "user", "content": data})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"}, # Force JSON if your parser needs it
            temperature=0.1
        )
        
        return response.choices[0].message.content
