# Synthetic French legal corpus

Invented documents for the engine tests, the bench (`bench/run_bench.py`) and the leak tests of the
other modules. Every person, company, address, phone number and identifier is invented. Identifiers with a
check digit (SIREN, SIRET, NIR, IBAN, VAT, card, LEI, ISIN) are generated valid from a fixed seed; phone
numbers use the ARCEP ranges reserved for fiction (01 99 00, 04 65 71, 06 39 98...).

| File | Type |
|---|---|
| `docs/01_assignation.txt` | assignation before the Tribunal judiciaire |
| `docs/02_conclusions_appel.txt` | conclusions d'appelant (Cour d'appel, chambre sociale) |
| `docs/03_contrat_travail.txt` | contrat de travail à durée indéterminée |
| `docs/04_jugement_cph.txt` | jugement de conseil de prud'hommes |
| `docs/05_echange_emails.txt` | e-mail exchange lawyer / client |
| `docs/06_extrait_kbis.txt` | Kbis-like extract |
| `docs/07_pv_assemblee.txt` | procès-verbal d'assemblée générale (SCI) |
| `docs/08_mise_en_demeure.txt` | lettre de mise en demeure |
| `docs/09_constat_internet.txt` | procès-verbal de constat sur internet |

Each `docs/<name>.gold.json` holds:

- `title`: the dossier title a lawyer would type (`"Haddad c. Brivanor Logistique SAS"`);
- `parties`: the names a lawyer would register (`kind`, `value`, `id`);
- `mentions`: every mention that must be masked (`id`, `kind`, `text`, `start`, `end`, `checksum`);
- `keep_clear`: text that must stay in clear (courts with their city, institutions, laws, ordinary words).

Annotation policy: titles (M., Mme, Maître) and legal forms (SAS, SARL) are not part of a mention, nor are
the words "société", "groupe", "banque" before a company name. Addresses run from the street number to the
city (with CEDEX). Case numbers and birth dates cover the number or the date only.

The documents are generated: edit `build_fixtures.py` (inline markup `[[KIND:id|text]]` for mentions,
`((text))` for clear text) and run `python tests/fixtures/build_fixtures.py`. A test checks the files are
up to date.
