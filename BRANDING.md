# ProofBoard visual identity

## Purpose

Tie every claim to evidence you can re-check, and say plainly when it stops holding.

## Design system

- Maker's mark: by OBEOS.
- Project name: ProofBoard.
- Accent: `#60a5fa` (assurance blue).
- Canvas: `#0c1220`; primary text: `#f3f5fa`; secondary text: `#99a7bc`.
- Symbol: a board of claims with two ticked rows and one crossed row.
- Banner: `assets/brand/github-banner.svg`, 1200 × 400, with a self-contained dark background for light and dark GitHub themes.
- Shared with the other OBEOS projects: typography, spacing, grid, footer line and the README section order. Each project keeps its own accent colour and symbol; Sentinel's cyan shield is the reference, Blackbox is amber, Casefile violet, Dockyard green, RestorePoint coral and PacketStory pink.
- SVG has no script, external fonts, linked images or animation. Keep title and description accessible.

## Editorial rules

Explain the working product before the roadmap. Keep setup, limits and evidence visible. Do not add unverified release, security, performance, platform-support, test-count or AI capability claims; link a test or a recorded evidence file instead. This repository's own claims live in [`proofboard.toml`](proofboard.toml) and are checked in CI.

## Maintenance

Edit the SVG as text. Keep the name and descriptor inside the left text area (x=48 through x=860); reserve the right area for the symbol. Preserve the viewBox. `assets/social-preview.png` is the banner on a 1280 × 640 canvas, for GitHub's social preview setting.
