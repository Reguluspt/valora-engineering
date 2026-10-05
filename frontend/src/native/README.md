# Native product integration (WIN-4A)

This directory owns browser-side infrastructure only. The Preliminary Intake and Completion pages consume useNativeIntegration; business commands, Result currentness, Customer binding and Official Intake remain in their existing feature/API modules. React uses existing Valora presentation classes. The [Frontend Architecture Rule](../../../docs/architecture/VALORA_FRONTEND_ARCHITECTURE_RULE.md) applies.

The authenticated browser GET /api/v1/client-compatibility returns exactly the six frozen compatibility fields. Product actions require strict valora.native/2 hello {protocol, capabilities, clientCompatibility: 1}, matching API/web contracts, the minimum client version and all four product capabilities. A higher recommended version produces a visible warning. Browser-only, incompatible/update-required and revoked/error remain explicit states. No product action downgrades to v1; the v1 adapter and hello shape remain supported for WIN-3 consumers.

The exact reserved resource prefix is /api/v1/.valora-native/v2/. Normal API routing returns 404 for this namespace rather than SPA HTML. Native resource fetches use credentials: omit, same-origin mode, redirect rejection, no-store caching and the current document referrer. They never use the authenticated API request wrapper. A controlling service worker disables native transfer.

Native Excel selection prepares a one-use GET token and materializes a bounded .xls/.xlsx browser File. The page sets its existing File state; only the existing explicit upload button creates a batch or uploads. The product ceiling is 10 MiB; the older native 64 MiB ceiling remains a v1 safety bound.

Windows Result save binds preparation to the authoritative Result ID, version, MIME, size, extension and SHA-256. The feature supplies the existing authenticated Result download callback. Browser verification precedes a raw native POST; the native host independently verifies size/MIME/hash before creating an opaque artifact handle. Save As success is reported only after native success. Cancellation/failure does not trigger browser download. Browser download remains an explicit separate action.

Tokens are 192-bit, expire after one minute, are consumed once (including a wrong method), and belong to one bridge generation. At most eight tickets/transfers/response streams are outstanding. Navigation, session revocation and close invalidate tokens and dispose native response streams and temp artifacts. Temp paths and bytes never appear in bridge JSON; no native backend HTTP or authentication access exists.

Full WIN-4 remains **PARTIAL**. Working Document/Word product wiring, DocumentRevision, Office Save observation, notifications, OS deep-link activation, provider/OAuth launch, MSIX/signing/update and Preview/UAT remain deferred. No WIN-5 authorization follows from WIN-4A.
