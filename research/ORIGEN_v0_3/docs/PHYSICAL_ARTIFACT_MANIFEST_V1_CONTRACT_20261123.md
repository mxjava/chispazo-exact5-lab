# ORIGEN physical-evidence manifest v1

**Status:** research-only structural contract  
**Target:** one Chispazo Clásico contest  
**Schema:** origen.physical-evidence-manifest.v1  
**Implementation:** physical_evidence_manifest_v1.py

## Security boundary

The parser accepts only canonical, bounded JSON and returns an UnverifiedPhysicalEvidenceManifest. It validates shape, target modality/time, required artifact coverage, signature references, custody references and declared time-proof consistency.

It does not read the source objects, recompute their digests or byte lengths, verify signatures, establish legal identity or role authorization, check revocation, validate timestamp tokens, verify external ledger inclusion, or prove that a custodian is independent. All fields remain untrusted declarations. The existing independent trust adapter remains BLOCKED_PROVENANCE and does not consume this manifest.

A valid structural manifest is not a verified evidence package.

## Required artifact taxonomy

Exactly one distinct source object and original-byte digest is required for each artifact type:

| Artifact type | Meaning | Classification |
|---|---|---|
| DRAW-ACTA | Signed draw Acta | Official procedure record |
| SALES-CLOSE-SUMMARY | Sumario de sorteo (cierre de venta) | Chispazo Acta attachment |
| CS11-WINNING-NUMBERS | Números Ganadores de los Sorteos CS-11 | Chispazo Acta attachment |
| POST-DRAW-SUMMARY | Sumario de sorteo after the draw | Chispazo Acta attachment |
| WEIGHING-STRIP | Original Tira de Pesaje | Chispazo Acta attachment |
| PARTICIPATION-CANCELLATION-SIGNATURE-MEDIA | Original participation/cancellation files and associated electronic-signature media | Official procedure custody control |
| SCALE-CALIBRATION-CERTIFICATE | Calibration record for the scale used | ORIGEN metrology support; policy 25 requires at least annual calibration |
| EQUIPMENT-URN-RECORD | Draw machine, feeder and urn identity/configuration record | ORIGEN physical support |
| SPHERE-NUMBER-MAPPING-REGISTER | Mapping of sphere identifiers to printed numbers | ORIGEN physical support |
| CS12-ROOM-ACCESS-REGISTER | CS-12 attendance/access record for the draw room | Official procedure record |
| SEGOB-OIC-CUSTODY-RECORD | Deposit/retrieval record for the security-box/OIC custody path | Official procedure custody control |
| DRAW-RECORDING-FULL | Full recording from sphere weighing through the electronic draw | Official procedure documentary witness |
| DRAW-RECORDING-EDITED | Edited recording of the draw, retained with the Acta | Official procedure Acta media |
| WINNER-RELATION-REPORT-WITH-SIGNATURE | Report Relación de Ganadores and its electronic signature | Official procedure report |
| MJF-TRANSACTION-FILE | Archivo Maestro de Transacciones deposited after the 21:00 nightly close | Official nightly custody record |
| MJF-SIGNATURE-PRINTED-FORM | MJF electronic-signature print form | Official nightly custody record |
| CS02-DAILY-EQUIPMENT-INSPECTION | Daily equipment-function inspection form CS-02 | Official procedure equipment control |

The four Acta attachments are exactly the four rows listed for Chispazo in policy 11 of SGVO-PRO-05. The winner-relation report/signature and the recordings are separately required by policies 11, 12 and 30. The MJF and its printed signature form are included because the procedure's nightly annex describes their deposit after 21:00. Participation/cancellation media, CS-02, CS-12, calibration and SEGOB/OIC custody are separate procedure controls. Equipment/urn identity and sphere-to-number mapping are additional ORIGEN physical-support requirements. None is represented as an additional verbatim row in the policy-11 attachment matrix.

V1 requires separate source objects and distinct original-byte digests. A single combined bundle containing multiple logical records is not representable by v1; do not split or reserialize a source file and then claim the derived bytes are the original source. A future schema version may add explicit byte-range/page locators for a signed bundle.

## V2 temporal-intake mapping binding

The V2 temporal intake requires a dedicated `mapping_artifact_ref` and
`mapping_artifact_sha256` on every sphere row. All 28 rows for one target
must bind the same mapping-register object and original-byte digest. The
reference must also be present in the caller's `declared_mapping_refs`
structural membership set. This set is only an untrusted declaration: it does
not authenticate the object, recompute its digest, establish institutional
authority, or prove the source object is the official mapping register.
Those checks remain the responsibility of the independently provisioned
verifier. A generic weighing/source-document reference cannot substitute for
the mapping-register artifact. The independent verifier must retrieve and hash
the original mapping-register bytes, parse the authoritative 28 sphere-ID to
printed-number assignments, and compare every V2 row pair against that
authenticated mapping. The structural parser does not inspect the mapping
artifact's contents and cannot detect a bijective reassignment by itself.

The public `verify_mapping_artifact_byte_binding` API in
`mapping_artifact_binding.py` accepts the original V1 manifest bytes, the
original mapping-register bytes, and the 28 V2 rows. It parses the exact
manifest bytes with `parse_unverified_physical_manifest`, extracts the
unique `SPHERE-NUMBER-MAPPING-REGISTER` claim, and checks the mapping bytes'
length and SHA-256 against that extracted claim. It also checks that every
V2 row repeats the manifest claim's target, source-object reference and
digest. The result is explicitly
`MAPPING_ARTIFACT_BYTES_MATCHED_NOT_AUTHENTICATED`; it includes the manifest
SHA-256 for traceability. The public API no longer accepts a caller-created
`PhysicalArtifactClaim`. Its private claim-level primitive is not an
application entry point.

The API still does **not** authenticate the manifest, parse the opaque
mapping document, or compare its 28 sphere-number pairs with V2. A bijective
swap of two V2 numbers can therefore pass this byte-binding check; this
negative scope is intentional and covered by tests. The helper is not an
independent trust backend and cannot change the adapter's
`BLOCKED_PROVENANCE` result.

The V2 gate fails closed when the mapping reference/digest is absent,
malformed, inconsistent across sphere rows, or not present in the declared
mapping-reference set. This structural binding does not change the
`BLOCKED_PROVENANCE` authentication boundary.

## MIME declarations

The parser requires semantic MIME compatibility for the two recording artifact types:
- DRAW-RECORDING-FULL and DRAW-RECORDING-EDITED must declare a `video/*` media type.
- Non-recording artifact types must not declare a `video/*` media type.

This is a structural consistency check on the declared MIME string. It does not inspect file signatures/magic bytes, decode a recording, or prove that the original source object matches the declared media type. The independent verifier must inspect the actual bytes and apply its own allowlist/content-detection policy.

## Target binding

The target must be CLASSIC, have a canonical positive decimal contest ID, a Mexico City local draw date, and a UTC close timestamp resolving exactly to 21:00:00 America/Mexico_City on that local date. A 15:00 De las Tres close is rejected.

This is a schedule-slot check, not proof that the contest ID or official close event is genuine. That requires an independently authenticated official source and any approved schedule exception.

## Signatures

Every signature claim binds one artifact digest to a subject ID, role, key ID, supported algorithm and signature digest. Signature digests are unique; a subject may make only one signature claim per artifact; one key_id cannot be attributed to multiple subject IDs.

DRAW-ACTA must declare these role labels, derived from policy 2 and policy 11:
- GENERAL-DIRECTORATE-REPRESENTATIVE
- SUBDIRECTORATE-GENERAL-SALES-OPERATIONS-REPRESENTATIVE
- INFORMATION-TECHNOLOGY-REPRESENTATIVE
- SEGOB-INSPECTOR

WEIGHING-STRIP must declare exactly four distinct subjects and exactly these activity-5.4 roles:
- SPHERE-WEIGHING-RESPONSIBLE
- SUBDIRECTORATE-GENERAL-SALES-OPERATIONS-REPRESENTATIVE
- SEGOB-INSPECTOR
- GENERAL-DIRECTORATE-REPRESENTATIVE

PARTICIPATION-CANCELLATION-SIGNATURE-MEDIA, WINNER-RELATION-REPORT-WITH-SIGNATURE and MJF-SIGNATURE-PRINTED-FORM must each have an IT-representative signature claim. CS02-DAILY-EQUIPMENT-INSPECTION must declare both the EQUIPMENT-OPERATOR and SGVO-representative roles. These role strings are schema labels; the parser does not authenticate the people or verify the signature bytes.

## Custody and time declarations

Every required artifact must have at least one custody event. Each event binds an artifact digest, globally unique event ID, custodian subject/role, received-at UTC time, custody receipt digest and timestamp-proof digest. The referenced time proof must carry the exact same event ID as the custody event.

Each referenced timestamp proof must exist and its declared event time must exactly equal the custody event's received-at time. Authority/event identities and proof digests must be unique. Signer and custodian subject IDs must be disjoint; time-authority identifiers must not literally alias declared signer or custodian identifiers. These are structural identifier checks only and do not authenticate real-world identity or independence.

The ledger anchor must claim a different resulting head digest from its previous head. This is only a structural transition check; the parser does not verify the ledger or inclusion proof.

## Adversarial acceptance tests

The isolated suite covers:
- missing or duplicate artifact types and duplicate source-object IDs;
- signer-key identity aliasing, invalid media types, and mismatched recording/non-recording video MIME declarations, including explicit video/mp4 and text/csv coverage;
- omission of full/edited draw recordings, winner-relation report/signature, nightly MJF/signature form or CS-02 inspection;
- cross-contest artifact binding;
- De las Tres 15:00 slot and mismatched local date;
- missing Acta roles and missing/duplicate weighing-strip signers;
- signature references to unknown artifacts;
- missing custody events, signer/custodian subject aliasing and missing/mismatched time proofs;
- duplicate custody event IDs, custody/time-proof event-ID mismatch, duplicate time authority/event identities and authority aliasing;
- unchanged ledger head;
- boolean byte lengths, duplicate JSON keys, noncanonical JSON and excessive nesting;
- valid structural manifest still returns no authentication capability and the independent adapter remains BLOCKED_PROVENANCE.

## External work still required

Before any authenticated classification, a separate verifier must:
1. retrieve original source bytes from controlled immutable intake;
2. recompute byte lengths and SHA-256 values;
3. verify detached signatures against independently provisioned institutional trust roots;
4. authorize signer roles and check validity/revocation/separation of duties;
5. validate trusted timestamp tokens or independently anchored ledger inclusion;
6. verify actual SEGOB/OIC custody receipts and chain continuity;
7. independently review the implementation and real source artifacts.

Passing the parser tests does not satisfy any of those external requirements and does not authorize production or EDGE_SUPPORTED.
