# mistral-filetree-skill — portage Vibe Code

FILETREE.md : arborescence du projet avec une ligne informative par fichier et hash de fraîcheur (port de nekocode/mistral-filetree-skill-skill).

Portage des skills de [filetree-skill](https://github.com/nekocode/filetree-skill) (archive de la branche `main`, 24 novembre 2026) vers le format Agent Skills utilisé par Vibe Code. 1 skills.

## Skills portées

- `mistral-filetree-skill` : Règles partagées pour générer, mettre à jour et vérifier un FILETREE.md (une ligne informative par fichier ...

## Installation

**Option A — comme plugin (expérimental)** : copier ce dossier entier dans `~/.vibe/plugins/mistral-filetree-skill/`.

**Option B — comme skills individuelles** : copier chaque sous-dossier de `skills/` (sauf `_shared`, qui est un dossier de support) dans `~/.vibe/skills/` ou `~/.agents/skills/` (niveau utilisateur), ou `./.vibe/skills/` / `./.agents/skills/` (niveau projet). Dans une session Vibe Code, `/reload` les prend en compte ; `/skills` les liste.

**Option C — depuis Claude Code** : si les skills sont déjà installées côté Claude Code, `/vibe:import` dans Vibe Code reprend instructions, skills, subagents, hooks et serveurs MCP.

Détail des adaptations : voir `PORT-NOTES.md`.

## Licence

MIT déclarée dans le README du dépôt d'origine (voir `.claude-plugin/plugin.json` amont)
