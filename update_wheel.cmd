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


:: update needed packages
python -m pip install --user --upgrade setuptools wheel


:: Make sure you are in the same directory as your setup.py file.
cd /d %dir%


:: create a dist/ folder in your main directory with the compressed files for your package.
python -m pip install --user --upgrade setuptools wheel
python setup.py sdist bdist_wheel


:: Check that you have twine installed.
python -m pip install --user --upgrade twine
:: Twine manages the file upload to PyPi.
twine upload dist/* 


PAUSE