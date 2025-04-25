# SmarTerm ✨

Your intelligent terminal assistant powered by Google Gemini.

SmarTerm is a command-line tool designed to enhance your terminal experience. It allows you to interact with your shell (Windows CMD/PowerShell, Linux/macOS Bash/Zsh) more intuitively using artificial intelligence to:

*   Generate complex shell commands from natural language descriptions.
*   Explain the output of the commands you run.
*   Analyze command errors and suggest corrections.
*   Automatically adapt to the operating system you are using.

## Core Features

*   **ASK Mode**: Ask the AI to generate a command for you.
*   **EXECUTE Mode**: Use the terminal as usual, with superpowers waiting.
*   **AI Explanation (Verbose Mode)**: Get an automatic explanation of the output after each successful command in EXECUTE mode.
*   **AI Error Analysis**: If a command fails, the AI attempts to explain the error and may propose a corrected command.
*   **OS Adaptation**: The system prompt sent to the AI adapts to Windows, Linux, or macOS for more accurate suggestions.
*   **History Context**: The AI considers previous commands to better understand your intent.
*   **Rich Interface**: Uses the `rich` library for clear and colorful display.

## Installation

**Prerequisites:**

*   **Python 3** (version 3.7+ recommended)
*   **Git**

Ensure that Python and Git are installed and accessible from your PATH.

**Quick Installation (One-Liners):**

⚠️ **Warning:** Running scripts downloaded directly from the internet carries security risks. Inspect the script content if you have any doubts before executing.

*   **Linux / macOS (Bash):**

    ```bash
    curl -sSL https://raw.githubusercontent.com/calebreseau/smarterm/main/install.sh | bash
    ```

*   **Windows (PowerShell):**

    *If using PowerShell 6+:*
    ```powershell
    irm https://raw.githubusercontent.com/calebreseau/smarterm/main/install.ps1 | iex
    ```
    *If using Windows PowerShell 5.1 (typically included in Windows 10/11):*
    ```powershell
    iwr https://raw.githubusercontent.com/calebreseau/smarterm/main/install.ps1 -UseBasicParsing | Select-Object -ExpandProperty Content | iex
    ```

These commands will:
1.  Clone the repository into `$HOME/smarterm` (Linux/macOS) or `$env:USERPROFILE\smarterm` (Windows).
2.  Install the necessary Python dependencies (`google-generativeai`, `rich`).
3.  Attempt to add the script's directory to your user PATH (Linux/macOS via a symbolic link in `~/.local/bin`, Windows via the user environment variable).

➡️ Open a **new terminal** after installation for the PATH changes to take effect.

## Configuration

SmarTerm needs a Google Gemini API key to function.

1.  Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  Create a configuration file named `config.ini` in the following location:
    *   **Linux/macOS:** `~/smarterm/config.ini`
    *   **Windows:** `C:\Users\YOUR_USERNAME\smarterm\config.ini`
    *(The installation script clones the code into `~/smarterm` or `$env:USERPROFILE\smarterm`. You need to create the `config.ini` file **inside** this folder.)*

3.  Add the following content to `config.ini`, replacing `YOUR_API_KEY_HERE` with your actual key:

    ```ini
    [API]
    GEMINI_API_KEY = YOUR_API_KEY_HERE
    ```

## Usage

Once installed and configured, open a new terminal and launch the application simply with:

```bash
smarterm
```

The application will start and display a banner followed by the prompt.

**Modes:**

*   **`(E)` EXECUTE** (default): Type your shell commands directly (e.g., `ls -l`, `dir`).
    *   If verbose mode is enabled (`V`), the AI will explain the output.
    *   In case of an error, the AI will analyze the problem.
*   **`(A)` ASK**: Ask the AI a question or request a command generation (e.g., `list python processes`, `how to find files larger than 100MB?`).
    *   If the AI proposes a command (`CMD:...`), you can confirm, modify, or cancel it before execution.

**Special Commands:**

*   `!!`: Switch between EXECUTE and ASK modes.
*   `!verbose` or `!v`: Toggle verbose mode (automatic explanations in EXECUTE mode).
*   `!clear` or `!cls`: Clear the terminal screen.
*   `exit` or `!q`: Quit SmarTerm.

## License

This project is licensed under the [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-nc-sa/4.0/).

See the [LICENSE](LICENSE) file for details. 