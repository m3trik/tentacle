@ECHO Off


ECHO/
ECHO Maya version? (ex. 2022)
rem set /p maya_version=
set maya_version=2022
set mayapy="C:\Program Files\Autodesk\Maya%maya_version%\bin\mayapy.exe"


rem python -c "import tentacle"
python utils_test.py

%mayapy% utils_maya_test.py


PAUSE