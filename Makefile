PYTHON ?= python3
GA68 ?= ga68
GA68FLAGS ?= --gnu --upper-stropping
PROGRAM ?= objective-algol68

O68_SOURCES := $(wildcard *.o68)
A68_SOURCES := $(O68_SOURCES:.o68=.a68)

.PHONY: all test run clean

all: test

%.a68: %.o68 o2a.py
	$(PYTHON) o2a.py "$<" --output "$@"

$(PROGRAM): $(A68_SOURCES)
	$(GA68) $(GA68FLAGS) -o "$@" $(A68_SOURCES)

test: $(PROGRAM)
	./$(PROGRAM)

run: $(PROGRAM)
	./$(PROGRAM)

clean:
	rm -f $(A68_SOURCES) $(PROGRAM)
