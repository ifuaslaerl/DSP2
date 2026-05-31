#include <MIDI.h>
#include "pitches.h"

#define NUM_MOTORS 6

const byte stepPins[NUM_MOTORS + 1] = {0, 3, 5, 7, 9, 11, 13};
const byte dirPins[NUM_MOTORS + 1]  = {0, 2, 4, 6, 8, 10, 12};

unsigned long motorPeriods[NUM_MOTORS + 1] = {0};
unsigned long prevStepMicros[NUM_MOTORS + 1] = {0};

const byte NO_NOTE = 255;
byte currentNote[NUM_MOTORS + 1];

const bool motorDirection = HIGH;
const unsigned int STEP_PULSE_US = 3;

MIDI_CREATE_INSTANCE(HardwareSerial, Serial, MIDI);

void setup() 
{
  for (byte i = 1; i <= NUM_MOTORS; i++) {
    pinMode(stepPins[i], OUTPUT);
    pinMode(dirPins[i], OUTPUT);

    digitalWrite(stepPins[i], LOW);
    digitalWrite(dirPins[i], motorDirection);

    currentNote[i] = NO_NOTE;
  }

  MIDI.setHandleNoteOn(handleNoteOn);
  MIDI.setHandleNoteOff(handleNoteOff);
  MIDI.begin(MIDI_CHANNEL_OMNI);
}

void loop() 
{
  MIDI.read();

  for (byte i = 1; i <= NUM_MOTORS; i++) {
    singleStep(i);
  }
}

void handleNoteOn(byte channel, byte note, byte velocity)
{
  if (channel < 1 || channel > NUM_MOTORS) return;

  // Muitos dispositivos MIDI mandam NoteOn com velocity 0 em vez de NoteOff.
  if (velocity == 0) {
    handleNoteOff(channel, note, velocity);
    return;
  }

  unsigned long period = pitchVals[note];

  // Nota fora da faixa configurada no pitches.h
  if (period == 0) {
    motorPeriods[channel] = 0;
    currentNote[channel] = NO_NOTE;
    return;
  }

  motorPeriods[channel] = period;
  currentNote[channel] = note;
  prevStepMicros[channel] = micros();
}

void handleNoteOff(byte channel, byte note, byte velocity)
{
  if (channel < 1 || channel > NUM_MOTORS) return;

  // Só desliga se o NoteOff corresponde à nota atualmente tocada.
  if (currentNote[channel] == note) {
    motorPeriods[channel] = 0;
    currentNote[channel] = NO_NOTE;
  }
}

void singleStep(byte motorNum)
{
  unsigned long period = motorPeriods[motorNum];
  if (period == 0) return;

  unsigned long now = micros();

  if ((unsigned long)(now - prevStepMicros[motorNum]) >= period) {
    prevStepMicros[motorNum] += period;

    digitalWrite(stepPins[motorNum], HIGH);
    delayMicroseconds(STEP_PULSE_US);
    digitalWrite(stepPins[motorNum], LOW);
  }
}