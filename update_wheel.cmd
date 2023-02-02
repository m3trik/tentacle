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


python -c "from pythontk import File; File.incVersion('%dir%\%name%\__init__.py')"
echo %name% package version number incremented.


:: upload the package wheel to pipy
cd /d %dir%
:: 
python -m pip install --user --upgrade setuptools wheel
python setup.py sdist bdist_wheel
:: 
python -m pip install --user --upgrade twine
twine upload dist/* 


PAUSE