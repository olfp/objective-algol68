PYTHON ?= python3
GA68 ?= ga68
GA68FLAGS ?= -std=gnu68 -fstropping=upper
PROGRAM ?= objective-algol68

O68_SOURCES := $(wildcard *.o68)
A68_SOURCES := $(O68_SOURCES:.o68=.a68)
A68_OBJECTS := $(A68_SOURCES:.a68=.o)

.PHONY: all test run clean

all: test

%.a68: %.o68 o2a.py
	$(PYTHON) o2a.py "$<" --output "$@"

%.o: %.a68
	$(GA68) $(GA68FLAGS) -c -o "$@" "$<"

$(PROGRAM): $(A68_OBJECTS)
	$(GA68) $(GA68FLAGS) -o "$@" $(A68_OBJECTS)

test: $(PROGRAM)
	./$(PROGRAM)

run: $(PROGRAM)
	./$(PROGRAM)

clean:
	rm -f $(A68_SOURCES) $(A68_OBJECTS) $(PROGRAM)
