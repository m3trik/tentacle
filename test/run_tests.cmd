@ECHO Off


ECHO/
rem ECHO Maya version? (ex. 2022)
rem set /p ver=
set version=2022
set mayapy="%programfiles%\Autodesk\Maya%version%\bin\mayapy.exe"


rem python -c "import test"
rem python tk_test.py

rem %mayapy% -c "import maya.standalone; maya.standalone.initialize(name='python')"


rem %mayapy% mayatk_test.py
rem %mayapy% edittk_test.py
rem %mayapy% comptk_test.py
rem %mayapy% rigtk_test.py
%mayapy% xformtk_test.py


PAUSE