# copied from pylint, could
all:
	ruff check --exit-zero --output-format=json files/simple.py | sed "s#$(PWD)/##" > simple.json
