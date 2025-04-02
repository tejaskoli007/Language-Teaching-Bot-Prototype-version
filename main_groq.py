import os
import requests
import sqlite3
from dotenv import load_dotenv

# Load .env variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Groq API setup
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama3-8b-8192"

#  Database Setup

def init_db():
    conn = sqlite3.connect("mistakes.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mistakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_input TEXT,
            correction TEXT,
            feedback TEXT
        )
    ''')
    cursor.execute('DELETE FROM mistakes')  # Clear previous run's mistakes
    conn.commit()
    conn.close()

def log_mistake(user_input, correction, feedback):
    conn = sqlite3.connect("mistakes.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO mistakes (user_input, correction, feedback) VALUES (?, ?, ?)",
                   (user_input, correction, feedback))
    conn.commit()
    conn.close()

def show_summary():
    conn = sqlite3.connect("mistakes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_input, correction, feedback FROM mistakes")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("\nNo mistakes were made! Great job!")
        return

    print("\nMistake Summary:")
    for i, (inp, corr, fb) in enumerate(rows, 1):
        print(f"\nMistake {i}")
        print(f"User said: {inp}")
        print(f"Correction: {corr}")
        print(f"Feedback: {fb}")

# Groq API Call 

def call_groq(messages):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.7
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=payload)

    if response.status_code != 200:
        print(" Groq API Error:", response.status_code)
        print("Response:", response.text)
        return "[API Error]"

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        if not content:
            return "[Empty response from model]"
        return content
    except Exception as e:
        print(" Failed to parse Groq response:", e)
        print("Full response:", response.text)
        return "[Parsing Error]"

# Bot Logic

def get_user_info():
    print("Welcome to the Language Learning Chatbot!")
    known_lang = input(" What is your native language? ")
    target_lang = input(" What language would you like to learn? ")
    level = input(" What is your current level in that language? (Beginner / Intermediate / Advanced): ")
    return known_lang, target_lang, level

def generate_scene(target_lang, level):
    system_prompt = f"You are a helpful AI tutor. The user is learning {target_lang} at {level} level."
    user_prompt = f"""
Suggest 3 different realistic roleplay scenes to help practice {target_lang}.
Each should have:
- A short title
- A one-line description
Number them from 1 to 3.
"""

    response = call_groq([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ])

    print("\nChoose a scene to practice:")
    print(response)

    while True:
        try:
            choice = int(input("\nEnter 1, 2, or 3 to choose your scene: "))
            if choice in [1, 2, 3]:
                break
            else:
                print("Please enter 1, 2, or 3.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    # Extract selected scene line
    scene_lines = response.strip().split("\n")
    selected_lines = [line for line in scene_lines if line.strip().startswith(f"{choice}.")]
    selected_scene = selected_lines[0] if selected_lines else "[Scene not found]"

    return selected_scene

def correct_user_input(user_input, target_lang):
    prompt = f"""
You are a language teacher. The user is learning {target_lang}.
Here is their message: "{user_input}"

1. Check for grammar or vocabulary mistakes.
2. If there are any, correct the sentence and explain briefly.
3. If it's already correct, just say "Looks good!"
Return ONLY the feedback explanation. Then in a new line, write: Correction: <corrected version>
"""
    full_feedback = call_groq([{"role": "system", "content": prompt}])
    
    if "Correction:" in full_feedback:
        feedback, correction = full_feedback.split("Correction:")
        correction = correction.strip()
        feedback = feedback.strip()
    else:
        feedback = full_feedback.strip()
        correction = "[No correction needed]"
    return feedback, correction

def generate_bot_reply(user_input, target_lang):
    prompt = f"""
You're helping a user practice {target_lang}. Respond naturally to their message: "{user_input}"
Keep it short and friendly.
"""
    return call_groq([{"role": "system", "content": prompt}])

def chat_loop(target_lang, scene_context):
    print("\n Starting scene:")
    print(f"{scene_context}")
    print("\nLet's begin the conversation! (Type 'exit' to end early)\n")
    print(f"Bot: Let's start! Say something in {target_lang}.")

    for i in range(3):
        user_input = input(" You: ")
        if user_input.lower() == "exit":
            break

        feedback, correction = correct_user_input(user_input, target_lang)
        print(f"Feedback: {feedback}")

        if correction != "[No correction needed]":
            log_mistake(user_input, correction, feedback)

        bot_reply = generate_bot_reply(user_input, target_lang)
        print(f" Bot: {bot_reply}\n")

#  Run

if __name__ == "__main__":
    init_db()
    known_lang, target_lang, level = get_user_info()
    selected_scene = generate_scene(target_lang, level)
    chat_loop(target_lang, selected_scene)
    show_summary()
