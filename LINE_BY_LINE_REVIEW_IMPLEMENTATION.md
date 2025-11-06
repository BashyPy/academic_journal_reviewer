# Line-by-Line Review Implementation

## Overview
Implemented comprehensive line-by-line review system with exact quotes, line numbers, and specific recommendations integrated into LangGraph and LangChain workflows.

## Changes Made

### 1. Base Agent (`app/agents/base_agent.py`)
**Line Numbering:**
- Added automatic line numbering to manuscript content
- Format: `Line 1: [content]`, `Line 2: [content]`, etc.
- Passed to all specialist agents for precise referencing

**Enhanced JSON Format:**
```json
{
  "finding": "**Line X**: \"exact quoted text\" - Issue: [problem] - Fix: [solution]",
  "line_reference": "X"
}
```

### 2. Specialist Agents (`app/agents/specialist_agents.py`)
**All agents now require:**
- 10-15 line-specific findings
- Exact quotes with line numbers
- Format: `**Line X**: "quoted text" - Issue - Fix`

**Methodology Agent:**
- Line-by-line methodology analysis
- Statistical methods validation per line
- Reproducibility checks with line references

**Literature Agent:**
- Line-by-line citation analysis
- Missing references identified by line
- Gap analysis with specific line numbers

**Clarity Agent:**
- Line-by-line writing analysis
- Grammar and readability per line
- Rewrite suggestions for specific lines

**Ethics Agent:**
- Line-by-line ethical analysis
- Compliance checks with line references
- Ethical concerns identified by line

### 3. Synthesis Agent (`app/agents/synthesis_agent.py`)
**Enhanced Report Structure:**
```markdown
# Detailed Professional Review Report

## Introduction
[2-3 paragraphs]

## Summary of Key Findings
- [Bullet points with specific data]

## Methodological Approach
[2-3 paragraphs]

## Line-by-Line Review

### Abstract Section
**Line 5**: "The sample size was 50 participants"
- Issue: No power analysis justification
- Recommendation: Add G*Power calculation

**Line 8**: "Results showed significant differences"
- Issue: No effect size reported
- Recommendation: Include Cohen's d or eta-squared

### Introduction Section
**Line 23**: "Previous studies have shown..."
- Issue: No specific citations provided
- Recommendation: Add Smith et al. (2020) and Jones (2021)

[Continue for ALL sections]

## Implications and Future Directions
[2-3 paragraphs]

## Strengths and Limitations
### Strengths
1. [With line references]
### Limitations
1. [With line references]

## Recommendations
1. **Line 45-47**: [Specific change]
2. **Line 89**: [Specific change]

## Conclusion
[2-3 paragraphs]
```

### 4. LangGraph Workflow (`app/services/langgraph_workflow.py`)
**Integration Points:**
- Line numbering added in `_run()` function
- Numbered content passed to all review methods
- Prompts updated to request LINE-BY-LINE analysis
- All agent prompts reference NUMBERED MANUSCRIPT

**Code Changes:**
```python
# Add line numbers to content
lines = content.split('\n')
numbered_content = '\n'.join([f"Line {i+1}: {line}" for i, line in enumerate(lines)])
enhanced_context = {**state["context"], "content": numbered_content}
```

### 5. LangChain Service (`app/services/langchain_service.py`)
**Already Compatible:**
- Accepts numbered content through context
- Passes to all LLM providers
- RAG integration maintains line numbers
- Chain-of-thought preserves line references

## Review Format Example

```markdown
### Methods Section Line-by-Line Review

**Line 145**: "Participants were recruited through convenience sampling"
- Issue: No justification for non-random sampling method
- Impact: Limits generalizability of findings
- Fix: Add rationale for convenience sampling or use random sampling

**Line 156**: "Data was analyzed using SPSS version 25"
- Issue: No specific statistical tests mentioned
- Impact: Unclear which analyses were performed
- Fix: Specify tests (e.g., "independent t-tests, α=0.05")

**Line 167**: "Results were significant (p<0.05)"
- Issue: No effect size reported
- Impact: Cannot assess practical significance
- Fix: Add "Cohen's d=0.65, indicating medium effect"

**Line 178**: "The correlation was r=0.45"
- Issue: No confidence interval provided
- Impact: Uncertainty in estimate unclear
- Fix: Report "r=0.45, 95% CI [0.32, 0.58]"
```

## Integration Flow

```
1. Manuscript Upload
   ↓
2. Base Agent: Add Line Numbers
   Line 1: Abstract text...
   Line 2: More abstract...
   ↓
3. LangGraph Workflow: Pass Numbered Content
   ↓
4. Specialist Agents: Analyze Line-by-Line
   - Methodology: Lines 145-200
   - Literature: Lines 23-89
   - Clarity: Lines 1-250
   - Ethics: Lines 201-220
   ↓
5. Synthesis Agent: Compile Line-by-Line Report
   ↓
6. Final Report with Line References
```

## Key Features

### ✅ Exact Line Numbers
Every finding references specific line(s)

### ✅ Exact Quotes
All issues include quoted text from manuscript

### ✅ Specific Recommendations
Each line gets concrete fix suggestion

### ✅ Section Organization
Reviews organized by manuscript section

### ✅ Severity Classification
Major/moderate/minor per line issue

### ✅ Comprehensive Coverage
15-20 line-specific findings per agent

## Testing Checklist

- [ ] Upload manuscript
- [ ] Verify line numbers in agent prompts
- [ ] Check specialist agent findings have line numbers
- [ ] Verify synthesis report has line-by-line section
- [ ] Confirm exact quotes present
- [ ] Validate recommendations are specific
- [ ] Check all sections covered (Abstract, Intro, Methods, Results, Discussion)
- [ ] Verify format: **Line X**: "quote" - Issue - Fix

## Expected Output Quality

**Before:**
"The methodology section needs improvement in statistical reporting."

**After:**
```
**Line 156**: "Data was analyzed using SPSS"
- Issue: No specific statistical tests mentioned
- Impact: Unclear which analyses performed
- Fix: Specify "independent t-tests (α=0.05) and Pearson correlations"
```

## Benefits

1. **Precision**: Exact line references eliminate ambiguity
2. **Actionability**: Authors know exactly what to change
3. **Efficiency**: No searching for mentioned issues
4. **Completeness**: Every section gets detailed review
5. **Professionalism**: Matches journal review standards

## Notes

- Line numbering happens automatically in base agent
- All agents receive numbered content
- Synthesis agent compiles line-by-line findings
- Format strictly enforced in prompts
- 10-15 findings per agent = 40-60 total line-specific issues
- Full manuscript content included for context

---

**Status:** ✅ Fully Integrated
**Components:** Base Agent, Specialist Agents, Synthesis Agent, LangGraph, LangChain
**Output:** Comprehensive line-by-line reviews with exact quotes and recommendations
