@ECHO Off


ECHO/
rem ECHO Maya version? (ex. 2022)
rem set /p ver=
set version=2022
set mayapy="%programfiles%\Autodesk\Maya%version%\bin\mayapy.exe"


python -c "import test"
python tk_test.py

rem %mayapy% -c "import maya.standalone; maya.standalone.initialize(name='python')"


%mayapy% mayatk_test.py


PAUSE