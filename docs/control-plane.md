# Control Plane

The control plane is an operator-facing surface for the agent runtime. It is intentionally separate from the model and execution workers.

## Initial surface
- Run inventory and execution state
- Live execution/event stream
- Pending human approvals
- Token and latency summary
- Worker/API/database/Redis health
- Navigation for agents, tools, memory, evaluations

## Security boundary
The UI is not an authorization source. Every approval, tool action, and tenant-scoped read must be authorized by the API policy layer. UI state is advisory and can never grant a model permission.

## Next integration
Replace the initial static dashboard data with authenticated API queries and WebSocket event streaming. Add run detail views, approval review/decision workflows, audit history, agent/version management, memory inspection, and evaluation dashboards.