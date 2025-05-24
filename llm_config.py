"""
Configuration for the LLM used in the agents.
"""
import os
from dotenv import load_dotenv

load_dotenv()

def get_llm_config():
    return {
        "config_list": [{
            "model": "gemma2:2b",
            "base_url": "http://localhost:11434",
            "api_type": "ollama"
        }],
        "temperature": 0.1,
        "timeout": 120,
        "cache_seed": None
    }

def get_sqlcoder_config():
    return {
        "config_list": [{
            "base_url": "http://localhost:11434",
            "model": "sqlcoder:7b",
            "api_type": "ollama"
        }],
        "temperature": 0.1,
        "timeout": 120,
        "cache_seed": None
    }

# def get_llm_config():
#     return {
#         "config_list": [{
#             "model": "llama3-70b-8192",
#             "api_key": os.getenv("GROQ_API_KEY"),
#             "base_url": "https://api.groq.com/openai/v1",
#             "api_type": "openai"
#         }],
#         "temperature": 0.1,
#         "timeout": 120,
#         "cache_seed": None
#     }

