from django.shortcuts import render, redirect
from django.http.response import StreamingHttpResponse
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.http import HttpResponse
from .models import Chat

from openai import OpenAI
from openai.types.responses import ResponseTextDeltaEvent, ResponseOutputItemDoneEvent, ResponseFunctionToolCall
from openai.types.conversations import Message

import os
from dotenv import load_dotenv
import json

from .tools import *
from .helper_functions import create_messages

load_dotenv(override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Additional functions
def chat(conversation_id: str, prompt: str, file: TemporaryUploadedFile = None):
    
    messages = create_messages(prompt=prompt, file=file)
  
    # Thinking phase
    iteration = 1
    
    thinking_stream = client.responses.create(
        conversation=conversation_id,
        model="gpt-5.4-mini",
        stream=True,
        tools=tools_schema,
        instructions="Return response in markdown always unless user requests for other format.",
        input=messages
    )
    
    while True:
        if iteration > 1:
            all_messages = client.conversations.items.list(conversation_id=conversation_id, order="asc").data
            assistant_messages = []
            
            for message in all_messages:
                if isinstance(message, Message):
                    if message.role == "assistant":
                        if message.status == "completed":
                            assistant_messages.append(json.dumps(message.content[0].text))
                            
            instructions = f"""
            You are in a loop. 
            
            ### Here is your last message (observation):
            {assistant_messages[-1]}
            
            ### Here is the original user input:
            {messages}
            
            ### Further actions
            Continue thinking and reasoning, and call on more tools/actions if needed. You can break out the loop if no tools are needed.
            
            ### Additional requirements
            As always, return response in markdown, unless user requests for other format.
            """
        
            thinking_stream = client.responses.create(
                conversation=conversation_id,
                model="gpt-5.4-mini",
                stream=True,
                tools=tools_schema,
                instructions=instructions,
                input=""
            )

        actions = []
        
        for event in thinking_stream:
            if isinstance(event, ResponseTextDeltaEvent):
                print(event.delta, end="", flush=True)
                yield f"{event.delta}"
            
            elif isinstance(event, ResponseOutputItemDoneEvent):
                if isinstance(event.item, ResponseFunctionToolCall):
                    actions.append(event.item)
                    
        if len(actions) == 0:
            break
        
        for tool in actions:
            if tool.name == "process_youtube_link":
                output = process_youtube_link(json.loads(tool.arguments)["uri"])
            
            elif tool.name == "harmful_or_not":
                output = harmful_or_not(json.loads(tool.arguments)["transcript"])
                
            elif tool.name == "check_weather":
                city, country = json.loads(tool.arguments)
                output = check_weather(city, country)
            
            client.conversations.items.create(
                conversation_id=conversation_id,
                items=[
                    {
                        "type": "function_call_output",
                        "call_id": tool.call_id,
                        "output": output,
                    }
                ]
            )
        
        iteration += 1
        if iteration >= 5:
            client.conversations.items.create(
                conversation_id=conversation_id,
                items=[
                    {
                        "role": "assistant",
                        "content": "Task was not finished, I have to summarize the last 5 conversations and inform user task was not complete."
                    }
                ]
            )
            
            end_stream = client.responses.create(
                conversation=conversation_id,
                model="gpt-5.4-mini",
                instructions=f"A task was not finished, refer to user message from {iteration} chats ago and inform them of task incomplete. Return response in markdown always.",
                stream=True,
            )
            
            for event in end_stream:
                if isinstance(event, ResponseTextDeltaEvent):
                    yield f"{event.delta}"
                    
            break
        


# Create your views here.

# @login_required
def home(request):
    if request.user.is_authenticated:
        try:
            # obtain user's name, then get their conversation ID first
            user_data = Chat.objects.all().filter(user=request.user)
            
            uuid = []
            for data in user_data:
                uuid.append(data.uuid)
            
            context = {"chat_uuid": uuid}
            
            return render(request, "mysite/index.html", context=context)
        
        except Chat.DoesNotExist:
            return render(request, "mysite/index.html")


# figure out a way to not let user access this path directly
# @login_required
def chat_test(request):
    
    # first check if the user with the UUID has conv_id
    if request.user.is_authenticated:
        if request.method == "POST":
            # capture user, prompt and uuid from POST request
            user = request.user
            browser_data = request.POST.dict()
            
            prompt = browser_data["prompt"]
            uuid = browser_data["uuid"]
            
            # first, check if user has chat history, else create one
            entry = Chat.objects.get_or_create(user=user, uuid=uuid)
            data, ok = entry
        
            # then, if ok is True, create a new OpenAI convo ID, else get their convo ID
            if ok:
                conversation = client.conversations.create()
                conversation_id = conversation.id
                data.conv_id = conversation_id
                print(f"\n[DEBUG] New conversation ID created! Using conversation ID: {conversation_id}")
            
            else:
                conversation_id = data.conv_id
                print(f"\n[DEBUG] Existing conversation ID found! Using conversation ID: {conversation_id}")
            
            # [DEBUG] store conversation ids in a file for the time being to delete them later
            if conversation_id:
                with open("conversation_ids.txt", "a") as conversations:
                    conversations.write(f"{conversation_id}\n")
            
            # if user uploaded any files, write it to destination and format messages for prompt and files to save, 
            # else only format messages for prompt
            if request.FILES:
                # upload the file
                file_metadata = request.FILES["file"]          
            else:
                file_metadata = None
            
            data.save()
            
            # next, invoke the model
            return StreamingHttpResponse(chat(conversation_id=conversation_id, prompt=prompt, file=file_metadata), content_type="text/x-markdown")

# @login_required
def chat_history(request, uuid):
    if request.user.is_authenticated:
        
        try:
            # get message history
            conv_id = Chat.objects.get(user=request.user, uuid=uuid).conv_id
            
            openai_conversations_history = client.conversations.items.list(conversation_id=conv_id, order="asc").data
            rejected_statuses = ["incomplete", "failed", "cancelled"]
            
            # https://stackoverflow.com/questions/4731572/django-counter-in-loop-to-index-list
            user_chat = []
            assistant_chat = []
                            
            for message in openai_conversations_history:
                if isinstance(message, Message):
                    if message.role == "user":
                        if message.status == "completed":
                            user_chat.append(json.dumps(message.content[0].text))
                        elif message.status in rejected_statuses:
                            user_chat.append("")
                    
                    elif message.role == "assistant":
                        if message.status == "completed":
                            assistant_chat.append(json.dumps(message.content[0].text))
                        elif message.status in rejected_statuses:
                            assistant_chat.append("")
            
            # get chat UUIDs for message history buttons
            user_data = Chat.objects.all().filter(user=request.user)
            chat_uuids = [data.uuid for data in user_data]
        
            context = {
                "uuid": uuid,
                "all_messages": zip(user_chat, assistant_chat),
                "chat_uuids": chat_uuids
            }
            
            return render(request, "mysite/chat_history.html", context=context)
        
        except Chat.DoesNotExist:
            return redirect("/")
        
            
def logout(request):
    logout(request)
    return HttpResponse("<h1>Logout success</h1>")