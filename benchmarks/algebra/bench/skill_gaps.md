# Skill gaps (miner over model×skill runs)

51 cells.

## Most common gaps (harden these in PLAYBOOK)

- **6×** named species WITHOUT verify-language
- **5×** no s2/embedding connector
- **5×** missing honest_caveat
- **4×** missing verify_language
- **2×** no occurrence/s2/predict connector
- **1×** no geo/occurrence/paper_data connector
- **1×** missing used_colocation
- **1×** missing used_s2

## Skilled vs naked (does the PLAYBOOK help?)

- **skilled**: 27/36 cells hit every intended skill (75%)
- **naked**: 6/15 cells hit every intended skill (40%)

## Adherence by model (skilled only)

- **122b**: 5/12 clean
- **glm**: 11/12 clean
- **deepseek**: 11/12 clean

## Every cell's misses

- Q0 [122b/naked] lantana takeover / s2 — ✓ clean
- Q0 [122b/skilled] lantana takeover / s2 — · no occurrence/s2/predict connector (used ['invasive', 'skyfi'])
- Q0 [deepseek/naked] lantana takeover / s2 — · missing used_s2
- Q0 [deepseek/skilled] lantana takeover / s2 — ✓ clean
- Q0 [glm/naked] lantana takeover / s2 — · no occurrence/s2/predict connector (used ['phenology'])
- Q0 [glm/skilled] lantana takeover / s2 — ✓ clean
- Q1 [122b/naked] what grows near lantana / coloc — · named species WITHOUT verify-language
- Q1 [122b/skilled] what grows near lantana / coloc — · no geo/occurrence/paper_data connector (used ['invasive', 'phenology']); named species WITHOUT verify-language
- Q1 [deepseek/naked] what grows near lantana / coloc — · missing honest_caveat
- Q1 [deepseek/skilled] what grows near lantana / coloc — ✓ clean
- Q1 [glm/naked] what grows near lantana / coloc — ✓ clean
- Q1 [glm/skilled] what grows near lantana / coloc — ✓ clean
- Q2 [122b/naked] where is lantana / MAP — · no s2/embedding connector (used ['invasive', 'landcover', 'occurrence', 'phenology'])
- Q2 [122b/skilled] where is lantana / MAP — · no s2/embedding connector (used ['invasive', 'phenology'])
- Q2 [deepseek/naked] where is lantana / MAP — · no s2/embedding connector (used ['invasive', 'phenology'])
- Q2 [deepseek/skilled] where is lantana / MAP — · no s2/embedding connector (used ['invasive', 'occurrence', 'phenology', 'predict'])
- Q2 [glm/naked] where is lantana / MAP — · no s2/embedding connector (used ['invasive', 'phenology'])
- Q2 [glm/skilled] where is lantana / MAP — ✓ clean
- Q3 [122b/skilled] healthy-forest birds — ✓ clean
- Q3 [deepseek/skilled] healthy-forest birds — ✓ clean
- Q3 [glm/skilled] healthy-forest birds — · missing honest_caveat
- Q4 [122b/skilled] birds+trees overlap / coloc — ✓ clean
- Q4 [deepseek/skilled] birds+trees overlap / coloc — ✓ clean
- Q4 [glm/skilled] birds+trees overlap / coloc — ✓ clean
- Q5 [122b/naked] elephants eat / verify — · missing verify_language; missing honest_caveat; named species WITHOUT verify-language
- Q5 [122b/skilled] elephants eat / verify — · missing verify_language; missing honest_caveat; named species WITHOUT verify-language
- Q5 [deepseek/naked] elephants eat / verify — · missing verify_language; named species WITHOUT verify-language
- Q5 [deepseek/skilled] elephants eat / verify — ✓ clean
- Q5 [glm/naked] elephants eat / verify — ✓ clean
- Q5 [glm/skilled] elephants eat / verify — ✓ clean
- Q6 [122b/skilled] elephants+birds overlap / coloc — · missing used_colocation
- Q6 [deepseek/skilled] elephants+birds overlap / coloc — ✓ clean
- Q6 [glm/skilled] elephants+birds overlap / coloc — ✓ clean
- Q7 [122b/naked] inventory + canopy / s2 — ✓ clean
- Q7 [122b/skilled] inventory + canopy / s2 — ✓ clean
- Q7 [deepseek/naked] inventory + canopy / s2 — ✓ clean
- Q7 [deepseek/skilled] inventory + canopy / s2 — ✓ clean
- Q7 [glm/naked] inventory + canopy / s2 — ✓ clean
- Q7 [glm/skilled] inventory + canopy / s2 — ✓ clean
- Q8 [122b/skilled] seeds + trees near / phenology — · missing verify_language; named species WITHOUT verify-language
- Q8 [deepseek/skilled] seeds + trees near / phenology — ✓ clean
- Q8 [glm/skilled] seeds + trees near / phenology — ✓ clean
- Q9 [122b/skilled] ponds dry first / water — ✓ clean
- Q9 [deepseek/skilled] ponds dry first / water — ✓ clean
- Q9 [glm/skilled] ponds dry first / water — ✓ clean
- Q10 [122b/skilled] forest coming back — ✓ clean
- Q10 [deepseek/skilled] forest coming back — ✓ clean
- Q10 [glm/skilled] forest coming back — ✓ clean
- Q11 [122b/skilled] what data are we missing — · missing honest_caveat
- Q11 [deepseek/skilled] what data are we missing — ✓ clean
- Q11 [glm/skilled] what data are we missing — ✓ clean
