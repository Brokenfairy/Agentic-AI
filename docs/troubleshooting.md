# SkillFlow AI Troubleshooting Guide

Common issues and their solutions.

---

## 🔑 API Key Issues

### Gemini API Key Missing

**Symptom:**
```
Error: GOOGLE_API_KEY not found
or
Gemini extraction failed, falling back to heuristics
```

**Solutions:**

1. **Add the key to .env:**
   ```bash
   # .env
   GOOGLE_API_KEY=your_key_here
   ```

2. **Or enable demo mode (no key needed):**
   ```bash
   # .env
   DEMO_MODE=true
   DEMO_ALLOW_MOCK_EXTRACTION=true
   ```

3. **Verify key format:**
   - Should start with `AIzaSy...`
   - Get from: https://makersuite.google.com/app/apikey

4. **Test the key:**
   ```python
   import google.generativeai as genai
   genai.configure(api_key="your_key")
   model = genai.GenerativeModel('gemini-2.0-flash')
   response = model.generate_content("Hello")
   print(response.text)
   ```

---

### Tavily API Failure

**Symptom:**
```
WARNING: Tavily API error
Falling back to mock URLs
```

**Solutions:**

1. **Add Tavily key:**
   ```bash
   # .env
   TAVILY_API_KEY=tvly-...
   ```
   Get from: https://tavily.com/

2. **Enable demo mode (uses mock URLs):**
   ```bash
   # .env
   DEMO_MODE=true
   DEMO_ALLOW_MOCK_SEARCH=true
   ```

3. **Test Tavily connection:**
   ```python
   from tavily import TavilyClient
   client = TavilyClient(api_key="your_key")
   result = client.search("test query")
   print(result)
   ```

---

### Langfuse Not Working

**Symptom:**
```
Langfuse trace failed
or
No trace URL generated
```

**Solutions:**

1. **Add Langfuse keys (optional):**
   ```bash
   # .env
   LANGFUSE_PUBLIC_KEY=pk-...
   LANGFUSE_SECRET_KEY=sk-...
   LANGFUSE_HOST=https://cloud.langfuse.com
   ```

2. **Verify system works without Langfuse:**
   - This is expected behavior!
   - System creates local trace_id even without Langfuse
   - Errors are non-fatal

3. **Check Langfuse dashboard:**
   - https://cloud.langfuse.com
   - Traces appear after 30-60 seconds

---

## 🖥️ Installation Issues

### Playwright Not Installed

**Symptom:**
```
Error: Playwright not found
Page read falling back to requests only
```

**Solutions:**

1. **Install Playwright:**
   ```bash
   pip install playwright
   playwright install
   ```

2. **Or use without Playwright:**
   - System works with `requests` + `BeautifulSoup`
   - JavaScript-heavy sites may not load fully
   - Demo mode provides mock content

3. **Verify installation:**
   ```python
   from playwright.sync_api import sync_playwright
   with sync_playwright() as p:
       browser = p.chromium.launch()
       print("Playwright OK")
       browser.close()
   ```

---

### Import Errors

**Symptom:**
```
ModuleNotFoundError: No module named 'core'
ImportError: cannot import name 'X' from 'Y'
```

**Solutions:**

1. **Install all dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Check Python path:**
   ```bash
   # Run from project root
   cd /path/to/skillflow-ai
   python -c "import sys; print(sys.path)"
   ```

3. **Verify folder structure:**
   ```
   skillflow-ai/
   ├── core/
   │   └── __init__.py  <-- Must exist
   ├── tools/
   │   └── __init__.py  <-- Must exist
   └── ...
   ```

4. **Fix missing __init__.py:**
   ```bash
   touch core/__init__.py
   touch tools/__init__.py
   touch components/__init__.py
   touch config/__init__.py
   ```

---

### Streamlit Import Error

**Symptom:**
```
Error: streamlit not found
Cannot run app.py
```

**Solutions:**

1. **Install Streamlit:**
   ```bash
   pip install streamlit
   ```

2. **Verify installation:**
   ```bash
   streamlit --version
   ```

3. **Alternative: Run CLI version:**
   ```bash
   python main.py "your query"
   ```

---

## 📊 Excel Export Issues

### Excel Export Error

**Symptom:**
```
Error writing Excel file
Permission denied: outputs/...
```

**Solutions:**

1. **Create outputs folder:**
   ```bash
   mkdir outputs
   ```

2. **Fix permissions:**
   ```bash
   # Linux/Mac
   chmod 755 outputs
   
   # Windows (run as Administrator if needed)
   icacls outputs /grant Users:F
   ```

3. **Use absolute path:**
   ```python
   from pathlib import Path
   output_dir = Path.home() / "skillflow_outputs"
   output_dir.mkdir(exist_ok=True)
   ```

4. **Check disk space:**
   ```bash
   df -h  # Linux/Mac
   dir    # Windows
   ```

---

### Excel File Corrupted

**Symptom:**
```
Cannot open Excel file
File format invalid
```

**Solutions:**

1. **Verify openpyxl installation:**
   ```bash
   pip install openpyxl
   ```

2. **Test with simple data:**
   ```python
   from tools.excel_writer_tool import write_excel
   rows = [{"Query": "Test", "Website": "test.com", "URL": "http://test.com"}]
   result = write_excel(rows, query="Test")
   print(result)
   ```

3. **Check file exists before opening:**
   ```python
   from pathlib import Path
   path = Path("outputs/skillflow_results_...xlsx")
   assert path.exists()
   assert path.stat().st_size > 0
   ```

---

## 📝 YAML/Config Issues

### YAML Load Error

**Symptom:**
```
Error parsing skill.yaml
YAMLError: could not determine a constructor
```

**Solutions:**

1. **Validate YAML syntax:**
   ```bash
   # Install yamllint
   pip install yamllint
   yamllint skills/price_extractor/skill.yaml
   ```

2. **Check for tabs vs spaces:**
   - YAML requires spaces, not tabs
   - Use 2-space indentation

3. **Common fixes:**
   ```yaml
   # WRONG (tabs)
   name:	price_extractor
   
   # RIGHT (spaces)
   name: price_extractor
   ```

4. **Test specific file:**
   ```python
   import yaml
   with open("skills/price_extractor/skill.yaml") as f:
       data = yaml.safe_load(f)
       print(data)
   ```

---

### Skill Not Loading

**Symptom:**
```
Skill 'X' not found
Supervisor could not select skill
```

**Solutions:**

1. **Verify skill structure:**
   ```
   skills/
   └── price_extractor/
       ├── skill.yaml  <-- Required
       └── SKILL.md    <-- Optional but recommended
   ```

2. **Check skill.yaml format:**
   ```yaml
   name: price_extractor  # Must match folder name
   version: "1.0"
   description: "Extracts prices"
   ```

3. **Reload skills:**
   ```python
   from core.skill_loader import load_all_skills
   skills = load_all_skills()
   print(list(skills.keys()))
   ```

---

## 🔄 Workflow Issues

### Workflow Fails Mid-Execution

**Symptom:**
```
Workflow failed at node: extraction
Error: ...
```

**Solutions:**

1. **Enable demo mode for safety:**
   ```bash
   # .env
   DEMO_MODE=true
   DEMO_NEVER_FAIL_WORKFLOW=true
   ```

2. **Check logs:**
   ```python
   # In the failed state
   print(state.logs)
   print(state.errors)
   ```

3. **Run with event tracing:**
   ```python
   def on_event(evt):
       print(evt)
   
   state = run_workflow("your query", on_event=on_event)
   ```

4. **Test individual components:**
   ```python
   # Test query parser
   from core.query_parser import parse_query
   print(parse_query("your query"))
   
   # Test supervisor
   from core.supervisor import run_supervisor
   # ...
   ```

---

### Workflow Too Slow

**Symptom:**
```
Workflow takes >30 seconds
Page reads timing out
```

**Solutions:**

1. **Increase parallel workers:**
   ```bash
   # .env
   PARALLEL_PAGE_READS=4
   ```

2. **Reduce URL limit:**
   ```bash
   # .env
   DEFAULT_URL_LIMIT=3
   ```

3. **Use demo mode (faster):**
   ```bash
   # .env
   DEMO_MODE=true  # Uses mock data, skips real scraping
   ```

4. **Check network connectivity:**
   ```bash
   ping google.com
   ```

---

### Extraction Quality Poor

**Symptom:**
```
Low confidence scores
Many fallback extractions
```

**Solutions:**

1. **Add Gemini for better extraction:**
   ```bash
   # .env
   GOOGLE_API_KEY=your_key
   DEFAULT_MODEL=gemini-2.0-flash
   ```

2. **Check HTML content quality:**
   ```python
   from tools.page_reader import read_page
   result = read_page("https://example.com/product")
   print(len(result["content"]))  # Should be >1000 chars
   ```

3. **Improve selectors for specific site:**
   ```python
   # In extractor_engine.py
   FIELD_EXTRACTORS = {
       "price": [
           r'class="[^"]*price[^"]*"[^>]*>([^<]+)',  # Site-specific
       ]
   }
   ```

---

## 🧪 Testing Issues

### pytest Not Found

**Symptom:**
```
command not found: pytest
```

**Solutions:**

```bash
pip install pytest pytest-asyncio pytest-mock
```

---

### Tests Failing

**Symptom:**
```
FAILED tests/test_X.py::test_Y - AssertionError
```

**Solutions:**

1. **Run specific test with verbose output:**
   ```bash
   pytest tests/test_skill_loader.py -v -s
   ```

2. **Check demo mode is enabled:**
   ```bash
   export DEMO_MODE=true
   pytest
   ```

3. **Run final check instead:**
   ```bash
   python final_check.py
   ```

---

## 🌐 Network Issues

### Cannot Reach External APIs

**Symptom:**
```
Connection timeout
SSL certificate error
```

**Solutions:**

1. **Use demo mode:**
   ```bash
   DEMO_MODE=true
   ```

2. **Check proxy settings:**
   ```bash
   # .env
   HTTP_PROXY=http://proxy.company.com:8080
   HTTPS_PROXY=http://proxy.company.com:8080
   ```

3. **Verify firewall:**
   ```bash
   curl -I https://api.tavily.com
   ```

---

## 💾 Replay System Issues

### Replay File Not Found

**Symptom:**
```
FileNotFoundError: traces/replay.json
```

**Solutions:**

1. **Create traces folder:**
   ```bash
   mkdir traces
   ```

2. **Save a replay first:**
   ```python
   from core.workflow_replay import save_replay
   from core.workflow_executor import run_workflow
   
   state = run_workflow("test query")
   save_replay(state, "traces/demo_replay.json")
   ```

3. **Use absolute path:**
   ```python
   from pathlib import Path
   replay_path = Path(__file__).parent / "traces" / "replay.json"
   ```

---

## 🐛 Debug Mode

### Enable Debug Logging

```python
# In your script or .env
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check System Health

```bash
python final_check.py
```

### Validate Individual Components

```python
# test_components.py
from core.skill_loader import load_all_skills
from core.query_parser import parse_query
from tools.web_search_tool import search_web

print("Skills:", list(load_all_skills().keys()))
print("Parsed:", parse_query("Find iPhone 15 price"))
print("Search:", search_web("test", limit=2, allow_mock=True))
```

---

## 📞 Getting Help

If issues persist:

1. **Check final_check.py output**
   ```bash
   python final_check.py > debug.log 2>&1
   ```

2. **Verify environment**
   ```bash
   python --version  # Should be 3.10+
   pip list | grep -E "streamlit|langchain|pytest"
   ```

3. **Review architecture docs**
   - See `docs/architecture.md` for component details

4. **Check demo checklist**
   - See `docs/demo_checklist.md` for setup steps

---

**Last Updated:** Phase 7 - Final QA
**Version:** 1.0
