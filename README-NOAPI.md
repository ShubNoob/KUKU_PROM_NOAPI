# Promo Extractor — Kuku AI Generalist Assignment, Problem 1

Reads a microdrama's screenplays and returns ranked 20–60 second promo clips that open
on a hook (first 3 seconds), cut on a cliffhanger, and make sense to someone who has never
seen the show. For every promo: episode, start/end timestamps, hook, cliffhanger, one line
on why it works, a tier and a posting order.

## Two modes, one pipeline

| Step | What it does | Rules mode (default) | LLM mode (optional) |
|---|---|---|---|
| 1 Parse | script → timeline of camera / action / dialogue / sound events, times in seconds, shot cuts | Python | Python |
| 2 Find hooks | 3–5 hook moments per episode | script signals: bracketed emotions, action verbs, sound cues, `!` | LLM, 1 call per episode |
| 3 Frame | hook → window up to 60 s; rejects times that match no line; hook within 3 s | Python | Python |
| 4 Judge | pick the cut, score hook / cliffhanger / middle, "never seen the show" test, write hook, cliffhanger, why | `?`, trailing `...`, threats; flags names never shown on screen | LLM, 1 call per clip |
| 5 Check the cut | snap the end to a real line end or shot cut inside 20–60 s; log every fix | Python | Python |
| 6 Sort and rank | Tier 1 ready / Tier 2 trim / Tier 3 rejected with reason; posting order | score order, overlapping clips pushed down | LLM, 1 call |
| 7 Hand check | human labels the top picks blind; `--score` reports agreement | Human | Human |

**The submitted outputs were made in rules mode.** LLM mode is built and tested (OpenAI,
Claude and Gemini response handling are covered by tests with stand-in servers), but API
access failed during the assignment window (Gemini overload and quota errors, no paid
credits), so it was not run on the full input pack.

In both modes the model never owns time: every timestamp is checked against the script
and the 20–60 s and 3-second rules are enforced in code.

## Run it

**Colab:** open `notebook.ipynb`, run the cells in order, upload the scripts zip when asked.
No API key is needed for the main run.

**Locally:**
```bash
pip install -r requirements.txt
python test_checks.py                             # 16 checks
python run.py scripts.zip --out outputs           # rules mode, all episodes, no API key
python run.py --score outputs/hand_check.csv      # after labelling the hand-check sheet
streamlit run app.py                              # dashboard for the results
```

**LLM mode:** set the key, then pick the provider and model:
```bash
export OPENAI_API_KEY=...
python run.py scripts.zip --provider openai --model gpt-5-mini --fallback gpt-4o-mini --out outputs_llm
```
`--provider anthropic` (key `ANTHROPIC_API_KEY`) and `--provider gemini` (`GEMINI_API_KEY`)
work the same way. Defaults live in `config.yaml`.

## Outputs (`outputs/`)

| File | What |
|---|---|
| `shortlist.md` | Tier 1 in posting order, then Tier 2 and Tier 3 with reasons |
| `promos.json` | every judged clip with segments, scores, notes and run metadata |
| `promos.csv` | the same, one row per clip |
| `failures.csv` | hooks rejected by the checks, Tier 3 reasons, corrected timestamps |
| `hand_check.csv` | top picks without scores, for blind human labelling |
| `run_log.json` | counts, timings, model calls and tokens (LLM mode), config used |

## Scale and cost

Rules mode: a 50-episode show runs in seconds at zero cost. LLM mode: about 300 calls per
show (50 to find hooks, up to 250 to judge, 1 to rank); `run_log.json` records the tokens,
so cost per show = tokens × the model's price. Responses are cached in `.cache/`, a backup
model takes over when the main one is overloaded or rate-limited, and the run stops cleanly
(keeping finished work) when credits or quota run out.

## Files

`run.py` pipeline · `parser.py` scripts → timeline · `framer.py` windows + timestamp checks ·
`llm_nodes.py` model wrapper, prompts and the rules engine · `ranker.py` tiers, ranking,
outputs · `app.py` Streamlit dashboard · `test_checks.py` tests · `config.yaml` settings ·
`rule_maker.py` + `reference_promos.txt` optional, not used in the submitted run: learns hook
and cliffhanger patterns from 60 ReelShort / DramaBox promo Shorts with a video-capable model.

## Known limits

- Works from the script, not the video: it can't judge acting, pacing on screen or audio.
- One continuous segment per promo, inside one episode.
- Rules mode reads loud moments well but misses quiet hooks with no emotional tag or
  keyword (e.g. "Because we know who he is."), and its "never seen the show" test only
  catches unseen names, not missing backstory in general.

## Confidentiality

Kuku's scripts are confidential: `.gitignore` keeps scripts, outputs and the cache out of
the repo. Upload the zip at run time.
