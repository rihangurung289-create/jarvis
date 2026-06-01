"""Step 3: Execute parsed commands on the system."""

import os
import subprocess
import webbrowser

import config
from parser import Command, CommandType
import volume as volume_control


class CommandExecutor:
    """Runs system actions based on parsed commands."""

    def execute(self, command: Command) -> str:
        """Execute a command and return a human-readable result message."""
        handlers = {
            CommandType.OPEN_APP: self._open_app,
            CommandType.SEARCH_WEB: self._search_web,
            CommandType.SHUTDOWN: self._shutdown,
            CommandType.RESTART: self._restart,
            CommandType.CANCEL_SHUTDOWN: self._cancel_shutdown,
            CommandType.SLEEP: self._sleep,
            CommandType.VOLUME_UP: self._volume_up,
            CommandType.VOLUME_DOWN: self._volume_down,
            CommandType.VOLUME_SET: self._volume_set,
            CommandType.VOLUME_MUTE: self._volume_mute,
            CommandType.VOLUME_UNMUTE: self._volume_unmute,
            CommandType.EXIT: self._exit_assistant,
            CommandType.UNKNOWN: self._unknown,
        }
        handler = handlers.get(command.type, self._unknown)
        return handler(command)

    def _open_app(self, command: Command) -> str:
        app_key = command.target.lower().strip()
        executable = config.APP_ALIASES.get(app_key, app_key)

        try:
            if executable.startswith("ms-"):
                os.startfile(executable)
            else:
                subprocess.Popen(executable, shell=True)
            return f"Opening {command.target}."
        except OSError as exc:
            return f"Could not open {command.target}: {exc}"

    def _search_web(self, command: Command) -> str:
        if not command.target:
            return "What would you like me to search for?"

        url = config.SEARCH_URL.format(query=command.target.replace(" ", "+"))
        webbrowser.open(url)
        return f"Searching the web for {command.target}."

    def _shutdown(self, _command: Command) -> str:
        os.system("shutdown /s /t 5")
        return "Shutting down in 5 seconds. Say cancel shutdown to abort."

    def _restart(self, _command: Command) -> str:
        os.system("shutdown /r /t 5")
        return "Restarting in 5 seconds. Say cancel shutdown to abort."

    def _cancel_shutdown(self, _command: Command) -> str:
        result = os.system("shutdown /a")
        if result == 0:
            return "Shutdown or restart cancelled."
        return "No pending shutdown to cancel."

    def _sleep(self, _command: Command) -> str:
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return "Putting the computer to sleep."

    def _volume_up(self, _command: Command) -> str:
        if not volume_control.AVAILABLE:
            return "Volume control unavailable. Install pycaw and comtypes."

        level = volume_control.change_volume(config.VOLUME_STEP)
        return f"Volume increased to {level} percent."

    def _volume_down(self, _command: Command) -> str:
        if not volume_control.AVAILABLE:
            return "Volume control unavailable. Install pycaw and comtypes."
        level = volume_control.change_volume(-config.VOLUME_STEP)
        return f"Volume decreased to {level} percent."

    def _volume_set(self, command: Command) -> str:
        if not volume_control.AVAILABLE:
            return "Volume control unavailable. Install pycaw and comtypes."
        try:
            target = int(command.target)
        except ValueError:
            return "Could not parse volume level."
        level = volume_control.set_volume_percent(target)
        return f"Volume set to {level} percent."

    def _volume_mute(self, _command: Command) -> str:
        if not volume_control.AVAILABLE:
            return "Volume control unavailable. Install pycaw and comtypes."
        volume_control.set_mute(True)
        return "Muted."

    def _volume_unmute(self, _command: Command) -> str:
        if not volume_control.AVAILABLE:
            return "Volume control unavailable. Install pycaw and comtypes."
        volume_control.set_mute(False)
        level = volume_control.get_volume_percent()
        return f"Unmuted. Volume is {level} percent."

    def _exit_assistant(self, _command: Command) -> str:
        return "__EXIT__"

    def _unknown(self, _command: Command) -> str:
        return (
            "I didn't understand that. Try: open notepad, volume up, "
            "set volume to fifty, cancel shutdown, or exit."
        )
