py -m PyInstaller --onefile --windowed ^
	--icon=soundifier.ico ^
	--additional-hooks-dir=. ^
	--add-data "soundifier.ico:." ^
	--add-data "assets:assets" ^
	gui.py
pause