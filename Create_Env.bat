@echo off
REM create_env.bat - Create a Python virtual environment and install required packages.
REM Usage: create_env.bat [env_name]
REM If no env_name is provided, defaults to myEnv.
REM Installs: pip (upgrade), google, protobuf==3.17.3, PyQt5

SETLOCAL ENABLEDELAYEDEXPANSION

IF "%~1"=="" (
    SET "ENV_NAME=myEnv"
) ELSE (
    IF /I "%~1"=="-h" GOTO :help
    IF /I "%~1"=="--help" GOTO :help
    SET "ENV_NAME=%~1"
)

ECHO Creating / using environment: %ENV_NAME%

WHERE python >NUL 2>&1
IF ERRORLEVEL 1 (
    ECHO [ERROR] Python not found in PATH. Install Python and retry.
    EXIT /B 1
)

REM Create venv if it does not exist
IF NOT EXIST "%ENV_NAME%\Scripts\python.exe" (
    ECHO [INFO] Creating virtual environment...
    python -m venv "%ENV_NAME%"
    IF ERRORLEVEL 1 (
        ECHO [ERROR] Failed to create virtual environment.
        EXIT /B 1
    )
) ELSE (
    ECHO [INFO] Virtual environment already exists.
)

REM Activate environment
CALL "%ENV_NAME%\Scripts\activate.bat"
IF ERRORLEVEL 1 (
    ECHO [ERROR] Failed to activate virtual environment.
    EXIT /B 1
)

ECHO [INFO] Upgrading pip...
python -m pip install --upgrade pip
IF ERRORLEVEL 1 (
    ECHO [ERROR] Failed to upgrade pip.
    EXIT /B 1
)

ECHO [INFO] Installing required packages: google protobuf==3.17.3 PyQt5
pip install google protobuf==3.17.3 PyQt5
IF ERRORLEVEL 1 (
    ECHO [ERROR] Package installation failed.
    EXIT /B 1
)

ECHO [SUCCESS] Environment '%ENV_NAME%' ready.
ECHO To activate later (CMD): CALL "%ENV_NAME%\Scripts\activate.bat"
ECHO To activate in PowerShell: .\%ENV_NAME%\Scripts\Activate.ps1
GOTO :eof

:help
ECHO Usage: create_env.bat [env_name]
ECHO   env_name  Optional name of the virtual environment folder (default: myEnv)
ECHO Example: create_env.bat .venv
EXIT /B 0
