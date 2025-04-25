#Requires -Version 5.1

<#
.SYNOPSIS
    Installe l'application SmarTerm sur Windows.
.DESCRIPTION
    Ce script vérifie Python et Git, clone le dépôt SmarTerm,
    installe les dépendances Python et ajoute l'application au PATH utilisateur.
.NOTES
    Auteur: Gemini
    Assurez-vous d'exécuter ce script avec PowerShell.
    Vous devrez peut-être ajuster la politique d'exécution PowerShell :
    Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
#>

param(
    # URL du dépôt Git de SmarTerm
    [Parameter(Mandatory=$false)]
    [string]$RepositoryUrl = "https://github.com/calebreseau/smarterm",

    # Répertoire d'installation (par défaut: $HOME\smarterm)
    [Parameter(Mandatory=$false)]
    [string]$InstallDir = "$env:USERPROFILE\smarterm"
)

# Fonction pour afficher les messages
function Write-Log {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Message,
        [Parameter(Mandatory=$false)]
        [ValidateSet('INFO', 'WARN', 'ERROR')]
        [string]$Level = 'INFO'
    )
    $Color = switch ($Level) {
        'INFO'  { 'Green' }
        'WARN'  { 'Yellow' }
        'ERROR' { 'Red' }
        default { 'White' }
    }
    Write-Host "[$Level] $Message" -ForegroundColor $Color
}

# --- Vérifications Préliminaires ---
Write-Log "Démarrage de l'installation de SmarTerm..."

# Vérifier Python
Write-Log "Vérification de l'installation de Python..."
$pythonExists = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonExists) {
    Write-Log "Python n'a pas été trouvé. Veuillez l'installer depuis python.org et assurez-vous qu'il est dans le PATH." -Level ERROR
    Write-Log "Assurez-vous de cocher 'Add Python to PATH' lors de l'installation." -Level ERROR
    exit 1
}
Write-Log "Python trouvé: $($pythonExists.Source)"

# Vérifier Pip (généralement inclus avec Python)
Write-Log "Vérification de Pip..."
$pipExists = Get-Command pip -ErrorAction SilentlyContinue
if (-not $pipExists) {
    Write-Log "Pip n'a pas été trouvé. Essayez de réinstaller Python ou exécutez: python -m ensurepip --upgrade" -Level ERROR
    exit 1
}
Write-Log "Pip trouvé."

# Vérifier Git
Write-Log "Vérification de Git..."
$gitExists = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitExists) {
    Write-Log "Git n'a pas été trouvé. Veuillez l'installer depuis git-scm.com." -Level ERROR
    exit 1
}
Write-Log "Git trouvé."

# --- Installation ---

# Vérifier si le répertoire d'installation existe déjà
if (Test-Path $InstallDir) {
    Write-Log "Le répertoire d'installation '$InstallDir' existe déjà. Tentative de mise à jour." -Level WARN
    Push-Location $InstallDir
    Write-Log "Mise à jour du dépôt via 'git pull'..."
    git pull
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Échec de la mise à jour du dépôt. Veuillez vérifier manuellement." -Level ERROR
        Pop-Location
        exit 1
    }
    Pop-Location
} else {
    Write-Log "Clonage du dépôt '$RepositoryUrl' dans '$InstallDir'..."
    git clone $RepositoryUrl $InstallDir
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Échec du clonage du dépôt." -Level ERROR
        exit 1
    }
}

# Aller dans le répertoire d'installation
Push-Location $InstallDir

# Installer les dépendances
Write-Log "Installation des dépendances Python depuis requirements.txt..."
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Log "Échec de l'installation des dépendances Python." -Level ERROR
    Pop-Location
    exit 1
}
Write-Log "Dépendances installées avec succès."

# --- Configuration du PATH --- 
Write-Log "Ajout de '$InstallDir' au PATH utilisateur..."

try {
    $CurrentUserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $PathItems = $CurrentUserPath -split ';'

    if ($PathItems -contains $InstallDir) {
        Write-Log "Le répertoire '$InstallDir' est déjà dans le PATH utilisateur." -Level INFO
    } else {
        # Ajouter le répertoire et nettoyer les éventuels points-virgules doubles
        $NewPath = "$CurrentUserPath;$InstallDir" -replace ';+', ';'
        [Environment]::SetEnvironmentVariable("Path", $NewPath.Trim(';'), "User")
        Write-Log "'$InstallDir' ajouté au PATH utilisateur avec succès." -Level INFO
        Write-Log "Vous devrez peut-être redémarrer votre terminal ou votre session pour que le changement prenne effet." -Level WARN
    }
} catch {
    Write-Log "Erreur lors de la modification du PATH utilisateur: $($_.Exception.Message)" -Level ERROR
    Write-Log "Vous devrez ajouter '$InstallDir' manuellement à votre PATH." -Level WARN
}

# Revenir au répertoire d'origine
Pop-Location

Write-Log "Installation de SmarTerm terminée avec succès!"
Write-Log "Vous pouvez maintenant essayer d'exécuter la commande 'smarterm' dans un nouveau terminal." 