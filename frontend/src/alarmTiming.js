export function shouldTriggerSimulationAlarm(
  playing,
  hasResult,
  alreadyTriggered,
  simulationTime,
  alertIssuanceSeconds,
) {
  return playing && hasResult && !alreadyTriggered && simulationTime >= alertIssuanceSeconds;
}