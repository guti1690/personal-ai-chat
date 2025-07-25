import json
import os
from gradio.components.radio import Radio
import requests
import gradio as gr
from tools import tools
from dotenv import load_dotenv
from openai import OpenAI
from utils import get_system_prompt

load_dotenv(override=True)

OPENAI_URL = os.getenv("OPENAI_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL")
PUSHOVER_USER = os.getenv("PUSHOVER_USER")
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")
PUSHOVER_URL = os.getenv("PUSHOVER_URL")
openai = OpenAI(base_url=OPENAI_URL, api_key=OPENAI_API_KEY)

def push(message):
    if not PUSHOVER_URL:
        raise ValueError("PUSHOVER_URL is not set")

    print(f"Push: {message}")
    payload = {"user": PUSHOVER_USER, "token": PUSHOVER_TOKEN, "message": message}
    requests.post(PUSHOVER_URL, data=payload)

def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording interest from {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}

def record_unknown_question(question):
    push(f"Recording {question} asked that I couldn't answer")
    return {"recorded": "ok"}

def handle_tool_calls(tool_calls):
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"Tool called: {tool_name}", flush=True)
        tool = globals().get(tool_name)
        result = tool(**arguments) if tool else {}
        results.append({"role": "tool", "content": json.dumps(result), "tool_call_id": tool_call.id})
    return results

def chat(message, history):
    if not LLM_MODEL:
        raise ValueError("LLM_MODEL is not set")

    system_prompt = get_system_prompt()
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": message}]
    done = False

    while not done:
        response = openai.chat.completions.create(model=LLM_MODEL, messages=messages, tools=tools)
        finish_reason = response.choices[0].finish_reason

        if finish_reason != "tool_calls":
            done = True
            break

        # If the LLM wants to call a tool, we do that!
        if finish_reason == "tool_calls":
            message = response.choices[0].message
            tool_calls = message.tool_calls
            results = handle_tool_calls(tool_calls)
            messages.append(message)
            messages.extend(results)

    return response.choices[0].message.content

gr.ChatInterface(chat, type="messages").launch()
