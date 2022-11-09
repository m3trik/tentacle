@ECHO OFF
ECHO Must be run with elevated privileges if previous build directories are to be deleted.
ECHO/


::delete previous build directories:
set "dir=%CLOUD%\Code\_scripts\tentacle"
rem ECHO %cd%
echo Attempting to remove "%dir%/build" ..
rmdir /s /q "%dir%/build"
echo Attempting to remove "%dir%/dist" ..
rmdir /s /q "%dir%/dist"
ECHO/


:: upload the package wheel to pipy
cd /d %dir%
:: 
python -m pip install --user --upgrade setuptools wheel
python setup.py sdist bdist_wheel
:: 
python -m pip install --user --upgrade twine
twine upload dist/* 


PAUSE