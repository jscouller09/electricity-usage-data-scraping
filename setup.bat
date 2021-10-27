@echo OFF&setlocal

rem set anaconda install location
set root=C:\Anaconda3
echo Anaconda location: %root%

rem set local working directory
set script_dir=%~dp0
echo Script location: %script_dir%

rem get parent directory, assume github repo
for %%i in ("%~dp0..") do set "parent_folder=%%~fi"
echo GitHub repo path: %parent_folder%

rem assume conda environment name is same as github repo, get from parent folder
set env_name=%parent_folder%
:GetFolder
set GetFolderTemp=%env_name:*\=%
If Not %GetFolderTemp%==%env_name% (
    set env_name=%GetFolderTemp%
    Goto :GetFolder
)
echo Environment name: %env_name%

rem activate conda
echo Activating conda...
call %root%\Scripts\activate.bat %root%

rem create/update the conda environment if it doesn't exist
echo Creating %env_name% conda environment...
call conda env create -f environment.yml
echo Updating %env_name% conda environment...
call conda env update -f environment.yml

rem activate right conda environment
echo Activating %env_name% conda environment...
call conda activate %env_name%

rem rem install/activate extenstions
rem echo Adding extensions to jupyter notebook...
rem call jupyter contrib nbextension install
rem rem call jupyter nbextension install hide_code --py --sys-prefix
rem rem call jupyter nbextension enable hide_code --py 
rem rem call jupyter serverextension enable hide_code --py 
rem call jupyter nbextension install ipympl --py --symlink --sys-prefix 
rem call jupyter nbextension enable ipympl --py --sys-prefix 
rem rem call jupyter nbextension enable init_cell
rem call jupyter nbextension enable autoscroll/main

rem rem set location of autoscroll extension, assuing conda env is same as repo name
rem set autoscroll_config_dir=%root%\envs\%env_name%\Lib\site-packages\jupyter_contrib_nbextensions\nbextensions\autoscroll

rem echo Copying new autoscroll config to:
rem echo %autoscroll_config_dir%
rem copy %script_dir%\autoscroll.yaml %autoscroll_config_dir%\autoscroll.yaml
rem echo Copying done!

ECHO Setup complete!
pause