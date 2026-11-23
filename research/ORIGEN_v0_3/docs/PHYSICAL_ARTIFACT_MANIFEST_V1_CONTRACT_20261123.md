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

## Target binding

The target must be CLASSIC, have a canonical positive decimal contest ID, a Mexico City local draw date, and a UTC close timestamp resolving exactly to 21:00:00 America/Mexico_City on that local date. A 15:00 De las Tres close is rejected.

This is a schedule-slot check, not proof that the contest ID or official close event is genuine. That requires an independently authenticated official source and any approved schedule exception.

## Signatures

Every signature claim binds one artifact digest to a subject ID, role, key ID, supported algorithm and signature digest. Signature digests are unique; a subject may make only one signature claim per artifact.

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

Every required artifact must have at least one custody event. Each event binds an artifact digest, event ID, custodian subject/role, received-at UTC time, custody receipt digest and timestamp-proof digest.

Each referenced timestamp proof must exist and its declared event time must exactly equal the custody event's received-at time. Authority/event identities and proof digests must be unique. Time-authority identifiers must not literally alias declared signer or custodian identifiers.

The ledger anchor must claim a different resulting head digest from its previous head. This is only a structural transition check; the parser does not verify the ledger or inclusion proof.

## Adversarial acceptance tests

The isolated suite covers:
- missing or duplicate artifact types and duplicate source-object IDs;
- omission of full/edited draw recordings, winner-relation report/signature, nightly MJF/signature form or CS-02 inspection;
- cross-contest artifact binding;
- De las Tres 15:00 slot and mismatched local date;
- missing Acta roles and missing/duplicate weighing-strip signers;
- signature references to unknown artifacts;
- missing custody events and missing/mismatched time proofs;
- duplicate time authority/event identities and authority aliasing;
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
