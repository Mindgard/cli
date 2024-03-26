python3 release.py
python3 -m build
python3 -m twine upload --repository testpypi dist/* 