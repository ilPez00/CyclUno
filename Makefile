# CyclUno firmware — two builds from one tree (see platformio.ini)
#   cycluno : the deck — SPI TFT + framed v2 protocol, this is what aion talks to
#   mouse   : standalone HID mouse + MPU6050, no display, ASCII line protocol
#
# Host gate (no toolchain needed, runs anywhere with g++):
#   make test          -> HUD logic + joystick nav + deck tests + wire contract
#
# Real builds (need PlatformIO: `pip install platformio`):
#   make build         -> pio run -e cycluno
#   make flash         -> pio run -e cycluno -t upload
#   make monitor       -> pio run -e cycluno -t monitor
#   make mouse         -> flash the mouse firmware instead
#   make diag          -> flash + monitor the wiring diagnostic

CXX      ?= g++
CXXFLAGS ?= -std=c++17 -Wall -Wextra
INC      := -I include
OUT      := /tmp/cycluno_tests

# Where the upstream copy of the shared header lives, when the cyclops repo is
# checked out next to this one. Override: make proto-sync CYCLOPS=/path/to/repo
CYCLOPS ?= $(abspath ..)/cyclops
UPSTREAM_HDR := $(CYCLOPS)/firmware/lib/cyclops_shared/include/cyclops_shared.h

.PHONY: test contract proto-sync build flash monitor mouse diag test-mpu clean pio-check

test: contract proto-sync
	@mkdir -p $(OUT)
	$(CXX) $(CXXFLAGS) $(INC) test/test_cycluno.cpp -o $(OUT)/test_cycluno
	$(OUT)/test_cycluno
	$(CXX) $(CXXFLAGS) $(INC) test/test_joynav.cpp -o $(OUT)/test_joynav
	$(OUT)/test_joynav
	$(CXX) $(CXXFLAGS) $(INC) test/test_deck.cpp -o $(OUT)/test_deck
	$(OUT)/test_deck

# The library tests above gate include/*.h, which are Arduino-free. src/main.cpp
# is not host-compilable, so nothing gated it — and that is exactly where the
# deck once got replaced by an ASCII-protocol mouse sketch, silently killing
# aion's DeckLink (its decoder only ever sees 0xAA 0x55 frames). Textual gate:
# cheap, and it catches that specific regression.
contract:
	@for sym in cyclops_shared.h deck.h encode_frame MSG_INPUT_EVENT pack_input_event; do \
	  grep -q "$$sym" src/main.cpp || { \
	    echo "FAIL wire contract: src/main.cpp no longer references '$$sym'."; \
	    echo "  The cycluno env must speak the framed v2 protocol that"; \
	    echo "  aion/src/aion/deck/protocol.py is pinned to. Non-deck"; \
	    echo "  firmwares belong in their own src/<name>.cpp + [env:<name>]."; \
	    exit 1; }; \
	done
	@echo "OK: src/main.cpp still speaks the framed deck protocol"

# include/cyclops_shared.h is VENDORED from the cyclops repo. Identical today
# is not a contract: if the two drift, this firmware and the brain disagree
# about the wire and nothing else notices. Skipped (not failed) when the
# cyclops checkout is not next door, so the gate still runs standalone.
proto-sync:
	@if [ -f "$(UPSTREAM_HDR)" ]; then \
	  if diff -q include/cyclops_shared.h "$(UPSTREAM_HDR)" >/dev/null; then \
	    echo "OK: cyclops_shared.h matches $(CYCLOPS)"; \
	  else \
	    echo "FAIL: include/cyclops_shared.h has drifted from the cyclops repo."; \
	    diff -u include/cyclops_shared.h "$(UPSTREAM_HDR)" | head -40; \
	    exit 1; \
	  fi; \
	else \
	  echo "skip: no cyclops checkout at $(CYCLOPS) (set CYCLOPS=... to gate)"; \
	fi

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

mouse: pio-check
	pio run -e mouse -t upload && pio run -e mouse -t monitor

diag: pio-check
	pio run -e diag -t upload && pio run -e diag -t monitor

test-mpu: pio-check
	pio run -e test_mpu -t upload && pio run -e test_mpu -t monitor

clean:
	rm -rf $(OUT) .pio
