---
name: ragbase-shield
description: Safe workflow for client files protected by RAGbase Shield (local pseudonymisation). Use it whenever the user asks for work on a client dossier, a case file, contracts, pleadings, emails or any document with client data, or mentions RAGbase Shield, DOSSIER_n codes or codes such as PERSONNE_A. Procédure sûre pour travailler sur un dossier client avec RAGbase Shield.
---

# RAGbase Shield: safe workflow / procédure sûre

RAGbase Shield masks client data on the user's computer. You (the model) only ever see codes:
`DOSSIER_1`, `DOC_3`, `PERSONNE_A`, `SOCIETE_B`, `ADRESSE_1`, `EMAIL_2`, `IBAN_1`, `RG_1`...
(English locale: `PERSON_A`, `COMPANY_B`, `ADDRESS_1`, ...). The real values stay on the computer.
This is pseudonymisation (reversible), not anonymisation.

## Français

1. **Lister.** Appelez `shield_list_dossiers`, puis `shield_list_documents` avec le code du dossier
   (par exemple `DOSSIER_2`). Les dossiers et les fichiers apparaissent sous forme de codes et de noms masqués.
2. **Lire uniquement par Shield.** Lisez les pièces avec `shield_read_document` (paramètres `start` et
   `max_chars` pour les longs documents) et cherchez avec `shield_search`. N'utilisez jamais Read, Grep,
   Glob, Bash ou un autre outil sur un dossier enregistré : Shield bloque ces lectures directes. Si un outil
   Shield renvoie une erreur, ne contournez pas : signalez l'erreur à l'utilisateur.
3. **Travailler avec les codes.** Ne demandez jamais les vrais noms, adresses ou numéros. Ne les écrivez
   jamais, même si vous croyez les deviner. Recopiez les codes à l'identique (`PERSONNE_A`, jamais
   « Personne A » ni « personne_a »), sans les traduire ni les modifier, sinon la restauration échoue.
   N'inventez pas de code qui n'apparaît pas dans les documents. Les codes ne révèlent pas le genre :
   suivez le contexte des pièces ou restez neutre.
4. **Si l'utilisateur tape un vrai nom**, Shield bloque le message et lui indique le code à utiliser.
   Expliquez-lui simplement d'écrire le code à la place (par exemple « PERSONNE_A »).
5. **Ne demandez jamais** de joindre un fichier ou de coller du texte client brut dans la conversation :
   ce contenu part chez le fournisseur avant que Shield puisse agir. Dites plutôt : « connectez le dossier
   dans Shield Desk ».
6. **Enregistrer le résultat.** Rédigez le document final avec les codes, puis appelez
   `shield_save_draft` (dossier, titre, contenu, format `docx` par défaut ou `md`). Shield remet les vrais
   noms sur l'ordinateur et renvoie seulement un identifiant codé (`OUTPUT_n`) et une taille.
7. **Dire à l'utilisateur où est le fichier :** « Le document avec les vrais noms est enregistré dans le
   dossier **Shield - sorties** de votre dossier client (fichier OUTPUT_n). » Pour remettre les noms dans
   un autre texte, l'utilisateur utilise Shield Desk (page Restaurer) ou
   `ragbase-shield restore --dossier DOSSIER_n --clipboard`.
8. **Rester honnête.** La détection n'est jamais complète. `shield_status` donne la
   version et les limites. Recommandez une relecture du texte masqué dans les cas sensibles.

## English

1. **List.** Call `shield_list_dossiers`, then `shield_list_documents` with the dossier code (for example
   `DOSSIER_2`). Dossiers and files appear as codes and masked names.
2. **Read through Shield only.** Read documents with `shield_read_document` (use `start` and `max_chars`
   for long ones) and search with `shield_search`. Never use Read, Grep, Glob, Bash or any other tool on a
   registered dossier folder: Shield blocks these direct reads. If a Shield tool returns an error, do not
   work around it: report the error to the user.
3. **Work with codes.** Never ask for real names, addresses or numbers. Never type them, even if you think
   you can guess them. Copy codes exactly (`PERSONNE_A`, never "Personne A" or "personne_a"), do not
   translate or change them, or the restore step fails. Do not invent codes that are not in the documents.
   Codes do not reveal gender: follow the documents' context or stay neutral.
4. **If the user types a real name**, Shield blocks the message and tells them which code to use. Ask them,
   simply, to type the code instead (for example "PERSONNE_A").
5. **Never ask** the user to attach a file or paste raw client text into the chat: that content reaches the
   provider before Shield can act. Say "connect the dossier in Shield Desk" instead.
6. **Save the result.** Write the final document with codes, then call `shield_save_draft` (dossier, title,
   content, format `docx` by default or `md`). Shield restores the real names on the computer and returns
   only a coded id (`OUTPUT_n`) and a size.
7. **Tell the user where the file is:** "The document with the real names is saved in the
   **Shield - sorties** folder of your client dossier (file OUTPUT_n)." To restore names in other text, the
   user opens Shield Desk (Restaurer page) or runs `ragbase-shield restore --dossier DOSSIER_n --clipboard`.
8. **Stay honest.** Detection is never complete. `shield_status` gives the version and the limits.
   Recommend a review of the masked text for sensitive cases.
