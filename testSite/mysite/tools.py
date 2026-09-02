import os
import random
from google import genai
from dotenv import load_dotenv
from django.core.files.uploadedfile import TemporaryUploadedFile
import time
import base64
from openai import OpenAI

load_dotenv(override=True)

gemini_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def harmful_or_not(transcript: str) -> str:
    choice = random.choice(["harmful", "not_harmful"])
    
    return choice

def process_youtube_link(uri: str) -> str:
    messages = [
            {
                "type": "video",
                "uri": uri
            }
        ]
    
    interaction = gemini_client.interactions.create(
        model="gemini-3.5-flash",
        system_instruction="Describe the key events in this video, providing both audio and visual details. Include timestamps for salient moments.",
        input=messages
    )
    
    return interaction.output_text

def check_weather(city: str, country: str):
    choice = random.choice(["sunny", "rainy", "foggy", "hazy", "misty", "cool"])
    return choice

# def retrieve_context(query: str) -> list:
#     results = vector_store.similarity_search_with_relevance_scores(query)
#     sources = []
    
#     for result in results:
#         if result[1] >= 0.5:
#             sources.append((result[0].page_content, result[0].metadata))
            
#     if len(sources) == 0:
#         return "No relevant sources found."
    
#     else:
#         return sources

tools_schema = [
    {
        "type": "function",
        "name": "harmful_or_not",
        "description": "Determines if transcription is harmful or not, dependent on 'process_youtube_link' output, used when user asks if content is harmful or not.",
        "parameters": {
            "type": "object",
            "properties": {
                "transcript": {
                    "type": "string",
                    "description": "A transcript of a video or audio.",
                }
            },
            "required": ["transcript"]
        }
    },
    {
        "type": "function",
        "name": "process_youtube_link",
        "description": "Processes YouTube URIs to extract visual and audio descriptions, can be used independently from other functions, used when user inputs YouTube URLs.",
        "parameters": {
            "type": "object",
            "properties": {
                "uri": {
                    "type": "string",
                    "description": "A string of YouTube links.",
                }
            },
            "required": ["uri"]
        }
    },
    {
        "type": "function",
        "name": "check_weather",
        "description": "Check weather for a city in a country, can be used independently from other functions, used when user requests for weather condition in certain city or country. Default a city if only country was provided.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Name of a city associated with the country."
                },
                "country": {
                    "type": "string",
                    "description": "Name of a country to look up."
                }
            },
            "required": ["city", "country"]
        }
    },
    # {
    #     "type": "function",
    #     "name": "retrieve_context",
    #     "description": "Checks external knowledge base for more relevant and accurate information, dependent on transcript output and whether or not the content is harmful or not OR independently from other funtions, used when user requests more information outside of your knowledge.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "query": {
    #                 "type": "string",
    #                 "description": "Query to look up information."
    #             }
    #         },
    #         "required": ["query"]
    #     }
    # },
]