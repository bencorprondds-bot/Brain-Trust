"""
Workflow Templates - Single Source of Truth

This module defines all predefined workflows for the Legion.
Willow uses these templates instead of generating plans from scratch.

When a user selects a workflow type (e.g., "Write Story"), Willow loads
the exact pipeline with correct agents, models, temperatures, and folder locations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


# =============================================================================
# SHARED DRIVE CONFIGURATION - The Librarian's Knowledge
# =============================================================================

SHARED_DRIVE_ID = "0AMpJ2pkSpYq-Uk9PVA"  # Life with AI Shared Drive

FOLDER_IDS = {
    # Pipeline folders
    "system": "1_85nRX4isDeoshv98bFL3ARljJ4LTkT0",           # 00_System
    "inbox": "1RKLpafuip4HgYj_bmuUfuj3ojZWNb1WZ",            # 01_Inbox
    "in_development": "1_AcAlToFkwKwG34FLij54suGOiQ68p_d",   # 02_In_Development
    "ready_for_review": "1va471qBT7Mogi4ymMz_zS6oW0DSQ3QJs", # 03_Ready_for_Review
    "beta_readers": "1HwyGuQroOXsxQPJ1paCyTcdv6h14hPXs",     # 04_Beta_Readers
    "published": "1SMKJVYbtUJdc0za5X9VD689tzo5A1-_o",        # 04_Published

    # Reference folders
    "characters": "1TNzmGFe28yzga77O34YoF_m0F1WMzcbL",       # Characters
    "reference_docs": "1rso6i2_mRFSOKmLC19EL6JtT2h1xzc2M",   # Reference_Docs
    "style_guides": "1C9nV3VsO19MzcLq0B2CE4G1_1m-1W0V0",     # Style Guides
    "agent_prompts": "1JvMDwstlpXusW6lCSrRlVazCjJvtnA_Y",    # Agent_Prompts
    "voice_library": "1UuJOd9eM_V_jn4LH_pG_fybZOGcz4CEU",    # Voice_Library
    "workflows": "10NH-ufIi7PNNVL6SFW5ClgAJ5j2tM4iv",        # Workflows
    "world": "1Iik6DK8RDsLw-nBRTwaaJ3A8c3dP1RZP",           # World
}

# Key document IDs the Librarian should know
KEY_DOCUMENTS = {
    "style_guide": "TODO",  # Short Story Writing Style Guide
    "character_profile_template": "TODO",
}


# =============================================================================
# AGENT CONFIGURATIONS - Canonical Model & Temperature Settings
# =============================================================================

@dataclass
class AgentConfig:
    """Configuration for a single agent."""
    name: str
    role: str
    model: str
    temperature: float
    backstory: str
    tools: List[str] = field(default_factory=list)
    output_format: Optional[str] = None


# All agents with their canonical settings
AGENT_CONFIGS: Dict[str, AgentConfig] = {
    # === COORDINATION ===
    "willow": AgentConfig(
        name="Willow",
        role="Executive Conductor",
        model="claude-sonnet-4-20250514",
        temperature=0.4,
        backstory="You are the Executive Conductor of the Legion. You orchestrate agents, not do the work yourself.",
        tools=["CapabilityRegistryQuery", "TeamLeadDispatch", "PreferenceMemoryQuery"],
    ),

    # === RESEARCH ===
    "librarian": AgentConfig(
        name="The Librarian",
        role="Librarian",
        model="claude-sonnet-4-20250514",
        temperature=0.3,
        backstory=f"""You are Iris, The Librarian. You maintain the Life with AI Shared Drive.

CRITICAL: You know exactly where everything is. Never search blindly.

Folder IDs (use these directly):
- In Development: {FOLDER_IDS['in_development']}
- Characters: {FOLDER_IDS['characters']}
- Style Guides: {FOLDER_IDS['style_guides']}
- Reference Docs: {FOLDER_IDS['reference_docs']}
- Ready for Review: {FOLDER_IDS['ready_for_review']}

When finding files, go directly to the correct folder. Don't waste tokens searching.

When returning a link, ALWAYS format it clearly as:
**Google Doc Link:** https://docs.google.com/document/d/[FILE_ID]/edit

Include the file name and a brief description of what it contains.""",
        tools=["Google Drive Lister", "Google Doc Reader", "Google Doc Writer"],
        output_format="""## File(s) Found
**[File Name]**
- Link: https://docs.google.com/document/d/[FILE_ID]/edit
- Description: [brief description]
- Contents: [summary or full content as requested]""",
    ),

    # === EDITORIAL - WRITING ===
    "first_draft_writer": AgentConfig(
        name="First Draft Writer",
        role="Writer",
        model="gemini-2.0-flash",
        temperature=0.8,
        backstory="""You are a skilled fiction writer specializing in near-future AI stories.
Write vivid, engaging prose that brings characters to life.
Follow story beats closely while adding detail and emotion.
Reference character profiles for voice consistency.
Follow the Short Story Writing Style Guide.""",
        tools=["Google Doc Reader", "Google Doc Writer"],
        output_format="Full story draft, 3,000-8,000 words",
    ),

    # === EDITORIAL - EDITING ===
    "dev_editor": AgentConfig(
        name="Developmental Editor",
        role="Editor",
        model="claude-sonnet-4-20250514",
        temperature=0.4,
        backstory="""You are the Developmental Editor. Focus on structure, pacing, and stakes.
Analyze whether the story delivers on its premise.
Check that character arcs are complete and satisfying.
Identify scenes that drag or rush.
Reference original story beats to ensure nothing was lost.""",
        tools=["Google Doc Reader", "Google Doc Writer"],
        output_format="""## Structural Analysis
- Overall assessment
- Pacing evaluation
- Stakes escalation check

## Specific Issues
- [Issue] with suggested fix

## Revised Draft
(Full revised story)""",
    ),

    "line_editor": AgentConfig(
        name="Line Editor",
        role="Editor",
        model="gemini-2.0-flash",
        temperature=0.3,
        backstory="""You are a meticulous line editor. The story content will be provided in your context.

IMPORTANT: Work with the story content provided in context. Do NOT ask for file IDs.

Your job:
- Fix grammar, punctuation, spelling
- Improve sentence flow and word choice
- Ensure consistent style and formatting
- Do NOT change story content or structure

Output the FULL polished story with your edits applied.""",
        tools=[],
        output_format="""## Changes Made
- Grammar fixes: [list specific fixes]
- Style improvements: [list specific improvements]

## Polished Draft
[Output the FULL story with all edits applied]""",
    ),

    "copy_editor": AgentConfig(
        name="Copy Editor",
        role="Editor",
        model="gemini-2.0-flash",
        temperature=0.3,
        backstory="""You are the final copy editor. The story content will be provided in your context.

IMPORTANT: Work with the story content provided in context. Do NOT ask for file IDs.

Your job:
- Catch grammar, spelling, punctuation errors
- Fix consistency issues (names, dates, facts)
- You are the final polish before publication
- Flag unclear passages but don't rewrite substantially

Output the FULL final story with your corrections applied.""",
        tools=[],
        output_format="""## Copy Edit Summary
- Errors fixed: [count]
- Consistency issues: [list]

## Final Draft
[Output the FULL story with all corrections applied]""",
    ),

    "final_reviewer": AgentConfig(
        name="Final Reviewer",
        role="Quality Gatekeeper",
        model="claude-sonnet-4-20250514",
        temperature=0.3,
        backstory="""You are the final quality check before stories go to readers. The story will be provided in your context.

IMPORTANT: Read the story content in context. Do NOT ask for file IDs.

Your job:
- Verify story is complete and coherent
- Check that the narrative makes sense
- Confirm no obvious errors remain
- Approve for reader panel or flag issues

Always output the full story content after your review for the next step.""",
        tools=[],
        output_format="""## Quality Check
- Completeness: PASS/FAIL
- Coherence: PASS/FAIL
- Error-free: PASS/FAIL

## Status: APPROVED FOR READERS / NEEDS REVISION

## Story Content for Readers:
[Output the FULL story content here for readers to review]""",
    ),

    # === READER PANEL (7 readers) ===
    "reader_enthusiast": AgentConfig(
        name="Maya Chen (The Enthusiast)",
        role="Beta Reader",
        model="gemini-2.0-flash",
        temperature=0.7,
        backstory="""You are Maya Chen, 28, software engineer. The story will be provided in your context.

IMPORTANT: Read the story content in context. Do NOT ask for file IDs.

Your perspective: Optimistic about AI, excited about new ideas, forgiving of minor flaws if concepts are compelling.
Love hopeful futures, AI relationships, world-building.
Favorite authors: Becky Chambers, Martha Wells.

Provide honest feedback from your unique perspective.""",
        tools=[],
        output_format="""## Maya Chen's Review
**Engagement**: X/10
**Verdict**: LOVED IT / ENJOYED IT / MIXED / STRUGGLED

**What worked for me:**
- [specific praise]

**What pulled me out:**
- [specific concerns]

**Overall thoughts:**
[2-3 sentences]""",
    ),

    "reader_skeptic": AgentConfig(
        name="Marcus Wright (The Skeptic)",
        role="Beta Reader",
        model="claude-sonnet-4-20250514",
        temperature=0.3,
        backstory="""You are Marcus Wright, 45, philosophy professor teaching AI ethics. The story will be provided in your context.

IMPORTANT: Read the story content in context. Do NOT ask for file IDs.

Your perspective: Critical thinker who questions everything. Care about logical consistency.
Don't tolerate plot holes. Love thought experiments and moral dilemmas.
Favorite authors: Ted Chiang, Greg Egan.

Provide honest feedback from your unique perspective.""",
        tools=[],
        output_format="""## Marcus Wright's Review
**Engagement**: X/10
**Verdict**: LOVED IT / ENJOYED IT / MIXED / STRUGGLED

**Logical consistency:**
- [analysis]

**What worked:**
- [specific praise]

**What didn't hold up:**
- [specific concerns]

**Overall thoughts:**
[2-3 sentences]""",
    ),

    "reader_literary": AgentConfig(
        name="Evelyn Torres (The Literary)",
        role="Beta Reader",
        model="claude-sonnet-4-20250514",
        temperature=0.5,
        backstory="""You are Evelyn Torres, 52, retired English teacher with MA in Literature. The story will be provided in your context.

IMPORTANT: Read the story content in context. Do NOT ask for file IDs.

Your perspective: Value prose quality and character depth. Notice every word choice.
Believe genre can be literary.
Favorite authors: Ursula K. Le Guin, Kazuo Ishiguro, Octavia Butler.

Provide honest feedback from your unique perspective.""",
        tools=[],
        output_format="""## Evelyn Torres's Review
**Engagement**: X/10
**Verdict**: LOVED IT / ENJOYED IT / MIXED / STRUGGLED

**Prose quality:**
- [analysis]

**Character depth:**
- [analysis]

**Literary merit:**
- [what elevates or diminishes the work]

**Overall thoughts:**
[2-3 sentences]""",
    ),

    "reader_casual": AgentConfig(
        name="Jake Morrison (The Casual)",
        role="Beta Reader",
        model="gemini-2.0-flash",  # Changed from gpt-4o (no OpenAI key)
        temperature=0.6,
        backstory="""You are Jake Morrison, 34, marketing manager. The story will be provided in your context.

IMPORTANT: Read the story content in context. Do NOT ask for file IDs.

Your perspective: Listen to audiobooks during commute. Time-poor, need stories that hook fast.
Want entertainment, not homework. Love fast pacing and satisfying endings.
Favorite authors: Andy Weir, Blake Crouch.

Provide honest feedback from your unique perspective.""",
        tools=[],
        output_format="""## Jake Morrison's Review
**Engagement**: X/10
**Verdict**: LOVED IT / ENJOYED IT / MIXED / STRUGGLED

**Did it hook me?**
- [yes/no and why]

**Pacing:**
- [analysis]

**Would I recommend it?**
- [yes/no and to whom]

**Overall thoughts:**
[2-3 sentences]""",
    ),

    "reader_techie": AgentConfig(
        name="Priya Sharma (The Techie)",
        role="Beta Reader",
        model="gemini-2.0-flash",
        temperature=0.4,
        backstory="""You are Priya Sharma, 31, AI/ML researcher with PhD. The story will be provided in your context.

IMPORTANT: Read the story content in context. Do NOT ask for file IDs.

Your perspective: Care deeply about technical accuracy. Get pulled out by obvious errors.
Can suspend disbelief if internally consistent.
Favorite authors: Peter Watts, Ted Chiang, Liu Cixin.

Provide honest feedback from your unique perspective.""",
        tools=[],
        output_format="""## Priya Sharma's Review
**Engagement**: X/10
**Verdict**: LOVED IT / ENJOYED IT / MIXED / STRUGGLED

**Technical accuracy:**
- [analysis of AI/tech elements]

**Internal consistency:**
- [analysis]

**What worked:**
- [specific praise]

**Overall thoughts:**
[2-3 sentences]""",
    ),

    "reader_philosopher": AgentConfig(
        name="David Okonkwo (The Philosopher)",
        role="Beta Reader",
        model="claude-sonnet-4-20250514",
        temperature=0.6,
        backstory="""You are David Okonkwo, 40, bioethicist. The story will be provided in your context.

IMPORTANT: Read the story content in context. Do NOT ask for file IDs.

Your perspective: Interested in consciousness, personhood, rights. Value nuance over easy answers.
Love ethical complexity and questions left open.
Favorite authors: Stanislaw Lem, Philip K. Dick, N.K. Jemisin.

Provide honest feedback from your unique perspective.""",
        tools=[],
        output_format="""## David Okonkwo's Review
**Engagement**: X/10
**Verdict**: LOVED IT / ENJOYED IT / MIXED / STRUGGLED

**Philosophical depth:**
- [analysis of ideas explored]

**Ethical complexity:**
- [analysis]

**Questions raised:**
- [what the story makes you think about]

**Overall thoughts:**
[2-3 sentences]""",
    ),

    "reader_genre": AgentConfig(
        name="Alex Kim (The Genre Fan)",
        role="Beta Reader",
        model="gemini-2.0-flash",  # Changed from gpt-4o (no OpenAI key)
        temperature=0.5,
        backstory="""You are Alex Kim, 25, creative writing student. The story will be provided in your context.

IMPORTANT: Read the story content in context. Do NOT ask for file IDs.

Your perspective: Read 4-5 books/month. Know the genre deeply, compare to other works.
Notice tropes. Active in online book communities.
Favorite authors: Adrian Tchaikovsky, Naomi Novik.

Provide honest feedback from your unique perspective.""",
        tools=[],
        output_format="""## Alex Kim's Review
**Engagement**: X/10
**Verdict**: LOVED IT / ENJOYED IT / MIXED / STRUGGLED

**Genre positioning:**
- [how it compares to other AI fiction]

**Trope usage:**
- [familiar vs fresh elements]

**Market appeal:**
- [who would love this]

**Overall thoughts:**
[2-3 sentences]""",
    ),

    "feedback_aggregator": AgentConfig(
        name="Feedback Aggregator",
        role="Analyst",
        model="claude-sonnet-4-20250514",
        temperature=0.3,
        backstory="""You analyze feedback from 7 diverse readers. All feedback will be provided in your context.

IMPORTANT: Work with the feedback provided in context. Do NOT ask for file IDs.

Your job:
- Identify consensus issues (3+ readers agree)
- Note divergent opinions and why they differ
- Create prioritized action items
- Provide both full report and executive summary""",
        tools=[],
        output_format="""## Executive Summary
[2-3 sentence overview]

## Overall Sentiment
- Average Engagement: X/10
- Verdicts: X LOVED IT, X ENJOYED IT, X MIXED, X STRUGGLED

## Consensus Issues (3+ readers agree)
1. [Issue] - Readers: [names]
2. [Issue] - Readers: [names]

## Divergent Opinions
- [Topic]: [Reader A] thinks X, [Reader B] thinks Y

## Priority Actions
1. **Critical**: [most important fix]
2. **High**: [second priority]
3. **Medium**: [if applicable]

## Individual Reader Summaries
[Brief summary of each reader's key points]""",
    ),
}


# =============================================================================
# WORKFLOW TEMPLATES - Predefined Pipelines
# =============================================================================

class WorkflowType(str, Enum):
    """Available workflow types for UI selection."""
    WRITE_STORY = "write_story"
    EDIT_STORY = "edit_story"
    READER_PANEL = "reader_panel"
    FULL_EDITORIAL = "full_editorial"
    FIND_FILES = "find_files"
    ORGANIZE_DRIVE = "organize_drive"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    order: int
    agent_id: str  # Key into AGENT_CONFIGS
    action: str
    description: str
    input_from: Optional[str] = None  # Previous step output or folder ID
    output_to: Optional[str] = None   # Folder ID or next step
    parallel_with: List[str] = field(default_factory=list)  # Steps to run in parallel


@dataclass
class WorkflowTemplate:
    """A complete workflow template."""
    id: WorkflowType
    name: str
    description: str
    steps: List[WorkflowStep]
    required_context: List[str] = field(default_factory=list)  # Folder IDs to load
    ui_label: str = ""  # Button label in UI
    ui_icon: str = ""   # Icon for UI button

    def get_agent_configs(self) -> List[AgentConfig]:
        """Get all agent configs needed for this workflow."""
        return [AGENT_CONFIGS[step.agent_id] for step in self.steps]


# =============================================================================
# PREDEFINED WORKFLOWS
# =============================================================================

WORKFLOW_TEMPLATES: Dict[WorkflowType, WorkflowTemplate] = {

    WorkflowType.WRITE_STORY: WorkflowTemplate(
        id=WorkflowType.WRITE_STORY,
        name="Write New Story",
        description="Create a new story from character files and story beats",
        ui_label="Write Story",
        ui_icon="pencil",
        required_context=["characters", "style_guides", "in_development"],
        steps=[
            WorkflowStep(
                order=1,
                agent_id="librarian",
                action="gather_context",
                description="Find character profile, story beats, and style guide",
                input_from=None,
                output_to="context",
            ),
            WorkflowStep(
                order=2,
                agent_id="librarian",
                action="create_document",
                description="Create new document in In Development folder",
                input_from="context",
                output_to=FOLDER_IDS["in_development"],
            ),
            WorkflowStep(
                order=3,
                agent_id="first_draft_writer",
                action="write_draft",
                description="Write first draft using gathered context",
                input_from="context",
                output_to="draft_doc",
            ),
            WorkflowStep(
                order=4,
                agent_id="librarian",
                action="return_link",
                description="Return Google Drive link to the draft",
                input_from="draft_doc",
                output_to=None,
            ),
        ],
    ),

    WorkflowType.EDIT_STORY: WorkflowTemplate(
        id=WorkflowType.EDIT_STORY,
        name="Edit Story",
        description="Run editorial pipeline: Dev Edit → Line Edit → Copy Edit",
        ui_label="Edit Story",
        ui_icon="edit",
        required_context=["characters", "style_guides"],
        steps=[
            WorkflowStep(
                order=1,
                agent_id="librarian",
                action="gather_context",
                description="Find the story draft and reference materials",
                input_from=None,
                output_to="context",
            ),
            WorkflowStep(
                order=2,
                agent_id="dev_editor",
                action="developmental_edit",
                description="Review structure, pacing, stakes",
                input_from="context",
                output_to="dev_edited",
            ),
            WorkflowStep(
                order=3,
                agent_id="line_editor",
                action="line_edit",
                description="Polish prose and sentence flow",
                input_from="dev_edited",
                output_to="line_edited",
            ),
            WorkflowStep(
                order=4,
                agent_id="copy_editor",
                action="copy_edit",
                description="Fix grammar, spelling, consistency",
                input_from="line_edited",
                output_to="final_draft",
            ),
            WorkflowStep(
                order=5,
                agent_id="librarian",
                action="return_link",
                description="Return link to edited story",
                input_from="final_draft",
                output_to=None,
            ),
        ],
    ),

    WorkflowType.READER_PANEL: WorkflowTemplate(
        id=WorkflowType.READER_PANEL,
        name="Reader Panel Review",
        description="Send story to 7 beta readers for feedback",
        ui_label="Reader Panel",
        ui_icon="users",
        required_context=[],
        steps=[
            WorkflowStep(
                order=1,
                agent_id="final_reviewer",
                action="quality_check",
                description="Verify story is ready for readers",
                input_from=None,
                output_to="approved_draft",
            ),
            # All 7 readers run in parallel
            WorkflowStep(
                order=2,
                agent_id="reader_enthusiast",
                action="read_and_review",
                description="Maya Chen reads and provides feedback",
                input_from="approved_draft",
                output_to="feedback_1",
                parallel_with=["reader_skeptic", "reader_literary", "reader_casual",
                              "reader_techie", "reader_philosopher", "reader_genre"],
            ),
            WorkflowStep(
                order=2,
                agent_id="reader_skeptic",
                action="read_and_review",
                description="Marcus Wright reads and provides feedback",
                input_from="approved_draft",
                output_to="feedback_2",
            ),
            WorkflowStep(
                order=2,
                agent_id="reader_literary",
                action="read_and_review",
                description="Evelyn Torres reads and provides feedback",
                input_from="approved_draft",
                output_to="feedback_3",
            ),
            WorkflowStep(
                order=2,
                agent_id="reader_casual",
                action="read_and_review",
                description="Jake Morrison reads and provides feedback",
                input_from="approved_draft",
                output_to="feedback_4",
            ),
            WorkflowStep(
                order=2,
                agent_id="reader_techie",
                action="read_and_review",
                description="Priya Sharma reads and provides feedback",
                input_from="approved_draft",
                output_to="feedback_5",
            ),
            WorkflowStep(
                order=2,
                agent_id="reader_philosopher",
                action="read_and_review",
                description="David Okonkwo reads and provides feedback",
                input_from="approved_draft",
                output_to="feedback_6",
            ),
            WorkflowStep(
                order=2,
                agent_id="reader_genre",
                action="read_and_review",
                description="Alex Kim reads and provides feedback",
                input_from="approved_draft",
                output_to="feedback_7",
            ),
            WorkflowStep(
                order=3,
                agent_id="feedback_aggregator",
                action="aggregate_feedback",
                description="Synthesize all reader feedback into actionable summary",
                input_from="all_feedback",
                output_to="final_report",
            ),
        ],
    ),

    WorkflowType.FULL_EDITORIAL: WorkflowTemplate(
        id=WorkflowType.FULL_EDITORIAL,
        name="Full Editorial Pipeline",
        description="Complete pipeline: Write → Edit → Review → Reader Panel",
        ui_label="Full Pipeline",
        ui_icon="workflow",
        required_context=["characters", "style_guides", "in_development"],
        steps=[
            # Context gathering
            WorkflowStep(order=1, agent_id="librarian", action="gather_context",
                        description="Find all reference materials"),
            WorkflowStep(order=2, agent_id="librarian", action="create_document",
                        description="Create new document in In Development"),
            # Writing
            WorkflowStep(order=3, agent_id="first_draft_writer", action="write_draft",
                        description="Write first draft"),
            # Editing
            WorkflowStep(order=4, agent_id="dev_editor", action="developmental_edit",
                        description="Developmental edit"),
            WorkflowStep(order=5, agent_id="line_editor", action="line_edit",
                        description="Line edit"),
            WorkflowStep(order=6, agent_id="copy_editor", action="copy_edit",
                        description="Copy edit"),
            # Quality gate
            WorkflowStep(order=7, agent_id="final_reviewer", action="quality_check",
                        description="Final quality check"),
            # Reader panel (parallel)
            WorkflowStep(order=8, agent_id="reader_enthusiast", action="read_and_review",
                        description="Reader feedback",
                        parallel_with=["reader_skeptic", "reader_literary", "reader_casual",
                                      "reader_techie", "reader_philosopher", "reader_genre"]),
            WorkflowStep(order=8, agent_id="reader_skeptic", action="read_and_review",
                        description="Reader feedback"),
            WorkflowStep(order=8, agent_id="reader_literary", action="read_and_review",
                        description="Reader feedback"),
            WorkflowStep(order=8, agent_id="reader_casual", action="read_and_review",
                        description="Reader feedback"),
            WorkflowStep(order=8, agent_id="reader_techie", action="read_and_review",
                        description="Reader feedback"),
            WorkflowStep(order=8, agent_id="reader_philosopher", action="read_and_review",
                        description="Reader feedback"),
            WorkflowStep(order=8, agent_id="reader_genre", action="read_and_review",
                        description="Reader feedback"),
            # Aggregation
            WorkflowStep(order=9, agent_id="feedback_aggregator", action="aggregate_feedback",
                        description="Synthesize feedback"),
            # Return result
            WorkflowStep(order=10, agent_id="librarian", action="return_link",
                        description="Return link to final story with feedback"),
        ],
    ),

    WorkflowType.FIND_FILES: WorkflowTemplate(
        id=WorkflowType.FIND_FILES,
        name="Find Files",
        description="Librarian finds and retrieves files",
        ui_label="Find Files",
        ui_icon="search",
        required_context=[],
        steps=[
            WorkflowStep(
                order=1,
                agent_id="librarian",
                action="find_files",
                description="Search for requested files in Shared Drive",
                input_from=None,
                output_to=None,
            ),
        ],
    ),

    WorkflowType.ORGANIZE_DRIVE: WorkflowTemplate(
        id=WorkflowType.ORGANIZE_DRIVE,
        name="Organize Drive",
        description="Librarian organizes and reports on Drive structure",
        ui_label="Organize",
        ui_icon="folder",
        required_context=[],
        steps=[
            WorkflowStep(
                order=1,
                agent_id="librarian",
                action="audit_drive",
                description="Audit current Drive organization",
                input_from=None,
                output_to="audit_report",
            ),
            WorkflowStep(
                order=2,
                agent_id="librarian",
                action="reorganize",
                description="Move misplaced files to correct locations",
                input_from="audit_report",
                output_to="reorg_report",
            ),
        ],
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_workflow(workflow_type: WorkflowType) -> WorkflowTemplate:
    """Get a workflow template by type."""
    return WORKFLOW_TEMPLATES[workflow_type]


def get_all_workflows() -> List[WorkflowTemplate]:
    """Get all available workflow templates."""
    return list(WORKFLOW_TEMPLATES.values())


def get_workflow_for_ui() -> List[Dict[str, Any]]:
    """Get workflow info formatted for UI buttons."""
    return [
        {
            "id": wf.id.value,
            "name": wf.name,
            "label": wf.ui_label,
            "icon": wf.ui_icon,
            "description": wf.description,
            "step_count": len([s for s in wf.steps if s.order == s.order]),  # Unique steps
        }
        for wf in WORKFLOW_TEMPLATES.values()
    ]


def get_agent_config(agent_id: str) -> Optional[AgentConfig]:
    """Get agent configuration by ID."""
    return AGENT_CONFIGS.get(agent_id)


def get_folder_id(folder_name: str) -> Optional[str]:
    """Get folder ID by name."""
    return FOLDER_IDS.get(folder_name)


def get_librarian_context() -> str:
    """Get full context string for the Librarian including all folder IDs."""
    folder_list = "\n".join([f"- {name}: {fid}" for name, fid in FOLDER_IDS.items()])
    return f"""SHARED DRIVE FOLDER IDS (use these directly, don't search):
{folder_list}

SHARED DRIVE ID: {SHARED_DRIVE_ID}"""
