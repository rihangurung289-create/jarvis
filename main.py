"""
Jarvis - a simple voice-controlled laptop assistant.

Pipeline:
  1. listener  -> capture speech and convert to text
  2. parser    -> map text to a structured command
  3. executor  -> run the command on your system
  4. speaker   -> optional spoken feedback
  5. ui        -> Siri-style overlay when Jarvis wakes up
"""

import time

from ai_reply import generate_reply, get_responder
from executor import CommandExecutor
from listener import VoiceListener
from parser import Command, CommandParser, CommandType
from speaker import VoiceSpeaker
from ui import create_ui
from wake import contains_wake_word, strip_wake_word

import config


def run() -> None:
    listener = VoiceListener()
    parser = CommandParser()
    executor = CommandExecutor()
    speaker = VoiceSpeaker()
    ui = create_ui()
    ui.start()
    time.sleep(0.3)  # Let the overlay thread initialize

    listener.calibrate()
    speaker.say("Jarvis is ready.")

    print("=" * 50)
    print("Jarvis Voice Assistant")
    print("Examples:")
    print(f'  "{config.WAKE_WORD} open notepad"')
    print(f'  "{config.WAKE_WORD} volume up" / "exit"')
    print(f'  "{config.WAKE_WORD} what is the capital of France?"')
    print(f"Speech engine: {config.RECOGNITION_ENGINE}")
    if config.ENABLE_AI_CHAT:
        if get_responder().enabled:
            print(f"AI chat: on ({config.OPENAI_MODEL})")
        else:
            print("AI chat: enabled - add API key to .env")
    if config.REQUIRE_WAKE_WORD:
        print(f'Say "{config.WAKE_WORD}" to wake me up, then your command.')
    if config.ENABLE_WAKE_UI:
        print("Wake overlay: on (press Esc on the overlay to dismiss)")
    print("=" * 50)
    print()

    try:
        while True:
            wake_result = listener.listen()
            if not wake_result.text:
                continue

            if config.REQUIRE_WAKE_WORD:
                if not contains_wake_word(wake_result.text):
                    continue
                command_text = strip_wake_word(wake_result.text)
            else:
                command_text = wake_result.text.strip()

            ui.show("listening")
            command_result = wake_result

            if not command_text:
                print("Wake word detected - waiting for command...")
                command_result = listener.listen()
                if not command_result.text:
                    ui.show("error")
                    time.sleep(1.2)
                    ui.hide()
                    continue
                command_text = command_result.text.strip()

            ui.set_status("Listening...", f'"{command_text}"')
            ui.show("processing")

            command = parser.parse(command_text)

            if command.type == CommandType.UNKNOWN and config.ENABLE_AI_CHAT:
                command = Command(type=CommandType.CHAT, target=command_text)

            if command.type == CommandType.CHAT:
                ui.show("processing", "Thinking...")
                result = generate_reply(
                    command.target or command_text,
                    "User",
                )
            else:
                result = executor.execute(command)

            print(f"Jarvis: {result}\n")
            ui.show("speaking", result)
            speaker.say(result)

            if command.type == CommandType.EXIT or result == "__EXIT__":
                print("Goodbye!")
                break

            time.sleep(0.8)
            ui.hide()
    finally:
        ui.shutdown()


if __name__ == "__main__":
    run()
