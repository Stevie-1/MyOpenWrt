# traffic-monitor Makefile (host build for WSL2 / Ubuntu development)
# Phase 2 will populate src/*.c. For now this Makefile is wired up so
# `make` from an empty src/ fails fast with a clear message rather than
# silently producing nothing.

CC      ?= gcc
CFLAGS  := -Wall -Wextra -O2 -std=c11 -pthread -Iinclude
LDFLAGS := -lpcap -lpthread

SRC_DIR := src
INC_DIR := include
BIN_DIR := bin
TARGET  := $(BIN_DIR)/traffic_monitor

SRCS := $(wildcard $(SRC_DIR)/*.c)
OBJS := $(SRCS:.c=.o)

.PHONY: all clean check-sources

all: check-sources $(TARGET)

check-sources:
	@if [ -z "$(SRCS)" ]; then \
		echo "[ERROR] no .c files under $(SRC_DIR)/ yet."; \
		echo "        Phase 2 implementation pending. See README.md for plan."; \
		exit 1; \
	fi

$(TARGET): $(OBJS) | $(BIN_DIR)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f $(SRC_DIR)/*.o
	rm -rf $(BIN_DIR)
