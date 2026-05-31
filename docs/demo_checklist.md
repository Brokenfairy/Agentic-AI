# SkillFlow AI Demo Checklist

Complete checklist for ensuring a successful demo presentation.

---

## ✅ Pre-Demo Setup

### Environment Configuration

- [ ] **`.env` file configured**
  - Copy `.env.example` to `.env`
  - Fill in required API keys OR enable demo mode
  - Verify `DEMO_MODE=true` for guaranteed stability

- [ ] **Python environment ready**
  - Python 3.10+ installed
  - Virtual environment activated (recommended)
  - All dependencies installed: `pip install -r requirements.txt`

- [ ] **Playwright installed** (optional but recommended)
  ```bash
  playwright install
  ```

- [ ] **API Keys status**
  - [ ] GOOGLE_API_KEY: Present OR demo mode enabled
  - [ ] TAVILY_API_KEY: Present OR demo cache enabled
  - [ ] LANGFUSE_PUBLIC_KEY: Optional (mock works without)
  - [ ] LANGFUSE_SECRET_KEY: Optional (mock works without)

### System Validation

- [ ] **Run final readiness check**
  ```bash
  python final_check.py
  ```
  - Expected: Score 75+ with all critical checks passing

- [ ] **Run pytest suite**
  ```bash
  pytest tests/ -v
  ```
  - Expected: All tests passing or skipped

- [ ] **Verify folder structure**
  - [ ] `outputs/` exists (create if missing)
  - [ ] `traces/` exists (create if missing)
  - [ ] `skills/` contains all skill YAMLs
  - [ ] `agents/` contains agent definitions

### Demo Data Preparation

- [ ] **Test demo queries locally**
  ```bash
  python main.py "Find top 5 URLs for iPhone 15 and extract price and rating"
  ```

- [ ] **Verify Excel export works**
  - Check `outputs/` folder for generated `.xlsx` files
  - Open one file to verify formatting

- [ ] **Cache ready** (if using demo mode)
  - Verify `demo_cache/` contains sample data OR
  - System will auto-generate mock data

---

## 🎬 During Demo

### Opening the Demo

1. **Start Streamlit app**
   ```bash
   streamlit run app.py
   ```

2. **Wait for initial load**
   - Verify sidebar loads with demo queries
   - Check environment status indicators

### Demo Flow (Recommended)

#### Phase 1: Introduction (2 minutes)
- [ ] Show the SkillFlow AI interface
- [ ] Explain the query-driven approach
- [ ] Point out the workflow visualization area

#### Phase 2: Basic Query (3 minutes)
- [ ] Click first demo query: "Find top 5 URLs for iPhone 15 and extract price and rating"
- [ ] Click **Run Workflow**
- [ ] Watch the workflow graph animate
- [ ] Point out:
  - Supervisor selecting skills
  - URLs being discovered
  - Extraction happening

#### Phase 3: Explain Results (2 minutes)
- [ ] Show selected skills panel
- [ ] Show URLs discovered
- [ ] Show execution timeline
- [ ] Show extraction results table

#### Phase 4: Excel Export (1 minute)
- [ ] Click **Download Excel** button
- [ ] Open downloaded file to show formatted output
- [ ] Highlight: columns, styling, data integrity

#### Phase 5: Advanced Query (3 minutes)
- [ ] Clear the query
- [ ] Enter: "Find restaurants in Bangalore and extract rating and location"
- [ ] Run and compare different skill selection
- [ ] Point out:
  - Different skills selected
  - Location extractor triggered
  - Price extractor skipped

#### Phase 6: Observability (2 minutes)
- [ ] Show Langfuse trace link (if configured)
- [ ] Show per-skill execution times
- [ ] Show confidence scores
- [ ] Mention: everything is logged and traceable

#### Phase 7: Fault Tolerance (2 minutes)
- [ ] Explain demo mode and fallbacks
- [ ] Show that system completes even with failures
- [ ] Mention: each component has graceful degradation

---

## 🛡️ Demo Safety Features

### Automatic Fallbacks

| Component | Fallback Behavior |
|-----------|------------------|
| Tavily API | Mock URLs auto-generated |
| Page Read | Mock content with realistic data |
| Gemini LLM | Regex/heuristic extraction |
| Langfuse | Silent no-op, trace_id still generated |
| Excel Writer | Error logged, workflow continues |

### Demo Mode Triggers

System automatically enters safe mode when:
- `DEMO_MODE=true` in environment
- API keys missing
- Network timeouts occur
- Rate limits hit

### Quick Recovery

If something goes wrong:
1. Click **Clear** button
2. Select a demo query from sidebar
3. Click **Run Workflow** again
4. System will use cached/mock data

---

## 📊 Expected Demo Outputs

### For iPhone Query

**Skills Selected:**
- query_understanding
- url_scraper
- price_extractor
- rating_extractor
- excel_writer

**Expected Results:**
- 5 URLs discovered
- 3-5 successful extractions
- 0-2 fallback extractions
- Excel file generated with all columns

### For Restaurant Query

**Skills Selected:**
- query_understanding
- url_scraper
- rating_extractor
- location_extractor
- excel_writer

**Expected Results:**
- 5 URLs discovered
- Location data extracted
- Price extractor skipped (correctly)

---

## ⚠️ Common Demo Issues & Fixes

### Issue: Streamlit won't start
**Fix:**
```bash
pip install streamlit
streamlit run app.py
```

### Issue: No URLs found
**Fix:**
- Check `DEMO_MODE=true` in `.env`
- Mock data will auto-generate

### Issue: Excel won't download
**Fix:**
- Ensure `outputs/` folder exists
- Check write permissions

### Issue: Workflow seems slow
**Fix:**
- Normal for first run (Playwright init)
- Subsequent runs faster
- Use `PARALLEL_PAGE_READS=4` for speed

### Issue: Langfuse errors in console
**Fix:**
- Expected if keys not configured
- Errors are non-fatal
- Mock tracing still works

---

## 📝 Post-Demo

- [ ] **Save interesting traces**
  - Copy trace IDs from successful runs
  - Save to `traces/` for replay

- [ ] **Collect feedback**
  - Note questions asked
  - Document feature requests
  - Record any issues

- [ ] **Clean up outputs**
  ```bash
  # Optional: clear old Excel files
  rm outputs/*.xlsx
  ```

---

## 🎯 Demo Success Criteria

A successful demo should demonstrate:

1. ✅ **Query-Driven Execution**
   - Natural language triggers skill selection

2. ✅ **Agentic Workflow**
   - Supervisor intelligently selects skills
   - Graph shows live execution

3. ✅ **Observable System**
   - Every step logged and timed
   - Langfuse trace available

4. ✅ **Fault Tolerance**
   - Graceful fallbacks
   - Demo mode stability

5. ✅ **Production Artifacts**
   - Excel export with professional formatting
   - Structured data output

6. ✅ **Extensibility**
   - YAML-driven skills
   - Easy to add new extractors

---

## 🚀 Emergency Demo Mode

If all else fails, use replay:

```bash
# Pre-record a successful run
python main.py "Find iPhone 15 price" --json > traces/success_run.json

# During demo, replay it
python -c "from core.workflow_replay import replay_workflow; replay_workflow('traces/success_run.json')"
```

Or use the cached demo data which is always available with `DEMO_MODE=true`.

---

**Last Updated:** Phase 7 - Final QA
**Version:** 1.0
