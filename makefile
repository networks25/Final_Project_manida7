install:
	python3 -m pip install --user requests beautifulsoup4 pillow

run:
	python3 gocomics_viewer.py

clean:
	rm -rf __pycache__ downloaded_comics

