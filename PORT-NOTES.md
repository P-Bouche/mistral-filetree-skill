# Notes de portage — mistral-filetree-skill

Date du portage : 24 novembre 2026. Source : https://github.com/nekocode/mistral-filetree-skill-skill (branche main).

## Adaptations effectuées

- Frontmatter `SKILL.md` conservé (Agent Skills standard) et validé : `name` en slug kebab-case, `description` <= 1024 caractères.
- `description` réécrite : les slash-commands `/mistral-filetree-skill:init` / `/mistral-filetree-skill:update` n'existent pas sous Vibe ; la skill s'invoque directement.
- Les flux des commandes (`init.md`, `update.md`, `lint.md`, `uninstall.md`) sont copiés dans le dossier de la skill comme fichiers support.
- Les hooks Claude Code (`hooks.json`, `commit_guard.py`) ne sont pas portés automatiquement : voir `claude-code-incompatibles/`.

## Éléments non portés automatiquement

- Hooks et événements de session spécifiques au harnais Claude Code.
- Manifestes de marketplace (`/plugin marketplace add ...`) : Vibe Code découvre les plugins autrement (dossier `~/.vibe/plugins/` + `plugin.json`).

## Licence du contenu source

MIT déclarée dans le README du dépôt d'origine (voir `.claude-plugin/plugin.json` amont)

- Licence MIT déclarée par le dépôt d'origine (nekocode/filetree-skill) ; texte MIT standard ajouté lors du portage, Copyright attribué à l'auteur d'origine.
