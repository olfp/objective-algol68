PYTHON ?= python3
GA68 ?= ga68
GA68FLAGS ?= -std=gnu68 -fstropping=upper

COLLECTION ?= collection
SHAPES ?= shapes

COLLECTION_U68 := collection.u68
COLLECTION_O68 := $(COLLECTION_U68:.u68=.o68)
COLLECTION_A68 := $(COLLECTION_O68:.o68=.a68)
COLLECTION_OBJ := $(COLLECTION_A68:.a68=.o)

SHAPES_U68 := shapemod.o68 main.u68
SHAPES_O68 := $(SHAPES_O68:.u68=.o68)
SHAPES_A68 := $(SHAPES_O68:.o68=.a68)
SHAPES_OBJ := $(SHAPES_A68:.a68=.o)

.PHONY: all test run clean

all: $(COLLECTION) $(SHAPES)

%.o68: %.u68 u682a68
	$(PYTHON) u682a68 <"$<" >"$@"

%.a68: %.o68 o2a.py
	$(PYTHON) o2a.py "$<" --output "$@"

%.o: %.a68
	$(GA68) $(GA68FLAGS) -c -o "$@" "$<"

$(COLLECTION): $(COLLECTION_OBJ)
	$(GA68) $(GA68FLAGS) -o "$@" $(COLLECTION_OBJ)

$(SHAPES): $(SHAPES_OBJ)
	$(GA68) $(GA68FLAGS) -o "$@" $(SHAPES_OBJ)

test: $(COLLECTION) $(SHAPES)
	./$(COLLECTION)
	./$(SHAPES)

run: $(COLLECTION) $(SHAPES)
	./$(COLLECTION)
	./$(SHAPES)

clean:
	rm -f $(COLLECTION_A68) $(COLLECTION_O68) $(COLLECTION_OBJ) $(SHAPES_A68) $(SHAPES_O68) $(SHAPES_OBJ) $(COLLECTION) $(SHAPES)
