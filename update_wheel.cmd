@ECHO OFF
ECHO Must be run with elevated privileges if previous build directories are to be deleted.
ECHO/

:: Admin check
fltmc >nul 2>nul || set _=^"set _ELEV=1^& cd /d """%cd%"""^& "%~f0" %* ^"&&((if "%_ELEV%"=="" ((powershell -nop -c start cmd -args '/d/x/s/v:off/r',$env:_ -verb runas >nul 2>nul) || (mshta vbscript:execute^("createobject(""shell.application"").shellexecute(""cmd"",""/d/x/s/v:off/r ""&createobject(""WScript.Shell"").Environment(""PROCESS"")(""_""),,""runas"",1)(window.close)"^) >nul 2>nul)))& exit /b)


::wheel directory
set "name=tentacle"
::
set "dir=%CLOUD%\Code\_scripts\%name%"

::delete previous build directories:
rem ECHO %cd%
echo Attempting to remove "%dir%/build" ..
rmdir /s /q "%dir%/build"
echo Attempting to remove "%dir%/dist" ..
rmdir /s /q "%dir%/dist"
ECHO/

:: Get and update the version number
for /f "delims=" %%i in ('python -c "from pythontk import File; ver = File.updateVersion(r'%dir%/%name%/__init__.py'); print(ver)"') do set ver=%%i
echo %name% package version number incremented to %ver%.

:: upload the package wheel to pipy
cd /d %dir%
:: 
python -m pip install --user --upgrade setuptools wheel
python setup.py sdist bdist_wheel
:: 
python -m pip install --user --upgrade twine

:: Set your PyPI username and password (use an API token as the password)
set /p TWINE_USERNAME=Enter your username:
set /p TWINE_PASSWORD=Enter your password:

:: Attempt to upload using twine and check for errors
twine upload --username %TWINE_USERNAME% --password %TWINE_PASSWORD% dist/* 2> upload_errors.txt
if %errorlevel% neq 0 (
    echo Twine upload failed. Reverting the version number.
    python -c "from pythontk import File; ver = File.updateVersion(r'%dir%/%name%/__init__.py', 'decrement')"
) else (
    echo Twine upload successful.
)

:: Remove temporary file
del upload_errors.txt


PAUSE