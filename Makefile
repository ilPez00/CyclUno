# CyclUno firmware — build / flash / test
#
# Host gate (no toolchain needed, runs anywhere with g++):
#   make test          -> HUD logic + joystick nav tests
#
# Real builds (need PlatformIO: `pip install platformio`):
#   make build         -> pio run -e cycluno   (compile gate)
#   make flash         -> pio run -e cycluno -t upload
#   make monitor       -> pio run -e cycluno -t monitor

CXX      ?= g++
CXXFLAGS ?= -std=c++17 -Wall -Wextra
INC      := -I include
OUT      := /tmp/cycluno_tests

.PHONY: test build flash monitor clean pio-check

test:
	@mkdir -p $(OUT)
	$(CXX) $(CXXFLAGS) $(INC) test/test_cycluno.cpp -o $(OUT)/test_cycluno
	$(OUT)/test_cycluno
	$(CXX) $(CXXFLAGS) $(INC) test/test_joynav.cpp -o $(OUT)/test_joynav
	$(OUT)/test_joynav

pio-check:
	@command -v pio >/dev/null 2>&1 || { \
	  echo "PlatformIO not found. Install: pip install platformio"; \
	  exit 1; }

build: pio-check
	pio run -e cycluno

flash: pio-check
	pio run -e cycluno -t upload

monitor: pio-check
	pio run -e cycluno -t monitor

clean:
	rm -rf $(OUT) .pio
