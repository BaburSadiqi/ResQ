import assert from "node:assert/strict";
import test from "node:test";
import { shouldTriggerSimulationAlarm } from "../src/alarmTiming.js";

test("simulation alarm waits until the playing clock reaches alert issuance", () => {
  assert.equal(shouldTriggerSimulationAlarm(true, true, false, 0, 22.3), false);
  assert.equal(shouldTriggerSimulationAlarm(true, true, false, 22.2, 22.3), false);
  assert.equal(shouldTriggerSimulationAlarm(true, true, false, 22.3, 22.3), true);
  assert.equal(shouldTriggerSimulationAlarm(true, true, false, 22.4, 22.3), true);
});

test("simulation alarm does not start before a result or outside playback", () => {
  assert.equal(shouldTriggerSimulationAlarm(false, true, false, 30, 22.3), false);
  assert.equal(shouldTriggerSimulationAlarm(true, false, false, 30, 22.3), false);
  assert.equal(shouldTriggerSimulationAlarm(true, true, true, 30, 22.3), false);
});