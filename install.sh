#!/bin/bash

# Script d'installation pour SmarTerm (Linux/macOS)

# Variables (Modifiez l'URL du dépôt)
REPO_URL="https://github.com/calebreseau/smarterm"
INSTALL_DIR="$HOME/smarterm"
BIN_DIR="$HOME/.local/bin"
PYTHON_CMD="python3"
PIP_CMD="$PYTHON_CMD -m pip"
SCRIPT_NAME="smarterm"
TARGET_SCRIPT="smarterm.py"

# Couleurs
C_RED='\033[0;31m'
C_GREEN='\033[0;32m'
C_YELLOW='\033[0;33m'
C_NC='\033[0m' # No Color

# Fonction pour afficher les messages
log() {
    LEVEL=$1
    MSG=$2
    case $LEVEL in
        INFO)  echo -e "[${C_GREEN}INFO${C_NC}] $MSG" ;;
        WARN)  echo -e "[${C_YELLOW}WARN${C_NC}] $MSG" ;;
        ERROR) echo -e "[${C_RED}ERROR${C_NC}] $MSG" >&2 ;;
        *)     echo -e "$MSG" ;;
    esac
}

# Fonction pour vérifier si une commande existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# --- Vérifications Préliminaires ---
log INFO "Démarrage de l'installation de SmarTerm..."

# Vérifier Python 3
log INFO "Vérification de Python 3..."
if ! command_exists $PYTHON_CMD; then
    log ERROR "$PYTHON_CMD n'a pas été trouvé. Veuillez installer Python 3."
    exit 1
fi
PYTHON_VERSION=$($PYTHON_CMD --version)
log INFO "Python trouvé: $PYTHON_VERSION"

# Vérifier Pip
log INFO "Vérification de Pip..."
if ! $PYTHON_CMD -m pip --version > /dev/null 2>&1; then
    log ERROR "Pip n'a pas été trouvé pour $PYTHON_CMD. Essayez: $PYTHON_CMD -m ensurepip --upgrade"
    exit 1
fi
log INFO "Pip trouvé."

# Vérifier Git
log INFO "Vérification de Git..."
if ! command_exists git; then
    log ERROR "Git n'a pas été trouvé. Veuillez l'installer (ex: sudo apt install git / brew install git)."
    exit 1
fi
log INFO "Git trouvé."

# --- Installation ---

# Vérifier si le répertoire d'installation existe déjà
if [[ -d "$INSTALL_DIR" ]]; then
    log WARN "Le répertoire d'installation '$INSTALL_DIR' existe déjà. Tentative de mise à jour."
    cd "$INSTALL_DIR" || { log ERROR "Impossible d'accéder à $INSTALL_DIR"; exit 1; }
    log INFO "Mise à jour du dépôt via 'git pull'..."
    if ! git pull; then
        log ERROR "Échec de la mise à jour du dépôt. Veuillez vérifier manuellement."
        cd - > /dev/null # Revenir au répertoire précédent
        exit 1
    fi
    cd - > /dev/null # Revenir au répertoire précédent
else
    log INFO "Clonage du dépôt '$REPO_URL' dans '$INSTALL_DIR'..."
    if ! git clone "$REPO_URL" "$INSTALL_DIR"; then
        log ERROR "Échec du clonage du dépôt."
        exit 1
    fi
fi

# Aller dans le répertoire d'installation
cd "$INSTALL_DIR" || { log ERROR "Impossible d'accéder à $INSTALL_DIR après clonage/mise à jour."; exit 1; }

# Ajouter/Vérifier le Shebang
log INFO "Vérification/Ajout du shebang à $TARGET_SCRIPT..."
if ! grep -q "^#!/usr/bin/env $PYTHON_CMD" $TARGET_SCRIPT; then
  log INFO "Ajout du shebang #!/usr/bin/env $PYTHON_CMD"
  # Crée un fichier temporaire avec le shebang puis le contenu original
  echo "#!/usr/bin/env $PYTHON_CMD" | cat - $TARGET_SCRIPT > temp_script && mv temp_script $TARGET_SCRIPT
  if [[ $? -ne 0 ]]; then
      log ERROR "Échec de l'ajout du shebang."
      cd - > /dev/null
      exit 1
  fi
else
  log INFO "Shebang déjà présent."
fi

# Rendre le script exécutable
log INFO "Rendre $TARGET_SCRIPT exécutable..."
if ! chmod +x $TARGET_SCRIPT; then
    log ERROR "Échec de la modification des permissions pour $TARGET_SCRIPT."
    cd - > /dev/null
    exit 1
fi

# Installer les dépendances
log INFO "Installation des dépendances Python depuis requirements.txt..."
if ! $PIP_CMD install -r requirements.txt; then
    log ERROR "Échec de l'installation des dépendances Python."
    cd - > /dev/null
    exit 1
fi
log INFO "Dépendances installées avec succès."

# --- Configuration du lien symbolique --- 
log INFO "Configuration du lien symbolique dans $BIN_DIR..."

# Créer le répertoire bin s'il n'existe pas
mkdir -p "$BIN_DIR"

# Obtenir le chemin absolu du script cible
TARGET_SCRIPT_ABS_PATH="$(realpath $TARGET_SCRIPT)"
LINK_PATH="$BIN_DIR/$SCRIPT_NAME"

# Créer ou mettre à jour le lien symbolique
if ln -sf "$TARGET_SCRIPT_ABS_PATH" "$LINK_PATH"; then
    log INFO "Lien symbolique '$LINK_PATH' créé/mis à jour avec succès."
else
    log ERROR "Échec de la création du lien symbolique '$LINK_PATH'."
    log WARN "Vous devrez peut-être ajouter manuellement un lien ou ajouter '$INSTALL_DIR' à votre PATH."
    cd - > /dev/null
    exit 1 # Considérer comme une erreur bloquante pour la commande directe
fi

# Vérifier si BIN_DIR est dans le PATH (informatif)
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    log WARN "Le répertoire '$BIN_DIR' ne semble pas être dans votre PATH."
    log WARN "Ajoutez la ligne suivante à votre fichier de configuration shell (ex: ~/.bashrc, ~/.zshrc):"
    log WARN "  export PATH=\"$HOME/.local/bin:\$PATH\""
    log WARN "Puis rechargez votre configuration (ex: source ~/.bashrc) ou ouvrez un nouveau terminal."
fi

# Revenir au répertoire d'origine
cd - > /dev/null

log INFO "Installation de SmarTerm terminée avec succès!"
log INFO "Vous pouvez maintenant essayer d'exécuter la commande '$SCRIPT_NAME' dans un nouveau terminal." 