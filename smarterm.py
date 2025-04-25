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
def load_api_key(config_file='config.ini') -> str | None:
    """Charge la clé API Gemini depuis un fichier de configuration."""
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
        console.print(f"[bold red]Erreur:[/bold red] Fichier de configuration '[cyan]{config_file}[/cyan]' introuvable.")
        console.print("Veuillez créer ce fichier avec le contenu suivant:")
        console.print("[bright_black on white] [API]                                [/]")
        console.print("[bright_black on white] GEMINI_API_KEY = VOTRE_CLE_API_ICI [/]")
        return None
    except (configparser.NoSectionError, configparser.NoOptionError):
        console.print(f"[bold red]Erreur:[/bold red] Clé '[cyan]GEMINI_API_KEY[/cyan]' non trouvée dans la section [bold green][API][/bold green] du fichier '[cyan]{config_file}[/cyan]'.")
        console.print("Assurez-vous que le fichier contient:")
        console.print("[bright_black on white] [API]                                [/]")
        console.print("[bright_black on white] GEMINI_API_KEY = VOTRE_CLE_API_ICI [/]")
        return None
    except Exception as e:
         console.print(f"[bold red]Erreur inattendue[/bold red] lors de la lecture de '[cyan]{config_file}[/cyan]': {e}")
         return None

# --- Initialisation du client API ---
api_key = load_api_key()
if not api_key:
    sys.exit(1)

try:
    client = genai.Client(api_key=api_key)
except Exception as e:
    console.print(f"[bold red]Erreur[/bold red] lors de l'initialisation du client Gemini avec la clé fournie: {e}")
    sys.exit(1)

# --- Génération dynamique du Prompt Système --- 
def get_system_prompt() -> str:
    """Génère le prompt système en fonction de l'OS détecté."""
    os_name = platform.system()
    if os_name == "Windows":
        shell_type = "CMD/PowerShell"
        os_specific_guidance = "Tu opères dans un terminal sous Windows."
    elif os_name == "Linux":
        shell_type = "bash/zsh ou autre shell standard Linux"
        os_specific_guidance = "Tu opères dans un terminal sous Linux."
    elif os_name == "Darwin": # macOS
        shell_type = "bash/zsh ou autre shell standard macOS"
        os_specific_guidance = "Tu opères dans un terminal sous macOS."
    else:
        shell_type = "shell inconnu"
        os_specific_guidance = f"Tu opères dans un terminal sous un système d'exploitation inconnu ({os_name}). Essaye d'utiliser des commandes POSIX standard."

    return (
        f"{os_specific_guidance} "
        f"Ton objectif est d'aider l'utilisateur à atteindre ses buts en exécutant des commandes {shell_type}. "
        f"Utilise l'historique des commandes et leurs sorties pour comprendre le contexte. "
        f"Anticipe les besoins de l'utilisateur si possible. "
        f"Quand tu dois exécuter une commande, réponds *uniquement* avec 'CMD:' suivi de la commande exacte. "
        f"Exemple (Windows): CMD:dir /w. Exemple (Linux/macOS): CMD:ls -l. "
        f"Pour toute autre réponse (explication, question), utilise du langage naturel. "
        f"Sois concis dans tes réponses."
    )

# Définir le prompt système au démarrage
SYSTEM_PROMPT = get_system_prompt()

def get_user_confirmation(command: str) -> tuple[bool, str]:
    """
    Affiche la commande proposée, permet à l'utilisateur de la modifier,
    et attend sa confirmation (Entrée) ou annulation (Ctrl+C). Utilise Rich pour l'affichage.

    Returns:
        Un tuple (bool, str):
        - Le booléen indique si l'exécution doit avoir lieu (True) ou non (False).
        - La chaîne est la commande à exécuter (originale ou modifiée).
    """
    console.print(f"[magenta]AI propose:[/magenta] [bold yellow]{command}[/bold yellow]")
    prompt_text = "Confirmer/Modifier et Entrée (Ctrl+C pour annuler/corriger) > "

    try:
        # Utiliser Prompt.ask de Rich pour un input stylisé
        user_command = Prompt.ask(f"[cyan]{prompt_text}[/cyan]", default="", show_default=False).strip()

        if not user_command:
            return True, command
        else:
            return True, user_command
    except KeyboardInterrupt:
        console.print(f"\n[magenta][SYSTEM][/magenta] Commande annulée. Vous pouvez demander une correction.")
        return False, "" # Pas de commande à exécuter

def execute_command(command: str) -> tuple[str, str, int]:
    """Exécute la commande et retourne stdout, stderr, et le code de retour, avec affichage via Rich."""
    stdout_lines = []
    stderr_lines = []
    try:
        console.print(f"[blue]--- Exécution de : [bold]{command}[/bold] ---[/blue]")
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')

        # Lire stdout avec Rich
        if process.stdout:
            for line in process.stdout:
                line_content = line.strip()
                console.print(f"[dim]OUT>[/dim] {line_content}") # Style 'dim' pour la sortie standard
                stdout_lines.append(line_content)
            process.stdout.close()

        # Lire stderr avec Rich
        if process.stderr:
            # Créer une console spécifique pour stderr pour l'affichage coloré
            console_stderr = Console(file=sys.stderr, style="bold red")
            for line in process.stderr:
                line_content = line.strip()
                # Imprimer sur stderr via la console dédiée
                console_stderr.print(f"ERR> {line_content}")
                stderr_lines.append(line_content)
            process.stderr.close()

        process.wait()
        returncode = process.returncode
        status_style = "green" if returncode == 0 else "red"
        console.print(f"[blue]--- Commande terminée (code: [{status_style}]{returncode}[/{status_style}]) ---[/blue]")
        return "\n".join(stdout_lines), "\n".join(stderr_lines), returncode

    except Exception as e:
        error_msg = f"Erreur lors de l'exécution de la commande: {e}"
        # Imprimer l'erreur d'exception sur stderr également
        console_stderr_except = Console(file=sys.stderr, style="bold red")
        console_stderr_except.print(f"ERR> {error_msg}")
        return "", error_msg, -1

def get_ai_response(user_input: str, history: list = None, verbose: bool = True) -> str:
    """
    Interagit avec l'API Gemini. Retourne la réponse texte ou une erreur formatée.
    """
    if history is None:
        history = []

    # Préparer l'historique pour Gemini (liste plate de chaînes)
    flat_history = []
    flat_history.append(SYSTEM_PROMPT)

    for entry in history[-5:]: # Limiter l'historique envoyé
        if "user_input" in entry: # Requête utilisateur en mode ASK
            flat_history.append(f"Utilisateur (ASK): {entry['user_input']}")

        if "ai_command" in entry:
            # L'IA a répondu avec une commande (après une requête ASK)
            stdout_part = f"\nSortie:\n```\n{entry.get('stdout', '').strip()}\n```" if entry.get('stdout') else ""
            stderr_part = f"\nErreurs:\n```\n{entry.get('stderr', '').strip()}\n```" if entry.get('stderr') else ""
            flat_history.append(f"Assistant (CMD:{entry['ai_command']}):{stdout_part}{stderr_part}\nCode retour: {entry['return_code']}")
        elif "ai_response" in entry:
            # L'IA a répondu avec du texte (après une requête ASK)
            flat_history.append(f"Assistant (TEXT): {entry['ai_response']}")
        elif "ai_action" in entry and "proposed_command" in entry:
            # Action annulée par l'utilisateur (après une requête ASK)
            flat_history.append(f"Assistant: (Action annulée par l'utilisateur : Proposition était 'CMD:{entry['proposed_command']}')")
        elif "user_command" in entry: # Commande exécutée directement en mode EXECUTE
            stdout_part = f"\nSortie:\n```\n{entry.get('stdout', '').strip()}\n```" if entry.get('stdout') else ""
            stderr_part = f"\nErreurs:\n```\n{entry.get('stderr', '').strip()}\n```" if entry.get('stderr') else ""
            flat_history.append(f"Utilisateur (EXECUTE CMD:{entry['user_command']}):{stdout_part}{stderr_part}\nCode retour: {entry['return_code']}")

    # Ajouter la dernière requête utilisateur (mode ASK)
    flat_history.append(f"Utilisateur (ASK): {user_input}")

    # Ajouter l'instruction de verbosité si nécessaire
    if not verbose:
        flat_history.append("Assistant (Instruction): Réponds uniquement avec 'CMD: ta_commande_exacte'. Ne fournis aucune explication ou texte supplémentaire.")

    try:
        response = client.models.generate_content(
            model='models/gemini-2.5-pro-exp-03-25',
            contents=flat_history,
            )

        if response.text:
            return response.text.strip()
        else:
            # Utiliser Rich pour afficher le feedback de debug
            console.print(f"[magenta][SYSTEM][/magenta] DEBUG - Prompt Feedback:", response.prompt_feedback)
            # Retourner un message d'erreur formaté pour la boucle principale
            return "[AI_ERROR]Désolé, je n'ai pas pu générer de réponse. Vérifiez les éventuels blocages de sécurité."

    except genai.errors.ClientError as e:
        # Gérer spécifiquement l'erreur de quota épuisé
        if "RESOURCE_EXHAUSTED" in str(e):
            error_msg = "Quota d'API Google Gemini épuisé. Veuillez vérifier votre plan et vos informations de facturation."
            console.print(f"[bold red]ERR>[/bold red] {error_msg}", style="bold red")
            return f"[AI_ERROR]{error_msg}"
        else:
            # Autres erreurs client de l'API
            error_msg = f"Erreur client API Gemini: {e}"
            console.print(f"[bold red]ERR>[/bold red] {error_msg}", style="bold red")
            return f"[AI_ERROR]Erreur de communication avec l'IA (Client)."

    except Exception as e:
        # Autres exceptions génériques
        error_msg = f"Erreur inattendue lors de l'appel à l'API Gemini: {e}"
        # Imprimer l'erreur système immédiatement avec Rich (sans stderr)
        console.print(f"[bold red]ERR>[/bold red] {error_msg}", style="bold red")
        # Retourner un message d'erreur formaté pour la boucle principale
        return f"[AI_ERROR]Erreur inattendue de communication avec l'IA."

# --- Nouvelle fonction pour obtenir l'explication de l'IA ---
def get_ai_explanation(command: str, stdout: str, stderr: str, return_code: int) -> str:
    """Demande à l'IA d'expliquer la sortie d'une commande."""
    explanation_prompt = (
        f"Peux-tu expliquer brièvement la sortie de la commande suivante ?\n\n"
        f"Commande: `{command}`\n"
        f"Code retour: {return_code}\n\n"
        f"Sortie Standard (stdout):\n```\n{stdout.strip() if stdout else '[Vide]'}\n```\n\n"
        f"Sortie d'Erreur (stderr):\n```\n{stderr.strip() if stderr else '[Vide]'}\n```\n\n"
        f"Explication:"
    )

    try:
        # Appel API simplifié, sans l'historique de conversation principal
        response = client.models.generate_content(
            model='models/gemini-2.5-pro-exp-03-25', # Ou un modèle plus rapide si suffisant
            contents=[SYSTEM_PROMPT, explanation_prompt], # Utilise le prompt dynamique
            # On pourrait ajouter des safety_settings plus stricts ici si besoin
        )
        if response.text:
            return response.text.strip()
        else:
            console.print(f"[magenta][SYSTEM][/magenta] DEBUG - Prompt Feedback (Explanation):", response.prompt_feedback)
            return "[AI_ERROR]Impossible d'obtenir une explication."
    except genai.errors.ClientError as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            error_msg = "Quota d'API Google Gemini épuisé pour l'explication."
            console.print(f"[bold red]ERR>[/bold red] {error_msg}", style="bold red")
            return f"[AI_ERROR]{error_msg}"
        else:
            error_msg = f"Erreur client API pendant la demande d'explication: {e}"
            console.print(f"[bold red]ERR>[/bold red] {error_msg}", style="bold red")
            return f"[AI_ERROR]Erreur de communication pour l'explication (Client)."
    except Exception as e:
        error_msg = f"Erreur inattendue pendant la demande d'explication: {e}"
        console.print(f"[bold red]ERR>[/bold red] {error_msg}", style="bold red")
        return f"[AI_ERROR]Erreur inattendue pour l'explication."

# --- Nouvelle fonction pour l'analyse d'erreur par l'IA ---
def get_ai_error_analysis(command: str, stdout: str, stderr: str, return_code: int) -> str:
    """Demande à l'IA d'expliquer une erreur de commande et de proposer une correction."""
    error_prompt = (
        f"La commande suivante a échoué:\n\n"
        f"Commande: `{command}`\n"
        f"Code retour: {return_code}\n\n"
        f"Sortie Standard (stdout):\n```\n{stdout.strip() if stdout else '[Vide]'}\n```\n\n"
        f"Sortie d'Erreur (stderr):\n```\n{stderr.strip() if stderr else '[Aucune]'}\n```\n\n"
        f"Peux-tu expliquer brièvement la cause de cette erreur et proposer une commande corrigée si possible ? "
        f"Si tu proposes une commande, utilise *uniquement* le format 'CMD: nouvelle_commande_exacte'. "
        f"Sinon, fournis juste l'explication."
    )

    try:
        # Appel API sans l'historique de conversation pour cette tâche spécifique
        response = client.models.generate_content(
            model='models/gemini-2.5-pro-exp-03-25', # Modèle performant pour l'analyse
            contents=[SYSTEM_PROMPT, error_prompt], # Utilise le prompt dynamique
        )
        if response.text:
            return response.text.strip()
        else:
            console.print(f"[magenta][SYSTEM][/magenta] DEBUG - Prompt Feedback (Error Analysis):", response.prompt_feedback)
            return "[AI_ERROR]Impossible d'analyser l'erreur."
    except genai.errors.ClientError as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            error_msg = "Quota d'API Google Gemini épuisé pour l'analyse d'erreur."
            console.print(f"[bold red]ERR>[/bold red] {error_msg}", style="bold red")
            return f"[AI_ERROR]{error_msg}"
        else:
            error_msg = f"Erreur client API pendant l'analyse de l'erreur: {e}"
            console.print(f"[bold red]ERR>[/bold red] {error_msg}", style="bold red")
            return f"[AI_ERROR]Erreur de communication pour l'analyse d'erreur (Client)."
    except Exception as e:
        error_msg = f"Erreur inattendue pendant l'analyse de l'erreur: {e}"
        console.print(f"[bold red]ERR>[/bold red] {error_msg}", style="bold red")
        return f"[AI_ERROR]Erreur inattendue pour l'analyse d'erreur."

def main():
    """Boucle principale du terminal avec modes, verbosité, Rich UI et gestion d'erreurs."""
    # Clarification dans le message d'accueil
    console.print("[bold magenta]Terminal IA[/bold magenta]")
    console.print("[magenta]Modes:[/magenta]")
    console.print("  [bold](E)XECUTE[/bold]: Tapez des commandes shell directement.")
    console.print("  [bold](A)SK[/bold]    : Posez des questions ou demandez des commandes à l'IA.")
    console.print("[magenta]Commandes spéciales:[/magenta]")
    console.print("[cyan]  '!!'      [/cyan]: Changer de mode (EXECUTE/ASK)")
    console.print("[cyan]  '!verbose'[/cyan] ou [cyan]'!v'[/cyan]: Basculer mode verbose (explications post-commande ON[bold green]V[/bold green]/OFF)")
    console.print("[cyan]  'exit'    [/cyan]: Quitter")

    command_history = []
    mode = "EXECUTE"
    verbose_mode = True

    while True:
        try:
            verbose_indicator = "[bold green]V[/bold green]" if verbose_mode else " "
            mode_indicator = "[bold blue]E[/bold blue]" if mode == "EXECUTE" else "[bold yellow]A[/bold yellow]"
            prompt_prefix = f"({mode_indicator}{verbose_indicator}) > "

            # Utiliser Prompt.ask pour l'input principal
            user_input = Prompt.ask(f"[cyan]{prompt_prefix}[/cyan]", default="", show_default=False).strip()

            if user_input.lower() == 'exit':
                break

            if user_input == '!!':
                mode = "ASK" if mode == "EXECUTE" else "EXECUTE"
                console.print(f"[magenta][SYSTEM][/magenta] Passage en mode [bold]{mode}[/bold].")
                continue

            if user_input.lower() in ['!verbose', '!v']:
                verbose_mode = not verbose_mode
                status = "[bold green]activé[/bold green]" if verbose_mode else "[bold red]désactivé[/bold red]"
                console.print(f"[magenta][SYSTEM][/magenta] Mode verbose {status}.")
                continue

            if not user_input:
                continue

            # --- Logique selon le mode ---
            executed_command_info = None
            command_failed = False
            ai_error_analysis_result = None

            if mode == "EXECUTE":
                # --- Exécution directe ---
                stdout, stderr, return_code = execute_command(user_input)
                executed_command_info = {"command": user_input, "stdout": stdout, "stderr": stderr, "return_code": return_code}
                command_history.append({"user_command": user_input, "stdout": stdout, "stderr": stderr, "return_code": return_code})
                if return_code != 0 or stderr:
                    command_failed = True

            elif mode == "ASK":
                # --- Interaction IA ---
                with console.status("[bold green]IA réfléchit..."):
                    ai_output = get_ai_response(user_input, command_history, verbose=verbose_mode)

                if ai_output.startswith("[AI_ERROR]"):
                    error_message = ai_output.replace("[AI_ERROR]", "").strip()
                    console.print(f"[bold red]AI Erreur:[/bold red] {error_message}")
                    command_history.append({"user_input": user_input, "ai_response": f"ERREUR: {error_message}"})

                elif ai_output.startswith("CMD:"):
                    # --- Proposition de commande par l'IA ---
                    proposed_command = ai_output[4:].strip()
                    should_execute, command_to_execute = get_user_confirmation(proposed_command)

                    if should_execute:
                        stdout, stderr, return_code = execute_command(command_to_execute)
                        executed_command_info = {"command": command_to_execute, "stdout": stdout, "stderr": stderr, "return_code": return_code}
                        command_history.append({"user_input": user_input, "ai_command": command_to_execute, "stdout": stdout, "stderr": stderr, "return_code": return_code})
                        if return_code != 0 or stderr:
                            command_failed = True
                    else:
                        command_history.append({"user_input": user_input, "ai_action": "Commande proposée annulée", "proposed_command": proposed_command})
                else:
                    # --- Réponse texte de l'IA ---
                    console.print(f"[green]AI:[/green] {ai_output}")
                    command_history.append({"user_input": user_input, "ai_response": ai_output})

            # --- Analyse d'Erreur Post-Exécution (si échec) ---
            if command_failed and executed_command_info:
                console.print("[yellow]Analyse de l'erreur par l'IA...[/yellow]")
                with console.status("[bold yellow]IA analyse l'erreur..."):
                    ai_error_analysis_result = get_ai_error_analysis(**executed_command_info)

                if ai_error_analysis_result:
                    if ai_error_analysis_result.startswith("[AI_ERROR]"):
                        error_message = ai_error_analysis_result.replace("[AI_ERROR]", "").strip()
                        console.print(f"[bold red]Erreur Analyse:[/bold red] {error_message}")
                        # L'échec de l'analyse est géré, pas besoin d'ajouter spécifiquement à l'historique ici
                    elif ai_error_analysis_result.startswith("CMD:"):
                        # --- Proposition de correction par l'IA ---
                        corrected_command = ai_error_analysis_result[4:].strip()
                        console.print("[yellow]IA suggère une correction:[/yellow]")
                        should_execute_correction, correction_to_execute = get_user_confirmation(corrected_command)
                        if should_execute_correction:
                            # Exécuter la correction
                            corr_stdout, corr_stderr, corr_ret_code = execute_command(correction_to_execute)
                            # Ajouter la tentative de correction à l'historique
                            command_history.append({
                                "user_input": "Correction auto suite à erreur", # Indiquer le contexte
                                "ai_command": correction_to_execute,
                                "stdout": corr_stdout,
                                "stderr": corr_stderr,
                                "return_code": corr_ret_code
                            })
                            # Si la correction échoue aussi, on ne relance pas l'analyse pour éviter boucle
                            if corr_ret_code != 0 or corr_stderr:
                                console.print("[bold red]La correction proposée a également échoué.[/bold red]")
                        else:
                             # Correction refusée
                            command_history.append({
                                "user_input": "Analyse erreur effectuée",
                                "ai_action": "Correction proposée refusée",
                                "proposed_command": corrected_command
                            })
                    else:
                        # L'IA a fourni une explication sans commande
                        console.print(f"[yellow]Analyse IA:[/yellow]\n{ai_error_analysis_result}")
                         # L'analyse elle-même n'est pas une action historisable de la même manière qu'une commande

            # --- Explication Post-Exécution (si succès ET verbose) ---
            elif not command_failed and verbose_mode and executed_command_info:
                console.print("[grey50]Explication du résultat par l'IA...[/grey50]")
                with console.status("[bold green]IA explique..."):
                    explanation = get_ai_explanation(**executed_command_info)
                if explanation.startswith("[AI_ERROR]"):
                    error_message = explanation.replace("[AI_ERROR]", "").strip()
                    console.print(f"[bold red]Erreur Explication:[/bold red] {error_message}")
                else:
                    console.print(f"[italic grey50]Explication IA:[/italic grey50]\n{explanation}")

        except EOFError:
            break
        except KeyboardInterrupt:
            console.print(f"\n[magenta][SYSTEM][/magenta] Interruption reçue. Tapez 'exit' pour quitter.")

    console.print(f"\n[magenta][SYSTEM][/magenta] Au revoir!")

if __name__ == "__main__":
    main() 