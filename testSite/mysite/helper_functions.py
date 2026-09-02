import os
from google import genai
from dotenv import load_dotenv
from django.core.files.uploadedfile import TemporaryUploadedFile
from .models import Chat
import time
import base64
from openai import OpenAI
from openai.types.conversations import Message

load_dotenv(override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
gemini_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def create_messages(prompt: str, file: TemporaryUploadedFile):
    if file:
        audio_contenttypes = ["audio/mp4", "audio/mpeg"]
                
        file_content = file.file
        file_location = file.temporary_file_path()
        print(file_location)
        filesize = file.size
        file_contenttype = file.content_type
        
        # refer to this/these: 
        # https://stackoverflow.com/questions/69473608/concurrent-writing-to-multiple-files-using-asyncio 
        # https://www.twilio.com/en-us/blog/developers/tutorials/building-blocks/working-with-files-asynchronously-in-python-using-aiofiles-and-asyncio
                
        if file_contenttype == "video/mp4":
            if filesize < 20_971_520:
                bytes_video = file_content.read()
                base_64_video = base64.b64encode(bytes_video).decode()
                
                messages_gemini = [
                    {
                        "type": "video",
                        "data": base_64_video,
                        "mime_type": file_contenttype
                    },
                    {
                        "type": "text",
                        "text": "Describe the key events in this video, providing both audio and visual details. Include timestamps for salient moments."
                    }
                ]
        
            else:
                myfile = gemini_client.files.upload(file=file_location)
                                
                while not myfile.state and myfile.state.name != "ACTIVE":
                    time.sleep(3)
                    myfile = gemini_client.files.get(file=myfile.name)
                
                messages_gemini = [
                    {
                        "type": "video",
                        "uri": myfile.uri,
                        "mime_type": myfile.mime_type
                    },
                    {
                        "type": "text",
                        "text": "Describe the key events in this video, providing both audio and visual details. Include timestamps for salient moments."
                    }
                ]
                
            interaction = gemini_client.interactions.create(
                model="gemini-3.5-flash",
                input=messages_gemini
            )
            
            messages = [
                {
                    "role": "system",
                    "content": f"Video was pre-processed by Gemini model.\nVideo details: '{interaction.output_text}'."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
        elif file_contenttype == "image/jpeg":
            image_bytes = file_content.read()
            image_base64 = base64.b64encode(image_bytes).decode()
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_image",
                            "image": image_base64
                        },
                        {
                            "type": "input_text",
                            "text": prompt
                        }
                    ]
                }
            ]

        elif file_contenttype in audio_contenttypes:
            audio_file_buffered = file_content
            
            transcription = client.audio.transcriptions.create(
                model="gpt-transcribe",
                file=audio_file_buffered
            )
            
            messages = [
                {
                    "role": "system",
                    "content": f"Audio file was uploaded, and the transcription is ready for you.\nAudio transcripted: '{transcription.text}'"
                },
                {
                    "role": "user",
                    "content": prompt
                },
            ]
        
        # clear away the file from temporary location
        os.remove(file_location)
            
    else:
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
    
    return messages