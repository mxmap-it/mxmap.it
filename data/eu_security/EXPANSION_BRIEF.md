# EU Security Map — expansion wave 2 (perimeter extension)

Owner request (2026-11-09): extend the national-security perimeter to bodies that
may run an **autonomous mail domain**. Wave 1 (`research/{cc}.json`) covered police,
gendarmerie, border guard, intelligence, interior/defence ministries, cyber agencies.

## New categories to research (per country)

| type | what | examples |
|---|---|---|
| `armed_forces` | each service branch + top command: Army, Navy, Air Force, Space/Cyber command, General/Defence Staff, Joint Operations Command, Military Police | `esercito.difesa.it`, `marina.difesa.it`, `aeronautica.difesa.it`, `navy.mil.xx`, `army.cz` |
| `border_guard` | independent maritime / coast-guard / border authorities NOT in wave 1 | coast guard, maritime authority, customs-border agency |
| `other_natsec` | other security-relevant state bodies with own mail domain: national crisis/civil-protection agency, nuclear/radiation safety regulator, national security-clearance / classified-info authority, critical-infrastructure protection agency, military procurement/armaments agency, port security authority **only if it has a security mandate** | |

## INCLUSION RULE (strict)

Include an entity **only if** its email domain is DIFFERENT from every domain already
listed in `data/eu_security/research/{cc}.json` for that country (read it first).
Subdomains count as different (e.g. `marina.difesa.it` ≠ `difesa.it`) — those are
exactly the cases we want. If a branch mails on the same domain as its ministry, do
NOT add it (record that in `gaps`, e.g. "Navy mails on mod.gov.xx").

## Evidence

Same as wave 1: for each mail domain, URL where an address was seen, `kind` ∈
`contact_page|privacy_page|press_page|official_pdf|other_official|assumed_from_website`,
`note` with an example address. Never invent. Low confidence if assumed.

## Output

`data/eu_security/research_ext/{cc}.json` — same schema as wave 1:

```json
{"country":"IT","country_name_en":"Italy","group":"eu27","researched_at":"2026-11-09","wave":2,
 "entities":[{"id":"it-marina","type":"armed_forces","name_native":"Marina Militare","name_en":"Italian Navy","acronym":"MM","website":"https://www.marina.difesa.it","mail_domains":["marina.difesa.it"],"evidence":[{"domain":"marina.difesa.it","url":"https://...","kind":"contact_page","note":"urp@marina.difesa.it"}],"confidence":"high","notes":""}],
 "gaps":[]}
```

`id` = `{cc}-{slug}`, must NOT collide with ids in wave 1. Write each country file as
soon as done. Do NOT edit `research/` files. Do NOT commit (the coordinator commits).
