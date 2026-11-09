export function shouldTriggerSimulationAlarm(
  playing: boolean,
  hasResult: boolean,
  alreadyTriggered: boolean,
  simulationTime: number,
  alertIssuanceSeconds: number,
): boolean;