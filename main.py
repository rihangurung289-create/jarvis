"""
Jarvis — a simple voice-controlled laptop assistant.

Pipeline:
  1. listener  -> capture speech and convert to text
  2. parser    -> map text to a structured command
  3. guardian  -> identify user, detect weird behavior, log activity
  4. executor  -> run the command on your system
  5. speaker   -> optional spoken feedback
  6. ui        -> Siri-style overlay when Jarvis wakes up
"""

import time

from ai_reply import generate_reply, get_responder
from executor import CommandExecutor
from guardian import SecurityGuardian
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
    guardian = SecurityGuardian()
    ui = create_ui()
    ui.start()
    time.sleep(0.3)  # Let the overlay thread initialize

    listener.calibrate()
    speaker.say("Jarvis is ready.")

    print("=" * 50)
    print("Jarvis Voice Assistant")
    print("Examples:")
    print(f'  "{config.WAKE_WORD} open notepad"')
    print(f'  "{config.WAKE_WORD} enroll user Alex"')
    print(f'  "{config.WAKE_WORD} who am i"')
    print(f'  "{config.WAKE_WORD} volume up" / "exit"')
    print(f'  "{config.WAKE_WORD} what is the capital of France?"')
    print(f"Speech engine: {config.RECOGNITION_ENGINE}")
    if config.ENABLE_AI_CHAT:
        if get_responder().enabled:
            print(f"AI chat: on (OpenAI {config.OPENAI_MODEL})")
        else:
            print("AI chat: enabled — add OPENAI_API_KEY to .env (see .env.example)")
    if config.REQUIRE_WAKE_WORD:
        print(f'Say "{config.WAKE_WORD}" to wake me up, then your command.')
    if config.ENABLE_WAKE_UI:
        print("Wake overlay: on (press Esc on the overlay to dismiss)")
    if config.ENABLE_GUARDIAN:
        print("Guardian security: on (logs who speaks + flags weird use)")
        print("  View log: python security_report.py")
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
                print("Wake word detected — waiting for command...")
                command_result = listener.listen()
                if not command_result.text:
                    ui.show("error")
                    time.sleep(1.2)
                    ui.hide()
                    continue
                command_text = command_result.text.strip()

            identification = guardian.merge_identifications(
                guardian.identify(wake_result.audio),
                guardian.identify(command_result.audio),
            )
            ui.set_status(
                "Listening…",
                f'{identification.display_name} — "{command_text}"',
            )
            ui.show("processing")

            command = parser.parse(command_text)

            if command.type == CommandType.UNKNOWN and config.ENABLE_AI_CHAT:
                command = Command(type=CommandType.CHAT, target=command_text)

            if command.type == CommandType.ENROLL_USER:
                result = _handle_enrollment(listener, guardian, command, ui, speaker)
                print(f"Jarvis: {result}\n")
                time.sleep(0.8)
                ui.hide()
                continue

            if command.type == CommandType.WHO_AM_I:
                result = guardian.who_am_i_message()
                print(f"Jarvis: {result}\n")
                ui.show("speaking", result)
                speaker.say(result)
                time.sleep(0.8)
                ui.hide()
                continue

            verdict = guardian.evaluate(identification, command, command_text)

            if verdict.blocked:
                result = verdict.block_reason
                ui.show("error", result)
            elif command.type == CommandType.CHAT:
                ui.show("processing", "Thinking…")
                result = generate_reply(
                    command.target or command_text,
                    identification.display_name,
                )
            else:
                if verdict.incidents:
                    ui.show("processing", "Security check…")
                result = executor.execute(command)

            guardian.record_interaction(
                identification, command, command_text, result, verdict
            )

            print(f"Jarvis: {result}\n")
            if verdict.incidents and not verdict.blocked:
                print(f"[Guardian] Noted: {', '.join(verdict.incidents)}\n")

            ui.show("speaking", result)
            speaker.say(result)

            if command.type == CommandType.EXIT or result == "__EXIT__":
                print("Goodbye!")
                break

            time.sleep(0.8)
            ui.hide()
    finally:
        ui.shutdown()


def _handle_enrollment(
    listener: VoiceListener,
    guardian: SecurityGuardian,
    command,
    ui,
    speaker: VoiceSpeaker,
) -> str:
    name = command.target.strip()
    if not name:
        return "Say enroll user followed by your name."

    samples = []
    needed = config.GUARDIAN_ENROLL_SAMPLES
    ui.show("listening", f"Enrollment for {name}")

    for index in range(needed):
        prompt = (
            f"Sample {index + 1} of {needed}. Say your name or any short phrase."
            if index
            else f"Say a short phrase so I learn your voice, {name}."
        )
        speaker.say(prompt)
        ui.set_status("Enrolling…", prompt)
        sample = listener.listen()
        if sample.audio:
            samples.append(sample.audio)

    if len(samples) < 1:
        return "Enrollment failed. I could not hear you."

    return guardian.enroll_user(name, samples)


if __name__ == "__main__":
    run()
