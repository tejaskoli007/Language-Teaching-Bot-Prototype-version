import os
import openai
import sqlite3
from dotenv import load_dotenv

# Load API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Database Setup 

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
    cursor.execute('DELETE FROM mistakes')  # Clear old session
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
        print("\n No mistakes were made! Great job!")
        return

    print("\n Mistake Summary:")
    for i, (inp, corr, fb) in enumerate(rows, 1):
        print(f"\n Mistake {i}")
        print(f"User said: {inp}")
        print(f"Correction: {corr}")
        print(f"Feedback: {fb}")

# OpenAI Chat Call 

def call_openai(messages):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI API Error:", e)
        return "[OpenAI Error]"

# Chatbot Logic

def get_user_info():
    print("Welcome to the Language Learning Chatbot (OpenAI Version)!")
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

    response = call_openai([
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

    # Extract scene
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
    full_feedback = call_openai([{"role": "system", "content": prompt}])
    
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
    return call_openai([{"role": "system", "content": prompt}])

def chat_loop(target_lang, scene_context):
    print("\nStarting scene:")
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



if __name__ == "__main__":
    init_db()
    known_lang, target_lang, level = get_user_info()
    selected_scene = generate_scene(target_lang, level)
    chat_loop(target_lang, selected_scene)
    show_summary()
