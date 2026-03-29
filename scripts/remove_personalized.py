import os
import re

def process_hub():
    path = r"c:\VSProjects\ET_jaimatadi\ET\frontend\src\pages\HubPage.jsx"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Removals
    content = content.replace("const [personalizedMeta, setPersonalizedMeta] = useState(null) // stores agent metadata", "")
    content = content.replace("if (convo.personalizedMeta) setPersonalizedMeta(convo.personalizedMeta)", "")
    content = content.replace("setPersonalizedMeta(null)", "")
    
    # Remove startPersonalizedFeed block
    pattern_func = r"// ── NEW: Personalized Feed .*?  // ── Follow-up Q&A"
    content = re.sub(pattern_func, "  // ── Follow-up Q&A", content, flags=re.DOTALL)
    
    # Tool title
    content = content.replace("if (tool === 'personalized') return '🧠 Personalized Intelligence Feed'\n", "")
    
    # Hub personalized section
    pattern_section = r"{/\* ── Personalized Feed Card ──────────────────────── \*/}.*?<div className=\"hub-divider-row\">"
    content = re.sub(pattern_section, "<div className=\"hub-divider-row\">", content, flags=re.DOTALL)
    
    # Agent Meta stats
    pattern_meta = r"{/\* ── Agent Metadata Banner \(personalized feed only\) ─── \*/}.*?<div className=\"hub-chat-history\">"
    content = re.sub(pattern_meta, "<div className=\"hub-chat-history\">", content, flags=re.DOTALL)
    
    # Source articles
    pattern_source = r"{/\* ── Source Articles \(personalized feed only\) ────── \*/}.*?{loading && \("
    content = re.sub(pattern_source, "{loading && (", content, flags=re.DOTALL)
    
    # Loading title/sub
    content = content.replace(
        "{tool === 'personalized' ? 'Intelligence Agent is working...' : 'Agent is processing...'}",
        "'Agent is processing...'"
    )
    content = content.replace(
        "{tool === 'personalized'\n                    ? 'Generating queries → Fetching RSS → Evaluating relevance → Gap analysis → Briefing'\n                    : 'Collecting intel, generating insights.'}",
        "'Collecting intel, generating insights.'"
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def process_intel():
    path = r"c:\VSProjects\ET_jaimatadi\ET\backend\app\routes\intel.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Remove the personalized feed section
    pattern_intel = r"# ── Personalized Intelligence Agent ─────────────────────────────.*"
    content = re.sub(pattern_intel, "", content, flags=re.DOTALL)
    
    # Also remove imports if present (like PersonalizedIntelAgent)
    content = re.sub(r"from app\.intel\.personalized_agent import PersonalizedIntelAgent\n", "", content)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

process_hub()
process_intel()
print("Processed both files")
