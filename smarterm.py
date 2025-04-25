import subprocess
import sys
import os
import platform # Ajout de l'import platform
import google.genai as genai
import configparser
from rich.console import Console # Import Rich Console
from rich.prompt import Prompt # Import Rich Prompt pour un input stylisé

# --- Initialisation Rich Console ---
console = Console()

# --- Configuration ---
# Construire le chemin par défaut vers config.ini dans le dossier utilisateur
default_config_path = os.path.join(os.path.expanduser('~'), 'smarterm', 'config.ini')

def load_api_key(config_file=default_config_path) -> str | None:
    """Loads the Gemini API key from a configuration file.
    By default, searches in $HOME/smarterm/config.ini.
    """
    config = configparser.ConfigParser()
    try:
        if not os.path.exists(config_file):
             raise FileNotFoundError
        config.read(config_file)
        api_key = config.get('API', 'GEMINI_API_KEY', fallback=None)
        if not api_key:
            raise configparser.NoOptionError('GEMINI_API_KEY', 'API')
        return api_key
    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] Configuration file '[cyan]{config_file}[/cyan]' not found.")
        console.print("Please create this file with the following content:")
        console.print("[bright_black on white] [API]                             [/]")
        console.print("[bright_black on white] GEMINI_API_KEY = YOUR_API_KEY_HERE [/]")
        return None
    except (configparser.NoSectionError, configparser.NoOptionError):
        console.print(f"[bold red]Error:[/bold red] Key '[cyan]GEMINI_API_KEY[/cyan]' not found in section [bold green][API][/bold green] of file '[cyan]{config_file}[/cyan]'.")
        console.print("Ensure the file contains:")
        console.print("[bright_black on white] [API]                             [/]")
        console.print("[bright_black on white] GEMINI_API_KEY = YOUR_API_KEY_HERE [/]")
        return None
    except Exception as e:
         console.print(f"[bold red]Unexpected error[/bold red] reading '[cyan]{config_file}[/cyan]': {e}")
         return None

# --- Initialisation du client API ---
api_key = load_api_key()
if not api_key:
    sys.exit(1)

try:
    client = genai.Client(api_key=api_key)
except Exception as e:
    console.print(f"[bold red]Error[/bold red] initializing Gemini client with the provided key: {e}")
    sys.exit(1)

# --- Génération dynamique du Prompt Système --- 
def get_system_prompt() -> str:
    """Generates the system prompt based on the detected OS."""
    os_name = platform.system()
    if os_name == "Windows":
        shell_type = "CMD/PowerShell"
        os_specific_guidance = "You are operating in a terminal on Windows."
    elif os_name == "Linux":
        shell_type = "bash/zsh or other standard Linux shell"
        os_specific_guidance = "You are operating in a terminal on Linux."
    elif os_name == "Darwin": # macOS
        shell_type = "bash/zsh or other standard macOS shell"
        os_specific_guidance = "You are operating in a terminal on macOS."
    else:
        shell_type = "unknown shell"
        os_specific_guidance = f"You are operating in a terminal on an unknown operating system ({os_name}). Try using standard POSIX commands."

    return (
        f"{os_specific_guidance} "
        f"Your goal is to help the user achieve their tasks by executing {shell_type} commands. "
        f"Use the command history and their outputs to understand the context. "
        f"Anticipate the user's needs if possible. "
        f"When you need to execute a command, respond *only* with 'CMD:' followed by the exact command. "
        f"Example (Windows): CMD:dir /w. Example (Linux/macOS): CMD:ls -l. "
        f"For any other response (explanation, question), use natural language. "
        f"Be concise in your responses."
    )

# Définir le prompt système au démarrage
SYSTEM_PROMPT = get_system_prompt()

def get_user_confirmation(command: str) -> tuple[bool, str]:
    """
    Displays the proposed command, allows the user to modify it,
    and waits for confirmation (Enter) or cancellation (Ctrl+C). Uses Rich for display.

    Returns:
        A tuple (bool, str):
        - The boolean indicates whether execution should proceed (True) or not (False).
        - The string is the command to execute (original or modified).
    """
    console.print(f"[magenta]AI proposes:[/magenta] [bold yellow]{command}[/bold yellow]")
    prompt_text = "Confirm/Modify and Enter (Ctrl+C to cancel/correct) > "

    try:
        # Use Rich's Prompt.ask for styled input
        user_command = Prompt.ask(f"[cyan]{prompt_text}[/cyan]", default="", show_default=False).strip()

        if not user_command:
            return True, command
        else:
            return True, user_command
    except KeyboardInterrupt:
        console.print(f"\n[magenta][SYSTEM][/magenta] Command cancelled. You can ask for a correction.")
        return False, "" # No command to execute

def execute_command(command: str) -> tuple[str, str, int]:
    """Executes the command and returns stdout, stderr, and return code, with Rich display."""
    stdout_lines = []
    stderr_lines = []
    try:
        console.print(f"[blue]--- Executing: [bold]{command}[/bold] ---[/blue]")
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')

        # Read stdout with Rich
        if process.stdout:
            for line in process.stdout:
                line_content = line.strip()
                console.print(f"[dim]OUT>[/dim] {line_content}") # 'dim' style for standard output
                stdout_lines.append(line_content)
            process.stdout.close()

        # Read stderr with Rich
        if process.stderr:
            # Create a specific console for stderr for colored output
            console_stderr = Console(file=sys.stderr, style="bold red")
            for line in process.stderr:
                line_content = line.strip()
                # Print to stderr via the dedicated console
                console_stderr.print(f"ERR> {line_content}")
                stderr_lines.append(line_content)
            process.stderr.close()

        process.wait()
        returncode = process.returncode
        status_style = "green" if returncode == 0 else "red"
        console.print(f"[blue]--- Command finished (code: [{status_style}]{returncode}[/{status_style}]) ---[/blue]")
        return "\n".join(stdout_lines), "\n".join(stderr_lines), returncode

    except Exception as e:
        error_msg = f"Error executing command: {e}"
        # Print the exception error to stderr as well
        console_stderr_except = Console(file=sys.stderr, style="bold red")
        console_stderr_except.print(f"ERR> {error_msg}")
        return "", error_msg, -1

def get_ai_response(user_input: str, history: list = None, verbose: bool = True) -> str:
    """
    Interacts with the Gemini API. Returns the text response or a formatted error.
    """
    if history is None:
        history = []

    # Prepare history for Gemini (flat list of strings)
    flat_history = []
    flat_history.append(SYSTEM_PROMPT) # Use dynamic prompt

    for entry in history[-5:]: # Limit history sent
        if "user_input" in entry: # User query in ASK mode
            flat_history.append(f"User (ASK): {entry['user_input']}")

        if "ai_command" in entry:
            # AI responded with a command (after an ASK query)
            stdout_part = f"\nOutput:\n```\n{entry.get('stdout', '').strip()}\n```" if entry.get('stdout') else ""
            stderr_part = f"\nErrors:\n```\n{entry.get('stderr', '').strip()}\n```" if entry.get('stderr') else ""
            flat_history.append(f"Assistant (CMD:{entry['ai_command']}):{stdout_part}{stderr_part}\nReturn Code: {entry['return_code']}")
        elif "ai_response" in entry:
            # AI responded with text (after an ASK query)
            flat_history.append(f"Assistant (TEXT): {entry['ai_response']}")
        elif "ai_action" in entry and "proposed_command" in entry:
            # Action cancelled by user (after an ASK query)
            flat_history.append(f"Assistant: (Action cancelled by user: Proposal was 'CMD:{entry['proposed_command']}')")
        elif "user_command" in entry: # Command executed directly in EXECUTE mode
            stdout_part = f"\nOutput:\n```\n{entry.get('stdout', '').strip()}\n```" if entry.get('stdout') else ""
            stderr_part = f"\nErrors:\n```\n{entry.get('stderr', '').strip()}\n```" if entry.get('stderr') else ""
            flat_history.append(f"User (EXECUTE CMD:{entry['user_command']}):{stdout_part}{stderr_part}\nReturn Code: {entry['return_code']}")

    # Add the latest user query (ASK mode)
    flat_history.append(f"User (ASK): {user_input}")

    # Add verbosity instruction if needed
    if not verbose:
        flat_history.append("Assistant (Instruction): Respond only with 'CMD: your_exact_command'. Do not provide any explanation or additional text.")

    try:
        response = client.models.generate_content(
            model='models/gemini-2.5-pro-exp-03-25',
            contents=flat_history,
            )

        if response.text:
            return response.text.strip()
        else:
            # Use Rich to display debug feedback
            console.print(f"[magenta][SYSTEM][/magenta] DEBUG - Prompt Feedback:", response.prompt_feedback)
            # Return a formatted error message to be displayed by the main loop
            return "[AI_ERROR]Sorry, I could not generate a response. Check for potential safety blocks."

    except genai.errors.ClientError as e:
        # Specifically handle quota exhausted error
        if "RESOURCE_EXHAUSTED" in str(e):
            error_msg = "Google Gemini API quota exceeded. Please check your plan and billing details."
            console.print(f"[bold red]ERR>[/bold red] {error_msg}", style="bold red")
            return f"[AI_ERROR]{error_msg}"
        else:
            # Other API client errors
            error_msg = f"Gemini API client error: {e}"
            console.print(f"[bold red]ERR>[/bold red] {error_msg}", style="bold red")
            return f"[AI_ERROR]Communication error with AI (Client)."

    except Exception as e:
        # Other generic exceptions
        error_msg = f"Unexpected error during Gemini API call: {e}"
        # Print the system error immediately with Rich (without stderr)
        console.print(f"[bold red]ERR>[/bold red] {error_msg}", style="bold red")
        # Return a formatted error message for the main loop
        return f"[AI_ERROR]Unexpected communication error with AI."

# --- Nouvelle fonction pour obtenir l'explication de l'IA ---
def get_ai_explanation(command: str, stdout: str, stderr: str, return_code: int) -> str:
    """Asks the AI to explain the output of a command."""
    explanation_prompt = (
        f"Can you briefly explain the output of the following command?\n\n"
        f"Command: `{command}`\n"
        f"Return Code: {return_code}\n\n"
        f"Standard Output (stdout):\n```\n{stdout.strip() if stdout else '[Empty]'}\n```\n\n"
        f"Standard Error (stderr):\n```\n{stderr.strip() if stderr else '[Empty]'}\n```\n\n"
        f"Explanation:"
    )

    try:
        # Simplified API call, without the main conversation history
        response = client.models.generate_content(
            model='models/gemini-2.5-pro-exp-03-25', # Or a faster model if sufficient
            contents=[SYSTEM_PROMPT, explanation_prompt], # Use dynamic prompt
            # Stricter safety_settings could be added here if needed
        )
        if response.text:
            return response.text.strip()
        else:
            console.print(f"[magenta][SYSTEM][/magenta] DEBUG - Prompt Feedback (Explanation):", response.prompt_feedback)
            return "[AI_ERROR]Could not get an explanation."
    except genai.errors.ClientError as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            error_msg = "Google Gemini API quota exceeded for explanation."
            console.print(f"[bold red]ERR>[/bold red] {error_msg}", style="bold red")
            return f"[AI_ERROR]{error_msg}"
        else:
            error_msg = f"API client error during explanation request: {e}"
            console.print(f"[bold red]ERR>[/bold red] {error_msg}", style="bold red")
            return f"[AI_ERROR]Communication error for explanation (Client)."
    except Exception as e:
        error_msg = f"Unexpected error during explanation request: {e}"
        console.print(f"[bold red]ERR>[/bold red] {error_msg}", style="bold red")
        return f"[AI_ERROR]Unexpected error for explanation."

# --- Nouvelle fonction pour l'analyse d'erreur par l'IA ---
def get_ai_error_analysis(command: str, stdout: str, stderr: str, return_code: int) -> str:
    """Asks the AI to explain a command error and suggest a correction."""
    error_prompt = (
        f"The following command failed:\n\n"
        f"Command: `{command}`\n"
        f"Return Code: {return_code}\n\n"
        f"Standard Output (stdout):\n```\n{stdout.strip() if stdout else '[Empty]'}\n```\n\n"
        f"Standard Error (stderr):\n```\n{stderr.strip() if stderr else '[None]'}\n```\n\n"
        f"Can you briefly explain the cause of this error and propose a corrected command if possible? "
        f"If you propose a command, use *only* the format 'CMD: new_exact_command'. "
        f"Otherwise, just provide the explanation."
    )

    try:
        # API call without conversation history for this specific task
        response = client.models.generate_content(
            model='models/gemini-2.5-pro-exp-03-25', # High-performance model for analysis
            contents=[SYSTEM_PROMPT, error_prompt], # Use dynamic prompt
        )
        if response.text:
            return response.text.strip()
        else:
            console.print(f"[magenta][SYSTEM][/magenta] DEBUG - Prompt Feedback (Error Analysis):", response.prompt_feedback)
            return "[AI_ERROR]Could not analyze the error."
    except genai.errors.ClientError as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            error_msg = "Google Gemini API quota exceeded for error analysis."
            console.print(f"[bold red]ERR>[/bold red] {error_msg}", style="bold red")
            return f"[AI_ERROR]{error_msg}"
        else:
            error_msg = f"API client error during error analysis: {e}"
            console.print(f"[bold red]ERR>[/bold red] {error_msg}", style="bold red")
            return f"[AI_ERROR]Communication error for error analysis (Client)."
    except Exception as e:
        error_msg = f"Unexpected error during error analysis: {e}"
        console.print(f"[bold red]ERR>[/bold red] {error_msg}", style="bold red")
        return f"[AI_ERROR]Unexpected error for error analysis."

# --- ASCII Art Banner --- 
# (Assigné à une variable pour éviter les problèmes de parsing dans les f-strings ou print multilignes)
BANNER = r"""
                            _                      
                           | |                     
   ___ _ __ ___   __ _ _ __| |_ ___ _ __ _ __ ___  
  / __| '_` _ \ / _` | '__| __/ _ \ '__| '_` _ \ 
 \__ \ | | | | | (_| | |  | ||  __/ |  | | | | | | |
 |___/_| |_| |_|\__,_|_|   \__\___|_|  |_| |_| |_|
                                                   
                                                   
"""

def main():
    """Main loop of the terminal with modes, verbosity, Rich UI, and error handling."""

    # --- Initial Screen Clear ---
    os_name = platform.system()
    if os_name == "Windows":
        os.system('cls')
    else:
        os.system('clear')

    # --- Display Banner ---
    console.print(f"[bold cyan]{BANNER}[/bold cyan]")
    version = "1.0"
    repo_url = "https://github.com/calebreseau/smarterm"
    console.print(f"[dim]Version {version} | {repo_url}[/dim]\n")

    # Welcome message and instructions
    console.print("[magenta]Modes:[/magenta]")
    console.print("  [bold](E)XECUTE[/bold]: Type shell commands directly.")
    console.print("  [bold](A)SK[/bold]    : Ask questions or request commands from the AI.")
    console.print("[magenta]Special Commands:[/magenta]")
    console.print("[cyan]  '!!'       [/cyan]: Switch mode (EXECUTE/ASK)")
    console.print("[cyan]  '!verbose' [/cyan] or [cyan]'!v'[/cyan]: Toggle verbose mode (explanations ON[bold green]V[/bold green]/OFF)")
    console.print("[cyan]  '!clear'   [/cyan] or [cyan]'!cls'[/cyan]: Clear screen")
    console.print("[cyan]  'exit' [/cyan] or [cyan]'!q' [/cyan]: Quit")

    command_history = []
    mode = "EXECUTE"
    verbose_mode = True
    # os_name already detected for initial clear

    while True:
        try:
            verbose_indicator = "[bold green]V[/bold green]" if verbose_mode else " "
            mode_indicator = "[bold blue]E[/bold blue]" if mode == "EXECUTE" else "[bold yellow]A[/bold yellow]"
            prompt_prefix = f"({mode_indicator}{verbose_indicator}) > "

            # Use Prompt.ask for main input
            user_input = Prompt.ask(f"[cyan]{prompt_prefix}[/cyan]", default="", show_default=False).strip()

            # --- Internal Special Commands ---
            input_lower = user_input.lower()

            if input_lower in ['exit', '!q']:
                break

            if input_lower == '!!':
                mode = "ASK" if mode == "EXECUTE" else "EXECUTE"
                console.print(f"[magenta][SYSTEM][/magenta] Switched to [bold]{mode}[/bold] mode.")
                continue

            if input_lower in ['!verbose', '!v']:
                verbose_mode = not verbose_mode
                status = "[bold green]enabled[/bold green]" if verbose_mode else "[bold red]disabled[/bold red]"
                console.print(f"[magenta][SYSTEM][/magenta] Verbose mode {status}.")
                continue

            if input_lower in ['!clear', '!cls']:
                if os_name == "Windows":
                    os.system('cls')
                else:
                    os.system('clear')
                # Redisplay banner and instructions after clearing
                console.print(f"[bold cyan]{BANNER}[/bold cyan]") # Use variable
                console.print(f"[dim]Version {version} | {repo_url}[/dim]\n")
                console.print("[magenta]Modes:[/magenta]")
                console.print("  [bold](E)XECUTE[/bold]: Type shell commands directly.")
                console.print("  [bold](A)SK[/bold]    : Ask questions or request commands from the AI.")
                console.print("[magenta]Special Commands:[/magenta]")
                console.print("[cyan]  '!!'       [/cyan]: Switch mode (EXECUTE/ASK)")
                console.print("[cyan]  '!verbose' [/cyan] or [cyan]'!v'[/cyan]: Toggle verbose mode (explanations ON[bold green]V[/bold green]/OFF)")
                console.print("[cyan]  '!clear'   [/cyan] or [cyan]'!cls'[/cyan]: Clear screen")
                console.print("[cyan]  'exit' [/cyan] or [cyan]'!q' [/cyan]: Quit")
                continue # Move to the next loop iteration

            if not user_input:
                continue

            # --- Logic based on mode ---
            executed_command_info = None
            command_failed = False
            ai_error_analysis_result = None

            if mode == "EXECUTE":
                # --- Direct execution ---
                stdout, stderr, return_code = execute_command(user_input)
                executed_command_info = {"command": user_input, "stdout": stdout, "stderr": stderr, "return_code": return_code}
                command_history.append({"user_command": user_input, "stdout": stdout, "stderr": stderr, "return_code": return_code})
                if return_code != 0 or stderr:
                    command_failed = True

            elif mode == "ASK":
                # --- AI Interaction ---
                with console.status("[bold green]AI thinking..."): # Translated
                    ai_output = get_ai_response(user_input, command_history, verbose=verbose_mode)

                if ai_output.startswith("[AI_ERROR]"):
                    error_message = ai_output.replace("[AI_ERROR]", "").strip()
                    console.print(f"[bold red]AI Error:[/bold red] {error_message}") # Translated
                    command_history.append({"user_input": user_input, "ai_response": f"ERROR: {error_message}"})

                elif ai_output.startswith("CMD:"):
                    # --- Command proposal by AI ---
                    proposed_command = ai_output[4:].strip()
                    should_execute, command_to_execute = get_user_confirmation(proposed_command)

                    if should_execute:
                        stdout, stderr, return_code = execute_command(command_to_execute)
                        executed_command_info = {"command": command_to_execute, "stdout": stdout, "stderr": stderr, "return_code": return_code}
                        command_history.append({"user_input": user_input, "ai_command": command_to_execute, "stdout": stdout, "stderr": stderr, "return_code": return_code})
                        if return_code != 0 or stderr:
                            command_failed = True
                    else:
                        # Command cancelled in get_user_confirmation, message already printed
                        command_history.append({"user_input": user_input, "ai_action": "Proposed command cancelled", "proposed_command": proposed_command})
                else:
                    # --- Text response from AI ---
                    console.print(f"[green]AI:[/green] {ai_output}") # Translated
                    command_history.append({"user_input": user_input, "ai_response": ai_output})

            # --- Post-Execution Error Analysis (if failed) ---
            if command_failed and executed_command_info:
                console.print("[yellow]Analyzing error with AI...[/yellow]") # Translated
                with console.status("[bold yellow]AI analyzing error..."): # Translated
                    ai_error_analysis_result = get_ai_error_analysis(**executed_command_info)

                if ai_error_analysis_result:
                    if ai_error_analysis_result.startswith("[AI_ERROR]"):
                        error_message = ai_error_analysis_result.replace("[AI_ERROR]", "").strip()
                        console.print(f"[bold red]Analysis Error:[/bold red] {error_message}") # Translated
                        # Failure to analyze is handled, no specific history entry needed here
                    elif ai_error_analysis_result.startswith("CMD:"):
                        # --- Correction proposal by AI ---
                        corrected_command = ai_error_analysis_result[4:].strip()
                        console.print("[yellow]AI suggests a correction:[/yellow]") # Translated
                        should_execute_correction, correction_to_execute = get_user_confirmation(corrected_command)
                        if should_execute_correction:
                            # Execute the correction
                            corr_stdout, corr_stderr, corr_ret_code = execute_command(correction_to_execute)
                            # Add correction attempt to history
                            command_history.append({
                                "user_input": "Auto-correction after error", # Translated context
                                "ai_command": correction_to_execute,
                                "stdout": corr_stdout,
                                "stderr": corr_stderr,
                                "return_code": corr_ret_code
                            })
                            # If the correction also fails, don't re-analyze to avoid loops
                            if corr_ret_code != 0 or corr_stderr:
                                console.print("[bold red]The proposed correction also failed.[/bold red]") # Translated
                        else:
                             # Correction refused
                            command_history.append({
                                "user_input": "Error analysis performed", # Translated
                                "ai_action": "Proposed correction refused", # Translated
                                "proposed_command": corrected_command
                            })
                    else:
                        # AI provided an explanation without a command
                        console.print(f"[yellow]AI Analysis:[/yellow]\n{ai_error_analysis_result}") # Translated
                         # The analysis itself isn't a loggable action like a command

            # --- Post-Execution Explanation (if success AND verbose) ---
            elif not command_failed and verbose_mode and executed_command_info:
                console.print("[grey50]Getting explanation from AI...[/grey50]") # Translated
                with console.status("[bold green]AI explaining..."): # Translated
                    explanation = get_ai_explanation(**executed_command_info)
                if explanation.startswith("[AI_ERROR]"):
                    error_message = explanation.replace("[AI_ERROR]", "").strip()
                    console.print(f"[bold red]Explanation Error:[/bold red] {error_message}") # Translated
                else:
                    console.print(f"[italic grey50]AI Explanation:[/italic grey50]\n{explanation}") # Translated

        except EOFError:
            break
        except KeyboardInterrupt:
            console.print(f"\n[magenta][SYSTEM][/magenta] Interruption received. Type 'exit' or '!q' to quit.") # Translated

    console.print(f"\n[magenta][SYSTEM][/magenta] Goodbye!") # Translated

if __name__ == "__main__":
    main() 