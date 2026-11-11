export function loadStatusLabel(load: {
  released: boolean
  completed: boolean
  issueResolved: boolean
}) {
  return load.released
    ? 'Released'
    : load.completed
      ? 'Ready for release'
      : !load.issueResolved
        ? 'Held'
        : 'Awaiting loading'
}
