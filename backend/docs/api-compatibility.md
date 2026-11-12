# API compatibility and ownership

All original 59 HTTP operations remain available under the same URLs. Nginx provides local path routing; AWS API Gateway/ALB provide deployed routing. No custom Python gateway was added. The frozen original OpenAPI and current service contracts are in `backend/packages/contracts/openapi/`. Each named body/response schema is fully expanded there.

The migration intentionally hardens resource authorization, malformed inputs, replay conflicts, upload privacy/limits, closed-run edits, and unresolved loading shortfalls. These can return 401/403/409/413/415/422 where the previous backend accepted unsafe state. Proof retrieval now needs authentication; the frontend transport adds a bearer token only for the configured API origin. Driver delays use the nonterminal DELAY outcome. Offline events preserve the exact original payload and acknowledgement retries.

Driver compatibility additions include STARTED for safely queued offline departure,
GET `/api/v1/driver/sync` for actor/device recovery pages and GET `/api/v1/driver/history`
for the scoped audit timeline. The original POST sync response remains a list. The HTTP
adapter caches each authenticated driver's mapped route and overlays its own queued actions.
Store-manager handoffs use per-order receipt commands, preserving the driver-only POD boundary.
Existing local records lacking an actor ID are retained but require explicit ownership
reconciliation before replay by an authenticated user; they are not silently attributed to a
new login. Signed manager evidence remains on the device, while receipt quantities and notes
are committed to the backend. Driver POD photos/signatures use private object storage.

| Owner | Method | URL | Query/path inputs | Body | Success response | Role gate |
|---|---|---|---|---|---|---|
| identity-access | POST | `/api/v1/auth/login` | none | `{'$ref': '#/components/schemas/LoginRequest'}` | `200: {'$ref': '#/components/schemas/TokenResponse'}` | public probe/login |
| identity-access | GET | `/api/v1/auth/me` | none | `none` | `200: {'$ref': '#/components/schemas/UserProfile'}` | authenticated |
| identity-access | PATCH | `/api/v1/auth/me` | none | `{'$ref': '#/components/schemas/ContactUpdate'}` | `200: {'$ref': '#/components/schemas/UserProfile'}` | authenticated |
| identity-access | GET | `/api/v1/admin/users` | none | `none` | `200: {'items': {'$ref': '#/components/schemas/AdminUserOut'}, 'type': 'array', 'title': 'Response List Users Api V1 Admin Users Get'}` | ADMIN |
| identity-access | POST | `/api/v1/admin/users` | none | `{'$ref': '#/components/schemas/AdminUserCreate'}` | `201: {'$ref': '#/components/schemas/AdminUserOut'}` | ADMIN |
| identity-access | PATCH | `/api/v1/admin/users/{user_id}` | user_id (required) | `{'$ref': '#/components/schemas/AdminUserUpdate'}` | `200: {'$ref': '#/components/schemas/AdminUserOut'}` | ADMIN |
| identity-access | POST | `/api/v1/admin/users/{user_id}/reassign-trip` | user_id (required) | `{'$ref': '#/components/schemas/TripReassign'}` | `204: {}` | ADMIN |
| identity-access | POST | `/api/v1/admin/users/{user_id}/reset-password` | user_id (required) | `{'$ref': '#/components/schemas/PasswordReset'}` | `204: {}` | ADMIN |
| identity-access | GET | `/api/v1/reference/store-managers` | none | `none` | `200: {'items': {'$ref': '#/components/schemas/ManagerContact'}, 'type': 'array', 'title': 'Response List Store Managers Api V1 Reference Store Managers Get'}` | DISPATCHER, DRIVER, LOADER |
| identity-access | GET | `/health/live` | none | `none` | `200: {'$ref': '#/components/schemas/LiveHealth'}` | public probe/login |
| identity-access | GET | `/health/ready` | none | `none` | `200: {'$ref': '#/components/schemas/ReadyHealth'}` | public probe/login |
| network-fleet | GET | `/api/v1/reference/depots` | none | `none` | `200: {'items': {'$ref': '#/components/schemas/DepotOut'}, 'type': 'array', 'title': 'Response List Depots Api V1 Reference Depots Get'}` | authenticated |
| network-fleet | GET | `/api/v1/reference/outlets` | depot, brand, district | `none` | `200: {'type': 'array', 'items': {'$ref': '#/components/schemas/OutletOut'}, 'title': 'Response List Outlets Api V1 Reference Outlets Get'}` | authenticated |
| network-fleet | GET | `/api/v1/reference/outlets/{outlet_id}` | outlet_id (required) | `none` | `200: {'$ref': '#/components/schemas/OutletOut'}` | authenticated |
| network-fleet | GET | `/api/v1/reference/vehicles` | depot, type, refrigerated | `none` | `200: {'type': 'array', 'items': {'$ref': '#/components/schemas/VehicleOut'}, 'title': 'Response List Vehicles Api V1 Reference Vehicles Get'}` | authenticated |
| network-fleet | GET | `/api/v1/reference/vehicles/{vehicle_id}` | vehicle_id (required) | `none` | `200: {'$ref': '#/components/schemas/VehicleOut'}` | authenticated |
| network-fleet | GET | `/api/v1/reference/calendar` | from, to, operating_only | `none` | `200: {'type': 'array', 'items': {'$ref': '#/components/schemas/CalendarDayOut'}, 'title': 'Response List Calendar Api V1 Reference Calendar Get'}` | authenticated |
| network-fleet | PATCH | `/api/v1/reference/vehicles/{vehicle_id}/availability` | vehicle_id (required) | `{'$ref': '#/components/schemas/VehicleAvailability'}` | `200: {'$ref': '#/components/schemas/VehicleOut'}` | ADMIN, DISPATCHER |
| network-fleet | POST | `/api/v1/admin/outlets` | none | `{'$ref': '#/components/schemas/OutletCreate'}` | `201: {'$ref': '#/components/schemas/OutletOut'}` | ADMIN |
| network-fleet | POST | `/api/v1/admin/vehicles` | none | `{'$ref': '#/components/schemas/VehicleCreate'}` | `201: {'$ref': '#/components/schemas/VehicleOut'}` | ADMIN |
| network-fleet | GET | `/health/live` | none | `none` | `200: {'$ref': '#/components/schemas/LiveHealth'}` | public probe/login |
| network-fleet | GET | `/health/ready` | none | `none` | `200: {'$ref': '#/components/schemas/ReadyHealth'}` | public probe/login |
| operations | GET | `/health/live` | none | `none` | `200: {'$ref': '#/components/schemas/LiveHealth'}` | public probe/login |
| operations | GET | `/health` | none | `none` | `200: {'$ref': '#/components/schemas/LiveHealth'}` | public probe/login |
| operations | GET | `/health/ready` | none | `none` | `200: {'$ref': '#/components/schemas/ReadyHealth'}` | public probe/login |
| operations | GET | `/health/db` | none | `none` | `200: {'$ref': '#/components/schemas/ReadyHealth'}` | public probe/login |
| operations | POST | `/api/v1/orders` | none | `{'$ref': '#/components/schemas/OrderCreate'}` | `201: {'$ref': '#/components/schemas/OrderOut'}` | DISPATCHER, STORE_MANAGER |
| operations | GET | `/api/v1/orders/stops` | outlet_id, date | `none` | `200: {'type': 'array', 'items': {'$ref': '#/components/schemas/StopOut'}, 'title': 'Response List Order Stops Api V1 Orders Stops Get'}` | authenticated |
| operations | GET | `/api/v1/orders/intake-status` | none | `none` | `200: {'$ref': '#/components/schemas/IntakeStatus'}` | authenticated |
| operations | POST | `/api/v1/orders/close` | date | `none` | `200: {'$ref': '#/components/schemas/ClosureResult'}` | DISPATCHER |
| operations | GET | `/api/v1/orders` | date, status, outlet_id, limit, offset | `none` | `200: {'type': 'array', 'items': {'$ref': '#/components/schemas/OrderOut'}, 'title': 'Response List Orders Api V1 Orders Get'}` | authenticated |
| operations | GET | `/api/v1/orders/{order_id}` | order_id (required) | `none` | `200: {'$ref': '#/components/schemas/OrderOut'}` | authenticated |
| operations | PATCH | `/api/v1/orders/{order_id}` | order_id (required) | `{'$ref': '#/components/schemas/OrderUpdate'}` | `200: {'$ref': '#/components/schemas/OrderOut'}` | DISPATCHER, STORE_MANAGER |
| operations | POST | `/api/v1/orders/{order_id}/cancel` | order_id (required) | `none` | `200: {'$ref': '#/components/schemas/OrderOut'}` | DISPATCHER, STORE_MANAGER |
| operations | POST | `/api/v1/orders/{order_id}/confirm` | order_id (required) | `none` | `200: {'$ref': '#/components/schemas/StatusResult'}` | DISPATCHER |
| operations | POST | `/api/v1/orders/{order_id}/receipt` | order_id (required) | `{'$ref': '#/components/schemas/ReceiptCreate'}` | `201: {'$ref': '#/components/schemas/ReceiptResult'}` | STORE_MANAGER |
| operations | POST | `/api/v1/orders/{order_id}/issues` | order_id (required) | `{'$ref': '#/components/schemas/IssueCreate'}` | `201: {'$ref': '#/components/schemas/OkResult'}` | STORE_MANAGER |
| operations | GET | `/api/v1/plans` | date, status | `none` | `200: {'type': 'array', 'items': {'$ref': '#/components/schemas/PlanOut'}, 'title': 'Response List Plans Api V1 Plans Get'}` | DISPATCHER |
| operations | GET | `/api/v1/plans/{plan_id}` | plan_id (required) | `none` | `200: {'$ref': '#/components/schemas/PlanOut'}` | DISPATCHER |
| operations | POST | `/api/v1/plans/auto-plan` | date | `none` | `201: {'$ref': '#/components/schemas/PlanOut'}` | DISPATCHER |
| operations | POST | `/api/v1/plans/{plan_id}/validate` | plan_id (required) | `none` | `200: {'$ref': '#/components/schemas/PlanValidation'}` | DISPATCHER |
| operations | PATCH | `/api/v1/plans/{plan_id}` | plan_id (required) | `{'$ref': '#/components/schemas/PlanEdit'}` | `200: {'$ref': '#/components/schemas/PlanOut'}` | DISPATCHER |
| operations | POST | `/api/v1/plans/{plan_id}/publish` | plan_id (required) | `none` | `200: {'$ref': '#/components/schemas/PublishResult'}` | DISPATCHER |
| operations | POST | `/api/v1/deferrals` | none | `{'$ref': '#/components/schemas/DeferralCreate'}` | `201: {'$ref': '#/components/schemas/DeferralOut'}` | DISPATCHER |
| operations | GET | `/api/v1/deferrals` | date | `none` | `200: {'type': 'array', 'items': {'$ref': '#/components/schemas/DeferralOut'}, 'title': 'Response List Deferrals Api V1 Deferrals Get'}` | DISPATCHER |
| operations | GET | `/api/v1/deferrals/outlets/{outlet_id}/history` | outlet_id (required) | `none` | `200: {'type': 'array', 'items': {'$ref': '#/components/schemas/DeferralHistoryOut'}, 'title': 'Response Outlet Deferral History Api V1 Deferrals Outlets  Outlet Id  History Get'}` | DISPATCHER |
| operations | GET | `/api/v1/loading/trips` | date, depot | `none` | `200: {'type': 'array', 'items': {'$ref': '#/components/schemas/TripOut'}, 'title': 'Response List Loading Trips Api V1 Loading Trips Get'}` | DISPATCHER, DRIVER, LOADER |
| operations | GET | `/api/v1/loading/trips/{trip_id}` | trip_id (required) | `none` | `200: {'$ref': '#/components/schemas/TripOut'}` | DISPATCHER, DRIVER, LOADER |
| operations | POST | `/api/v1/loading/trips/{trip_id}/flags` | trip_id (required) | `{'$ref': '#/components/schemas/LoadFlagIn'}` | `201: {'$ref': '#/components/schemas/OkResult'}` | DISPATCHER, LOADER |
| operations | POST | `/api/v1/loading/trips/{trip_id}/start` | trip_id (required) | `none` | `200: {'$ref': '#/components/schemas/StatusResult'}` | DISPATCHER, LOADER |
| operations | POST | `/api/v1/loading/trips/{trip_id}/release` | trip_id (required) | `none` | `200: {'$ref': '#/components/schemas/StatusResult'}` | DISPATCHER, LOADER |
| operations | GET | `/api/v1/driver/trips/current` | none | `none` | `200: {'anyOf': [{'$ref': '#/components/schemas/TripOut'}, {'type': 'null'}], 'title': 'Response Current Trip Api V1 Driver Trips Current Get'}` | DISPATCHER, DRIVER |
| operations | POST | `/api/v1/driver/trips/start` | none | `none` | `200: {'$ref': '#/components/schemas/StatusResult'}` | DISPATCHER, DRIVER |
| operations | POST | `/api/v1/driver/stops/{stop_id}/events` | stop_id (required) | `{'$ref': '#/components/schemas/DeliveryEventIn'}` | `201: {'$ref': '#/components/schemas/DeviceResult'}` | DISPATCHER, DRIVER |
| operations | POST | `/api/v1/driver/sync` | none | `{'$ref': '#/components/schemas/SyncBatch'}` | `200: {'type': 'array', 'items': {'$ref': '#/components/schemas/DeliveryEventResult'}, 'title': 'Response Sync Events Api V1 Driver Sync Post'}` | DISPATCHER, DRIVER |
| operations | POST | `/api/v1/driver/uploads` | none | `{'$ref': '#/components/schemas/Body_upload_pod_api_v1_driver_uploads_post'}` | `200: {'$ref': '#/components/schemas/UploadResult'}` | DISPATCHER, DRIVER, LOADER |
| operations | POST | `/api/v1/driver/positions` | none | `{'$ref': '#/components/schemas/PositionIn'}` | `201: {'$ref': '#/components/schemas/OkResult'}` | DISPATCHER, DRIVER |
| operations | GET | `/api/v1/driver/positions/latest` | none | `none` | `200: {'items': {'$ref': '#/components/schemas/PositionOut'}, 'type': 'array', 'title': 'Response Latest Positions Api V1 Driver Positions Latest Get'}` | DISPATCHER, DRIVER |
| operations | POST | `/api/v1/driver/check-delivery-windows` | none | `none` | `200: {'$ref': '#/components/schemas/CreatedResult'}` | DISPATCHER, DRIVER |
| operations | GET | `/api/v1/driver/sync` | device_id (required), after, limit | `none` | `200: {'$ref': '#/components/schemas/SyncHistoryPage'}` | DISPATCHER, DRIVER |
| operations | GET | `/api/v1/driver/history` | limit, offset | `none` | `200: {'type': 'array', 'items': {'$ref': '#/components/schemas/DriverHistoryEvent'}, 'title': 'Response Route History Api V1 Driver History Get'}` | DISPATCHER, DRIVER |
| operations | POST | `/api/v1/admin/clock` | none | `{'$ref': '#/components/schemas/ClockAdvanceRequest'}` | `200: {'$ref': '#/components/schemas/ClockResult'}` | DISPATCHER |
| operations | GET | `/api/v1/admin/clock` | none | `none` | `200: {'$ref': '#/components/schemas/ClockResult'}` | DISPATCHER |
| operations | GET | `/api/v1/admin/events/poll` | since, limit, cursor | `none` | `200: {'$ref': '#/components/schemas/EventPage'}` | DISPATCHER |
| operations | GET | `/api/v1/admin/capacity/forecast` | date | `none` | `200: {'$ref': '#/components/schemas/CapacityForecast'}` | DISPATCHER |
| operations | GET | `/api/v1/admin/analytics/daily` | date | `none` | `200: {'$ref': '#/components/schemas/DailySummary'}` | DISPATCHER |
| operations | GET | `/api/v1/admin/analytics/fuel` | iso_year, iso_week | `none` | `200: {'$ref': '#/components/schemas/FuelSummary'}` | DISPATCHER |
| operations | GET | `/api/v1/admin/audit` | limit | `none` | `200: {'type': 'array', 'items': {'$ref': '#/components/schemas/AuditOut'}, 'title': 'Response List Audit Api V1 Admin Audit Get'}` | ADMIN |
| operations | GET | `/api/v1/analytics/demand-forecast` | none | `none` | `200: {'$ref': '#/components/schemas/DemandForecast'}` | DISPATCHER |
| operations | POST | `/api/v1/planning/jobs` | none | `{'$ref': '#/components/schemas/JobRequest'}` | `202: {'$ref': '#/components/schemas/JobResult'}` | DISPATCHER |
| operations | GET | `/api/v1/planning/jobs/{job_id}` | job_id (required) | `none` | `200: {'$ref': '#/components/schemas/JobStatus'}` | DISPATCHER |
| operations | POST | `/api/v1/planning/jobs/{job_id}/cancel` | job_id (required) | `none` | `200: {'$ref': '#/components/schemas/JobResult'}` | DISPATCHER |
| operations | GET | `/uploads/{key}` | key (required) | `none` | `200: {}` | authenticated |
| operations | GET | `/api/v1/evidence/{key}/download-url` | key (required) | `none` | `200: {'$ref': '#/components/schemas/DownloadResult'}` | authenticated |
| notifications | GET | `/api/v1/notifications` | limit, offset | `none` | `200: {'type': 'array', 'items': {'$ref': '#/components/schemas/NotificationOut'}, 'title': 'Response List Notifications Api V1 Notifications Get'}` | authenticated |
| notifications | POST | `/api/v1/notifications/{event_id}/read` | event_id (required) | `none` | `200: {'$ref': '#/components/schemas/OkResult'}` | authenticated |
| notifications | POST | `/api/v1/notifications/push-subscriptions` | none | `none` | `` | authenticated |
| notifications | GET | `/health/live` | none | `none` | `200: {'$ref': '#/components/schemas/LiveHealth'}` | public probe/login |
| notifications | GET | `/health/ready` | none | `none` | `200: {'$ref': '#/components/schemas/ReadyHealth'}` | public probe/login |
