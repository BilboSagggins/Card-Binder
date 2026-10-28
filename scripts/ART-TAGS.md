# Art tags: status (for picking this up later)

**What it is:** search cards by what's in the artwork ("moon", "beach", "snow"…). A free open-source AI model
(CLIP, `openai/clip-vit-base-patch16`) looks at each English Pokémon card picture once on GitHub's runner and
tags it with everyday concepts. No paid AI service or key.

**Where things are**
- `scripts/build-art-tags.py`: the scanner. Resumable: results go to `prices/art-tags.json`, and each run only
  does cards not tagged yet (newest first), `--limit N` per run. `--trial N --sheets` = random sample + picture grids.
- Trial page: `test/art-trial.html` (+ `test/art-trial.json`, 580 random cards), at
  https://bilbosagggins.github.io/Card-Binder/test/art-trial.html
- Library note: pin `transformers>=4.40,<5` (v5 changed `get_text_features`). Install torch from the CPU index.

**Settings after the trial**
- Two views per card (whole card letterboxed + the artwork window), averaged.
- A tag is kept when its score is 2.3+ standard deviations above that concept's average and it's among the card's
  top 20 matches; at most 8 tags per card. Noisy words (jobs, colours, drawing styles) are dropped (see `DROP`).
- Per-concept averages are saved in the output (`stats`) so later runs score new cards the same way.
- Speed: about 4 cards/second on a standard runner, so ~28,000 English cards ≈ 2 hours (split over runs).

**Status (2026-10-24)**
- [x] Trial: 580 cards. Snow and beach very accurate, moon good, a few misses on small details.
- [x] Kyle approved (2026-10-24). Full scan: `.github/workflows/art-tags.yml`, every 3 hours, 9,000 new cards per run
      (newest first) until all ~28,000 are done, then only new cards. Progress = `done` / `total` in `prices/art-tags.json`.
- [x] App: "🎨 In the art" filter in card search (English Pokémon), word match so "moon" includes "full moon" and
      "crescent moon"; the tag file is saved for offline.
- [x] First full scan done 2026-10-25 (27,160 cards; 908 have no TCGplayer picture, retried every two weeks).
- [x] 2026-10-28 refinement (Kyle asked): compared 4 setups on the 580-card sample (probe branch, art-compare.py).
      Winner: openai/clip-vit-large-patch14 with the card's name bar and text box blurred (stops "Food Prep" -> food,
      Cosmic Eclipse stamp -> eclipse). Likely matches (z 1.8-2.3) now kept and listed after clear ones. Rescan runs
      every 2 hours, 2,400 cards each (~1.8 s/card), about a day in total; cards keep their earlier tags until redone
      ("old_ids" in the file). App: everyday words (water, space, dessert, spooky...) map to art words.
- [ ] Later, if wanted: Japanese / One Piece cards, more words.
