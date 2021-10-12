@ECHO off

:: This command will install the package to your system. 
:: the package will then be found on Python’s import path, meaning you can use it anywhere without having to worry about the script directory, relative imports, or other complications. 

:: Now that structure is installed on your system, you can use the following import statement:
:: from tentacle import x
:: This will work no matter how you end up calling your application.

:: set the python version on your system that you want to install the package to.
set "_PYTHON=python.exe"
rem set "_PYTHON=C:\Program Files\Autodesk\3ds Max 2020\3dsmaxpy.exe"
rem set "_PYTHON=C:\Program Files\Autodesk\Maya2020\bin\mayapy.exe"

:: set the path to the directory containing setup.cfg, setup.py, and the package to be installed (tentacle folder).
set "_PACKAGE=."
rem set "_PACKAGE=O:\Cloud\Code\_scripts"

:: update setuptools:
:: pip install -U pip setuptools

:: The -e option stands for editable, which is important because it allows you to change the source code of your package without reinstalling it.
%_PYTHON% -m pip install -e %_PACKAGE%

PAUSE