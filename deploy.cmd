:: @echo off
:: start "" /B cmd /c "call env\Scripts\activate.bat && python manage.py runserver > server.log 2>&1"

:: Step 1: Pull latest changes from Git
::git pull origin main >> server.log 2>&1


::echo.
::echo =======================================
::echo Pulled the latest code successfully!
::echo =======================================
::pause

:: Step 2: Start Django server in background
:: @echo off
@REM start "" /B cmd /c "call env\Scripts\activate.bat && python manage.py runserver 0.0.0.0:8100 > server.log 2>&1"

@REM echo.
@REM echo =======================================
@REM echo Running successfully!
@REM echo =======================================
@REM pause
python manage.py runserver 0.0.0.0:8111